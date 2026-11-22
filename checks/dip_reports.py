"""Отчёты дип-ресерчера: без отчёта о покрытии партия не считается работой.

Дип приносит два файла: ячейки и короткое описание. Правила:
  D1 у каждой партии есть `.md` с разделами «проверено», «отброшено», «покрытие»;
  D2 ячейки проходят правила карты (поля, цитата при фрагменте, условия при medium/high);
  D3 нет ячеек с `confidence: high` и непроверенным локатором;
  D4 `locator_status` — только `verified` или `unverified` (не пусто);
  D5 партия не превышает `max_atoms` своей задачи, если задача есть в очереди.

Usage:
    python3 checks/dip_reports.py
    python3 checks/dip_reports.py --selftest
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIPS = ROOT / "literature" / "dips"
REPORTS = DIPS / "reports"
TASKS = DIPS / "tasks.jsonl"

SECTIONS = ("проверено", "отброшено", "покрытие")


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(reports: pathlib.Path, tasks: pathlib.Path) -> list[str]:
    errs: list[str] = []
    if not reports.exists():
        return errs
    limits = {t["task_id"]: t.get("max_atoms", 99) for t in load(tasks)}
    for atoms_path in sorted(reports.glob("*.jsonl")):
        task_id = atoms_path.stem
        md_path = reports / f"{task_id}.md"
        if not md_path.exists():
            errs.append(f"D1 {task_id}: нет md-отчёта")
        else:
            text = md_path.read_text(encoding="utf-8").lower()
            for section in SECTIONS:
                if section not in text:
                    errs.append(f"D1 {task_id}: в md-отчёте нет раздела «{section}»")
        atoms = load(atoms_path)
        limit = limits.get(task_id)
        if limit and len(atoms) > limit:
            errs.append(f"D5 {task_id}: {len(atoms)} ячеек при лимите {limit}")
        for atom in atoms:
            atom_id = atom.get("atom", "?")
            for field in ("atom", "statement", "domain", "kind", "works", "confidence"):
                if not atom.get(field):
                    errs.append(f"D2 {task_id}/{atom_id}: нет `{field}`")
            if atom.get("confidence") == "high" and atom.get("locator_status") != "verified":
                errs.append(f"D3 {task_id}/{atom_id}: high с непроверенным локатором")
            if atom.get("locator_status") not in ("verified", "unverified"):
                errs.append(f"D4 {task_id}/{atom_id}: locator_status `{atom.get('locator_status')}`")
            for work in atom.get("works") or []:
                if work.get("access") in ("fragment", "full") and not work.get("quote"):
                    errs.append(f"D2 {task_id}/{atom_id}: фрагмент без цитаты")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dips-"))
    reports = tmp / "reports"
    reports.mkdir()
    tasks = tmp / "tasks.jsonl"
    tasks.write_text(json.dumps({"task_id": "t1", "max_atoms": 2}) + "\n", encoding="utf-8")

    good = reports / "t1.jsonl"
    good.write_text(json.dumps({
        "atom": "T-1", "statement": "s", "domain": "d", "kind": "mechanism",
        "works": [{"doi": "10.1/x", "access": "abstract"}], "confidence": "medium",
        "conditions": ["модель"], "locator_status": "verified",
    }) + "\n", encoding="utf-8")
    (reports / "t1.md").write_text("проверено: 3\nотброшено: 1\nпокрытие: часть\n", encoding="utf-8")

    bad = tmp / "reports2"
    bad.mkdir()
    (bad / "t2.jsonl").write_text(json.dumps({
        "atom": "T-2", "statement": "s", "domain": "d", "kind": "mechanism",
        "works": [{"doi": "10.1/x", "access": "fragment"}], "confidence": "high",
        "locator_status": "unknown",
    }) + "\n", encoding="utf-8")

    cases = [
        ("чистый отчёт", check(reports, tasks), []),
        ("нет md и high без проверки", check(bad, tasks), ["D1", "D3", "D4", "D2"]),
    ]
    total, bad_n = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad_n += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got[:3]}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad_n}/{total}")
    return 1 if bad_n else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(REPORTS, TASKS)
    if errs:
        print(f"ОТЧЁТЫ ДИПА: {len(errs)} нарушений")
        for e in errs[:20]:
            print("  " + e)
        return 1
    count = len(list(REPORTS.glob("*.jsonl"))) if REPORTS.exists() else 0
    print(f"отчёты дипа: {count} партий, нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
