"""Координация двух-трёх исследовательских агентов в общем каталоге.

Файлы (всё внутри `.coord/`):
  agents/<name>.md        регистрация агента
  pending/<ID>/TASK.md    свободная задача (менять можно)
  active/<ID>/TASK.md     взятая задача (неизменяема; хранится sha256 в .claim.json)
  active/<ID>/RESULT.md   результат (пишет только исполнитель)
  active/<ID>/DONE.json   заявка о завершении + артефакты + проверки
  completed/<ID>/...      закрытая задача (переносит основной агент после проверки)
  events/<ts>-<agent>.md  журнал событий (только добавление)

Атомарность: взятие задачи — это `os.mkdir(.coord/active/<ID>)`; mkdir атомарен на одной ФС,
поэтому из двух одновременных попыток успешна ровно одна.

Команды:
  python3 tools/coord.py add --id ID --title "…" --area "glob" --accept "cmd" [--priority N]
  python3 tools/coord.py list
  python3 tools/coord.py take ID --agent fast
  python3 tools/coord.py finish ID --agent fast
  python3 tools/coord.py verify ID          # основной агент: прогнать accept-команды
  python3 tools/coord.py close ID           # после проверки: active -> completed
  python3 tools/coord.py stale              # показать задачи, просроченные по TTL
  python3 tools/coord.py release ID --agent fast --reason "…"   # добровольный отказ
"""

from __future__ import annotations

import argparse
import calendar
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
TTL_MIN = 180  # через сколько минут задача считается «зависшей»

# Зоны контракта состояния: их правит только main, иначе ломается checks/agents и гейт.
PROTECTED = (
    "core/", "laws/", "verus/", "checks/", "run.sh", "AGENTS.md",
    "kg/nodes.jsonl", "kg/migrate.py", "kg/kg.py", "tools/coord.py",
)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def event(agent: str, text: str) -> None:
    """Событие не должно теряться: имя уникально, запись атомарна через O_EXCL."""
    EVENTS.mkdir(parents=True, exist_ok=True)
    base = time.strftime("%Y%m%dT%H%M%S")
    stamp = f"{now()} — {agent}\n\n{text}\n"
    for n in range(1000):
        p = EVENTS / f"{base}-{os.getpid()}-{n:02d}-{agent}.md"
        try:
            with open(p, "x", encoding="utf-8") as f:
                f.write(stamp)
            return
        except FileExistsError:
            continue


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
        "## Критерии приёмки (команды, которые обязан прогнать основной агент)",
        "",
        *[f"- `{c}`" for c in accept],
        "",
        "## Правила",
        "",
        "- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (проверяется по sha256).",
        "- Результат — `RESULT.md` и `DONE.json` в каталоге задачи.",
        "- Чужие активные области не редактируются; нужные файлы вне области оформляются отдельной задачей.",
        "",
    ]
    return "\n".join(lines)


TRIVIAL_ACCEPT = ("true", ":", "exit 0", "echo", "")


def _accept_ok(cmds: list[str]) -> tuple[bool, str]:
    if not cmds:
        return False, "нет ни одной accept-команды"
    for c in cmds:
        t = c.strip()
        if t in TRIVIAL_ACCEPT or t.split()[0] in TRIVIAL_ACCEPT:
            return False, f"тривиальная команда: {c!r}"
        if "/" not in t:
            return False, f"команда не ссылается на файл: {c!r}"
    return True, ""


def cmd_add(a) -> int:
    ok, why = _accept_ok(a.accept)
    if not ok:
        print(f"ошибка: {why}")
        return 1
    d = PENDING / a.id
    if d.exists() or (ACTIVE / a.id).exists() or (DONE / a.id).exists():
        print(f"ошибка: задача {a.id} уже существует")
        return 1
    d.mkdir(parents=True)
    (d / "TASK.md").write_text(
        task_card(a.id, a.title, a.area, a.accept, a.priority, a.agent, a.note, a.kind,
                  a.standing),
        encoding="utf-8")
    event(a.agent, f"создана задача `{a.id}` — {a.title}")
    print(f"добавлено: {a.id}")
    return 0


def cmd_list(_a) -> int:
    for name, base in (("pending", PENDING), ("active", ACTIVE), ("completed", DONE)):
        if not base.exists():
            continue
        items = sorted(p for p in base.iterdir() if p.is_dir())
        print(f"\n== {name}: {len(items)}")
        for p in items:
            t = (p / "TASK.md")
            title = ""
            if t.exists():
                title = t.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            extra = ""
            if name == "active":
                c = p / ".claim.json"
                if c.exists():
                    j = json.loads(c.read_text(encoding="utf-8"))
                    extra = f" [agent={j.get('agent')}, taken={j.get('taken_at')}]"
                if (p / "DONE.json").exists():
                    extra += " DONE-заявка"
            kind = ""
            if t.exists():
                for ln in t.read_text(encoding="utf-8").splitlines()[:6]:
                    if ln.startswith("- вид:"):
                        kind = f" [{ln.split('`')[1]}]"
            print(f"  {p.name}: {title}{kind}{extra}")
    return 0


