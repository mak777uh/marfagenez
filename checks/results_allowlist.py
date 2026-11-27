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
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

CURRENT_SCHEMA = "marfagenez.experiment-result.v2"
LEGACY_SCHEMAS = {None, "experiment/1", "marfagenez.experiment-result.v1"}
LEGACY_LABEL = "legacy, не цитировать"

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


def classify(rel: str, path: pathlib.Path | None = None) -> str | None:
    # Result records have a schema contract, not just a filename convention.
    # Old records remain readable for historical analysis but are not citable.
    if re.search(r"run-[^/]+\.json$", rel):
        if "_archive" in pathlib.PurePosixPath(rel).parts:
            return LEGACY_LABEL
        if path is None:
            return "прогон модели"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        schema = data.get("schema")
        if schema == CURRENT_SCHEMA:
            model_commit = data.get("model_commit")
            if not isinstance(model_commit, str) or not model_commit:
                return None
            if model_commit.endswith("+dirty"):
                return LEGACY_LABEL
            return "прогон модели"
        if schema in LEGACY_SCHEMAS:
            return LEGACY_LABEL
        return None

    for pattern, name in ALLOW:
        if pattern == r"run-[^/]+\.json$":
            continue
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
        kind = classify(rel, path)
        if kind is None:
            bad.append(rel)
        else:
            counts[kind] += 1
    return bad, counts


def selftest() -> int:
    with tempfile.TemporaryDirectory(prefix="results-allow-") as tmp:
        results = pathlib.Path(tmp) / "results"
        allowed = {
            "EXP-X/run-current.json": {"schema": CURRENT_SCHEMA, "model_commit": "abc123"},
            "EXP-X/run-no-schema.json": {"experiment_id": "old"},
            "EXP-X/run-experiment-v1.json": {"schema": "experiment/1"},
            "EXP-X/run-v1.json": {"schema": "marfagenez.experiment-result.v1"},
            "EXP-X/run-dirty.json": {"schema": CURRENT_SCHEMA, "model_commit": "abc123+dirty"},
            "EXP-X/summary.json": {},
            "EXP-X/trace-sequential-n40.json": {},
            "capacity/exp99-rows.json": {},
            "capacity/rows.json": {},
            "fig/map.png": None,
        }
        bad = ["litsearch/run.json", "budget/openalex.jsonl", "EXP-X/notes.md",
               "EXP-X/run-unknown-schema.json"]
        for rel, payload in allowed.items():
            path = results / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if payload is None:
                path.write_bytes(b"PNG")
            else:
                path.write_text(json.dumps(payload), encoding="utf-8")
        (results / "EXP-X/run-unknown-schema.json").write_text(
            json.dumps({"schema": "marfagenez.experiment-result.v99"}), encoding="utf-8")
        for rel in bad[:3]:
            path = results / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        archived = results / "_archive" / "old" / "run-v1.json"
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_text(json.dumps({"schema": "marfagenez.experiment-result.v1"}), encoding="utf-8")

        found, counts = scan(results)
        ok_allowed = set(found).isdisjoint(allowed) and "EXP-X/run-unknown-schema.json" in found
        ok_bad = set(found) == set(bad)
        ok_current = counts.get("прогон модели", 0) == 1
        ok_legacy = counts.get(LEGACY_LABEL, 0) == 5
        ok_archived = classify("_archive/old/run-v1.json", archived) == LEGACY_LABEL
        print(f"  {'ok  ' if ok_allowed else 'FAIL'} current and legacy result classes are recognised")
        print(f"  {'ok  ' if ok_bad else 'FAIL'} foreign artifacts and unknown schema fail closed: {found}")
        print(f"  {'ok  ' if ok_current else 'FAIL'} only clean current schema is citable")
        print(f"  {'ok  ' if ok_legacy else 'FAIL'} missing/v1/dirty records are marked legacy")
        print(f"  {'ok  ' if ok_archived else 'FAIL'} archive remains historical")
        return 0 if all((ok_allowed, ok_bad, ok_current, ok_legacy, ok_archived)) else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        result = selftest()
        print(f"selftest: {'ok' if result == 0 else 'провал'}")
        return result
    # Keep the schema-class regression fixture in the ordinary run.sh exp gate.
    if selftest() != 0:
        print("schema allowlist selftest: FAIL")
        return 1
    if not RESULTS.exists():
        print("нет каталога results/")
        return 1
    bad, counts = scan(RESULTS)
    print("results/: " + ", ".join(f"{name}={n}" for name, n in sorted(counts.items())))
    print(f"  {LEGACY_LABEL}: {counts.get(LEGACY_LABEL, 0)}")
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
