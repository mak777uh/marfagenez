"""`results/` holds run records of the model — and nothing else.

Why an allowlist and not a denylist: the directory is restored with `git checkout -- results/`, so
search snapshots or budget ledgers placed there are lost by design. A denylist ("no `literature/` here")
is a game of whack-a-mole; a closed list is checkable.

The list below was derived from the tree as it stands (a census, not a guess): every pattern that exists
today is allowed, everything else fails. Adding a new artifact type is therefore a deliberate act that
touches this file and PROTOCOL.md.

Search material belongs in `literature/runs/`, the budget ledger in `literature/budget/`.

Usage:
    python3 checks/results_allowlist.py
    python3 checks/results_allowlist.py --census
    python3 checks/results_allowlist.py --selftest
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

ALLOW = [
    (r"run-[^/]+\.json$", "прогон модели"),
    (r"summary[^/]*\.json$", "сводка прогона"),
    (r"trace-[^/]+$", "трасса"),
    (r"[ABC]-trace-[^/]+$", "трасса плеча"),
    (r"exp99-[^/]+$", "сетка capacity"),
    (r"rows\.json$", "строки таблицы"),
    (r"stdout-[^/]+\.txt$", "перехваченный вывод"),
    (r"map\.png$", "рисунок"),
    (r"seeds\.json$", "сиды"),
    (r"(left|right|random)[^/]*\.json$", "артефакт сравнения"),
    (r"_archive/", "история (не проверяется)"),
]


def classify(rel: str) -> str | None:
    for pattern, name in ALLOW:
        if re.search(pattern, rel):
            return name
    return None


def scan(results: pathlib.Path) -> tuple[list[str], collections.Counter]:
    counts: collections.Counter = collections.Counter()
    bad: list[str] = []
    for path in sorted(results.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(results).as_posix()
        kind = classify(rel)
        if kind is None:
            bad.append(rel)
        else:
            counts[kind] += 1
    return bad, counts


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="results-allow-"))
    results = tmp / "results"
    good = [
        "EXP-X/run-2026-01-01.json",
        "EXP-X/summary.json",
        "EXP-X/trace-sequential-n40.json",
        "capacity/exp99-rows.json",
        "capacity/rows.json",
        "fig/map.png",
        "_archive/old/run-1.json",
    ]
    bad = ["litsearch/run.json", "budget/openalex.jsonl", "EXP-X/notes.md"]
    for rel in good + bad:
        path = results / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    found, counts = scan(results)
    ok_good = set(found).isdisjoint(good)
    ok_bad = set(found) == set(bad)
    print(f"  {'ok  ' if ok_good else 'FAIL'} разрешённые артефакты проходят (виды: {len(counts)})")
    print(f"  {'ok  ' if ok_bad else 'FAIL'} чужие артефакты ловятся: {found}")
    total = 2
    return 0 if (ok_good and ok_bad) else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        result = selftest()
        print(f"selftest: {'ok' if result == 0 else 'провал'}")
        return result
    if not RESULTS.exists():
        print("нет каталога results/")
        return 1
    bad, counts = scan(RESULTS)
    print("results/: " + ", ".join(f"{name}={n}" for name, n in sorted(counts.items())))
    if "--census" in argv:
        total = sum(counts.values()) + len(bad)
        print(f"всего файлов: {total}")
        return 0
    if bad:
        print(f"ЧУЖИЕ АРТЕФАКТЫ В results/: {len(bad)}")
        for rel in bad[:20]:
            print("  results/" + rel)
        if len(bad) > 20:
            print(f"  … и ещё {len(bad) - 20}")
        print("  поисковые снимки — в literature/runs/, леджер бюджета — в literature/budget/")
        return 1
    print("results/: только артефакты прогонов модели")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
