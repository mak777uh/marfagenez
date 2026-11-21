"""Ledger of OpenAlex budget use: a spent day must be visible, and a key must never be.

Why this check exists: `tools/budget.py` writes `literature/budget/openalex.jsonl`, and the repository is
public. So the rules are:
  L1 every line is a JSON object with ts, endpoint, run_id, channel, budget_before, budget_after;
  L2 timestamps never go backwards;
  L3 within one UTC day the remaining budget never increases after a request (a reset is a new day);
  L4 no value anywhere in the ledger contains an API key or a token-like string.

Usage:
    python3 checks/budget_ledger.py
    python3 checks/budget_ledger.py --selftest
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "literature" / "budget" / "openalex.jsonl"
SECRET_RE = re.compile(r"(api_key|token|secret|bearer)", re.I)

REQUIRED = ("ts", "endpoint", "run_id", "channel", "budget_before", "budget_after")


def check(path: pathlib.Path) -> list[str]:
    errs: list[str] = []
    if not path.exists():
        print("леджера нет: трат ещё не было")
        return errs
    rows: list[dict] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errs.append(f"L1 строка {n}: не JSON ({exc})")
            continue
        for key in REQUIRED:
            if key not in row:
                errs.append(f"L1 строка {n}: нет поля `{key}`")
        if SECRET_RE.search(line):
            errs.append(f"L4 строка {n}: похоже на секрет в коммитимом файле")
        rows.append(row)

    for prev, cur in zip(rows, rows[1:]):
        if str(cur.get("ts")) < str(prev.get("ts")):
            errs.append(f"L2 время идёт назад: {prev.get('ts')} -> {cur.get('ts')}")
        if str(cur.get("ts"))[:10] == str(prev.get("ts"))[:10]:
            before, after = cur.get("budget_before"), cur.get("budget_after")
            if isinstance(before, (int, float)) and isinstance(after, (int, float)) and after > before + 1e-9:
                errs.append(f"L3 остаток вырос внутри дня: {before} -> {after} ({cur.get('ts')})")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="budget-"))
    good = tmp / "good.jsonl"
    good.write_text("\n".join(json.dumps(r) for r in [
        {"ts": "2026-11-21T10:00:00Z", "endpoint": "/works", "run_id": "r1", "channel": "openalex",
         "budget_before": 1.0, "budget_after": 0.999},
        {"ts": "2026-11-21T11:00:00Z", "endpoint": "/works", "run_id": "r2", "channel": "openalex",
         "budget_before": 0.999, "budget_after": 0.998},
    ]) + "\n", encoding="utf-8")
    bad_secret = tmp / "secret.jsonl"
    bad_secret.write_text(json.dumps({"ts": "2026-11-21T10:00:00Z", "endpoint": "/works", "run_id": "r",
                                      "channel": "openalex", "budget_before": 1, "budget_after": 1,
                                      "note": "api_key=abcdef"}) + "\n", encoding="utf-8")
    bad_grow = tmp / "grow.jsonl"
    bad_grow.write_text("\n".join(json.dumps(r) for r in [
        {"ts": "2026-11-21T10:00:00Z", "endpoint": "/works", "run_id": "r1", "channel": "openalex",
         "budget_before": 0.5, "budget_after": 0.4},
        {"ts": "2026-11-21T10:05:00Z", "endpoint": "/works", "run_id": "r2", "channel": "openalex",
         "budget_before": 0.4, "budget_after": 0.9},
    ]) + "\n", encoding="utf-8")

    cases = [
        ("чистый леджер", check(good), []),
        ("секрет в файле", check(bad_secret), ["L4"]),
        ("остаток вырос", check(bad_grow), ["L3"]),
    ]
    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(LEDGER)
    if errs:
        print(f"ЛЕДЖЕР БЮДЖЕТА: {len(errs)} нарушений")
        for e in errs[:20]:
            print("  " + e)
        return 1
    print("леджер бюджета: формат и монотонность в порядке")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
