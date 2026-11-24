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


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def event(agent: str, text: str) -> None:
    EVENTS.mkdir(parents=True, exist_ok=True)
    p = EVENTS / f"{time.strftime('%Y%m%dT%H%M%S')}-{agent}.md"
    p.write_text(f"# {now()} — {agent}\n\n{text}\n", encoding="utf-8")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def task_card(task_id: str, title: str, area: str, accept: list[str], priority: int,
              author: str, note: str = "") -> str:
    lines = [
        f"# {task_id} — {title}",
        "",
        f"- автор: `{author}`",
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


def cmd_add(a) -> int:
    d = PENDING / a.id
    if d.exists() or (ACTIVE / a.id).exists() or (DONE / a.id).exists():
        print(f"ошибка: задача {a.id} уже существует")
        return 1
    d.mkdir(parents=True)
    (d / "TASK.md").write_text(task_card(a.id, a.title, a.area, a.accept, a.priority, a.agent, a.note),
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
            print(f"  {p.name}: {title}{extra}")
    return 0


def cmd_take(a) -> int:
    src = PENDING / a.id
    dst = ACTIVE / a.id
    if not src.exists():
        print(f"ошибка: {a.id} нет в pending")
        return 1
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
    for c in checks:
        r = subprocess.run(c, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        state = "ok" if r.returncode == 0 else "ПРОВАЛ"
        print(f"[{state}] {c}")
        if r.returncode != 0:
            failed += 1
            tail = (r.stdout or r.stderr).strip().splitlines()[-3:]
            for t in tail:
                print("     ", t)
    return 0 if failed == 0 else 1


def cmd_close(a) -> int:
    d = ACTIVE / a.id
    if not d.exists():
        print(f"ошибка: {a.id} не активна")
        return 1
    if not (d / "DONE.json").exists():
        print("ошибка: нет DONE.json")
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
        age = (time.time() - time.mktime(time.strptime(j["taken_at"], "%Y-%m-%dT%H:%M:%SZ"))) / 60
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
    if claim.get("agent") != a.agent and not a.force:
        print("ошибка: отпустить может только исполнитель (или с --force)")
        return 1
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
    p.add_argument("--note", default=""); p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("take"); p.add_argument("id"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_take)
    p = sub.add_parser("finish"); p.add_argument("id"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_finish)
    p = sub.add_parser("verify"); p.add_argument("id"); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("close"); p.add_argument("id"); p.set_defaults(fn=cmd_close)
    p = sub.add_parser("stale"); p.set_defaults(fn=cmd_stale)
    p = sub.add_parser("release"); p.add_argument("id"); p.add_argument("--agent", required=True)
    p.add_argument("--reason", default=""); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_release)
    p = sub.add_parser("register"); p.add_argument("--agent", required=True); p.set_defaults(fn=cmd_register)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
