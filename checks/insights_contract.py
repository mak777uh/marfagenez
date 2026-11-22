"""Контракт инсайтов: инсайт без опровержения и без опыта — не инсайт.

K1 обязательные поля и перечисления статусов;
K2 каждый `supports` существует среди ячеек карты;
K3 у инсайта есть хотя бы одна опора или явная пометка proposal (status=open без опор запрещён);
K4 `refuted_by` заполнен: чем именно утверждение можно сломать;
K5 у дизайна есть question, method, prediction и if_false;
K6 идентификаторы уникальны;
K7 инсайт не дублирует дословно одну ячейку (иначе это ячейка, а не инсайт).

Usage:
    python3 checks/insights_contract.py
    python3 checks/insights_contract.py --selftest
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSIGHTS = ROOT / "literature" / "map" / "insights.jsonl"
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
STATUSES = {"supported", "open", "contested"}


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(insights_path: pathlib.Path, atoms_path: pathlib.Path) -> list[str]:
    rows = load(insights_path)
    atoms = {a["atom"]: a for a in load(atoms_path)}
    errs: list[str] = []
    seen = set()
    for row in rows:
        iid = row.get("id", "?")
        for field in ("id", "statement", "status", "supports", "refuted_by", "design"):
            if not row.get(field):
                errs.append(f"K1 {iid}: нет `{field}`")
        if row.get("status") not in STATUSES:
            errs.append(f"K1 {iid}: статус `{row.get('status')}` вне перечисления")
        if iid in seen:
            errs.append(f"K6 {iid}: дубль идентификатора")
        seen.add(iid)
        supports = row.get("supports") or []
        if not supports and row.get("status") != "contested":
            errs.append(f"K3 {iid}: нет опор")
        for atom_id in supports:
            if atom_id not in atoms:
                errs.append(f"K2 {iid}: опора `{atom_id}` отсутствует в карте")
            elif (atoms[atom_id].get("statement") or "").strip() == (row.get("statement") or "").strip():
                errs.append(f"K7 {iid}: дословно повторяет ячейку `{atom_id}`")
        design = row.get("design") or {}
        for field in ("question", "method", "prediction", "if_false"):
            if not design.get(field):
                errs.append(f"K5 {iid}: в дизайне нет `{field}`")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="insights-"))
    atoms = tmp / "atoms.jsonl"
    atoms.write_text(json.dumps({"atom": "A-1", "statement": "факт"}) + "\n", encoding="utf-8")
    ins = tmp / "insights.jsonl"
    good = {"id": "I-1", "statement": "вывод", "status": "supported", "supports": ["A-1"],
            "refuted_by": "опыт Б", "design": {"question": "q", "method": "m", "prediction": "p", "if_false": "f"}}
    cases = [
        ("чистый инсайт", [good], []),
        ("нет опоры", [{**good, "supports": []}], ["K3"]),
        ("опора не существует", [{**good, "supports": ["A-9"]}], ["K2"]),
        ("нет опровержения", [{**good, "refuted_by": ""}], ["K1"]),
        ("нет if_false", [{**good, "design": {"question": "q", "method": "m", "prediction": "p"}}], ["K5"]),
        ("дубль", [good, good], ["K6"]),
    ]
    total, bad = 0, 0
    for name, rows, want in cases:
        ins.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        got = check(ins, atoms)
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got[:2]}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(INSIGHTS, ATOMS)
    if errs:
        print(f"ИНСАЙТЫ: {len(errs)} нарушений")
        for e in errs[:20]:
            print("  " + e)
        return 1
    print(f"инсайты: {len(load(INSIGHTS))}, нарушений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
