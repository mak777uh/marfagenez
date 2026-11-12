"""Is move_cost actually charged?

EXP-71 found `death_step = 64` at maintenance 1.25 for move_cost 0.0, 0.1 and
0.3 alike, while the arithmetic says 62.5, 27.8 and 13.2 (E_0 = 5.0). The
move fraction was nonzero (0.19, 0.11, 0.12), so some organisms moved. Either
the move cost is not charged, or the death is not caused by the deficit.

This is the cheap check that separates the two, and it is the kind of check
PROTOCOL.md says to do before the complex one: run BELOW the threshold, where
nobody dies, and look at the mean energy. If move_cost is charged, the mean
energy must fall as move_cost rises. If it does not, the cost is not reaching
the energy.

  maintenance 1.00, income 1.2, damage*repair 0.03 -> surplus 0.17 per step
  move_cost 0.0 -> surplus 0.1700
  move_cost 0.2 -> surplus 0.1700 - f*0.2
  move_cost 1.0 -> surplus 0.1700 - f*1.0

The mean energy is read at the end of a fixed run, so a difference in surplus
shows up as a difference in the mean, scaled by the number of steps.

The control that makes this specific: a move_cost large enough to exceed the
surplus must stop the population from growing its energy, even though nobody
dies.
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

INCOME = 1.2
R = 0.8
N = 160
CELLS = 40
SEED = 20250101
E_MAX = 10
E_0 = 5.0
DAMAGE = 0.02
REPAIR = 1.5
DRP = DAMAGE * REPAIR
STEPS = 4000
FRAMES = 2000


def run(policy, maint, move_cost, steps=STEPS):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", policy, "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(steps), "--every", str(max(1, steps // FRAMES)),
        "--seed", str(SEED),
        "--capacity", str(E_MAX), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(maint),
        "--damage-rate", repr(DAMAGE), "--repair-cost", repr(REPAIR),
        "--move-cost", repr(move_cost),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("trace failed: %s" % out.stderr[-1200:])
    after = set(os.listdir(trace_dir)) - before
    if not after:
        raise RuntimeError("no new trace")
    path = os.path.join(trace_dir, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    frames = data["frames"]
    last = frames[-1]
    living = [s for s in last["samples"] if s["alive"]]
    energies = [s["energy"] for s in living]

    moved = still = 0
    for fr in frames:
        for s in fr["samples"]:
            if not s["alive"]:
                continue
            if s.get("direction", 0) != 0:
                moved += 1
            else:
                still += 1
    total = moved + still

    return {
        "move_cost": move_cost,
        "maintenance": maint,
        "alive": len(living),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_max": max(energies) if energies else None,
        "move_fraction": moved / total if total else None,
        "steps": steps,
    }


def main():
    result = new_result(
        "exp72-is-the-move-cost-charged",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "frames": FRAMES,
            "income": INCOME, "regrow": R, "e_max": E_MAX, "e_0": E_0,
            "damage": DAMAGE, "repair": REPAIR,
            "field": "uniform", "rich": 2.4, "poor": 1.6,
            "policy": "sighted",
            "maintenance": 1.0,
        },
        "python3 checks/exp72_is_the_move_cost_charged.py",
    )
    set_arithmetic(result, {
        "surplus_at_maintenance_1": INCOME - 1.0 - DRP,
        "predicted_energy_growth": "steps * (surplus - move_fraction*move_cost)",
        "note": "maintenance 1.0 is below the threshold 1.17, so nobody dies "
                "and the energy keeps growing until E_max. The mean energy at "
                "the end is then a direct readout of the surplus.",
    })

    print("sighted at maintenance 1.0, below the threshold")
    rows = []
    for mc in (0.0, 0.2, 1.0, 5.0):
        row = run("sighted", 1.0, mc)
        rows.append(row)
        print("  mc=%.2f alive=%d energy_mean=%.4f energy_max=%.4f move_fraction=%.4f"
              % (mc, row["alive"], row["energy_mean"] or 0.0,
                 row["energy_max"] or 0.0, row["move_fraction"] or 0.0))

    add_series(result, "move_cost",
               [r["move_cost"] for r in rows],
               [r["energy_mean"] for r in rows])
    add_condition(result, "energy_vs_move_cost",
                  "mean energy after %d steps at maintenance 1.0" % STEPS,
                  {"points": rows})

    # controls
    # fires: at move_cost 0 the population must reach E_max, because the
    # surplus is positive and nothing else is being paid.
    fires = rows[0]["energy_max"] is not None and abs(rows[0]["energy_max"] - E_MAX) < 1e-6
    add_control(result, "fires", fires,
                "move_cost 0.0: energy_max %.6f against E_max %d. With no move "
                "cost and a positive surplus every survivor must fill up."
                % (rows[0]["energy_max"] or -1.0, E_MAX))

    # silent: at move_cost 0 nobody dies, so the population is not being
    # killed by anything but the surplus.
    silent = rows[0]["alive"] == N
    add_control(result, "silent", silent,
                "move_cost 0.0: alive %d of %d. Below the threshold nobody "
                "should die, so a death here would mean the threshold is not "
                "where the law says." % (rows[0]["alive"], N))

    # specific: the mean energy must fall as move_cost rises. A control that
    # passes whether or not the cost is charged is not specific.
    charged = rows[-1]["energy_mean"] is not None and rows[0]["energy_mean"] is not None
    drop = (rows[0]["energy_mean"] - rows[-1]["energy_mean"]) if charged else 0.0
    specific = drop > 0.01
    add_control(result, "specific", specific,
                "mean energy falls from %.4f to %.4f as move_cost goes 0.0 to "
                "5.0, a drop of %.4f. If the drop is zero the move cost is not "
                "reaching the energy."
                % (rows[0]["energy_mean"] or 0.0, rows[-1]["energy_mean"] or 0.0, drop))

    if fires and silent and specific:
        set_verdict(result, "passed",
                    "The move cost is charged: at maintenance 1.0 the mean "
                    "energy falls from %.4f to %.4f as move_cost goes 0.0 to "
                    "5.0, while nobody dies (alive %d of %d throughout). The "
                    "move cost therefore reaches the energy, and the constant "
                    "death step in EXP-71 is not a sign that it is ignored."
                    % (rows[0]["energy_mean"], rows[-1]["energy_mean"],
                       rows[0]["alive"], N))
    elif not specific:
        set_verdict(result, "failed",
                    "The mean energy does not fall with move_cost (%.4f to "
                    "%.4f). The move cost is not charged."
                    % (rows[0]["energy_mean"], rows[-1]["energy_mean"]))
    else:
        set_verdict(result, "failed",
                    "The move cost is charged (drop %.4f) but a control did "
                    "not fire: fires=%s silent=%s." % (drop, fires, silent))

    add_limitation(result, "One seed, one field shape, one read budget.")
    add_limitation(result,
                   "The mean energy is read at a fixed step, so a population "
                   "that reaches E_max early shows no further difference. The "
                   "test is therefore only sensitive while the mean is below "
                   "E_max.")
    add_limitation(result,
                   "This proves the cost is charged, not how large the charge "
                   "is per move. The move fraction is measured, not "
                   "controlled.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
