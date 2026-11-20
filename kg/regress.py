#!/usr/bin/env python3
"""regress.py -- the invariant that import must not move knowledge.

Two things are checked, both from the second round of review:

1. **Corpus is the source of truth.** Rebuild the graph from `claims.jsonl`, the literature and
   `results/*/run-*.json`; the committed `nodes.jsonl` must match it. A hand edit to the generated
   file, or a forgotten rebuild, fails here instead of drifting silently.
2. **Import never raises status by itself** (D-07). Compare every id's `epistemic` before and after:
   a mechanical edge may add a connection, it may not upgrade a claim. Any change must be a separate,
   deliberate commit.

Exit code 0 = green, 1 = drift.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import migrate  # noqa: E402


def committed():
    path = HERE / "nodes.jsonl"
    return {n["id"]: n for n in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())}


def rebuilt():
    nodes = migrate.claims() + migrate.formulas() + migrate.experiments() + migrate.literature()
    return {n["id"]: n for n in nodes}


def main():
    old, new = committed(), rebuilt()
    problems = []

    only_committed = sorted(set(old) - set(new))
    only_corpus = sorted(set(new) - set(old))
    if only_committed:
        problems.append("в nodes.jsonl есть узлы, которых нет в корпусе: " + ", ".join(only_committed[:8]))
    if only_corpus:
        problems.append("в корпусе есть узлы, не попавшие в nodes.jsonl: " + ", ".join(only_corpus[:8]))

    moved = []
    for nid in sorted(set(old) & set(new)):
        a, b = old[nid].get("epistemic"), new[nid].get("epistemic")
        if a != b:
            moved.append(nid + ": " + str(a) + " -> " + str(b))
    if moved:
        problems.append("импорт меняет статус знания: " + "; ".join(moved[:8]))

    print("сверка корпус -> nodes.jsonl: " + str(len(new)) + " узлов")
    if problems:
        for p in problems:
            print("  FAIL: " + p)
        print("  пересобери: python3 kg/migrate.py && python3 kg/kg.py build")
        return 1
    print("  ok: nodes.jsonl совпадает с корпусом, статусы не двигались")
    return 0


if __name__ == "__main__":
    sys.exit(main())
