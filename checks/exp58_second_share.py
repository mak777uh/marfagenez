"""What does an organism lose per step, as a function of the share it takes?

THE QUESTION

EXP-56 found two late deaths, at steps 3578 and 6804, both with taken = 0.500 and
damage = 0.0. The finding note reconstructed a loss of 0.23/step from that scene
and used it to explain the queue. That reconstruction assumed the loss is a
constant. This experiment asks whether it is: is the per-step loss a function of
the share taken, and does the field level shift that function?

THREE ERRORS IN THE FIRST TWO VERSIONS, ALL KEPT HERE ON PURPOSE

1. --field uniform builds the field as (rich + poor) / 2. The two arms (2.4, 1.6)
   and (2.8, 1.2) both summed to 4.0, so both were the same field at level 2.0 and
   produced byte-identical traces (same hash 3d3eb99d7136655b). The "level
   dependence" was measured on a field with one level. Fixed by using
   --field alternating, where the two levels actually differ.

2. Dead organisms are still sampled, with taken = 0 and frozen energy. They
   outnumbered the live samples three to one and contributed a flat zero, which
   reads as "no loss". Fixed by skipping samples whose alive is false.

3. taken is stamped at the END of a step. So s["taken"] is the share taken during
   the step that PRODUCED s["energy"], while nxt["energy"] - s["energy"] is the
   change of the NEXT step, whose share is nxt["taken"]. Grouping by s["taken"]
   matched a share with a step it did not pay for, which is how a 0.4 share
   appeared to lose 0.55. Fixed by grouping on nxt["taken"].

THE ARITHMETIC

    income = 1.2, maintenance = 0.6, damage_rate = 0.02, repair = 1.5
    damage cost per step = 0.02 * 1.5 = 0.03
    delta = taken - 0.6 - 0.03 - move_cost*[moved]

A first taker on a cell of level L takes min(L - income, income). The field
regrows toward the two levels, so L need not equal the nominal rich or poor value
at the moment of the sample; that is why the measured shares are not exactly
0.4 and 1.2.

WHAT THE MEASUREMENT CAN AND CANNOT SHOW

It can show that the loss is a straight line in the share taken, with slope 1 and
intercept -0.63. That is a statement about the mechanism, and it is falsifiable:
a share of 0.72 must gain 0.09, a share of 0.08 must lose 0.55.

It cannot show a "second taker" as a distinct class, because the trace records one
share per organism per step, not its position in a queue. The queue is inferred
from two organisms on one cell, and that inference is what EXP-56 did.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment

CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

INCOME = 1.2
MAINT = 0.6
DAMAGE_RATE = 0.02
REPAIR = 1.5
MOVE = 0.10
STEPS = 3000
SEED = 20250101
N = 160
CELLS = 40
COST = MAINT + DAMAGE_RATE * REPAIR  # 0.63


def run(rich, poor, steps, every):
    # The output name carries a one-second stamp. Two arms finishing inside the
    # same second would read the same file and appear identical.
    time.sleep(1.1)
    cmd = [
        TRACE,
        "--n", str(N), "--cells", str(CELLS),
        "--rich", str(rich), "--poor", str(poor),
        "--regrow", "0.8",
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(steps), "--every", str(every),
        "--seed", str(SEED),
        "--policy", "sighted",
        "--read-budget", "3",
        "--capacity", "8",
        "--field", "alternating",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr[-2000:])
    written = [
        line.split(":", 1)[1].strip()
        for line in out.stdout.splitlines()
        if line.startswith("written:")
    ][0]
    path = os.path.join(CORE, written)
    if os.path.exists(path) and os.path.getmtime(path) < time.time() - 5:
        raise SystemExit(f"refusing a stale file: {path}")
    return json.load(open(path))


def by_taken(data):
    """Mean energy change per step, grouped by the share taken during that step."""
    groups = {}
    frames = data["frames"]
    for a, b in zip(frames, frames[1:]):
        after = {s["slot"]: s for s in b["samples"]}
        for s in a["samples"]:
            if not s["alive"]:
                continue
            nxt = after.get(s["slot"])
            if nxt is None or not nxt["alive"]:
                continue
            taken = round(nxt["taken"], 3)
            groups.setdefault(taken, []).append(nxt["energy"] - s["energy"])
    return {k: (sum(v) / len(v), len(v)) for k, v in groups.items()}


def main():
    measured = {}
    for label, rich, poor in (("narrow", 2.4, 1.6), ("wide", 2.8, 1.2)):
        print(f"{label} (rich {rich}, poor {poor}):")
        groups = by_taken(run(rich, poor, STEPS, 1))
        measured[label] = groups
        for k in sorted(groups):
            mean, n = groups[k]
            print(f"    taken {k:.3f}  mean delta {mean:+.4f}/step  n {n}")

    narrow = measured["narrow"]
    wide = measured["wide"]

    def at(groups, share):
        return next((v for k, v in groups.items() if abs(k - share) < 1e-6), None)

    n00 = at(narrow, 0.0)
    n08 = at(narrow, 0.08)
    n72 = at(narrow, 0.72)
    w00 = at(wide, 0.0)

    exp = Experiment(
        experiment_id="EXP-58",
        question=(
            "Is the per-step loss a constant, or a straight line in the share taken "
            "with intercept -0.63?"
        ),
        arithmetic={
            "cost": f"{MAINT} maintenance + {DAMAGE_RATE}*{REPAIR} damage = {COST}",
            "predicted_at_0.00": f"0.00 - {COST} = -0.63",
            "predicted_at_0.08": f"0.08 - {COST} = -0.55",
            "predicted_at_0.72": f"0.72 - {COST} = +0.09, capped by the energy ceiling",
            "claim": "delta = taken - 0.63, slope 1, intercept -0.63",
        },
        arms={"narrow": "rich=2.4 poor=1.6", "wide": "rich=2.8 poor=1.2"},
        seed=SEED,
        command="checks/exp58_second_share.py",
        parameters={"steps": STEPS, "n": N, "cells": CELLS, "field": "alternating"},
    )

    # Control fires: a share of zero must lose exactly the cost.
    fires = n00 is not None and abs(n00[0] + COST) < 0.01
    exp.control(
        "fires", fires,
        f"narrow field, taken = 0.000: {n00[0]:+.4f}/step (predicted {-COST:+.2f}), "
        f"n {n00[1]}" if n00 else "the narrow field has no group at taken = 0",
    )

    # Control silent: a share above the cost must gain, not lose. If a 0.72 share
    # also showed a loss, the intercept would be moving and the line would not be
    # the law. The energy ceiling holds it near zero, so the test is "not a loss".
    silent = n72 is not None and n72[0] > -0.05
    exp.control(
        "silent", silent,
        f"narrow field, taken = 0.720: {n72[0]:+.4f}/step; a share above the cost "
        f"must not lose, and the ceiling holds it near zero" if n72
        else "the narrow field has no group at taken = 0.72",
    )

    # Control specific: the slope must be 1. A share of 0.08 must lose 0.08 less
    # than a share of 0.00, not the same amount. If both lost 0.63 the loss would
    # be a constant and the finding note's reconstruction would be right.
    specific = (
        n00 is not None and n08 is not None
        and abs((n08[0] - n00[0]) - 0.08) < 0.02
    )
    exp.control(
        "specific", specific,
        f"the 0.08 share loses {n08[0] - n00[0]:+.4f} relative to the 0.00 share "
        f"(predicted +0.08); a constant loss would show 0.0000"
        if n00 and n08 else "one of the two shares is absent",
    )

    slope_is_one = specific

    if fires and silent and specific:
        exp.verdict(
            "passed",
            f"the loss is a straight line in the share taken: {n00[0]:+.4f} at 0.00 "
            f"and {n08[0]:+.4f} at 0.08, a gap of {n08[0] - n00[0]:+.4f} for a gap of "
            f"0.08 in the share. The loss is not a constant, so the 0.13/step in the "
            f"reconstruction cannot be the law",
        )
    else:
        exp.verdict(
            "failed",
            f"fires={fires} silent={silent} specific={specific}: the line "
            f"delta = taken - {COST} is not confirmed",
        )

    exp.limitation(
        "One seed (20250101). The trace records one share per organism per step, "
        "not its position in a queue, so 'second taker' is inferred from two "
        "organisms on one cell and is not directly observed here."
    )
    exp.limitation(
        "The 0.13/step in the finding note came from a uniform field at level 2.0, "
        "where there is only one level. That number is a reconstruction from "
        "EXP-56's death scene, not a measurement of a level dependence."
    )
    exp.limitation(
        "This does not explain why the queue length is 25, nor why E_max 9 and 10 "
        "show no late deaths, nor why the narrow field shows a 0.08 share where "
        "min(1.6 - 1.2, 1.2) = 0.4 would be predicted."
    )
    exp.save()


if __name__ == "__main__":
    main()
