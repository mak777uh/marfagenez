"""EXP-64: why does a gradient field hold fewer organisms than an alternating one?

EXP-62 measured, at 20k steps and mean level 2.0:
    uniform      50 alive
    gradient     33 alive   <- worst
    alternating  60 alive   <- best

Walking toward food should help, so the gradient being worst is a surprise.
This experiment separates two accounts.

Account A: the poor end is below what an organism needs.
  A cell at level L gives `take = min(L, income)`. An organism needs
  `need + move_cost + damage*repair = 0.6 + 0.05 + 0.02*0.5 = 0.66` per step.
  If `L < 0.66` the cell cannot pay for a step even without moving, and an
  organism standing there must leave or die. The gradient's poor end is 1.6 and
  the alternating field's poor cells are also 1.6, so this account predicts the
  two fields should behave alike at their poor end -- and they do not, so
  something else is going on.

Account B: the walk is long.
  In a gradient the rich end is far from the poor end, so an organism that
  climbs pays `move_cost` for many steps. In an alternating field a rich cell is
  always adjacent, so the walk is one step. If Account B holds, the mean number
  of moves per organism should be much higher in the gradient, and the alive
  count should fall when `move_cost` rises in the gradient but not in the
  alternating field.

This experiment tests Account B directly: run both fields at three move costs.

Arms: {gradient, alternating} x {move_cost 0.0, 0.05, 0.20}

Prediction if B holds: in the gradient, alive falls sharply as move_cost rises;
in the alternating field it barely moves.
Prediction if B is wrong: both fields respond the same way to move_cost.

Controls:
  fires     -- at move_cost 0.0 the gradient is no longer worst: with a free
               step, distance stops mattering and the two fields should be
               closer than at 0.05
  silent    -- n=40 on a uniform field at move_cost 0.20 still gives 40 alive
               and no doubling: with no crowding there is nothing to lose
  specific  -- the gradient's alive count changes across the three move costs
               by more than the alternating field's does
"""

import json
import os
import subprocess

from experiment import Experiment
from result import CONTROL_TESTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 40
SEED = 7
STEPS = 50000
EVERY = 2500
OUTDIR = os.path.join(ROOT, "results", "EXP-64")


def run(field, move_cost, n=80, steps=STEPS):
    os.makedirs(OUTDIR, exist_ok=True)
    rich, poor = ("2.0", "2.0") if field == "uniform" else ("2.4", "1.6")
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(EVERY), "--seed", str(SEED), "--n", str(n),
           "--cells", str(CELLS), "--rich", rich, "--poor", poor,
           "--income", "1.0", "--maintenance", "0.6",
           "--damage-rate", "0.02", "--repair-cost", "0.5",
           "--move-cost", str(move_cost), "--energy", "10.0",
           "--field", field, "--read-budget", "3",
           "--memory-life", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit("trace failed %s mc=%s:\n%s" % (field, move_cost, out.stderr))
    written, h = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            h = line.split(":", 1)[1].strip()
    d = json.load(open(os.path.join(ROOT, written)))
    d["_hash"] = h
    return d


