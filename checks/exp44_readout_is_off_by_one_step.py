# -*- coding: utf-8 -*-
"""EXP-44: the extra 0.2 is the move cost, paid even when the cell does not change.

EXP-43 tried to explain a 0.4 drop with repair, but the trace shows `damage` is
0.0 in every frame - before and after.  So repair is not paying anything.  The
cross-tab of the 26 recorded steps:

    direction  moved  drop  count
       -1      False  0.2     4
       -1      False  0.4     1
       -1      True   0.4     3
        0      False  0.2     4
        0      False  0.4     2      <-- no direction, no move, still 0.4
        0      True   0.4     2      <-- no direction, but the cell changed
        1      False  0.2     2
        1      False  0.4     2
        1      True   0.4     6

Two rows do not fit any simple story: `direction 0` with a 0.4 drop and no move,
and `direction 0` with a change of cell.  That means `direction` in the trace is
NOT the decision that was applied on the step the drop is measured against.

The reason is the readout, not the model.  `samples()` is taken from outside
after `advance()` has finished, and it reports `r.last_direction` - the decision
of the step that just ran.  But the frame is numbered `self.step`, which
`advance` increments at the END.  So frame k carries the decision of step k and
the energy AFTER step k, while the drop between frame k and frame k+1 is the
cost of step k+1.  Comparing `direction` of frame k with the drop to frame k+1
is off by one step.

Test: shift the alignment by one and see whether the two impossible rows
disappear.  If `direction` from frame k+1 predicts the drop from frame k to
frame k+1, then

    drop = 0.2 + move_cost * (direction != 0)

must hold on every step, with no exceptions.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

COMMON = ["--steps", "40", "--every", "1", "--capacity", "10",
          "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
          "--energy", "5", "--field", "uniform", "--seed", "1",
          "--income", "0", "--regrow", "0", "--policy", "random"]


def run(extra):
    out = subprocess.run([str(BIN)] + COMMON + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def rows_of(r, move_cost):
    frames = [f for f in r["frames"] if f["samples"][0]["alive"]]
    out = []
    for a, b in zip(frames, frames[1:]):
        sa, sb = a["samples"][0], b["samples"][0]
        out.append({
            "step": b["step"],
            "dir_prev": sa["direction"],      # alignment used so far
            "dir_next": sb["direction"],      # alignment one step later
            "moved": sa["cell"] != sb["cell"],
            "drop": round(sa["energy"] - sb["energy"], 6),
        })
    return out


def main():
    arms = {}
    for cells in (2, 120):
        r = run(["--n", "1", "--cells", str(cells), "--move-cost", "0.2"])
        arms[f"cells{cells}"] = rows_of(r, 0.2)
        print(f"cells {cells}: {len(arms[f'cells{cells}'])} steps")

    exp = Experiment(
        experiment_id="readout-is-off-by-one-step",
        question="Совпадает ли решение, записанное в кадре, с шагом, за который посчитана цена?",
        arithmetic={
            "step_cost": "0.1 (maintenance) + 0.2 (damage_rate*repair_cost) = 0.2",
            "moving": "+ move_cost = 0.2",
            "prediction": "drop = 0.2 + 0.2*(direction != 0), direction from the LATER frame",
        },
        arms={k: f"one organism, no food, {k}" for k in arms},
        seed=1,
        command="python3 checks/exp44_readout_is_off_by_one_step.py",
        parameters={"steps": 40, "capacity": 10, "damage_rate": 0.2,
                    "maintenance": 0.1, "repair_cost": 0.5, "energy": 5,
                    "field": "uniform", "income": 0, "regrow": 0,
                    "policy": "random", "move_cost": 0.2, "cells": "2 or 120"},
    )
    for key, rows in arms.items():
        exp.add_arm(key, key, {"rows": rows, "n": len(rows)}, trace_hash=None)

    allrows = arms["cells2"] + arms["cells120"]
    prev_err = [round(x["drop"] - (0.2 + 0.2 * (x["dir_prev"] != 0)), 6) for x in allrows]
    next_err = [round(x["drop"] - (0.2 + 0.2 * (x["dir_next"] != 0)), 6) for x in allrows]
    prev_bad = sum(1 for e in prev_err if abs(e) > 1e-9)
    next_bad = sum(1 for e in next_err if abs(e) > 1e-9)
    print(f"alignment frame k:   {prev_bad} bad of {len(allrows)}")
    print(f"alignment frame k+1: {next_bad} bad of {len(allrows)}")

    # Control 1 (fires): the old alignment really does break - otherwise there is
    # nothing to explain.
    exp.control("fires", prev_bad > 0,
                f"frame-k alignment: {prev_bad} of {len(allrows)} steps disagree")

    # Control 2 (silent): the drop is never anything but 0.2 or 0.4 - no third
    # cost is hiding in the model.
    exp.control("silent", set(x["drop"] for x in allrows) <= {0.2, 0.4},
                f"distinct drops {sorted(set(x['drop'] for x in allrows))}")

    # Control 3 (specific): with the later frame's decision, every step agrees.
    exp.control("specific", next_bad == 0,
                f"frame-(k+1) alignment: {next_bad} of {len(allrows)} steps disagree")

    exp.limitation(
        "one organism, no food; this fixes the alignment of the readout, it does not "
        "say whether the same off-by-one affects other fields of the sample"
    )
    ok = prev_bad > 0 and next_bad == 0
    exp.verdict("passed" if ok else "failed",
                "решение в кадре относится к следующему шагу: цена сходится при сдвиге на один")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
