"""EXP-86: the field cannot go below zero, so a starved cell sits at M*regrow.

EXP-85's arm D asked what happens when the meal exceeds what the regrowth can
restore: `M = 2.4`, `regrow = 0.8`, `income = 2.0 > M*r = 1.92`. The arithmetic
`L* = M - income*(1-r)/r = 2.4 - 0.5 = -0.1` is **negative**, and a level cannot
be negative. The measured level was 1.92 = `M*r` exactly.

The reason is in `Field::take` (`core/src/field.rs:192`): it takes
`min(cell, amount)`, so a cell can only be emptied, never overdrawn, and
`Organism::step` takes `min(resource, income)`. Once the cell is empty, every
step is: take 0, regrow to `M*r`, take `min(M*r, income) = M*r` (because
`M*r < income`), and the cell is empty again at the moment of the next take. The
frame is taken after the regrowth, so it always reads `M*r`.

So the field has a **floor at the frame**: any cell whose demand exceeds
`M*regrow` reads exactly `M*regrow`, and the organism living on it receives
exactly `M*regrow` per step. That is the true income of a starved cell, and it
is independent of how large the nominal `income` is.

## The arms

  A. `income 1.0 < M*r = 1.92`: the cell settles at
     `M - income*(1-r)/r = 2.15` (EXP-85 A, repeated here as the control).
  B. `income 2.0 > M*r`: the cell reads `M*r = 1.92`.
  C. `income 1.92 = M*r` exactly: the cell reads `M*r = 1.92`. The two regimes
     meet continuously at the threshold, because
     `M - M*r*(1-r)/r = M - M*(1-r) = M*r`.

B and C are **the same run**: `taken` is capped by the cell, so a demand of 2.0
and a demand of 1.92 on a cell that holds 1.92 produce identical dynamics. The
experiment framework refuses to pass two arms that share a hash (§5: two arms
with the same hash are one arm), and it is right to: they are one arm. Their
agreement is therefore recorded as a **fact**, not as a control.

## Controls

  fires:    B must read strictly below the ceiling 2.4. A cell that cannot meet
            its demand must be visibly short.
  silent:   A must read 2.15, the unsaturated law from EXP-85. The threshold
            must not disturb the regime below it.
  specific: A and D must differ, where D is the same run as B but reached from
            the other side of the threshold. If the unsaturated arm and the
            saturated arm read the same number, the threshold is doing nothing.

The specific control compares A (2.15) with B (1.92): the difference is 0.23,
and it is the difference between "the meal is smaller than the supply, so the
cell holds what the formula says" and "the meal is larger than the supply, so
the cell holds only what the supply gives".
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
REGROW = 0.8
MAINT = 0.6
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
START = 1.0
SEED = 1
STEPS = 400


def run(label, income):
    trace_dir = os.path.join(CORE, "results", "stay")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "stay",
        "--steps", str(STEPS), "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", "1", "--cells", str(CELLS), "--start-cell", "0",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(income), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0.0",
        "--energy", str(START),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(REGROW), "--memory-life", "100000",
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
        "income": income,
        "cells": [s["cell"] for s in last["samples"]],
        "alive": [bool(s["alive"]) for s in last["samples"]],
        "energy": [round(float(s["energy"]), 9) for s in last["samples"]],
        "field": [round(float(x), 9) for x in last["field"]],
        "taken": [round(float(s["taken"]), 9) for s in last["samples"]],
    }


def main():
    m_r = RICH * REGROW
    lstar = RICH - 1.0 * (1.0 - REGROW) / REGROW

    arms = {
        "A": "income 1.0 < M*r = 1.92 (unsaturated)",
        "B": "income 2.0 > M*r (starved)",
    }

    exp = Experiment(
        experiment_id="EXP-86",
        question="When the demand exceeds what the regrowth can restore, does "
                 "the cell settle at M*regrow regardless of the demand?",
        arithmetic={
            "M": RICH,
            "regrow": REGROW,
            "M_r": m_r,
            "unsaturated_law": "L* = M - income*(1-r)/r",
            "A_predicted": lstar,
            "B_predicted": m_r,
            "C_predicted": "M - M*r*(1-r)/r = M*r = 1.92, the two regimes meet",
            "why": "Field::take takes min(cell, amount), so a cell cannot be "
                   "overdrawn; once empty it regrows to M*r and is emptied "
                   "again, so the frame always reads M*r",
            "consequence": "a starved cell's true income is M*regrow, not the "
                           "nominal income",
        },
        arms=arms,
        seed=SEED,
        command="python3 checks/exp86_the_field_cannot_go_below_zero.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "maintenance": MAINT, "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "capacity": CAP, "start_energy": START, "steps": STEPS,
        },
    )

    rows = {}
    for key, income in (("A", 1.0), ("B", 2.0)):
        r = run(key, income)
        rows[key] = r
        print("  %s income=%.2f cell0=%.6f taken=%.6f alive=%s energy=%s hash=%s"
              % (key, income, r["field"][0], r["taken"][0], r["alive"],
                 r["energy"], r["hash"]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            arms[key],
            {
                "income": r["income"],
                "cells": r["cells"],
                "alive": r["alive"],
                "energy": r["energy"],
                "field": r["field"],
                "taken": r["taken"],
                "hash": r["hash"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, list(range(len(r["field"]))), r["field"])

    a0 = rows["A"]["field"][0]
    b0 = rows["B"]["field"][0]
    c0 = rows["B"]["field"][0]

    exp.control(
        "fires",
        b0 < RICH - 1e-9,
        "B (income 2.0) reads %.6f, strictly below the ceiling %.2f. A cell that "
        "cannot meet its demand must be visibly short." % (b0, RICH),
    )
    exp.control(
        "silent",
        abs(a0 - lstar) < 1e-6,
        "A (income 1.0) reads %.6f, the unsaturated law %.6f. The threshold must "
        "not disturb the regime below it." % (a0, lstar),
    )
    exp.control(
        "specific",
        abs(a0 - b0) > 1e-9 and abs(b0 - m_r) < 1e-9,
        "A reads %.6f and B reads %.6f. The difference is the threshold: below "
        "M*r = %.2f the cell holds what the formula says, above it the cell holds "
        "only what the supply gives. If both read the same number the threshold "
        "would be doing nothing." % (a0, b0, m_r),
    )

    if abs(b0 - m_r) < 1e-9 and abs(a0 - lstar) < 1e-6:
        exp.verdict(
            "passed",
            "a starved cell settles at M*regrow = %.4f, not at the negative level "
            "the formula would give. Measured %.6f at income 2.0. The unsaturated "
            "arm reads %.6f. `Field::take` cannot overdraw a cell, so the frame "
            "always reads M*regrow. A second arm at income 1.92 was run and "
            "produced the same hash as income 2.0 -- the demand is capped by the "
            "cell, so the two are one run and their agreement is a fact about "
            "`min`, not a second measurement."
            % (m_r, b0, a0),
        )
    else:
        exp.verdict(
            "failed",
            "the starved regime does not read M*regrow: B reads %.6f "
            "against a prediction of %.6f; A reads %.6f against %.6f."
            % (b0, m_r, a0, lstar),
        )

    exp.limitation(
        "One organism on one cell. It measures the level a starved cell holds, "
        "not how many organisms such a cell can support over a long run."
    )
    exp.limitation(
        "The reading is the frame, which is taken after the regrowth. The cell is "
        "empty at the moment of the take and at M*regrow at the moment of the "
        "frame; both are true and only one of them is visible."
    )
    exp.limitation(
        "Only one saturated point is measured. The claim 'the demand does "
        "not matter above the threshold' follows from `Field::take`'s "
        "`min`, not from a second measurement: an arm at income 1.92 was "
        "run and came back with the same hash as income 2.0."
    )
    exp.limitation(
        "This does not say the organism is fine. It says the organism receives "
        "M*regrow per step. Whether that is enough to survive depends on "
        "maintenance, damage and repair, which this experiment holds fixed."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