def _active_areas() -> dict[str, tuple[str, list[str]]]:
    out = {}
    if not ACTIVE.exists():
        return out
    for p in ACTIVE.iterdir():
        if not p.is_dir():
            continue
        c = p / ".claim.json"
        if c.exists():
            j = json.loads(c.read_text(encoding="utf-8"))
            out[p.name] = (j.get("agent", "?"), j.get("area") or [])
    return out


def _norm_area(area: str) -> str:
    """Нормализует запись области; отказ на абсолютные пути, `..` и пустые записи."""
    a = area.strip().replace("\\", "/")
    if not a or a.startswith("/") or a.startswith("~"):
        raise ValueError(f"недопустимая область: {area!r}")
    n = os.path.normpath(a)
    if n in (".", "") or n.startswith(".."):
        raise ValueError(f"недопустимая область: {area!r}")
    return n


def _overlap(mine: list[str], theirs: list[str]) -> list[str]:
    """Пересечение по литеральному префиксу (до первого `*`).

    Граница `/` НЕ требуется: `docs/P*.md` должен конфликтовать с `docs/PLAN.md`.
    Цена — редкие ложные срабатывания (`core/bin` ↔ `core/binutils`); отказ безопаснее пропуска.
    """
    bad = []
    for m in mine:
        mp = _norm_area(m).split("*")[0]
        for t in theirs:
            tp = _norm_area(t).split("*")[0]
            if mp.startswith(tp) or tp.startswith(mp):
                bad.append(f"{m} ↔ {t}")
    return bad


def _protected(area: list[str]) -> list[str]:
    hit = []
    for a in area:
        try:
            ap = _norm_area(a).split("*")[0]
        except ValueError:
            hit.append(a)
            continue
        for z in PROTECTED:
            zn = _norm_area(z).split("*")[0]
            if ap.startswith(zn) or zn.startswith(ap):
                hit.append(a)
                break
    return hit


