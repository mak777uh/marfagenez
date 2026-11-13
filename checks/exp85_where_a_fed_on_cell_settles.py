"""EXP-85: a fed-on cell settles at M - income*(1-regrow)/regrow, not at M.

EXP-84 showed frame 0 of a `stay` run reading 2.2 on a rich cell of 2.4 and
2.16 on the second step. The arithmetic says the level at which a meal and the
regrowth balance is

    L* = (L* - income) + (M - (L* - income)) * regrow
       => L* = M - income * (1 - regrow) / regrow        (regrow > 0)

For M = 2.4, income = 1.0, regrow = 0.8: L* = 2.4 - 1.0 * 0.2 / 0.8 = 2.15.
EXP-66 measured 2.15 on a full ring. This experiment asks the same question
from the command line now that `--start-cell` exists, so the placement can be
chosen and the settled level can be read per cell rather than inferred.

The law has three regimes that must be distinguished:

    regrow = 0    L* = -infinity (the cell never comes back; it empties)
    regrow = 1    L* = M          (the cell is restored completely each step)
    0 < r < 1     L* = M - income*(1-r)/r  (a finite level strictly below M)

and it is only valid while `L* >= 0`. When `income > M*r`, the arithmetic gives
`L* < 0`, which is not a level the field can hold: the cell empties and the
organism must move or starve. The threshold is exactly `income = M*r`, which is
the same condition `Capacity.lean` states for `0 <= c*`.

## The arms

  A. rich cell 2.4, regrow 0.8, income 1.0, 400 steps, `--start-cell 0`.
     Predicted settled level 2.15.
  B. regrow 1.0, everything else equal. Predicted settled level 2.40.
  C. regrow 0.0, everything else equal. Predicted the cell empties (0.0).
  D. regrow 0.8 but income 2.0 > M*r = 1.92. Predicted the cell empties and the
     organism starves, because the level that would balance is negative.

The specific test is (A, B): the same meal, the same cell, and only the regrow
differs. If A settles at 2.15 and B at 2.40, the settled level is a property of
the meal and the regrowth, not of the ceiling.

## Controls

  fires:    A must settle strictly below its ceiling 2.4. A cell that is eaten
            every step and regrows at 0.8 cannot stay at 2.4.
  silent:   B (regrow 1.0) must settle at exactly 2.4. A full regrowth must
            hide the meal completely.
  specific: A and B must differ by exactly `income*(1-r)/r = 0.25`, and A must
            not be the midpoint of anything else -- the prediction has no free
            parameter.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

CELLS = 4
RICH = 2.4
POOR = 1.6
INCOME = 1.0
MAINT = 0.6
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
START = 1.0
SEED = 1
STEPS = 400


def run(label, regrow, income, start_cell):
    trace_dir = os.path.join(CORE, "results", "stay")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "stay",
        "--steps", str(STEPS), "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", "1", "--cells", str(CELLS), "--start-cell", str(start_cell),
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(income), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0.0",
        "--energy", str(START),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(regrow), "--memory-life", "100000",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("%s: trace failed: %s" % (label, out.stderr[-1500:]))
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    if not after:
        raise RuntimeError("%s: no new trace" % label)
    path = max(after, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    return {
        "hash": digest,
        "label": label,
        "regrow": regrow,
        "income": income,
        "start_cell": start_cell,
        "cells": [s["cell"] for s in last["samples"]],
        "alive": [bool(s["alive"]) for s in last["samples"]],
        "energy": [round(float(s["energy"]), 9) for s in last["samples"]],
        "field": [round(float(x), 9) for x in last["field"]],
        "taken": [round(float(s["taken"]), 9) for s in last["samples"]],
        "frames": len(data["frames"]),
    }


def main():
    arms = {
        "A": "rich cell 0, regrow 0.8, income 1.0, 400 steps",
        "B": "rich cell 0, regrow 1.0, income 1.0, 400 steps",
        "C": "rich cell 0, regrow 0.0, income 1.0, 400 steps",
        "D": "rich cell 0, regrow 0.8, income 2.0 (> M*r = 1.92), 400 steps",
    }
    lstar = RICH - INCOME * (1.0 - 0.8) / 0.8
    lstar_full = RICH
    lstar_d = RICH - 2.0 * (1.0 - 0.8) / 0.8

    exp = Experiment(
        experiment_id="EXP-85",
        question="Does a cell that is eaten every step settle at "
                 "M - income*(1-regrow)/regrow, rather than at its ceiling M?",
        arithmetic={
            "law": "L* = M - income*(1-regrow)/regrow  (0 < regrow < 1, L* >= 0)",
            "M": RICH,
            "income": INCOME,
            "regrow_A": 0.8,
            "L*_A": lstar,
            "regrow_B": 1.0,
            "L*_B": lstar_full,
            "regrow_C": 0.0,
            "L*_C": "regrow 0 leaves (M - income) forever: the cell empties",
            "regrow_D": 0.8,
            "income_D": 2.0,
            "L*_D": lstar_d,
            "threshold": "L* >= 0  <=>  income <= M*regrow = 1.92",
            "note": "the same threshold as Capacity.lean's 0 <= c*",
        },
        arms=arms,
        seed=SEED,
        command="python3 checks/exp85_where_a_fed_on_cell_settles.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "income": INCOME,
            "maintenance": MAINT, "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "capacity": CAP, "start_energy": START, "steps": STEPS,
        },
    )

    rows = {}
    for key, regrow, income in (("A", 0.8, 1.0), ("B", 1.0, 1.0),
                                ("C", 0.0, 1.0), ("D", 0.8, 2.0)):
        r = run(key, regrow, income, 0)
        rows[key] = r
        print("  %s regrow=%.2f income=%.2f cell0=%.6f alive=%s energy=%s"
              % (key, regrow, income, r["field"][0], r["alive"], r["energy"]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            arms[key],
            {
                "regrow": r["regrow"],
                "income": r["income"],
                "start_cell": r["start_cell"],
                "cells": r["cells"],
                "alive": r["alive"],
                "energy": r["energy"],
                "field": r["field"],
                "taken": r["taken"],
                "frames": r["frames"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, list(range(len(r["field"]))), r["field"])

    a0 = rows["A"]["field"][0]
    b0 = rows["B"]["field"][0]
    c0 = rows["C"]["field"][0]
    d0 = rows["D"]["field"][0]

    exp.control(
        "fires",
        a0 < RICH - 1e-9,
        "A (regrow 0.8) settles at %.6f, strictly below the ceiling %.2f. A cell "
        "eaten every step and regrown at 0.8 cannot stay at its ceiling." % (a0, RICH),
    )
    exp.control(
        "silent",
        abs(b0 - RICH) < 1e-9,
        "B (regrow 1.0) settles at %.6f, exactly the ceiling %.2f. A complete "
        "regrowth hides the meal." % (b0, RICH),
    )
    exp.control(
        "specific",
        abs((b0 - a0) - INCOME * (1.0 - 0.8) / 0.8) < 1e-9,
        "B - A = %.6f and income*(1-regrow)/regrow = %.6f. The prediction has no "
        "free parameter: it is the meal times the fraction the regrowth does not "
        "restore, divided by that same fraction."
        % (b0 - a0, INCOME * (1.0 - 0.8) / 0.8),
    )

    ok = (
        abs(a0 - lstar) < 1e-6
        and abs(b0 - RICH) < 1e-9
        and c0 < 1e-9
        and d0 < 1e-9
    )
    if ok:
        exp.verdict(
            "passed",
            "a fed-on cell settles at M - income*(1-regrow)/regrow. Measured "
            "%.4f against a prediction of %.4f with no free parameter; regrow 1.0 "
            "settles at the ceiling %.4f; regrow 0.0 empties the cell to %.4f; and "
            "income 2.0 > M*regrow = 1.92 empties it to %.4f, which is the same "
            "threshold Capacity.lean states for 0 <= c*."
            % (a0, lstar, b0, c0, d0),
        )
    else:
        exp.verdict(
            "failed",
            "the settled level does not follow M - income*(1-regrow)/regrow: "
            "A reads %.6f (predicted %.6f), B reads %.6f (predicted %.6f), "
            "C reads %.6f (predicted 0), D reads %.6f (predicted 0)."
            % (a0, lstar, b0, RICH, c0, d0),
        )

    exp.limitation(
        "One organism on one rich cell. It measures the settled level of a cell, "
        "not the capacity of a field: how many organisms can live on this level "
        "is a different question and is not touched here."
    )
    exp.limitation(
        "The law assumes the organism eats `income` every step and never moves. "
        "A moving organism samples several cells and the level it leaves behind "
        "depends on its path; EXP-66's 2.15 on a full ring is the same law but "
        "reached by a different route."
    )
    exp.limitation(
        "`income > M*regrow` empties the cell, but this experiment does not "
        "follow the organism after that. Whether it starves or finds another "
        "cell is the subject of the capacity experiments."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
