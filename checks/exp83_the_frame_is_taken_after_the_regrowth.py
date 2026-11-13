"""EXP-83: the frame is taken after the regrowth, so it never shows a meal.

EXP-82 read the trace's own echo of its field and found that the echo is not
the field that was asked for:

    A  --field alternating --rich 2.4 --poor 1.6   levels [2.2, 1.6, 2.2, 1.6]
    B  --field uniform    --rich 1.6 --poor 1.6    levels [1.6, 1.6, 1.6, 1.4]
    D  no --field flag                             levels [1.8, 0.2, 1.8, 0.2]

`Field::alternating(4, 2.4, 1.6, 0.8)` sets `cells = [2.4, 1.6, 2.4, 1.6]` and
`ceil = [2.4, 1.6, 2.4, 1.6]` (`core/src/field.rs:85-94`). Nothing in the
constructor produces 2.2. And 2.2 is exactly

    c + (ceil - c) * regrow = 1.6 + (2.4 - 1.6) * 0.8 = 2.2

so the echo is the field **after one regrowth from a poor cell**. In B the
uniform level is `(1.6 + 1.6) / 2 = 1.6` everywhere, and the echo is
`[1.6, 1.6, 1.6, 1.4]`: one cell at 1.4, which is `0.0 + (1.6 - 0.0) * 0.875`
or more simply a cell that was eaten empty and then regrew by 0.8. In D the
default is `rich 2.0, poor 0.2`, so the echo `[1.8, 0.2, 1.8, 0.2]` is
`0.2 + (2.0 - 0.2) * 0.888...` -- the default field, one regrowth in.

So the flags DO reach the field. What does not reach the reader is the field
**before** the first step. `trace.rs` builds the field, then runs the steps,
then records frames; `snapshot` reads `field.level(i)` at the moment the frame
is taken, which is after `Life::advance` has already eaten and regrown. The
first frame is therefore not "the field at step 0", it is "the field after one
step", and there is no frame that shows the field as it was built.

That is not a bug in the model. It is a bug in the instrument, and it has a
consequence that matters: **a frame can never show a cell at the moment it was
eaten.** The eat happens, the regrowth happens, and only then is the picture
taken. Every reading in this project that used the field to see "how much food
is left" saw the field 0.8 of the way back to full, not the field after the
meal. With `regrow = 0.8` the visible drop after eating `income = 1.0` from a
rich cell is `0.2`, not `1.0` -- a fifth of the truth.

## The arms

  A. `--field alternating --rich 2.4 --poor 1.6 --regrow 0.8`, `--steps 1`,
     `--every 1`, no organisms (`--n 0` is refused, so one organism on a cell
     that is not the one being watched). Read frame 0's levels.
     Prediction: `[2.2, 1.6, 2.2, 1.6]` -- rich cells at `1.6 + 0.8*0.8`.
  B. Same with `--regrow 0.0`. Prediction: `[1.6, 1.6, 1.6, 1.6]` -- with no
     regrowth the eaten cell stays eaten, and the echo shows the meal.
  C. Same with `--regrow 1.0`. Prediction: `[2.4, 1.6, 2.4, 1.6]` -- a full
     regrowth restores the ceiling and the meal is invisible again.
  D. `--field alternating --rich 2.4 --poor 1.6 --regrow 0.8` with `--steps 1`
     and the organism placed on a POOR cell: the poor cell is eaten to 0.6 and
     regrows to `0.6 + 0.8*1.0 = 1.4`, so the echo must show a 1.4.

The specific test is (A, B, C): the same field, the same meal, and the only
difference is `regrow`. If the echo tracks `regrow` as
`level = after_meal + (ceil - after_meal) * regrow`, the echo is a post-meal
post-regrowth reading and the instrument is understood.

## Controls

  fires:    B must show a cell at 1.6 where A shows 2.2. With `regrow = 0` the
            meal must be visible.
  silent:   C must show `[2.4, 1.6, 2.4, 1.6]`. A full regrowth must hide the
            meal completely, which is the claim.
  specific: A must equal `1.6 + 0.8 * (2.4 - 1.6) = 2.2` exactly, not 2.4 and
            not 1.6.

## What this does not prove

It does not say the model is wrong. The model eats, then regrows, and that
order is a design choice (`docs/FINDING-the-cap-is-applied-after-the-spend.md`
is the same shape of choice for the cap). It says the trace cannot show the
meal, and any conclusion drawn from "the field looks nearly full" is a
conclusion about the regrowth fraction, not about the eating.
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


def run(label, regrow, field="alternating"):
    trace_dir = os.path.join(CORE, "results", "stay")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "stay",
        "--steps", "1", "--every", "1",
        "--seed", str(SEED),
        "--n", "1", "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0.0",
        "--energy", str(START),
        "--field", field, "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(regrow), "--memory-life", "100000",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("%s: trace failed: %s" % (label, out.stderr[-1200:]))
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
    frames = data["frames"]
    return {
        "hash": digest,
        "label": label,
        "regrow": regrow,
        "levels0": [round(x, 9) for x in frames[0]["field"]],
        "levels_last": [round(x, 9) for x in frames[-1]["field"]],
        "cells": [s["cell"] for s in frames[0]["samples"]],
        "taken": [s["taken"] for s in frames[0]["samples"]],
        "energy": [s["energy"] for s in frames[0]["samples"]],
    }


def main():
    arms = {
        "A": "alternating 2.4/1.6, regrow 0.8, 1 step, stay on cell 0",
        "B": "alternating 2.4/1.6, regrow 0.0, 1 step, stay on cell 0",
        "C": "alternating 2.4/1.6, regrow 1.0, 1 step, stay on cell 0",
        "D": "alternating 2.4/1.6, regrow 0.8, 1 step, stay on cell 1 (poor)",
    }
    exp = Experiment(
        experiment_id="EXP-83",
        question="The trace's first frame shows a field that is not the field "
                 "that was built. Is the frame taken after the regrowth?",
        arithmetic={
            "built_alternating": [RICH, POOR, RICH, POOR],
            "ceil": [RICH, POOR, RICH, POOR],
            "income": INCOME,
            "organism_cell": 0,
            "after_meal_cell0": RICH - INCOME,
            "regrow_0.8_level0": (RICH - INCOME) + (RICH - (RICH - INCOME)) * 0.8,
            "regrow_0.0_level0": (RICH - INCOME) + (RICH - (RICH - INCOME)) * 0.0,
            "regrow_1.0_level0": (RICH - INCOME) + (RICH - (RICH - INCOME)) * 1.0,
            "visible_drop_at_0.8": (RICH - INCOME) + (RICH - (RICH - INCOME)) * 0.8 - RICH,
            "note": "the visible drop after eating income from a rich cell is "
                    "-(1 - regrow) * income, not -income",
        },
        arms=arms,
        seed=SEED,
        command="python3 checks/exp83_the_frame_is_taken_after_the_regrowth.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "income": INCOME,
            "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "start_energy": START,
            "steps": 1,
        },
    )

    rows = {}
    for key, regrow in (("A", 0.8), ("B", 0.0), ("C", 1.0), ("D", 0.8)):
        r = run(key, regrow)
        rows[key] = r
        print("  %s regrow=%.1f cells=%s taken=%s levels0=%s"
              % (key, regrow, r["cells"], r["taken"], r["levels0"]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            "%s" % arms[key],
            {
                "regrow": r["regrow"],
                "levels_frame0": r["levels0"],
                "organism_cells": r["cells"],
                "taken": r["taken"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, [0], [r["levels0"][0]])

    a0 = rows["A"]["levels0"][0]
    b0 = rows["B"]["levels0"][0]
    c0 = rows["C"]["levels0"][0]
    d1 = rows["D"]["levels0"][1]

    exp.control(
        "fires",
        abs(b0 - (RICH - INCOME)) < 1e-9,
        "B (regrow 0.0) shows cell 0 at %.6f; with no regrowth the eaten cell "
        "must stay eaten at %.6f." % (b0, RICH - INCOME),
    )
    exp.control(
        "silent",
        abs(c0 - RICH) < 1e-9,
        "C (regrow 1.0) shows cell 0 at %.6f; a full regrowth must restore the "
        "ceiling %.6f and hide the meal completely." % (c0, RICH),
    )
    exp.control(
        "specific",
        abs(a0 - 2.2) < 1e-9 and abs(d1 - 1.4) < 1e-9,
        "A (regrow 0.8) shows cell 0 at %.6f (predicted 2.2 = 1.4 + 0.8*1.0) "
        "and D shows the poor cell 1 at %.6f (predicted 1.4 = 0.6 + 0.8*1.0). "
        "The echo tracks regrow exactly, so it is a post-meal post-regrowth "
        "reading." % (a0, d1),
    )

    if abs(b0 - (RICH - INCOME)) < 1e-9 and abs(c0 - RICH) < 1e-9 \
            and abs(a0 - 2.2) < 1e-9 and abs(d1 - 1.4) < 1e-9:
        exp.verdict(
            "passed",
            "the frame is taken after the regrowth. The same meal leaves "
            "%.2f at regrow 0.0, %.2f at regrow 0.8 and %.2f at regrow 1.0 -- "
            "the model eats and then regrows, and the trace can only photograph "
            "the result. The visible drop after eating %.1f from a rich cell is "
            "%.1f, not %.1f, so every reading of the field as 'nearly full' was "
            "reading the regrowth fraction and not the eating."
            % (b0, a0, c0, INCOME, RICH - a0, INCOME),
        )
    else:
        exp.verdict(
            "failed",
            "the echo does not track regrow as the arithmetic says: regrow 0.0 "
            "gives %.6f (predicted %.6f), 0.8 gives %.6f (predicted 2.2), 1.0 "
            "gives %.6f (predicted %.6f), and the poor cell gives %.6f "
            "(predicted 1.4). The frame is not simply post-regrowth."
            % (b0, RICH - INCOME, a0, c0, RICH, d1),
        )

    exp.limitation(
        "One step on four cells. It shows that the first frame is post-regrowth; "
        "it does not measure how much food is really in the field over a run."
    )
    exp.limitation(
        "It does not say the ordering is wrong. Eat-then-regrow is a choice, and "
        "the same choice that puts the cap after the spend. It says the trace "
        "cannot show the meal, so a claim about depletion has to be made from "
        "`taken` and not from the field."
    )
    exp.limitation(
        "`--regrow 1.0` restores the ceiling every step, so the field is a "
        "constant and the organisms never deplete anything. That arm is a "
        "control, not a world."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
