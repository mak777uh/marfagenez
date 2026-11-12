"""EXP-68: bisect the death threshold and name the term that sets it.

EXP-67 found the population collapses between maintenance 1.1 (38 alive) and
1.2 (0 alive). Two candidate thresholds were registered before that run:

  mover: income - damage*repair          = 1.2 - 0.03 = 1.17
  sitter: c* - damage*repair = 1.7 - 0.03 = 1.67

The collapse is near 1.17, so the mover term is the live one. This experiment
bisects to 1e-4 and checks the collapse point against 1.17 exactly.

Arithmetic, before the run:

  A mover arrives on a cell, takes `income` (the cell is full at 1.2 under
  `regrow = 0.8` from a uniform field of 2.0: level returns to 2.0, and the
  organism takes income = 1.2), pays maintenance, then pays damage*repair to
  clear the damage it took that step. Net per step:

      income - maintenance - damage_rate*repair_cost

  Setting that to zero:

      maintenance* = income - damage_rate*repair_cost = 1.2 - 0.02*1.5 = 1.17

  So the bisection should land on 1.17 to within its resolution.

  A second prediction: just below the threshold, the surviving energy should be
  E_max - COST, because a mover that nets zero cannot accumulate. EXP-67 showed
  exactly that at maintenance 0.7, 0.8, 0.9, 1.0 (9.2700, 9.1700, 9.0700,
  8.9700 = E_max - COST each time). If the bisected threshold is the mover
  threshold, the energy at maintenance just below it must still be E_max - COST.

Pre-registered predictions:
  (a) threshold = 1.17 +- 0.0001;
  (b) energy just below the threshold = E_max - COST;
  (c) if the threshold is not 1.17, the per-step net is not
      income - maintenance - damage*repair and a term is missing.
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

PREDICTED = INCOME - DAMAGE * REPAIR
COST_OF = lambda m: m + DAMAGE * REPAIR


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
        "--income", str(INCOME), "--maintenance", repr(maint),
        "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=1200)
    if out.returncode != 0:
        raise RuntimeError("trace failed at maintenance=%r: %s"
                           % (maint, out.stderr[-1500:]))
    after = set(os.listdir(TRACE_DIR)) - before
    if not after:
        raise RuntimeError("no new trace at maintenance=%r" % maint)
    path = os.path.join(TRACE_DIR, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    living = [s for s in last["samples"] if s["alive"]]
    energies = [s["energy"] for s in living]
    return {
        "maintenance": maint,
        "cost": COST_OF(maint),
        "alive": len(living),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_min": min(energies) if energies else None,
    }


def main():
    result = new_result(
        "exp68-bisect-the-death-threshold",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "every": EVERY,
            "policy": "sighted", "read_budget": 3,
            "income": INCOME, "M": M, "regrow": R,
            "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "move_cost": MOVE, "field": "uniform", "rich": 2.4, "poor": 1.6,
            "e_max": E_MAX,
            "bisect_resolution": 1e-4,
        },
        "python3 checks/exp68_bisect_the_death_threshold.py",
    )
    set_arithmetic(result, {
        "predicted_threshold": PREDICTED,
        "formula": "income - damage_rate*repair_cost",
        "prediction_a": "bisection lands on 1.17 +- 1e-4",
        "prediction_b": "energy just below threshold = E_max - COST",
        "prediction_c": "otherwise a term is missing from the net",
    })

    lo, hi = 1.1, 1.2          # lo survives, hi does not (EXP-67)
    trail = []
    for _ in range(20):
        if hi - lo <= 1e-4:
            break
        mid = (lo + hi) / 2.0
        row = run(mid)
        trail.append(row)
        em = "--" if row["energy_mean"] is None else "%.6f" % row["energy_mean"]
        print("maint %.6f  cost %.6f  alive %3d  Emean %s"
              % (row["maintenance"], row["cost"], row["alive"], em))
        if row["alive"] > 0:
            lo = mid
        else:
            hi = mid

    threshold = (lo + hi) / 2.0
    add_series(result, "bisection", [r["maintenance"] for r in trail],
               [float(r["alive"]) for r in trail])
    add_condition(result, "bisection", "maintenance in [1.1, 1.2]",
                  {"threshold": threshold, "lo_survives": lo, "hi_dies": hi,
                   "trail": trail})

    # ---- controls ----
    # fires: the known-surviving end must survive.
    low_row = run(1.1)
    fires = low_row["alive"] > 0
    add_control(result, "fires", fires,
                "maintenance 1.1: alive %d; the surviving side is present"
                % low_row["alive"])

    # silent: the known-dying end must be empty.
    high_row = run(1.2)
    silent = high_row["alive"] == 0
    add_control(result, "silent", silent,
                "maintenance 1.2: alive %d; the dying side is empty"
                % high_row["alive"])

    # specific: the threshold must be 1.17 and not the sitter threshold 1.67,
    # and the energy just below it must be E_max - COST to 1e-4.
    d_pred = abs(threshold - PREDICTED)
    near = run(max(lo - 0.0005, 0.6))
    expected_energy = E_MAX - COST_OF(near["maintenance"])
    d_energy = (abs(near["energy_mean"] - expected_energy)
                if near["energy_mean"] is not None else 999.0)
    specific = d_pred <= 1e-4 and d_energy <= 1e-3
    add_control(result, "specific", specific,
                "threshold %.6f vs predicted %.6f (distance %.6f); energy just "
                "below it %.6f vs E_max - COST %.6f (distance %.6f)"
                % (threshold, PREDICTED, d_pred,
                   near["energy_mean"] if near["energy_mean"] is not None else -1.0,
                   expected_energy, d_energy))

    # ---- verdict ----
    if specific:
        set_verdict(result, "passed",
                    "The death threshold is %.6f, and income - damage*repair = "
                    "%.6f. A moving organism survives while its per-step take "
                    "exceeds maintenance plus repair, and dies when it does not. "
                    "The sitter threshold 1.67 is not what the field shows: these "
                    "organisms eat fresh cells, they do not eat their own steady "
                    "cell down." % (threshold, PREDICTED))
    else:
        set_verdict(result, "failed",
                    "The threshold is %.6f, which is %.6f from income - "
                    "damage*repair = %.6f. The per-step net is not "
                    "income - maintenance - damage*repair; a term is missing."
                    % (threshold, d_pred, PREDICTED))

    add_limitation(result,
                   "One seed, one field shape, one E_max. The threshold is a "
                   "property of these settings, not yet of the model.")
    add_limitation(result,
                   "The trace samples only the last step. The bisection locates "
                   "where the population is empty at step 8000, which is not the "
                   "same as where it dies.")
    add_limitation(result,
                   "A threshold at income - damage*repair is consistent with the "
                   "organisms always finding a full cell. It does not show that "
                   "they always will: at higher crowding the take per step falls "
                   "below income and the threshold must move.")

    path = save(result)
    print("threshold %.6f  predicted %.6f  distance %.6f"
          % (threshold, PREDICTED, abs(threshold - PREDICTED)))
    print("saved", path)


if __name__ == "__main__":
    main()
