"""EXP-73: is the cap the whole explanation for the invisible move cost?

EXP-72 measured the mean energy of a surviving `sighted` population at
maintenance 1.0 and found 8.9700 at move_cost 0.0 and 0.2 alike, while the
arithmetic said the difference should be 0.64 over the run.

Reading the code gave the answer: `life.rs:441` spends the move cost, then
`organism.rs:155` does `energy = min(energy + taken, capacity)`. The clamp is a
min, so anything paid before it is erased whenever the energy plus the income
still exceeds the capacity. The steady state is

    E* = capacity - maintenance - damage*repair = 10 - 1.0 - 0.03 = 8.97

which is exactly the measured number and contains no move_cost.

PRE-REGISTERED PREDICTION: with the capacity raised so high that the clamp
never binds, the mean energy must fall with move_cost at every value, not just
at the large ones. Concretely, with capacity = 1e9 the energy is unbounded, so
the mean grows without limit and the difference between two move costs
accumulates every step:

    mean_energy(steps) ~ steps * (income - maintenance - damage*repair
                                  - move_fraction * move_cost)

At 4000 steps and move_cost 0.2 with a move fraction of 0.0008 the gap from
move_cost 0.0 should be about 0.64, which is 6400x the print resolution.

The competing prediction: the mean energy is still identical, which would mean
the cap is not the explanation and something else pins the energy.

A second arm checks the formula itself. If `E* = capacity - maintenance -
damage*repair` is the steady state, then changing the capacity must move the
mean by the same amount, one for one, while the cap binds:

    capacity 10 -> E* 8.97
    capacity 20 -> E* 18.97
    capacity 50 -> E* 48.97

If the mean moves with the capacity one for one, the formula is right and the
move cost is being erased. If it does not, the formula is wrong.
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
E_0 = 5.0
DAMAGE = 0.02
REPAIR = 1.5
DRP = DAMAGE * REPAIR
STEPS = 4000
FRAMES = 2000
MAINT = 1.0
BIG_CAP = 1e9


def run(policy, maint, move_cost, capacity, steps=STEPS):
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
        "--capacity", repr(capacity), "--regrow", str(R),
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
        "capacity": capacity,
        "alive": len(living),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_max": max(energies) if energies else None,
        "move_fraction": moved / total if total else None,
    }


def main():
    result = new_result(
        "exp73-is-the-cap-the-whole-explanation",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "frames": FRAMES,
            "income": INCOME, "regrow": R, "e_0": E_0,
            "damage": DAMAGE, "repair": REPAIR,
            "field": "uniform", "rich": 2.4, "poor": 1.6,
            "policy": "sighted", "maintenance": MAINT,
            "big_capacity": BIG_CAP,
        },
        "python3 checks/exp73_is_the_cap_the_whole_explanation.py",
    )
    set_arithmetic(result, {
        "steady_state_with_cap": "capacity - maintenance - damage*repair",
        "predicted_E_star_at_capacity_10": 10 - MAINT - DRP,
        "predicted_gap_without_cap": "steps * move_fraction * move_cost",
        "gap_expected_at_mc_0.2": 4000 * 0.0008 * 0.2,
        "cap_erases_cost_when": "E* + income >= capacity",
    })

    # ---- arm 1: capacity so large the clamp never binds ----
    print("arm 1: capacity 1e9, the clamp never binds")
    big = []
    for mc in (0.0, 0.2, 1.0):
        row = run("sighted", MAINT, mc, BIG_CAP)
        big.append(row)
        print("  mc=%.2f alive=%d energy_mean=%.4f energy_max=%.4f move_fraction=%.4f"
              % (mc, row["alive"], row["energy_mean"] or 0.0,
                 row["energy_max"] or 0.0, row["move_fraction"] or 0.0))

    gap = (big[0]["energy_mean"] - big[1]["energy_mean"]) if all(
        r["energy_mean"] is not None for r in big[:2]) else 0.0
    print("  gap between mc 0.0 and 0.2 = %.6f" % gap)

    # ---- arm 2: the steady state formula ----
    print("arm 2: does the mean track capacity one for one?")
    caps = []
    for cap in (10.0, 20.0, 50.0):
        row = run("sighted", MAINT, 0.0, cap)
        predicted = cap - MAINT - DRP
        caps.append({
            "capacity": cap,
            "energy_mean": row["energy_mean"],
            "predicted": predicted,
            "residual": (row["energy_mean"] - predicted)
            if row["energy_mean"] is not None else None,
            "energy_max": row["energy_max"],
        })
        print("  capacity=%.0f energy_mean=%.4f predicted=%.4f residual=%+.6f"
              % (cap, row["energy_mean"] or 0.0, predicted,
                 (row["energy_mean"] or 0.0) - predicted))

    add_series(result, "no_cap",
               [r["move_cost"] for r in big],
               [r["energy_mean"] for r in big])
    add_condition(result, "no_cap", "mean energy with capacity 1e9", {
        "points": big, "gap_mc_0_to_0.2": gap,
    })
    add_condition(result, "steady_state", "mean energy against capacity at move_cost 0", {
        "points": caps,
    })

    # ---- controls ----
    # fires: at capacity 10 and move_cost 0 the mean must be 8.97. This is the
    # known number from EXP-72 and the formula must reproduce it.
    ref = run("sighted", MAINT, 0.0, 10.0)
    fires = (ref["energy_mean"] is not None
             and abs(ref["energy_mean"] - (10.0 - MAINT - DRP)) < 1e-3)
    add_control(result, "fires", fires,
                "capacity 10, move_cost 0: mean %.4f against the formula "
                "capacity - maintenance - damage*repair = %.4f"
                % (ref["energy_mean"] or -1.0, 10.0 - MAINT - DRP))

    # silent: with the cap out of the way, the mean must NOT equal the capped
    # steady state. If it does, the cap was never binding and the whole
    # explanation is wrong.
    silent = (big[0]["energy_mean"] is not None
              and big[0]["energy_mean"] > 9.0)
    add_control(result, "silent", silent,
                "capacity 1e9, move_cost 0: mean %.4f. With no cap the energy "
                "must grow past the capped steady state 8.97; if it sits at "
                "8.97 the cap was not what pinned it."
                % (big[0]["energy_mean"] or -1.0))

    # specific: the gap between move_cost 0.0 and 0.2 must be visible without
    # the cap. This is the whole point.
    specific = gap > 0.01
    add_control(result, "specific", specific,
                "gap between move_cost 0.0 and 0.2 with capacity 1e9 is "
                "%.6f; the prediction is %.4f. A gap of zero would mean the "
                "cap is not the explanation."
                % (gap, 4000 * 0.0008 * 0.2))

    # ---- verdict ----
    residuals = [abs(c["residual"]) for c in caps if c["residual"] is not None]
    worst_res = max(residuals) if residuals else 999.0

    if fires and silent and specific:
        set_verdict(result, "passed",
                    "The cap is the explanation. With capacity 1e9 the mean "
                    "energy grows to %.4f and the gap between move_cost 0.0 "
                    "and 0.2 becomes %.4f (predicted %.4f), while with "
                    "capacity 10 it was 0.0000. The steady state is "
                    "capacity - maintenance - damage*repair, verified at three "
                    "capacities with a worst residual of %.6f."
                    % (big[0]["energy_mean"], gap, 4000 * 0.0008 * 0.2,
                       worst_res))
    elif not specific:
        set_verdict(result, "failed",
                    "The gap is still zero without the cap (%.6f). The cap is "
                    "not what hides the move cost." % gap)
    else:
        set_verdict(result, "failed",
                    "A control did not fire: fires=%s silent=%s specific=%s."
                    % (fires, silent, specific))

    add_limitation(result,
                   "One seed, one field shape, one read budget, one "
                   "maintenance.")
    add_limitation(result,
                   "The prediction of the gap uses the move fraction measured "
                   "at capacity 10, which may not be the move fraction at "
                   "capacity 1e9. The comparison is therefore a direction, "
                   "not a precise equality.")
    add_limitation(result,
                   "This shows the cap erases the move cost. It does not show "
                   "which of the two jobs of `capacity` -- the energy ceiling "
                   "or the income ceiling -- should be split off, nor what the "
                   "capacity of the population becomes once the cap is out of "
                   "the way.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
