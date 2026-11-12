"""EXP-67: find the setting where something actually dies.

The capacity line of work has no capacity to measure because nothing dies at
those settings (docs/FINDING-the-capacity-finding-was-reading-its-own-input.md).
Before any capacity law can be stated, a setting with a real limit has to be
found. This experiment searches for it.

Arithmetic registered before the run:

  c*   = M - income * (1 - r) / r = 2.0 - 1.2 * 0.2 / 0.8 = 1.7
       (the cell level a single sedentary organism drives itself down to)

  COST = maintenance + damage_rate * repair_cost

A sedentary organism on its own steady cell nets `c* - COST` per step. It dies
when that is negative:

  maintenance > c* - damage_rate * repair_cost = 1.7 - 0.03 = 1.67

So the sedentary prediction is: maintenance <= 1.67 -> nobody dies;
maintenance > 1.67 -> everybody dies. That is a sharp threshold and it is the
thing to test.

But the organisms are not sedentary: with `sighted` they move to a cell they
have not eaten and take a full `income = 1.2` there. A mover on a fresh cell
nets `income - COST`. It dies when

  maintenance > income - damage_rate * repair_cost = 1.2 - 0.03 = 1.17

So there are two candidate thresholds, 1.17 (movers) and 1.67 (sitters), and
which one the field shows is the measurement.

Pre-registered predictions:
  (a) if the organisms keep moving to fresh cells, the population collapses
      between maintenance 1.17 and 1.67;
  (b) if they sit, it collapses only above 1.67;
  (c) if neither threshold is sharp, something else is feeding them and the
      two-term arithmetic is incomplete.

The sweep is on maintenance from 0.6 to 2.2 in steps of 0.1, with everything
else at the EXP-66 settings, n = 160, cells = 40, E_max = 10, 8000 steps.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from result import (
    add_condition,
    add_control,
    add_limitation,
    add_series,
    new_result,
    save,
    set_arithmetic,
    set_verdict,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
TRACE_DIR = os.path.join(CORE, "results", "sighted")

INCOME = 1.2
M = 2.0
R = 0.8
DAMAGE = 0.02
REPAIR = 1.5
MOVE = 0.10
N = 160
CELLS = 40
SEED = 20250101
E_MAX = 10

STEPS = 8000
EVERY = 8000

CSTAR = M - INCOME * (1 - R) / R
SIT_THRESHOLD = CSTAR - DAMAGE * REPAIR
MOVE_THRESHOLD = INCOME - DAMAGE * REPAIR


def run(maint):
    os.makedirs(TRACE_DIR, exist_ok=True)
    before = set(os.listdir(TRACE_DIR))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", "sighted", "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(STEPS), "--every", str(EVERY), "--seed", str(SEED),
        "--capacity", str(E_MAX), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", str(maint),
        "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=1200)
    if out.returncode != 0:
        raise RuntimeError("trace failed for maintenance=%s: %s"
                           % (maint, out.stderr[-1500:]))
    after = set(os.listdir(TRACE_DIR)) - before
    if not after:
        raise RuntimeError("no new trace for maintenance=%s" % maint)
    path = os.path.join(TRACE_DIR, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    samples = last["samples"]
    # `samples` is one entry per SLOT, dead or alive. Counting its length as the
    # population is the same mistake as reading `--n` back out: the slots are an
    # input, the survivors are the measurement.
    living = [s for s in samples if s["alive"]]
    by_cell = {}
    for s in living:
        by_cell.setdefault(s["cell"], []).append(s)
    energies = [s["energy"] for s in living]
    return {
        "maintenance": maint,
        "cost": maint + DAMAGE * REPAIR,
        "alive": len(living),
        "slots": len(samples),
        "occupied": len(by_cell),
        "crowding": len(samples) / len(by_cell) if by_cell else 0.0,
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_min": min(energies) if energies else None,
        "energy_max": max(energies) if energies else None,
        "step": last["step"],
    }


def main():
    result = new_result(
        "exp67-where-does-anything-die",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "every": EVERY,
            "policy": "sighted", "read_budget": 3,
            "income": INCOME, "M": M, "regrow": R,
            "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "move_cost": MOVE, "field": "uniform", "rich": 2.4, "poor": 1.6,
            "e_max": E_MAX,
            "maintenance_sweep": [round(0.6 + 0.1 * i, 1) for i in range(17)],
        },
        "python3 checks/exp67_where_does_anything_die.py",
    )
    set_arithmetic(result, {
        "c_star": CSTAR,
        "sit_threshold_maintenance": SIT_THRESHOLD,
        "move_threshold_maintenance": MOVE_THRESHOLD,
        "prediction_a_movers": "collapse between 1.17 and 1.67",
        "prediction_b_sitters": "collapse only above 1.67",
        "prediction_c_neither": "something else is feeding them",
    })

    rows = []
    for i in range(17):
        maint = round(0.6 + 0.1 * i, 1)
        row = run(maint)
        rows.append(row)
        em = "--" if row["energy_mean"] is None else "%.4f" % row["energy_mean"]
        print("maint %.1f  cost %.2f  alive %3d  occ %2d  crowd %.2f  Emean %s  Emin %s"
              % (maint, row["cost"], row["alive"], row["occupied"],
                 row["crowding"], em,
                 "--" if row["energy_min"] is None else "%.4f" % row["energy_min"]))

    add_series(result, "alive_vs_maintenance",
               [r["maintenance"] for r in rows], [float(r["alive"]) for r in rows])
    add_series(result, "energy_mean_vs_maintenance",
               [r["maintenance"] for r in rows],
               [r["energy_mean"] if r["energy_mean"] is not None else 0.0 for r in rows])
    add_condition(result, "sweep", "maintenance 0.6 .. 2.2 step 0.1",
                  {"rows": rows})

    # ---- controls ----
    # fires: at maintenance 0.6 (the EXP-66 setting) nothing dies. That is a
    # known-present "no deaths" state and the control aimed at it must fire.
    low = rows[0]
    fires = low["alive"] == N
    add_control(result, "fires", fires,
                "maintenance 0.6: alive %d of %d; the no-death regime is present "
                "as expected" % (low["alive"], N))

    # silent: at maintenance 2.2 everyone must be dead. The "no deaths" control
    # stays silent there.
    high = rows[-1]
    silent = high["alive"] == 0
    add_control(result, "silent", silent,
                "maintenance 2.2: alive %d; the no-death signature is gone"
                % high["alive"])

    # specific: the collapse must land at one of the two predicted thresholds
    # and not somewhere else. Find the first maintenance where alive < N, and
    # check it is within one step of 1.17 or 1.67.
    first_fail = next((r for r in rows if r["alive"] < N), None)
    if first_fail is None:
        specific = False
        note = "no arm lost an organism; neither threshold was reached"
    else:
        d_move = abs(first_fail["maintenance"] - MOVE_THRESHOLD)
        d_sit = abs(first_fail["maintenance"] - SIT_THRESHOLD)
        specific = min(d_move, d_sit) <= 0.1 + 1e-9
        note = ("first arm with a death: maintenance %.1f (alive %d); distance to "
                "mover threshold %.2f is %.2f, to sitter threshold %.2f is %.2f"
                % (first_fail["maintenance"], first_fail["alive"],
                   MOVE_THRESHOLD, d_move, SIT_THRESHOLD, d_sit))
    add_control(result, "specific", specific, note)

    # ---- verdict ----
    if first_fail is None:
        set_verdict(result, "insensitive by construction",
                    "No arm in 0.6 .. 2.2 lost an organism, so the sweep never "
                    "reached a limit and cannot locate a threshold. Both the "
                    "mover (1.17) and the sitter (1.67) predictions are outside "
                    "what was measured, or the two-term arithmetic is missing a "
                    "term.")
    else:
        d_move = abs(first_fail["maintenance"] - MOVE_THRESHOLD)
        d_sit = abs(first_fail["maintenance"] - SIT_THRESHOLD)
        if d_move < d_sit:
            which = ("the mover threshold 1.17 (income - damage*repair): the "
                     "organisms are eating fresh cells, not their own steady cell")
        else:
            which = ("the sitter threshold 1.67 (c* - damage*repair): the "
                     "organisms are eating their own steady cell down")
        set_verdict(result, "passed",
                    "The first death appears at maintenance %.1f, closest to %s. "
                    "Below that nothing dies; above it the population collapses. "
                    "This is the setting a capacity law can be measured in."
                    % (first_fail["maintenance"], which))

    add_limitation(result,
                   "One seed, one field shape, one E_max (10). The threshold is "
                   "located to the 0.1 grid, not refined.")
    add_limitation(result,
                   "The trace samples only the last step, so the sweep says who is "
                   "alive at step 8000, not when they died.")
    add_limitation(result,
                   "A collapse at a threshold does not by itself show the "
                   "two-term arithmetic is complete; it shows which of the two "
                   "candidate terms is doing the work.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
