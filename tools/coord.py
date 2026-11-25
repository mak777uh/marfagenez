"""Координация нескольких исследовательских агентов в ОБЩЕМ каталоге.

Полная версия после аудита 25.11.2026. Закрывает классы дефектов:

  1. Атомарность состояния   — все файлы через temp+fsync+replace (atomic_write).
  2. Взятие задачи           — двухфазное: сборка в скрытом tmp + один os.rename (commit-точка).
  3. Гонка проверки области  — общий замок `.coord/locks/coord.lock` на критические секции.
  4. Часы                    — всё время UTC, сравнение через calendar.timegm.
  5. Пустая область          — fail-closed: без области задачу брать нельзя.
  6. Проверка завершения     — close требует зелёный VERIFY.json; verify пишет протокол.
  7. Права                   — проверяются кодом: verify/close/release --force/maint — только main.

Плюс: heartbeat (os.utime на claim), boot_id (сменился = исполнитель мёртв),
recover для мусора после kill -9, статус-снапшот, сортировка очереди по приоритету.

Команды:
  register --agent main
  add --id ID --title "…" --area "glob" --accept "python3 checks/x.py" [--priority N]
      [--kind research|request|maint] [--standing] [--note "…"] [--agent main]
  list | take ID --agent X | heartbeat ID --agent X
  finish ID --agent X --artifacts path1 path2
  verify ID --agent main | close ID --agent main
  release ID --agent X --reason "…" [--force]
  stale | recover | status
"""

from __future__ import annotations

import argparse
import calendar
import re
import shlex
import contextlib
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
COORD = ROOT / ".coord"
PENDING = COORD / "pending"
ACTIVE = COORD / "active"
DONE = COORD / "completed"
EVENTS = COORD / "events"
AGENTS = COORD / "agents"
STANDING = COORD / "standing"
LOCKS = COORD / "locks"
GRAVEYARD = COORD / "graveyard"
GENS = COORD / "gens"
MAIL = COORD / "mail"
BOARD = COORD / "board.md"
MAIL_KINDS = ("note", "bug", "instruction", "question", "reply")

TTL_MIN = 180            # абсолютный предел жизни задачи
HEARTBEAT_TTL_MIN = 30   # без heartbeat столько минут — исполнитель считается мёртвым
LOCK_TTL_S = 120         # замок старше — ломаем (держится миллисекунды)
ACCEPT_TIMEOUT = 600     # точечные проверки, не гейт

PROTECTED = (
    "core/", "laws/", "verus/", "checks/", "run.sh", "AGENTS.md",
    "kg/nodes.jsonl", "kg/migrate.py", "kg/kg.py", "tools/coord.py",
)
TRIVIAL_ACCEPT = {"true", ":", "exit", "echo", ""}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
KINDS = ("research", "request", "maint")


def valid_id(value: str) -> str:
    """ID и имя агента — только безопасные символы: никаких `/`, `..`, пробелов."""
    if not isinstance(value, str) or not ID_RE.fullmatch(value) or value in (".", ".."):
        raise ValueError(f"недопустимый идентификатор: {value!r}")
    return value


# ---------------------------------------------------------------- утилиты

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_ts(s: str) -> float:
    """UTC-строка -> epoch. Именно timegm: mktime трактует UTC как локальное время."""
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def age_min(s: str) -> float:
    return (time.time() - parse_ts(s)) / 60


