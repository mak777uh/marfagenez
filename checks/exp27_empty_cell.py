"""EXP-27: does an organism that can see an empty cell move into it?

EXP-26 explained the empty cells at `n = 160` by claiming that `sighted` never
enters an empty cell in a uniform field, because an empty cell is not *richer*
than an occupied one -- it is the same. That is a claim about the decision rule,
and it can be tested without a population at all.

This experiment builds the smallest field that contains the question. Four
shapes, one organism each:

    equal        all three cells 1.6; the neighbours are what the organism stands on
    richer       cells 1.6 / 2.4 / 3.2; the right neighbour is plainly better
    enter-empty  cells 1.6 / 0.0 / 0.0, organism on cell 0 -- its only neighbour
                 is empty. **This is the question.**
    leave-empty  the same field, organism on cell 1 -- it stands on 0.0 and its
                 left neighbour is 1.6. The reverse question.

Arithmetic, written before the run
----------------------------------
The rule in `core/src/life.rs` for `Sighted` is

    best = max(here, left, right)
    if best > here:  step toward the better neighbour (tie -> left)
    else:            stay

so the prediction is exact:

    equal        0    best == here
    richer      +1    best = 3.2 > 2.4, right is the better one
    enter-empty  0    best = 1.6 == here; an empty cell is not better
    leave-empty -1    best = 1.6 > 0.0, the left neighbour is better

`Stay` is 0 in every shape. `Random` is recorded to show the field is not the
reason for the answer: it moves in every shape regardless of level.

A note on the read budget
-------------------------
`read_budget` must be 3, not 2. Seeing costs three reads -- the cell underfoot
and both neighbours -- and with a budget of 2 the right neighbour is never read,
so `Sighted` silently becomes "look left only". Measured before the fix: the
`richer` shape gave 0 instead of +1. This is the first thing this experiment
found, and it is a real trap for anyone building a sighted policy.

What this does not prove
------------------------
It does not prove that the empty cells at `n = 160` came from this rule. It
proves the rule refuses an empty neighbour, which is the mechanism EXP-26
assumed. The population-level consequence is still a separate measurement.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "checks"))
from experiment import Experiment  # noqa: E402

BIN = ROOT / "core" / "target" / "release" / "empty_cell"

# The prediction, written before the run. Keys are (policy, shape).
PREDICTED = {
    ("Stay", "equal"): 0,
    ("Stay", "richer"): 0,
    ("Stay", "enter-empty"): 0,
    ("Stay", "leave-empty"): 0,
    ("Sighted", "equal"): 0,
    ("Sighted", "richer"): 1,
    ("Sighted", "enter-empty"): 0,
    ("Sighted", "leave-empty"): -1,
}


def parse(text: str) -> list[dict]:
    """The binary prints `policy shape here left right -> direction`."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("policy") or "->" not in line:
            continue
        head, tail = line.split("->")
        parts = head.split()
        if len(parts) != 5:
            continue
        policy, shape, here, left, right = parts
        rows.append(
            {
                "policy": policy,
                "shape": shape,
                "here": here,
                "left": left,
                "right": right,
                "direction": int(tail.strip()),
            }
        )
    return rows


def main() -> int:
    out = subprocess.run([str(BIN)], capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stdout)
        print(out.stderr, file=sys.stderr)
        return out.returncode
    print(out.stdout)

    rows = parse(out.stdout)
    if not rows:
        print("no rows parsed -- the binary printed something unexpected")
        return 1

    exp = Experiment(
        experiment_id="empty-cell-refused",
        question=(
            "Does a sighted organism move into a neighbour that is empty but no "
            "richer than the cell it stands on?"
        ),
        arithmetic={
            "rule": "best = max(here, left, right); move only if best > here",
            "equal": "best == here -> 0",
            "richer": "best = 3.2 > 2.4, right better -> +1",
            "enter-empty": "best = 1.6 == here -> 0 (does not enter)",
            "leave-empty": "best = 1.6 > 0.0, left better -> -1 (does leave)",
            "stay": "never looks -> 0 in every shape",
            "read_budget": "3: underfoot + both neighbours; 2 silently drops the right",
        },
        arms={
            "sighted": "looks at both neighbours, moves only toward a richer one",
            "stay": "never looks; the control that must not move",
            "random": "moves without looking; shows the field is not the reason",
        },
        seed=7,
        command=str(BIN),
        parameters={
            "cells": 3,
            "energy": 10.0,
            "move_cost": 0.05,
            "read_budget": 3,
        },
    )

    for policy in ("Sighted", "Stay", "Random"):
        mine = [r for r in rows if r["policy"] == policy]
        if not mine:
            continue
        exp.add_arm(
            policy.lower(),
            policy,
            {
                r["shape"]: r["direction"] for r in mine
            },
            trace_hash=f"{policy}:"
            + ",".join(f"{r['shape']}={r['direction']}" for r in mine),
        )

    def dirs(policy: str, shape: str) -> int | None:
        for r in rows:
            if r["policy"] == policy and r["shape"] == shape:
                return r["direction"]
        return None

    # fires: the rule must move when a neighbour is plainly richer. If it never
    # moves, the experiment is measuring a dead organism, not a decision.
    richer = dirs("Sighted", "richer")
    fires = richer is not None and richer != 0
    exp.control("fires", fires, f"richer neighbour -> {richer} (expected non-zero)")

    # silent: with equal neighbours the sighted organism must stay. If it moves
    # here, the field offers no reason and the movement is noise.
    equal = dirs("Sighted", "equal")
    silent = equal == 0
    exp.control("silent", silent, f"equal neighbours -> {equal} (expected 0)")

    # specific: the answer must distinguish an empty neighbour from a richer one.
    # If both gave 0 the experiment would not be about emptiness at all.
    enter = dirs("Sighted", "enter-empty")
    specific = enter == 0 and richer not in (None, 0)
    exp.control(
        "specific",
        specific,
        f"empty neighbour -> {enter}, richer neighbour -> {richer} (must differ)",
    )

    # The prediction check: every (policy, shape) must match the arithmetic.
    mismatches = []
    for (policy, shape), want in PREDICTED.items():
        got = dirs(policy, shape)
        if got != want:
            mismatches.append(f"{policy}/{shape}: predicted {want}, got {got}")

    if fires and silent and specific and not mismatches:
        exp.verdict(
            "passed",
            "sighted stays on an empty neighbour (0) and leaves an empty cell "
            "for a richer one (-1); the decision rule refuses emptiness exactly "
            "as EXP-26 assumed, and every prediction matched",
        )
    elif mismatches:
        exp.verdict(
            "failed",
            "the decision rule did not match the arithmetic: " + "; ".join(mismatches),
        )
    else:
        exp.verdict(
            "void",
            "a control test failed, so the comparison is not about emptiness",
        )

    exp.limitation(
        "three cells, one organism, one step: this is the decision rule in "
        "isolation, not a population"
    )
    exp.limitation(
        "the empty neighbour is empty at the moment of looking; a cell that "
        "empties later in the same step is not covered"
    )
    exp.limitation(
        "what this does not prove: it does not show that empty cells at n = 160 "
        "come from this rule. It shows the rule cannot fill them, which is the "
        "mechanism EXP-26 assumed."
    )

    path = exp.save()
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
