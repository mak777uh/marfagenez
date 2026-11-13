"""Is the extra occupancy at income=1.20 a rotation, or a static fact?

FINDING-the-capacity-law-measured-the-wrong-ceiling.md records one number its
formula cannot explain: at income=1.20, cost=0.63, 40 cells, the bound is 40 and
the measurement is 42. The document attributes the surplus to a rotation -- an
organism that finds itself second moves away, eats a full portion, recovers, and
another one arrives to be second in its place -- and says outright that this is
"an inference from `taken` values, not a controlled result".

A rotation needs the second occupant to LEAVE. Leaving costs `move_cost`. So the
surplus should shrink as leaving gets more expensive, and vanish when leaving is
free-but-unaffordable.

The arithmetic, before any run:

    income = 1.20, cost = maintenance + damage*repair = 0.60 + 0.02*1.5 = 0.63
    M = 2.0, r = 0.8, cells = 40

    c*            = M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70
    first takes   = min(c*, income)        = min(1.70, 1.20) = 1.20
    left on cell  = c* - income            = 0.50
    second takes  = min(0.50, income)      = 0.50
    second loses  = cost - taken           = 0.63 - 0.50 = 0.13 per step

    a second occupant dies in  energy / 0.13  steps
    at energy 10.0 that is 76.9 steps; the trace samples every 1000, so a static
    second occupant cannot be seen at any sample after the first.

Two arms:

    A  move_cost = 0.00  -- leaving is free, so the rotation is unhindered
    B  move_cost = 0.20  -- leaving costs 0.20 against a recovery of 1.20-0.63
                           = 0.57 per step on a free cell, so leaving is still
                           affordable but no longer free

If the surplus is a rotation, B must hold fewer than A. If it is a static fact
about the field, move_cost cannot touch it and the two arms coincide.

`--policy stay` is the third arm: standing still cannot rotate at all, so it
must give exactly 40. If `stay` also gives more than 40, the surplus is not a
rotation and the whole reading is wrong.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment, ExperimentError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

M = 2.0
R = 0.8
CELLS = 40
INCOME = 1.20
MAINTENANCE = 0.60
DAMAGE = 0.02
REPAIR = 1.5
COST = MAINTENANCE + DAMAGE * REPAIR
C_STAR = M + INCOME - INCOME / R
LEFT = C_STAR - INCOME
LOSS = COST - LEFT
STEPS = 8000
EVERY = 1000


def run_trace(args):
    out = subprocess.run([TRACE] + args, capture_output=True, text=True)
    if out.returncode != 0:
        raise ExperimentError("trace failed: %s\n%s" % (out.returncode, out.stderr[-2000:]))
    path = None
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            path = line.split(":", 1)[1].strip()
    if path is None:
        raise ExperimentError("trace printed no `written:` line:\n%s" % out.stdout[-2000:])
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(full) as f:
        return json.load(f)


def occupancy(frame):
    alive = [s for s in frame["samples"] if s["alive"]]
    per_cell = {}
    for s in alive:
        per_cell[s["cell"]] = per_cell.get(s["cell"], 0) + 1
    doubles = sorted(c for c, k in per_cell.items() if k > 1)
    return len(alive), len(per_cell), doubles, alive


def main():
    exp = Experiment(
        experiment_id="EXP-88",
        question="At income=1.20 the field holds 42 where the bound is 40. Is that "
                 "surplus a rotation of second occupants, or a static fact about the "
                 "field that move_cost cannot touch?",
        arithmetic={
            "formula": "c* = M + income - income/r; second takes c* - income; "
                       "loses cost - taken per step",
            "M": M, "r": R, "income": INCOME, "cost": COST,
            "c_star": C_STAR, "first_takes": INCOME, "left_on_cell": LEFT,
            "second_takes": LEFT, "loss_per_step": LOSS,
            "steps_to_die": 10.0 / LOSS,
            "why_8000_steps": "a static second occupant dies in %.1f steps and the "
                              "trace samples every %d, so it cannot survive to a "
                              "second sample. Every sample after the first therefore "
                              "shows a rotating pair or no pair at all."
                              % (10.0 / LOSS, EVERY),
            "why_move_cost": "a rotation needs the second occupant to leave, and "
                             "leaving costs move_cost. If the surplus is a rotation "
                             "it must fall with move_cost.",
        },
        arms={"A_free": "move_cost=0.00, random layout",
              "B_paid": "move_cost=0.20, random layout",
              "C_stay": "policy=stay, move_cost=0.00, random layout",
              "D_even": "move_cost=0.00, even layout"},
        seed=1,
        command="python3 checks/exp88_is_the_surplus_a_rotation.py",
        parameters={"M": M, "regrow": R, "cells": CELLS, "income": INCOME,
                    "maintenance": MAINTENANCE, "damage": DAMAGE, "repair": REPAIR,
                    "steps": STEPS, "every": EVERY, "n": 160},
    )

    base = [
        "--field", "uniform", "--rich", "2.0", "--poor", "2.0", "--regrow", "0.8",
        "--cells", str(CELLS), "--n", "160", "--layout", "random",
        "--income", str(INCOME), "--maintenance", str(MAINTENANCE),
        "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
        "--capacity", "10", "--energy", "10.0",
        "--steps", str(STEPS), "--every", str(EVERY), "--seed", "1",
    ]

    arms = [
        ("A_free", ["--policy", "sighted", "--read-budget", "3", "--move-cost", "0.0"]),
        ("B_paid", ["--policy", "sighted", "--read-budget", "3", "--move-cost", "0.2"]),
        ("C_stay", ["--policy", "stay", "--move-cost", "0.0"]),
        ("D_even", ["--policy", "sighted", "--read-budget", "3", "--move-cost", "0.0",
                    "--layout", "even"]),
    ]

    for key, extra in arms:
        res = run_trace(base + extra)
        counts = []
        doubles_each = []
        for frame in res["frames"]:
            alive, occupied, doubles, _ = occupancy(frame)
            counts.append(alive)
            doubles_each.append(len(doubles))
        last = res["frames"][-1]
        alive, occupied, doubles, alive_samples = occupancy(last)
        exp.add_arm(key, dict(arms)[key], {
            "alive": alive,
            "occupied_cells": occupied,
            "double_cells": len(doubles),
            "double_cells_at": doubles,
            "alive_each_sample": counts,
            "double_cells_each_sample": doubles_each,
            "taken": sorted(round(s["taken"], 6) for s in alive_samples),
            "bound": CELLS,
        }, trace_hash=res["hash"])
        print("%-8s alive=%d occupied=%d doubles=%d at %s  alive/sample=%s"
              % (key, alive, occupied, len(doubles), doubles, counts))

    a = exp._result["conditions"]["A_free"]["metrics"]
    b = exp._result["conditions"]["B_paid"]["metrics"]
    c = exp._result["conditions"]["C_stay"]["metrics"]

    exp.control(
        "fires", a["alive"] > CELLS,
        "The free arm must reproduce the surplus the finding records. Bound is %d, "
        "measured %d." % (CELLS, a["alive"]),
    )
    exp.control(
        "silent", c["alive"] <= CELLS,
        "Standing still cannot rotate, so it must not exceed the bound. Measured %d "
        "against a bound of %d. If this arm also exceeded the bound the surplus "
        "would not be a rotation and the reading would be wrong."
        % (c["alive"], CELLS),
    )
    exp.control(
        "specific", b["alive"] < a["alive"],
        "If the surplus is a rotation it must shrink when leaving costs 0.20: the "
        "second occupant can still afford to leave (recovery on a free cell is "
        "%.2f per step against a cost of 0.20) but does so less often. Free arm %d, "
        "paid arm %d." % (INCOME - COST, a["alive"], b["alive"]),
    )

    exp.limitation(
        "One seed, one field kind (uniform), one income (1.20). The surplus is two "
        "organisms out of 40; a difference of one or two is at the edge of what a "
        "single seed can resolve."
    )
    exp.limitation(
        "`move_cost` is charged whether or not the destination is better, and "
        "`read_budget` is fixed at 3 in both moving arms. This experiment varies "
        "only the price of leaving, not the information an organism has."
    )
    exp.limitation(
        "The trace samples every %d steps. A second occupant that lives 76.9 steps "
        "is visible to the sampler only if it happens to be second at a sample. "
        "The count of double-occupied cells per sample is therefore a lower bound "
        "on how often sharing happens, not a measure of it." % EVERY
    )

    if a["alive"] > CELLS and c["alive"] <= CELLS and b["alive"] < a["alive"]:
        exp.verdict("passed", "The surplus exists, standing still does not produce "
                              "it, and it shrinks when leaving is paid for. All three "
                              "are what the rotation predicts.")
    else:
        exp.verdict("failed", "At least one of the three rotation predictions did not "
                              "hold; see the controls.")
    exp.save()


if __name__ == "__main__":
    main()
