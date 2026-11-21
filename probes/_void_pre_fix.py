"""Mark results recorded before the clamp fix as void.

The clamp in `core/src/organism.rs` used to run right after the income, which
erased `move_cost` (see `docs/FINDING-the-cap-is-applied-after-the-spend.md`).
Every result recorded before that fix describes a model that no longer exists:
an organism could move for free, so anything about the cost of moving, about
two organisms sharing a cell, about where deaths happen, or about capacity was
measured against a different dynamics.

The contract (`checks/contract.py`) does not know about the fix, so it reports
these as violations of its own rules (§5 no hashes, §4 verdict disagrees with
controls). Both readings are true: they are violations, and they are also void.
Marking them void is the honest move -- it keeps the record and says the numbers
are not usable.

This script does not delete anything. It rewrites the `verdict` field and adds
the reason. `--dry-run` shows what would change.
"""

import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REASON = (
    "VOID: recorded before the clamp was moved to the end of the step "
    "(`core/src/organism.rs`, 2026-11-12). With the clamp after the income "
    "`move_cost` was erased, so this run measures a dynamics that no longer "
    "exists. See `docs/FINDING-the-cap-is-applied-after-the-spend.md` and "
    "`docs/FINDING-capacity-is-the-number-of-feeding-cells.md`. Kept as a "
    "record; the numbers are not usable."
)

# Results recorded before the fix. Listed explicitly rather than by timestamp,
# because a timestamp would also catch runs that are fine.
VOID = [
    "results/EXP-52/run-2026-11-12T22-03-53.json",
    "results/EXP-56/run-2026-11-12T22-23-48.json",
    "results/EXP-56/run-2026-11-12T22-25-47.json",
    "results/EXP-58/run-2026-11-12T22-27-30.json",
    "results/EXP-60/run-2026-11-12T22-28-35.json",
    "results/EXP-61/run-2026-11-12T22-29-09.json",
    "results/exp31_capacity_was_forty/run-2026-11-12T21-49-53.json",
    "results/exp66-second-occupant/run-2026-11-12T22-43-36.json",
    "results/exp66-second-occupant/run-2026-11-12T22-43-55.json",
    "results/exp66-second-occupant/run-2026-11-12T22-44-54.json",
    "results/exp67-where-does-anything-die/run-2026-11-12T22-45-46.json",
    "results/exp67-where-does-anything-die/run-2026-11-12T22-46-25.json",
    "results/exp68-bisect-the-death-threshold/run-2026-11-12T22-46-56.json",
    "results/exp69-a-sitter-dies-at-the-same-maintenance/run-2026-11-12T22-49-18.json",
    "results/exp70-the-threshold-offset-is-the-window/run-2026-11-12T22-51-10.json",
    "results/exp71-does-hunger-feed-back-into-moving/run-2026-11-12T22-57-11.json",
    "results/exp72-is-the-move-cost-charged/run-2026-11-12T23-00-26.json",
    "results/exp73-is-the-cap-the-whole-explanation/run-2026-11-12T23-01-55.json",
]


def main():
    dry = "--dry-run" in sys.argv
    changed = 0
    missing = 0
    for rel in VOID:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("missing", rel)
            missing += 1
            continue
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
        old = data.get("verdict", {})
        if old.get("kind") == "void" and old.get("reason") == REASON:
            print("already void", rel)
            continue
        data["verdict"] = {"kind": "void", "reason": REASON}
        if dry:
            print("would void", rel, "(was %s)" % old.get("kind"))
        else:
            with io.open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print("voided", rel, "(was %s)" % old.get("kind"))
        changed += 1
    print("changed %d, missing %d" % (changed, missing))


if __name__ == "__main__":
    main()