def boot_id() -> str:
    try:
        return pathlib.Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def sha(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    try:
        d = os.open(path.parent, os.O_RDONLY)
        os.fsync(d)
        os.close(d)
    except OSError:
        pass


def atomic_json(path: pathlib.Path, obj) -> None:
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def event(agent: str, text: str) -> None:
    EVENTS.mkdir(parents=True, exist_ok=True)
    base = time.strftime("%Y%m%dT%H%M%S")
    body = f"# {now()} — {agent}\n\n{text}\n"
    for n in range(1000):
        p = EVENTS / f"{base}-{os.getpid()}-{n:02d}-{agent}.md"
        try:
            with open(p, "x", encoding="utf-8") as f:
                f.write(body)
            return
        except FileExistsError:
            continue


@contextlib.contextmanager
def lock(timeout: float = 60.0):
    LOCKS.mkdir(parents=True, exist_ok=True)
    path = LOCKS / "coord.lock"
    t0 = time.time()
    while True:
        try:
            path.mkdir()
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > LOCK_TTL_S:
                    staled = path.with_name(f"coord.lock.stale-{os.getpid()}-{time.time_ns()}")
                    try:
                        os.rename(path, staled)   # ровно один ломатель
                        shutil.rmtree(staled, ignore_errors=True)
                    except OSError:
                        pass
                    continue
            except FileNotFoundError:
                continue
            if time.time() - t0 > timeout:
                raise TimeoutError("замок координации занят слишком долго")
            time.sleep(0.05)
    token = f"{os.getpid()}-{time.time_ns()}"
    try:
        atomic_json(path / "owner.json", {"pid": os.getpid(), "token": token, "at": now()})
        yield
    finally:
        # удаляем только СВОЙ замок: чужой (перехваченный) не трогаем
        try:
            owner = json.loads((path / "owner.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            owner = {}
        if owner.get("token") == token:
            shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------- области

def area_warning(areas: list[str]) -> str | None:
    """Предупреждение, если область объявлена слишком узко.

    День 25.11.2026: шесть задач пришлось перезаключать, потому что область перечисляла отдельные файлы и
    не покрывала каталог, в котором они лежат. Область — контракт «что не тронется чужое», а не список
    угаданных файлов.
    """
    if not areas:
        return "пустая рабочая область"
    broad = [a for a in areas if "*" in a or a.endswith("/") or a.count("/") == 0]
    if broad:
        return None
    if len(areas) <= 3:
        return ("область из отдельных файлов без шаблона или каталога: "
                + ", ".join(areas[:3])
                + ". Если работа исследовательская, объявите каталог или шаблон "
                  "(например, docs/FINDING-*.md вместо одного файла).")
    return None


def norm_area(area: str) -> str:
    a = area.strip().replace("\\", "/")
    if not a or a.startswith("/") or a.startswith("~"):
        raise ValueError(f"недопустимая область: {area!r}")
    n = os.path.normpath(a)
    if n in (".", "") or n.startswith(".."):
        raise ValueError(f"недопустимая область: {area!r}")
    return n


def overlap(mine: list[str], theirs: list[str]) -> list[str]:
    """Конфликт по литеральному префиксу (до `*`), без границы `/`: `docs/P*.md` ↔ `docs/PLAN.md`."""
    bad = []
    for m in mine:
        try:
            mp = norm_area(m).split("*")[0]
        except ValueError:
            bad.append(f"{m} (недопустимая)")
            continue
        for t in theirs:
            try:
                tp = norm_area(t).split("*")[0]
            except ValueError:
                continue
            if mp.startswith(tp) or tp.startswith(mp):
                bad.append(f"{m} ↔ {t}")
    return bad


def in_area(rel: str, areas: list[str]) -> bool:
    """Настоящая проверка «путь внутри области»: нормализация, запрет `..`, glob-match."""
    try:
        rel_n = norm_area(rel)
    except ValueError:
        return False
    for a in areas:
        try:
            a_n = norm_area(a)
        except ValueError:
            continue
        literal = a_n.split("*")[0]
        if "*" in a_n:
            import fnmatch
            if fnmatch.fnmatch(rel_n, a_n) or rel_n.startswith(literal.rstrip("/") + "/"):
                return True
        else:
            if rel_n == a_n or rel_n.startswith(a_n.rstrip("/") + "/"):
                return True
    return False


def protected(area: list[str]) -> list[str]:
    hit = []
    for a in area:
        try:
            ap = norm_area(a).split("*")[0]
        except ValueError:
            hit.append(a)
            continue
        for z in PROTECTED:
            zn = norm_area(z).split("*")[0]
            if ap.startswith(zn) or zn.startswith(ap):
                hit.append(a)
                break
    return hit


# ---------------------------------------------------------------- карточки

def parse_card(text: str) -> dict:
    out = {"title": "", "area": [], "accept": [], "kind": "research", "priority": 50,
           "standing": False}
    section = None
    for ln in text.splitlines():
        if ln.startswith("# "):
            out["title"] = ln[2:].strip()
            continue
        if ln.startswith("- вид:"):
            out["kind"] = ln.split("`")[1] if "`" in ln else "research"
        if ln.startswith("- постоянная: да"):
            out["standing"] = True
        if ln.startswith("- приоритет:"):
            try:
                out["priority"] = int(ln.split(":")[1].strip())
            except (ValueError, IndexError):
                pass
        if ln.startswith("## Рабочая область"):
            section = "area"
            continue
        if ln.startswith("## Критерии приёмки"):
            section = "accept"
            continue
        if ln.startswith("## ") and section is not None:
            section = None
            continue
        if section and ln.strip().startswith("- `") and ln.strip().endswith("`"):
            out[section].append(ln.strip()[3:-1])
    return out


def card_of(path: pathlib.Path) -> dict:
    return parse_card(path.read_text(encoding="utf-8"))


def task_card(task_id: str, title: str, area: str, accept: list[str], priority: int,
              author: str, note: str = "", kind: str = "research",
              standing: bool = False) -> str:
    lines = [
        f"# {task_id} — {title}",
        "",
        f"- автор: `{author}`",
        f"- вид: `{kind}`",
        f"- постоянная: {'да — не исчезает после закрытия' if standing else 'нет'}",
        f"- приоритет: {priority}",
        f"- создана: {now()}",
        "",
        "## Рабочая область (файлы, которые задача вправе менять/создавать)",
        "",
        *[f"- `{a}`" for a in area.split(",") if a.strip()],
        "",
        "## Что нужно сделать",
        "",
        note or "_(заполняет автор задачи)_",
        "",
        "## Критерии приёмки (прогоняет только main)",
        "",
        *[f"- `{c}`" for c in accept],
        "",
        "## Правила",
        "",
        "- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).",
        "- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.",
        "- Чужие активные области не редактируются; нужное вне области — отдельной задачей.",
        "- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- генерации

def next_gen(task_id: str) -> int:
    GENS.mkdir(parents=True, exist_ok=True)
    p = GENS / task_id
    n = 1
    if p.exists():
        try:
            n = int(p.read_text(encoding="utf-8").strip()) + 1
        except ValueError:
            n = 1
    atomic_write(p, f"{n}\n")
    return n


# ---------------------------------------------------------------- команды

def cmd_register(a) -> int:
    try:
        valid_id(a.agent)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    AGENTS.mkdir(parents=True, exist_ok=True)
    p = AGENTS / f"{a.agent}.md"
    if p.exists() and not a.force:
        print(f"агент {a.agent} уже зарегистрирован (--force для перезаписи)")
        return 1
    role = "основной; публикует изменения всех агентов" if a.agent == "main" else "исследовательский партнёр"
    limit = "—" if a.agent == "main" else \
        "Git не использует; не правит core/, laws/, verus/, checks/, run.sh, AGENTS.md, kg/nodes.jsonl"
    atomic_write(p, f"# Агент `{a.agent}`\n\n- роль: {role}\n- зарегистрирован: {now()}\n"
                    f"- права на очередь: полные\n- ограничения: {limit}\n")
    event(a.agent, "регистрация")
    print(f"зарегистрирован: {a.agent}")
    return 0


def accept_ok(cmds: list[str]) -> tuple[bool, str]:
    if not cmds:
        return False, "нет ни одной accept-команды"
    for c in cmds:
        t = c.strip()
        head = t.split()[0] if t.split() else ""
        if t in TRIVIAL_ACCEPT or head in TRIVIAL_ACCEPT:
            return False, f"тривиальная команда: {c!r}"
        if "/" not in t:
            return False, f"команда не ссылается на файл: {c!r}"
        if t.startswith("git ") or "rm -rf" in t:
            return False, f"запрещённая команда в accept: {c!r}"
        if any(tok in t for tok in (";", "&&", "||", "|", ">", "<", "`", "$(", "\n")):
            return False, f"shell-операторы в accept запрещены: {c!r}"
        try:
            argv = shlex.split(t)
        except ValueError:
            return False, f"не разбирается: {c!r}"
        if not argv[0].startswith("python3"):
            return False, f"accept разрешён только для python3: {c!r}"
    return True, ""


def cmd_add(a) -> int:
    try:
        valid_id(a.id)
        valid_id(a.agent)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    ok, why = accept_ok(a.accept)
    if not ok:
        print(f"ошибка: {why}")
        return 1
    try:
        areas = [norm_area(x) for x in a.area.split(",") if x.strip()]
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    if not areas:
        print("ошибка: пустая рабочая область")
        return 1
    with lock():
        d = PENDING / a.id
        if d.exists() or (ACTIVE / a.id).exists():
            print(f"ошибка: задача {a.id} уже существует")
            return 1
        d.mkdir(parents=True)
        atomic_write(d / "TASK.md", task_card(a.id, a.title, ",".join(areas), a.accept,
                                              a.priority, a.agent, a.note, a.kind, a.standing))
    event(a.agent, f"создана задача `{a.id}` ({a.kind}, приоритет {a.priority})")
    print(f"добавлено: {a.id}")
    warn = area_warning(areas)
    if warn:
        print(f"внимание: {warn}")
    return 0


def _active_claims() -> dict:
    out = {}
    if ACTIVE.exists():
        for p in ACTIVE.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                c = p / ".claim.json"
                if c.exists():
                    try:
                        out[p.name] = read_json(c)
                    except json.JSONDecodeError:
                        continue
    return out


def _blocking_claims() -> dict:
    """Активные задачи, которые действительно занимают область.

    Сданная задача (`DONE.json` есть, `VERIFY.json` ещё нет) остаётся в `active/`, потому что её нужно
    верифицировать, но **область она больше не держит**: иначе каждый сданный раунд создаёт принудительную
    паузу на всё время чужой верификации. Именно так `fast` простоял ~40 минут дважды за день.
    """
    out = {}
    for name, claim in _active_claims().items():
        if (ACTIVE / name / "DONE.json").exists():
            continue
        out[name] = claim
    return out


def cmd_list(_a) -> int:
    for name, base in (("pending", PENDING), ("active", ACTIVE), ("completed", DONE)):
        if not base.exists():
            continue
        items = [p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if name == "pending":
            items.sort(key=lambda p: (card_of(p / "TASK.md").get("priority", 50), p.name))
        print(f"\n== {name}: {len(items)}")
        for p in items:
            if name == "completed":
                print(f"  {p.parent.name}/{p.name}")
                continue
            t = p / "TASK.md"
            card = card_of(t) if t.exists() else {}
            extra = ""
            if name == "active":
                c = p / ".claim.json"
                if c.exists():
                    j = read_json(c)
                    hb = (time.time() - c.stat().st_mtime) / 60
                    extra = (f" [agent={j.get('agent')}, gen={j.get('gen')}, "
                             f"возраст={age_min(j.get('taken_at')):.0f}м, hb={hb:.0f}м]")
                if (p / "DONE.json").exists():
                    extra += " DONE"
                if (p / "VERIFY.json").exists():
                    extra += (" VERIFY-ok" if read_json(p / "VERIFY.json").get("ok") else " VERIFY-FAIL")
            print(f"  {p.name}: {card.get('title', p.name)}{extra}")
    return 0


def cmd_take(a) -> int:
    try:
        valid_id(a.id)
        valid_id(a.agent)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    if not (AGENTS / f"{a.agent}.md").exists():
        print("ошибка: агент не зарегистрирован (`register --agent …`)")
        return 1
    with lock():
        src = PENDING / a.id
        t = src / "TASK.md"
        if not t.exists():
            print(f"ошибка: {a.id} нет в pending")
            return 1
        card = card_of(t)
        if not card["area"]:
            print("ошибка: у карточки пустая рабочая область — брать нельзя")
            return 1
        try:
            areas = [norm_area(x) for x in card["area"]]
        except ValueError as e:
            print(f"ошибка: {e}")
            return 1
        for other, claim in _blocking_claims().items():
            bad = overlap(areas, claim.get("area") or [])
            if bad:
                print(f"ошибка: область пересекается с активной {other} "
                      f"(агент {claim.get('agent')}): {bad}")
                return 1
        if protected(areas) and a.agent != "main":
            print(f"ошибка: защищённые зоны правит только main: {protected(areas)}")
            return 1
        if card["kind"] == "maint" and a.agent != "main":
            print("ошибка: задачи вида maint берёт только main")
            return 1
        standing = card["standing"]
        if standing:
            running = [r for r, c in _blocking_claims().items()
                       if c.get("parent") == a.id and not (ACTIVE / r / "DONE.json").exists()]
            if running:
                print(f"ошибка: раунд постоянной задачи уже идёт: {running[0]}")
                return 1
            round_id = f"{a.id}-{time.strftime('%Y%m%dT%H%M%S')}-{a.agent}"
        else:
            round_id = a.id
        dst = ACTIVE / round_id
        if dst.exists():
            print(f"ошибка: {round_id} уже взята")
            return 1
        gen = next_gen(a.id)
        tmp = ACTIVE / f".take-{a.id}-{os.getpid()}"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        shutil.copy2(t, tmp / "TASK.md")
        atomic_json(tmp / ".claim.json", {
            "agent": a.agent, "taken_at": now(), "task_sha256": sha(tmp / "TASK.md"),
            "area": areas, "kind": card["kind"], "priority": card["priority"],
            "gen": gen, "boot_id": boot_id(), "parent": a.id if standing else None,
            "standing": standing,
        })
        os.rename(tmp, dst)          # единственная commit-точка
        if not standing:
            shutil.rmtree(src, ignore_errors=True)
    unread = len(_iter_mail(a.agent, "new"))
    event(a.agent, f"взята задача `{round_id}` (gen={gen})")
    if unread:
        print(f"внимание: {unread} непрочитанных писем — `python3 tools/coord.py inbox --agent {a.agent}`")
    print(f"взято: {round_id}" + (" (постоянная карточка осталась в pending)" if standing else ""))
    return 0


def cmd_heartbeat(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print("ошибка: задача не активна")
        return 1
    claim = read_json(d / ".claim.json")
    if claim.get("agent") != a.agent:
        print(f"ошибка: задача у агента {claim.get('agent')}")
        return 1
    os.utime(d / ".claim.json")
    atomic_json(d / "HEARTBEAT.json", {"ts": now(), "boot_id": boot_id(), "gen": claim.get("gen")})
    print(f"heartbeat: {a.id}")
    return 0


def cmd_finish(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print("ошибка: задача не активна")
        return 1
    claim = read_json(d / ".claim.json")
    if claim.get("agent") != a.agent:
        print(f"ошибка: задача у агента {claim.get('agent')}")
        return 1
    if sha(d / "TASK.md") != claim.get("task_sha256"):
        print("ошибка: TASK.md изменён после взятия — запрещено")
        return 1
    if not (d / "RESULT.md").exists():
        print("ошибка: нет RESULT.md")
        return 1
    arts = []
    for rel in (a.artifacts or []):
        q = ROOT / rel
        if not q.exists():
            print(f"ошибка: артефакт не существует: {rel}")
            return 1
        if not in_area(rel, claim.get("area") or []):
            print(f"ошибка: артефакт вне рабочей области: {rel}")
            return 1
        arts.append({"path": rel, "sha256": sha(q), "bytes": q.stat().st_size})
    atomic_json(d / "DONE.json", {
        "task": a.id, "agent": a.agent, "gen": claim.get("gen"), "finished_at": now(),
        "artifacts": arts, "self_report": "RESULT.md", "checks": [],
    })
    event(a.agent, f"завершение заявлено `{a.id}` (gen={claim.get('gen')}, артефактов {len(arts)})")
    print(f"заявка принята: {a.id} (закрывает main после verify)")
    return 0


def _verify_fail(d: pathlib.Path, reason: str) -> int:
    atomic_json(d / "VERIFY.json", {"ok": False, "reason": reason, "verified_at": now()})
    print(f"verify: красный ({reason})")
    return 1


def cmd_verify(a) -> int:
    if a.agent != "main":
        print("ошибка: verify выполняет только main")
        return 1
    d = ACTIVE / a.id
    if not d.exists():
        print("ошибка: задача не активна")
        return 1
    if not (d / "DONE.json").exists():
        return _verify_fail(d, "нет DONE.json")
    claim = read_json(d / ".claim.json")
    if sha(d / "TASK.md") != claim.get("task_sha256"):
        return _verify_fail(d, "TASK.md изменён после взятия")
    card = card_of(d / "TASK.md")
    if not card["accept"]:
        return _verify_fail(d, "нет критериев приёмки")
    okc, why = accept_ok(card["accept"])
    if not okc:
        return _verify_fail(d, f"недопустимая accept-команда: {why}")
    done = read_json(d / "DONE.json")
    bad_art = [art["path"] for art in (done.get("artifacts") or [])
               if not (ROOT / art["path"]).exists() or sha(ROOT / art["path"]) != art["sha256"]]
    results = []
    for c in card["accept"]:
        argv = shlex.split(c)
        try:
            r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                               timeout=ACCEPT_TIMEOUT)
        except subprocess.TimeoutExpired:
            results.append({"cmd": c, "rc": 124, "tail": "timeout"})
            print(f"[ПРОВАЛ] {c}: timeout")
            continue
        except FileNotFoundError:
            results.append({"cmd": c, "rc": 127, "tail": "команда не найдена"})
            print(f"[ПРОВАЛ] {c}: команда не найдена")
            continue
        results.append({"cmd": c, "rc": r.returncode,
                        "tail": "\n".join((r.stdout or r.stderr).strip().splitlines()[-3:])})
        print(f"[{'ok' if r.returncode == 0 else 'ПРОВАЛ'}] {c}")
    ok = all(x["rc"] == 0 for x in results) and not bad_art
    atomic_json(d / "VERIFY.json", {
        "ok": ok, "task_sha256": claim.get("task_sha256"),
        "done_sha256": sha(d / "DONE.json"), "gen": claim.get("gen"),
        "verified_at": now(), "by": a.agent, "results": results, "bad_artifacts": bad_art,
    })
    if bad_art:
        print(f"ПРОВАЛ: артефакты изменены после заявки: {bad_art}")
    print("verify:", "зелёный" if ok else "красный")
    return 0 if ok else 1


def cmd_close(a) -> int:
    if a.agent != "main":
        print("ошибка: close выполняет только main")
        return 1
    with lock():
        d = ACTIVE / a.id
        if not d.exists():
            print("ошибка: задача не активна")
            return 1
        if not (d / "DONE.json").exists():
            print("ошибка: нет DONE.json")
            return 1
        v = d / "VERIFY.json"
        if not v.exists():
            print("ошибка: нет VERIFY.json — сначала `verify`")
            return 1
        ver = read_json(v)
        claim = read_json(d / ".claim.json")
        if not ver.get("ok"):
            print("ошибка: VERIFY.json не зелёный")
            return 1
        if ver.get("task_sha256") != claim.get("task_sha256") or ver.get("gen") != claim.get("gen"):
            print("ошибка: VERIFY.json от другой версии задачи")
            return 1
        if sha(d / "TASK.md") != claim.get("task_sha256"):
            print("ошибка: TASK.md изменён после verify")
            return 1
        done = read_json(d / "DONE.json")
        if ver.get("done_sha256") and ver["done_sha256"] != sha(d / "DONE.json"):
            print("ошибка: DONE.json изменён после verify")
            return 1
        bad = [x["path"] for x in (done.get("artifacts") or [])
               if not (ROOT / x["path"]).exists() or sha(ROOT / x["path"]) != x["sha256"]]
        if bad:
            print(f"ошибка: артефакты изменены после verify: {bad}")
            return 1
        month = time.strftime("%Y-%m")
        target = DONE / month / a.id
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target = DONE / month / f"{a.id}-gen{claim.get('gen')}"
        os.rename(d, target)
    event("main", f"закрыта задача `{a.id}` → completed/{month}/")
    print(f"закрыто: {a.id} → .coord/completed/{month}/{a.id}")
    return 0


def cmd_drop(a) -> int:
    """Убрать НЕВЗЯТУЮ задачу из очереди (карточка сохраняется в graveyard).

    Зачем: задача иногда теряет смысл — работа сделана в другом раунде, или карточка была тестовой.
    `close` требует DONE.json и не годится; без `drop` такая карточка висит вечно и её подхватывает другой
    агент: ровно это случилось с тестовой `P63-area-broad`, которую выполнил `fast` (цикл 636).
    """
    with lock():
        d = PENDING / a.id
        if not d.exists():
            print(f"ошибка: нет задачи {a.id} в pending (взятые задачи не удаляются)")
            return 1
        card = d / "TASK.md"
        text = card.read_text(encoding="utf-8") if card.exists() else ""
        save = GRAVEYARD / (time.strftime("%Y%m%dT%H%M%S") + f"-{a.id}.md")
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text(text + f"\n\n---\nубрана: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
                              f"\nпричина: {a.reason}\n", encoding="utf-8")
        shutil.rmtree(d)
    event(a.agent, f"задача `{a.id}` убрана из очереди: {a.reason}")
    print(f"убрано: {a.id} → {save.relative_to(ROOT)}")
    return 0


def cmd_release(a) -> int:
    with lock():
        return _release_locked(a)


def _release_locked(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print("ошибка: задача не активна")
        return 1
    claim = read_json(d / ".claim.json")
    if a.force and a.agent != "main":
        print("ошибка: release --force разрешён только main")
        return 1
    if claim.get("agent") != a.agent and not a.force:
        print("ошибка: отпустить может только исполнитель (или main с --force)")
        return 1
    hb_min = (time.time() - (d / ".claim.json").stat().st_mtime) / 60
    same_boot = claim.get("boot_id") == boot_id()
    if a.force and same_boot and hb_min < HEARTBEAT_TTL_MIN:
        print(f"ошибка: исполнитель жив (heartbeat {hb_min:.0f} мин назад) — force запрещён")
        return 1
    with lock():
        standing = bool(claim.get("standing"))
        GRAVEYARD.mkdir(parents=True, exist_ok=True)
        grave = GRAVEYARD / f"{d.name}-gen{claim.get('gen')}-{time.strftime('%Y%m%dT%H%M%S')}"
        if not standing:
            src_pending = PENDING / (claim.get("parent") or a.id)
            src_pending.mkdir(parents=True, exist_ok=True)
            atomic_write(src_pending / "TASK.md", (d / "TASK.md").read_text(encoding="utf-8"))
        os.rename(d, grave)
    event(a.agent, f"отпущена `{a.id}`: {a.reason} (heartbeat {hb_min:.0f} мин, boot совпал: {same_boot})")
    print(f"отпущено: {a.id} → graveyard; карточка "
          f"{'не тронута (постоянная)' if claim.get('standing') else 'возвращена в pending'}")
    return 0


def cmd_stale(_a) -> int:
    claims = _active_claims()
    bad = 0
    for task, c in sorted(claims.items()):
        d = ACTIVE / task
        hb = (time.time() - (d / ".claim.json").stat().st_mtime) / 60
        a = age_min(c.get("taken_at", now()))
        flags = []
        if c.get("boot_id") != boot_id():
            flags.append("boot сменился — исполнитель мёртв")
        if hb > HEARTBEAT_TTL_MIN:
            flags.append(f"нет heartbeat {hb:.0f} мин")
        if a > TTL_MIN:
            flags.append(f"возраст {a:.0f} мин")
        if flags:
            bad += 1
            print(f"просрочена: {task} (агент {c.get('agent')}, gen {c.get('gen')}): " + "; ".join(flags))
    if ACTIVE.exists():
        for p in ACTIVE.iterdir():
            if p.is_dir() and not p.name.startswith(".") and not (p / ".claim.json").exists():
                bad += 1
                print(f"сирота без .claim.json: {p.name} (лечится `recover`)")
    if bad == 0:
        print(f"просроченных нет (heartbeat TTL {HEARTBEAT_TTL_MIN} мин, предельный возраст {TTL_MIN} мин)")
    return 0


def cmd_recover(a) -> int:
    if a.agent != "main":
        print("ошибка: recover выполняет только main")
        return 1
    GRAVEYARD.mkdir(parents=True, exist_ok=True)
    moved = 0
    if ACTIVE.exists():
        for p in list(ACTIVE.glob(".take-*")):
            if time.time() - p.stat().st_mtime > 300:
                shutil.rmtree(p, ignore_errors=True)
                print(f"удалён мусор взятия: {p.name}")
        for p in list(ACTIVE.iterdir()):
            if p.is_dir() and not p.name.startswith(".") and not (p / ".claim.json").exists():
                target = GRAVEYARD / f"crashed-{time.strftime('%Y%m%dT%H%M%S')}-{p.name}"
                os.rename(p, target)
                moved += 1
                print(f"сирота убрана в graveyard: {p.name}")
    if LOCKS.exists():
        for l in list(LOCKS.iterdir()):
            if time.time() - l.stat().st_mtime > 600:
                shutil.rmtree(l, ignore_errors=True)
                print(f"снят замок-сирота: {l.name}")
    print(f"recover: сирот перенесено {moved}")
    return 0


def cmd_status(_a) -> int:
    lines = [f"# Статус координации — {now()}", ""]
    pend = sorted([p for p in PENDING.iterdir() if p.is_dir()], key=lambda p: p.name) \
        if PENDING.exists() else []
    lines += [f"## Свободные задачи: {len(pend)}", ""]
    for p in pend:
        c = card_of(p / "TASK.md")
        lines.append(f"- `{p.name}` ({c['kind']}, приоритет {c['priority']}): {c['title']}")
    claims = _active_claims()
    lines += ["", f"## Активные: {len(claims)}", ""]
    for task, c in sorted(claims.items()):
        d = ACTIVE / task
        hb = (time.time() - (d / ".claim.json").stat().st_mtime) / 60
        lines.append(f"- `{task}`: агент {c.get('agent')}, gen {c.get('gen')}, "
                     f"возраст {age_min(c.get('taken_at')):.0f}м, heartbeat {hb:.0f}м, "
                     f"DONE={(d / 'DONE.json').exists()}, VERIFY={(d / 'VERIFY.json').exists()}")
    if MAIL.exists():
        lines += ["", "## Непрочитанная почта", ""]
        for d in sorted(MAIL.iterdir()):
            if d.is_dir():
                lines.append(f"- `{d.name}`: {len(_iter_mail(d.name, 'new'))}")
    out = "\n".join(lines) + "\n"
    atomic_write(COORD / "STATUS.md", out)
    print(out)
    return 0


# ---------------------------------------------------------------- почта агентов

def _mail_dir(agent: str, box: str = "new") -> pathlib.Path:
    d = MAIL / agent / box
    d.mkdir(parents=True, exist_ok=True)
    return d


def _msg_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S") + f"-{os.getpid():05d}"


def cmd_note(a) -> int:
    """Письмо другому агенту (или всем). Лежит в его inbox, ничего не затирает."""
    try:
        valid_id(a.agent)
        if a.to != "all":
            valid_id(a.to)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    if not (AGENTS / f"{a.agent}.md").exists():
        print("ошибка: ты не зарегистрирован (`register --agent …`)")
        return 1
    if a.kind not in MAIL_KINDS:
        print(f"ошибка: вид сообщения {a.kind!r} не из {MAIL_KINDS}")
        return 1
    body = a.text or sys.stdin.read()
    if not body.strip():
        print("ошибка: пустое сообщение")
        return 1
    mid = _msg_id()
    header = [
        f"# {a.topic or '(без темы)'}",
        "",
        f"- id: `{mid}`",
        f"- от: `{a.agent}`",
        f"- кому: `{a.to}`",
        f"- вид: `{a.kind}`",
        f"- время: {now()}",
    ]
    if a.ref:
        header.append(f"- про: {a.ref}")
    header += ["", "---", "", body.rstrip(), ""]
    text = "\n".join(header)

    targets = [a.to] if a.to != "all" else [p.stem for p in AGENTS.glob("*.md") if p.stem != a.agent]
    for t in targets:
        atomic_write(_mail_dir(t, "new") / f"{mid}-{a.agent}.md", text)
    event(a.agent, f"письмо `{mid}` → {a.to} ({a.kind}): {a.topic or 'без темы'}")
    print(f"отправлено: {mid} → {', '.join(targets)}")
    return 0


def _iter_mail(agent: str, box: str):
    d = MAIL / agent / box
    if not d.exists():
        return []
    return sorted(d.glob("*.md"))


def cmd_inbox(a) -> int:
    try:
        valid_id(a.agent)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    boxes = ["new"] if not a.all else ["new", "read"]
    total = 0
    for box in boxes:
        msgs = _iter_mail(a.agent, box)
        total += len(msgs)
        if not msgs:
            continue
        print(f"\n== {a.agent}/{box}: {len(msgs)}")
        for m in msgs:
            head = m.read_text(encoding="utf-8").splitlines()
            topic = head[0][2:].strip() if head else m.name
            meta = " | ".join(ln[2:] for ln in head[1:8] if ln.startswith("- "))
            print(f"  {m.name}")
            print(f"    {topic}")
            if a.verbose:
                print(f"    {meta}")
    if total == 0:
        print(f"пусто: у {a.agent} нет писем")
    return 0


def cmd_read(a) -> int:
    try:
        valid_id(a.agent)
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    src = MAIL / a.agent / "new" / a.msg
    if not src.exists():
        print(f"ошибка: нет письма {a.msg} в новом")
        return 1
    if a.print:
        print(src.read_text(encoding="utf-8"))
    dst = MAIL / a.agent / "read" / a.msg
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dst)
    print(f"прочитано: {a.msg}")
    return 0


def cmd_board(a) -> int:
    """Общая доска: то, что должен увидеть каждый (поломки, запреты, договорённости)."""
    with lock():
        BOARD.parent.mkdir(parents=True, exist_ok=True)
        entry = f"\n## {now()} — {a.agent}\n\n{a.text}\n"
        if BOARD.exists():
            atomic_write(BOARD, BOARD.read_text(encoding="utf-8").rstrip() + "\n" + entry)
        else:
            atomic_write(BOARD, "# Доска координации\n" + entry)
    event(a.agent, f"запись на доску: {a.text.splitlines()[0][:80]}")
    print("записано на доску")
    return 0


def cmd_unread(_a) -> int:
    """Сколько непрочитанного у каждого агента — для status и быстрой проверки."""
    if not MAIL.exists():
        print("почты нет")
        return 0
    for d in sorted(MAIL.iterdir()):
        if d.is_dir():
            n = len(_iter_mail(d.name, "new"))
            print(f"{d.name}: {n}")
    return 0


# ---------------------------------------------------------------- CLI

def main(argv: list[str]) -> int:
    for d in (PENDING, ACTIVE, DONE, EVENTS, AGENTS, STANDING, LOCKS, GRAVEYARD, GENS):
        d.mkdir(parents=True, exist_ok=True)
    ap = argparse.ArgumentParser(prog="coord")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register"); p.add_argument("--agent", required=True)
    p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_register)

    p = sub.add_parser("add")
    p.add_argument("--id", required=True); p.add_argument("--title", required=True)
    p.add_argument("--area", required=True); p.add_argument("--accept", action="append", default=[])
    p.add_argument("--priority", type=int, default=50); p.add_argument("--agent", default="main")
    p.add_argument("--note", default="")
    p.add_argument("--kind", default="research", choices=list(KINDS))
    p.add_argument("--standing", action="store_true"); p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("take"); p.add_argument("id"); p.add_argument("--agent", required=True)
    p.set_defaults(fn=cmd_take)
    p = sub.add_parser("heartbeat"); p.add_argument("id"); p.add_argument("--agent", required=True)
    p.set_defaults(fn=cmd_heartbeat)
    p = sub.add_parser("finish"); p.add_argument("id"); p.add_argument("--agent", required=True)
    p.add_argument("--artifacts", nargs="*", default=[]); p.set_defaults(fn=cmd_finish)
    p = sub.add_parser("verify"); p.add_argument("id"); p.add_argument("--agent", default="main")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("close"); p.add_argument("id"); p.add_argument("--agent", default="main")
    p.set_defaults(fn=cmd_close)
    p = sub.add_parser("release"); p.add_argument("id"); p.add_argument("--agent", required=True)
    pd = sub.add_parser("drop"); pd.add_argument("id"); pd.add_argument("--agent", required=True); pd.add_argument("--reason", required=True); pd.set_defaults(fn=cmd_drop)
    p.add_argument("--reason", default=""); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_release)
    p = sub.add_parser("stale"); p.set_defaults(fn=cmd_stale)
    p = sub.add_parser("recover"); p.add_argument("--agent", default="main"); p.set_defaults(fn=cmd_recover)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("note")
    p.add_argument("--agent", required=True, help="кто пишет")
    p.add_argument("--to", required=True, help="кому (имя агента или all)")
    p.add_argument("--text", default="", help="текст; если пусто — читается stdin")
    p.add_argument("--topic", default=""); p.add_argument("--ref", default="")
    p.add_argument("--kind", default="note", choices=list(MAIL_KINDS))
    p.set_defaults(fn=cmd_note)

    p = sub.add_parser("inbox"); p.add_argument("--agent", required=True)
    p.add_argument("--all", action="store_true"); p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_inbox)

    p = sub.add_parser("read"); p.add_argument("msg"); p.add_argument("--agent", required=True)
    p.add_argument("--print", dest="print", action="store_true"); p.set_defaults(fn=cmd_read)

    p = sub.add_parser("board"); p.add_argument("--agent", required=True)
    p.add_argument("--text", required=True); p.set_defaults(fn=cmd_board)

    p = sub.add_parser("unread"); p.set_defaults(fn=cmd_unread)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except TimeoutError as e:
        print(f"ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
