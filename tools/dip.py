"""Дип-ресерчер: очередь задач и приём отчётов.

Дип работает по одной задаче и кладёт два файла: `<task_id>.jsonl` (ячейки) и `<task_id>.md` (отчёт).
Этот инструмент ведёт очередь, показывает состояние и готовит отчёты к приёму в карту. Он не вызывает
модель сам (ключ модели живёт в DSH, не в шелле) — вызов делает субагент или расписание.

Usage:
    python3 tools/dip.py add --task dip-2026-11-23-01 --domain evolution.ecology --question "…" [--min 8] [--max 12]
    python3 tools/dip.py list [--status queued]
    python3 tools/dip.py next
    python3 tools/dip.py report <task_id>          # что в отчёте: ячейки, проверка, готовность
    python3 tools/dip.py close <task_id> --status done
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIPS = ROOT / "literature" / "dips"
TASKS = DIPS / "tasks.jsonl"
REPORTS = DIPS / "reports"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(rows: list[dict]) -> None:
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    TASKS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def add(rest: list[str]) -> int:
    task_id = rest[rest.index("--task") + 1]
    rows = load(TASKS)
    if any(r["task_id"] == task_id for r in rows):
        print(f"задача {task_id} уже есть")
        return 1
    row = {
        "task_id": task_id,
        "domain": rest[rest.index("--domain") + 1],
        "question": rest[rest.index("--question") + 1],
        "must_have": ["локатор, проверенный через OpenAlex", "дословная цитата", "условия применимости"],
        "min_atoms": int(rest[rest.index("--min") + 1]) if "--min" in rest else 8,
        "max_atoms": int(rest[rest.index("--max") + 1]) if "--max" in rest else 12,
        "status": "queued",
        "created": now(),
    }
    rows.append(row)
    save(rows)
    print(f"добавлено: {task_id} ({row['domain']})")
    return 0


def listing(status: str | None) -> int:
    rows = load(TASKS)
    if status:
        rows = [r for r in rows if r["status"] == status]
    if not rows:
        print("очередь пуста")
        return 0
    for row in rows:
        print(f"{row['task_id']:<26} {row['status']:<8} {row['domain']:<28} {row['question'][:60]}")
    print(f"всего: {len(rows)}")
    return 0


def next_task() -> int:
    rows = [r for r in load(TASKS) if r["status"] == "queued"]
    if not rows:
        print("нет задач в очереди — добавь через `tools/dip.py add`")
        return 0
    pending = sorted(rows, key=lambda r: r["created"])[0]
    print(json.dumps(pending, ensure_ascii=False, indent=1))
    return 0


def report(task_id: str) -> int:
    atoms_path = REPORTS / f"{task_id}.jsonl"
    md_path = REPORTS / f"{task_id}.md"
    if not atoms_path.exists():
        print(f"нет отчёта {atoms_path}")
        return 1
    atoms = load(atoms_path)
    print(f"ячеек в отчёте: {len(atoms)}; md-описание: {'есть' if md_path.exists() else 'НЕТ'}")
    domains = sorted({a.get("domain") for a in atoms})
    kinds = {}
    for atom in atoms:
        kinds[atom.get("kind")] = kinds.get(atom.get("kind"), 0) + 1
    print("области: " + ", ".join(d for d in domains if d))
    print("виды: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    unverified = [a.get("atom") for a in atoms if a.get("locator_status") != "verified"]
    if unverified:
        print(f"без проверенного локатора: {len(unverified)} — {', '.join(map(str, unverified[:8]))}")
    print("готово к приёму: " + ("да" if md_path.exists() else "нет (нет md-отчёта)"))
    return 0


def close(task_id: str, status: str) -> int:
    rows = load(TASKS)
    found = False
    for row in rows:
        if row["task_id"] == task_id:
            row["status"] = status
            row["closed"] = now()
            found = True
    if not found:
        print(f"нет задачи {task_id}")
        return 1
    save(rows)
    print(f"{task_id}: {status}")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    verb, rest = argv[0], argv[1:]
    if verb == "add":
        return add(rest)
    if verb == "list":
        return listing(rest[rest.index("--status") + 1] if "--status" in rest else None)
    if verb == "next":
        return next_task()
    if verb == "report":
        return report(rest[0])
    if verb == "close":
        return close(rest[0], rest[rest.index("--status") + 1] if "--status" in rest else "done")
    print(f"неизвестный глагол {verb}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