def cmd_take(a) -> int:
    src = PENDING / a.id
    dst = ACTIVE / a.id
    if not src.exists():
        print(f"ошибка: {a.id} нет в pending")
        return 1
    area = _area_of(src / "TASK.md")
    if not area:
        print("ошибка: у карточки пустая рабочая область — брать нельзя")
        return 1
    try:
        area = [_norm_area(x) for x in area]
    except ValueError as e:
        print(f"ошибка: {e}")
        return 1
    busy = _active_areas()
    for other, (agent, other_area) in busy.items():
        bad = _overlap(area, other_area)
        if bad:
            print(f"ошибка: область пересекается с активной {other} (агент {agent}): {bad}")
            return 1
    prot = _protected(area)
    if prot and a.agent != "main":
        print(f"ошибка: защищённые зоны правит только main: {prot}")
        return 1
    card = (src / "TASK.md").read_text(encoding="utf-8")
    if "- вид: `maint`" in card and a.agent != "main":
        print("ошибка: задачи вида maint берёт только main")
        return 1
    txt = (src / "TASK.md").read_text(encoding="utf-8")
    standing = "- постоянная: да" in txt
    if standing:
        # Постоянная задача остаётся в pending: каждое взятие — отдельный раунд со своим каталогом.
        round_id = f"{a.id}-{time.strftime('%Y%m%dT%H%M%S')}"
        dst = ACTIVE / round_id
        try:
            dst.mkdir(parents=True)
        except FileExistsError:
            print(f"ошибка: раунд {round_id} уже существует")
            return 1
        shutil.copy2(src / "TASK.md", dst / "TASK.md")
        (dst / ".claim.json").write_text(json.dumps({
            "agent": a.agent, "taken_at": now(), "task_sha256": sha(dst / "TASK.md"),
            "area": _area_of(dst / "TASK.md"), "standing": True, "parent": a.id,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        event(a.agent, f"взят раунд постоянной задачи `{a.id}` → `{round_id}`")
        print(f"взято: раунд {round_id} (постоянная задача {a.id} осталась в pending)")
        return 0
    try:
        dst.mkdir(parents=True)  # атомарно: второму агенту достанется FileExistsError
    except FileExistsError:
        print(f"ошибка: {a.id} уже взята")
        return 1
    shutil.copy2(src / "TASK.md", dst / "TASK.md")
    (dst / ".claim.json").write_text(json.dumps({
        "agent": a.agent, "taken_at": now(), "task_sha256": sha(dst / "TASK.md"),
        "area": _area_of(dst / "TASK.md"),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(src)
    event(a.agent, f"взята задача `{a.id}`")
    print(f"взято: {a.id} агентом {a.agent}")
    return 0


def _area_of(task: pathlib.Path) -> list[str]:
    text = task.read_text(encoding="utf-8")
    out, inside = [], False
    for ln in text.splitlines():
        if ln.startswith("## Рабочая область"):
            inside = True
            continue
        if inside and ln.startswith("## "):
            break
        if inside and ln.strip().startswith("- `"):
            out.append(ln.strip()[3:-1])
    return out


def _accept_of(task: pathlib.Path) -> list[str]:
    text = task.read_text(encoding="utf-8")
    out, inside = [], False
    for ln in text.splitlines():
        if ln.startswith("## Критерии приёмки"):
            inside = True
            continue
        if inside and ln.startswith("## "):
            break
        if inside and ln.strip().startswith("- `"):
            out.append(ln.strip()[3:-1])
    return out


def cmd_finish(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print(f"ошибка: {a.id} не активна")
        return 1
    claim = json.loads((d / ".claim.json").read_text(encoding="utf-8"))
    if claim.get("agent") != a.agent:
        print(f"ошибка: {a.id} взята агентом {claim.get('agent')}, не {a.agent}")
        return 1
    if sha(d / "TASK.md") != claim.get("task_sha256"):
        print("ошибка: TASK.md изменён после взятия — это запрещено")
        return 1
    if not (d / "RESULT.md").exists():
        print("ошибка: нет RESULT.md")
        return 1
    done = {"task": a.id, "agent": a.agent, "finished_at": now(), "artifacts": [], "checks": []}
    if (d / "DONE.json").exists():
        try:
            done.update(json.loads((d / "DONE.json").read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            print("ошибка: DONE.json не разбирается как JSON")
            return 1
    done["task"], done["agent"], done["finished_at"] = a.id, a.agent, now()
    (d / "DONE.json").write_text(json.dumps(done, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    event(a.agent, f"объявлена завершённой `{a.id}`")
    print(f"заявка о завершении принята: {a.id} (закрывает основной агент после проверки)")
    return 0


def cmd_verify(a) -> int:
    if getattr(a, "agent", "main") != "main":
        print("ошибка: verify выполняет только main")
        return 1
    d = ACTIVE / a.id
    if not d.exists():
        print(f"ошибка: {a.id} не активна")
        return 1
    if not (d / "DONE.json").exists():
        print("нет DONE.json — завершение не заявлено")
        return 1
    claim = json.loads((d / ".claim.json").read_text(encoding="utf-8"))
    if sha(d / "TASK.md") != claim.get("task_sha256"):
        print("ПРОВАЛ: TASK.md изменён после взятия")
        return 1
    checks = _accept_of(d / "TASK.md")
    if not checks:
        print("в задаче нет критериев приёмки — проверить нечем")
        return 1
    failed = 0
    rec = []
    for c in checks:
        r = subprocess.run(c, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=600)
        state = "ok" if r.returncode == 0 else "ПРОВАЛ"
        print(f"[{state}] {c}")
        rec.append({"cmd": c, "rc": r.returncode,
                    "tail": "\n".join((r.stdout or r.stderr).strip().splitlines()[-3:])})
        if r.returncode != 0:
            failed += 1
    (d / "VERIFY.json").write_text(json.dumps({
        "ok": failed == 0, "task_sha256": claim.get("task_sha256"),
        "verified_at": now(), "by": getattr(a, "agent", "main"), "results": rec,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if failed == 0 else 1


def cmd_close(a) -> int:
    if getattr(a, "agent", "main") != "main":
        print("ошибка: close выполняет только main")
        return 1
    d = ACTIVE / a.id
    if not d.exists():
        print(f"ошибка: {a.id} не активна")
        return 1
    if not (d / "DONE.json").exists():
        print("ошибка: нет DONE.json")
        return 1
    v = d / "VERIFY.json"
    if not v.exists():
        print("ошибка: нет VERIFY.json — сначала `verify`")
        return 1
    try:
        ver = json.loads(v.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("ошибка: VERIFY.json не разбирается")
        return 1
    claim = json.loads((d / ".claim.json").read_text(encoding="utf-8"))
    if not ver.get("ok"):
        print("ошибка: VERIFY.json не зелёный")
        return 1
    if ver.get("task_sha256") != claim.get("task_sha256"):
        print("ошибка: VERIFY.json от другой версии карточки")
        return 1
    (DONE / a.id).mkdir(parents=True, exist_ok=True)
    for p in d.iterdir():
        shutil.move(str(p), str(DONE / a.id / p.name))
    d.rmdir()
    event("main", f"закрыта задача `{a.id}` после проверки")
    print(f"закрыто: {a.id} → .coord/completed/{a.id}")
    return 0


def cmd_stale(_a) -> int:
    if not ACTIVE.exists():
        return 0
    n = 0
    for p in sorted(ACTIVE.iterdir()):
        if not p.is_dir():
            continue
        c = p / ".claim.json"
        if not c.exists():
            continue
        j = json.loads(c.read_text(encoding="utf-8"))
        age = (time.time() - calendar.timegm(
            time.strptime(j["taken_at"], "%Y-%m-%dT%H:%M:%SZ"))) / 60
        if age > TTL_MIN and not (p / "DONE.json").exists():
            n += 1
            print(f"просрочена: {p.name} (агент {j.get('agent')}, {age:.0f} мин)")
    if n == 0:
        print(f"просроченных нет (TTL {TTL_MIN} мин)")
    return 0


def cmd_release(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print(f"ошибка: {a.id} не активна")
        return 1
    claim = json.loads((d / ".claim.json").read_text(encoding="utf-8"))
    if a.force and a.agent != "main":
        print("ошибка: release --force разрешён только main")
        return 1
    if claim.get("agent") != a.agent and not a.force:
        print("ошибка: отпустить может только исполнитель (или main с --force)")
        return 1
    if claim.get("standing"):
        # Раунд постоянной задачи: карточка живёт в pending всегда, её не надо создавать заново.
        for extra in ("RESULT.md", "DONE.json"):
            if (d / extra).exists():
                (d / extra).rename(d / (extra + ".abandoned"))
        (d / ".claim.json").unlink()
        d.rmdir()
        event(a.agent, f"отпущен раунд `{a.id}`: {a.reason}")
        print(f"отпущен раунд: {a.id} (постоянная карточка `{claim.get('parent')}` не тронута)")
        return 0
    dst = PENDING / a.id
    dst.mkdir(parents=True, exist_ok=True)
    shutil.move(str(d / "TASK.md"), str(dst / "TASK.md"))
    for extra in ("RESULT.md", "DONE.json"):
        if (d / extra).exists():
            (d / extra).rename(d / (extra + ".abandoned"))
    (d / ".claim.json").unlink()
    d.rmdir()
    event(a.agent, f"отпущена задача `{a.id}`: {a.reason}")
    print(f"отпущено: {a.id} → pending")
    return 0


def cmd_register(a) -> int:
    AGENTS.mkdir(parents=True, exist_ok=True)
    p = AGENTS / f"{a.agent}.md"
    p.write_text(f"""# Агент `{a.agent}`

- роль: {"основной; публикует изменения всех агентов" if a.agent == "main" else "исследовательский партнёр"}
- зарегистрирован: {now()}
- права на очередь: полные (создание, правка свободных задач, приоритет, отмена)
- ограничения: {"—" if a.agent == "main" else "Git не использует; не правит core/, laws/, verus/, checks/, run.sh, AGENTS.md, kg/nodes.jsonl; пишет литературные ячейки только в литературный inbox своего префикса"}
""", encoding="utf-8")
    event(a.agent, "регистрация в координации")
    print(f"зарегистрирован: {a.agent}")
    return 0


def main(argv: list[str]) -> int:
    COORD.mkdir(exist_ok=True)
    for d in (PENDING, ACTIVE, DONE, EVENTS, AGENTS):
        d.mkdir(exist_ok=True)
    ap = argparse.ArgumentParser(prog="coord")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); p.add_argument("--id", required=True); p.add_argument("--title", required=True)
    p.add_argument("--area", required=True); p.add_argument("--accept", action="append", default=[])
    p.add_argument("--priority", type=int, default=50); p.add_argument("--agent", default="main")
    p.add_argument("--note", default=""); p.add_argument("--kind", default="research")
    p.add_argument("--standing", action="store_true")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("take"); p.add_argument("id"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_take)
    p = sub.add_parser("finish"); p.add_argument("id"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_finish)
    p = sub.add_parser("verify"); p.add_argument("id")
    p.add_argument("--agent", default="main"); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("close"); p.add_argument("id")
    p.add_argument("--agent", default="main"); p.set_defaults(fn=cmd_close)
    p = sub.add_parser("stale"); p.set_defaults(fn=cmd_stale)
    p = sub.add_parser("release"); p.add_argument("id"); p.add_argument("--agent", required=True)
    p.add_argument("--reason", default=""); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_release)
    p = sub.add_parser("register"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_register)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