def census(frame):
    occ = {}
    for s in frame["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    alive = sum(occ.values())
    doubled = sum(1 for v in occ.values() if v >= 2)
    moved = sum(1 for s in frame["samples"] if s["alive"] and s.get("direction", 0) != 0)
    return alive, doubled, moved


def series(trace):
    return [census(fr)[0] for fr in trace["frames"]]


def main():
    ex = Experiment(
        experiment_id="EXP-64",
        question=(
            "Why does a gradient field hold fewer organisms (33) than an "
            "alternating one (60)? Account B says the walk is long in a "
            "gradient and one step in an alternating field, so the gradient "
            "should be hurt more by move_cost."
        ),
        arithmetic={
            "step_cost": "need + move_cost + damage*repair = 0.6 + 0.05 + 0.01 = 0.66",
            "step_cost_no_move": "0.6 + 0.01 = 0.61",
            "poor_cell_take_at_1.6": "min(1.6, income 1.0) = 1.0",
            "gradient_span": "2.4 - 1.6 = 0.8 over 40 cells = 0.02 per cell",
            "steps_to_cross_gradient": "0.8 / 0.02 = 40 steps",
            "alternating_step": "every rich cell is 1 step from a poor cell",
            "food_ceiling": "cells * M * r = 40 * 1.6 = 64 per round",
        },
        arms={
            "g0.00": "gradient, move_cost 0.00",
            "g0.05": "gradient, move_cost 0.05",
            "g0.20": "gradient, move_cost 0.20",
            "a0.00": "alternating, move_cost 0.00",
            "a0.05": "alternating, move_cost 0.05",
            "a0.20": "alternating, move_cost 0.20",
            "u0.20-n40": "uniform, move_cost 0.20, n=40",
        },
        seed=SEED,
        command="trace --policy sighted --cells 40 --steps 50000 "
                "--field {gradient,alternating} --move-cost {0.0,0.05,0.20}",
    )

    res = {}
    for field, tag in (("gradient", "g"), ("alternating", "a")):
        for mc in (0.0, 0.05, 0.20):
            key = "%s%.2f" % (tag, mc)
            tr = run(field, mc)
            alive, doubled, moved = census(tr["frames"][-1])
            s = series(tr)
            res[key] = dict(alive=alive, doubled=doubled, moved=moved,
                            series=s, hash=tr.get("_hash"))
            ex.add_arm(key, "%s, move_cost %.2f" % (field, mc), {
                "alive": alive,
                "doubled_cells": doubled,
                "moving_at_end": moved,
                "alive_at_half": s[len(s) // 2],
            }, trace_hash=tr.get("_hash"))

    tr40 = run("uniform", 0.20, n=40)
    a40, d40, m40 = census(tr40["frames"][-1])
    ex.add_arm("u0.20-n40", "uniform, move_cost 0.20, n=40", {
        "alive": a40, "doubled_cells": d40, "moving_at_end": m40,
    }, trace_hash=tr40.get("_hash"))

    g0, g5, g20 = res["g0.00"]["alive"], res["g0.05"]["alive"], res["g0.20"]["alive"]
    a0, a5, a20 = res["a0.00"]["alive"], res["a0.05"]["alive"], res["a0.20"]["alive"]

    ex.control(
        "fires",
        abs(g0 - a0) < abs(g5 - a5),
        "at move_cost 0.00 gradient %d vs alternating %d (gap %d); "
        "at 0.05 gradient %d vs alternating %d (gap %d). A free step should "
        "shrink the gap if distance is what hurts the gradient."
        % (g0, a0, abs(g0 - a0), g5, a5, abs(g5 - a5)),
    )
    ex.control(
        "silent",
        a40 == 40 and d40 == 0,
        "uniform n=40 at move_cost 0.20: %d alive, %d doubled" % (a40, d40),
    )
    g_drop = g0 - g20
    a_drop = a0 - a20
    ex.control(
        "specific",
        g_drop > a_drop,
        "gradient falls %d (from %d to %d) as move_cost goes 0.00 -> 0.20; "
        "alternating falls %d (from %d to %d). Account B predicts the "
        "gradient is hurt more." % (g_drop, g0, g20, a_drop, a0, a20),
    )

    ex.limitation(
        "move_cost also changes how many organisms can afford to move at all, "
        "so a fall in alive count is not attributable to distance alone."
    )
    ex.limitation(
        "One seed and 50k steps. EXP-63 showed a population can still be "
        "falling at 20k, so these counts may not be steady states."
    )
    ex.limitation(
        "The gradient and alternating fields differ in shape, not only in "
        "distance: the gradient's rich cells are contiguous, the alternating "
        "field's are isolated. The two accounts cannot be fully separated by "
        "move_cost alone."
    )

    if ex.controls_passed():
        ex.verdict(
            "passed",
            "gradient alive %d/%d/%d and alternating %d/%d/%d at move_cost "
            "0.00/0.05/0.20; gradient falls %d, alternating falls %d"
            % (g0, g5, g20, a0, a5, a20, g_drop, a_drop),
        )
    else:
        failed = [t for t in CONTROL_TESTS
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: %s" % ", ".join(failed))

    path = ex.save()
    print(path)
    for k in ("g0.00", "g0.05", "g0.20", "a0.00", "a0.05", "a0.20"):
        r = res[k]
        print("%-6s alive=%3d doubled=%2d moving=%2d series=%s"
              % (k, r["alive"], r["doubled"], r["moved"], r["series"]))
    print("u0.20-n40 alive=%3d doubled=%2d" % (a40, d40))


if __name__ == "__main__":
    main()
