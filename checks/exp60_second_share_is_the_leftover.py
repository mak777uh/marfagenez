"""The queue explains the shares: first taker 1.2, second 0.08, third nothing.

EXP-59 asked why the narrow field shows a share of 0.08 where the arithmetic
min(1.6 - 1.2, 1.2) = 0.4 predicts 0.4. The diagnostic answered it: the cell's
level at the moment of the take is 1.28, not 1.6, and two to eight organisms
stand on it.

1.28 = 1.6 * 0.8 and 1.92 = 2.4 * 0.8. The field is eaten every step and regrows
by 0.8 of the gap, so the level a taker sees is the nominal level times the
regrowth fraction, not the nominal level. The nominal values 2.4 and 1.6 are
ceilings, not the levels organisms meet.

With the level at 1.28 and income 1.2, take() is sequential:

    first taker:  min(1.28, 1.2) = 1.20   cell left 0.08
    second taker: min(0.08, 1.2) = 0.08   cell left 0.00
    third and later:             0.00

So the shares on the narrow field are 1.2, 0.08 and 0.0, in that order. The
0.08 share is not an anomaly; it is the second taker, and its size is the
leftover of the first take, which is set by the regrowth fraction.

THE ARITHMETIC

    nominal poor  1.6, regrow 0.8  ->  level seen 1.28
    nominal rich  2.4, regrow 0.8  ->  level seen 1.92
    income 1.2, cost 0.63

    first taker:  1.20 - 0.63 = +0.57   (capped, measures near 0)
    second taker: 0.08 - 0.63 = -0.55   (EXP-58 measured -0.5583)
    third:        0.00 - 0.63 = -0.63   (EXP-58 measured -0.6300)

THE PREDICTION THIS EXPERIMENT TESTS

If the 0.08 share is the second taker's leftover, then it must equal
level_seen - income, and it must move when the regrowth fraction moves. At
regrow 0.9 the level seen is 1.44, the first taker still takes 1.2, and the
second takes 0.24. At regrow 0.5 the level seen is 0.80, less than income, so the
first taker takes 0.80 and there is no second share at all.

That is the test: the second share is level_seen - income, and level_seen is
nominal * regrow. If the share stays at 0.08 across regrowth fractions, the
explanation is wrong.
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
REPAIR = 1.5
MOVE = 0.10
STEPS = 3000
SEED = 20250101
N = 160
CELLS = 40
POOR = 1.6
COST = MAINT + 0.02 * REPAIR  # 0.63


def run(regrow, steps, every):
    time.sleep(1.1)
    cmd = [
        TRACE,
        "--n", str(N), "--cells", str(CELLS),
        "--rich", "2.4", "--poor", str(POOR),
        "--regrow", str(regrow),
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--damage-rate", "0.02",
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


def shares(data):
    """The set of shares actually taken, and how often each occurs."""
    counts = {}
    frames = data["frames"]
    for a, b in zip(frames, frames[1:]):
        after = {s["slot"]: s for s in b["samples"]}
        for s in a["samples"]:
            if not s["alive"]:
                continue
            nxt = after.get(s["slot"])
            if nxt is None or not nxt["alive"]:
                continue
            k = round(nxt["taken"], 3)
            counts[k] = counts.get(k, 0) + 1
    return counts


def main():
    # regrow -> the level a taker sees on a poor cell, and the predicted shares
    arms = {
        "regrow-0.8": (0.8, 1.28, 1.20, 0.08),
        "regrow-0.9": (0.9, 1.44, 1.20, 0.24),
        "regrow-0.5": (0.5, 0.80, 0.80, None),
    }

    measured = {}
    for label, (regrow, seen, first, second) in arms.items():
        c = shares(run(regrow, STEPS, 1))
        measured[label] = c
        print(f"{label}: level seen {seen:.2f}, predicted first {first:.2f} "
              f"second {second if second is None else round(second, 2)}")
        for k in sorted(c):
            print(f"    taken {k:.3f}  n {c[k]}")

    c08 = measured["regrow-0.8"]
    c09 = measured["regrow-0.9"]
    c05 = measured["regrow-0.5"]

    def present(counts, share, tol=0.005):
        return any(abs(k - share) < tol and n > 10 for k, n in counts.items())

    # Control fires: at regrow 0.8 the second share is 1.28 - 1.20 = 0.08.
    fires = present(c08, 0.08)
    exp = Experiment(
        experiment_id="EXP-60",
        question=(
            "Is the 0.08 share the second taker's leftover, level_seen - income, "
            "where level_seen = nominal_poor * regrow?"
        ),
        arithmetic={
            "level_seen_0.8": f"{POOR} * 0.8 = 1.28",
            "level_seen_0.9": f"{POOR} * 0.9 = 1.44",
            "level_seen_0.5": f"{POOR} * 0.5 = 0.80",
            "first_share": f"min(level_seen, {INCOME})",
            "second_share_0.8": f"1.28 - {INCOME} = 0.08",
            "second_share_0.9": f"1.44 - {INCOME} = 0.24",
            "second_share_0.5": f"0.80 < {INCOME}, so no second share exists",
            "cost": f"{MAINT} + 0.02*{REPAIR} = {COST}",
        },
        arms={k: f"regrow={v[0]}" for k, v in arms.items()},
        seed=SEED,
        command="checks/exp60_second_share_is_the_leftover.py",
        parameters={"steps": STEPS, "n": N, "cells": CELLS, "field": "alternating"},
    )

    exp.control(
        "fires", fires,
        f"regrow 0.8 shows a share at 0.08: {sorted(c08)}",
    )

    # Control silent: at regrow 0.5 the level seen is 0.80, below income, so the
    # first taker takes 0.80 and NO second share can exist. The effect must be
    # absent there -- that is what makes it the regrowth leftover and not a
    # constant of the model.
    silent = present(c05, 0.80) and not present(c05, 0.08)
    exp.control(
        "silent", silent,
        f"regrow 0.5 shows a share at 0.80 and none at 0.08: {sorted(c05)}",
    )

    # Control specific: at regrow 0.9 the second share must be 0.24, not 0.08.
    # If it stayed at 0.08 the share would not follow the level seen.
    specific = present(c09, 0.24) and not present(c09, 0.08)
    exp.control(
        "specific", specific,
        f"regrow 0.9 shows a share at 0.24 and none at 0.08: {sorted(c09)}",
    )

    if fires and silent and specific:
        exp.verdict(
            "passed",
            f"the second share is the regrowth leftover: 0.08 at regrow 0.8, 0.24 "
            f"at 0.9, and no second share at 0.5 where the level seen falls below "
            f"income. The nominal levels 2.4 and 1.6 are ceilings, not the levels "
            f"organisms meet",
        )
    else:
        exp.verdict(
            "failed",
            f"fires={fires} silent={silent} specific={specific}: the share does not "
            f"follow level_seen - income",
        )

    exp.limitation(
        "One seed (20250101) and one field pair. The claim is about which shares "
        "exist and their size, not about how often each occurs."
    )
    exp.limitation(
        "The queue order is inferred from take() being sequential, not observed. The "
        "trace records the share, not the position in the queue."
    )
    exp.limitation(
        "This does not explain why the queue length is 25, nor why E_max 9 and 10 "
        "show no late deaths."
    )
    exp.save()


if __name__ == "__main__":
    main()
