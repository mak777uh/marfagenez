"""EXP-74: does moving the clamp to the end of the step change the capacity?

SUPERSEDED -- DO NOT TRUST THIS SCRIPT'S NUMBERS. Kept as a record of a
mistake. Two defects, both found after it ran:

  1. It looked for traces in `core/results/capacity/`, but `trace` writes to
     `core/results/<policy>/`, i.e. `core/results/sighted/`. It therefore found
     an old file and reported the old numbers as if they were new.
  2. It used `rich=2.4, poor=1.6`, but the recorded capacity of 80 was measured
     at `rich=2.0, poor=0.2`. With `poor=1.6 > income=1.2` a poor cell feeds,
     so the field shape cannot matter, and both fields gave 40 -- which is what
     it reported, and which says nothing about the clamp.

`checks/exp75_*.py` replaces it and passes. Its results were deleted.

The clamp in `organism.rs` used to be applied right after the income, which
erased the move cost (see `docs/FINDING-the-cap-is-applied-after-the-spend.md`).
It now runs last, after the income, the maintenance and the repair. All 122
tests pass, but every capacity number in the repo was measured with the old
order and is therefore suspect.

This experiment re-measures the capacity of the population under the new order,
in the two field shapes that gave the two recorded answers:

    alternating -> capacity 80 (the recorded number)
    uniform     -> capacity 40 (the recorded number)

PRE-REGISTERED PREDICTION: the capacity is a property of the field, not of the
order of operations, so the numbers should be unchanged. If they move, the
capacity was partly an artefact of the clamp and every capacity claim in the
repo has to be re-derived.

A second arm checks the steady-state law. With the clamp last the energy of a
rich organism is pinned to `capacity` every step, so the mean energy of a
surviving population must be exactly the capacity, not
`capacity - maintenance - damage*repair`. If the mean is 10.0000 at capacity
10 and 20.0000 at capacity 20, the new order does what it says.
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
DAMAGE = 0.02
REPAIR = 1.5
DRP = DAMAGE * REPAIR
STEPS = 4000
FRAMES = 2000
MAINT = 1.0


def run(policy, field, move_cost, capacity, steps=STEPS, cells=CELLS, n=N):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", policy, "--read-budget", "3",
        "--n", str(n), "--cells", str(cells),
        "--steps", str(steps), "--every", str(max(1, steps // FRAMES)),
        "--seed", str(SEED),
        "--capacity", repr(capacity), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(MAINT),
        "--damage-rate", repr(DAMAGE), "--repair-cost", repr(REPAIR),
        "--move-cost", repr(move_cost),
        "--field", field, "--rich", "2.4", "--poor", "1.6",
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

    cells_used = len({s["cell"] for s in living})
    return {
        "field": field,
        "move_cost": move_cost,
        "capacity": capacity,
        "alive": len(living),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_max": max(energies) if energies else None,
        "energy_min": min(energies) if energies else None,
        "move_fraction": moved / total if total else None,
        "cells_used": cells_used,
        "crowding": len(living) / cells_used if cells_used else None,
    }


def main():
    result = new_result(
        "exp74-capacity-with-the-clamp-at-the-end",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "frames": FRAMES,
            "income": INCOME, "regrow": R,
            "damage": DAMAGE, "repair": REPAIR,
            "policy": "sighted", "maintenance": MAINT,
            "clamp": "end of step",
        },
        "python3 checks/exp74_capacity_with_the_clamp_at_the_end.py",
    )
    set_arithmetic(result, {
        "steady_state_new": "capacity (the clamp is last)",
        "steady_state_old": "capacity - maintenance - damage*repair",
        "recorded_capacity_alternating": 80,
        "recorded_capacity_uniform": 40,
        "drp": DRP,
    })

    # ---- arm 1: capacity in the two field shapes ----
    print("arm 1: capacity by field shape, clamp at the end")
    rows = []
    for field in ("alternating", "uniform"):
        row = run("sighted", field, 0.0, 10.0)
        rows.append(row)
        print("  %-12s alive=%d cells_used=%d crowding=%.2f mean=%.4f max=%.4f"
              % (field, row["alive"], row["cells_used"],
                 row["crowding"] or 0.0, row["energy_mean"] or 0.0,
                 row["energy_max"] or 0.0))

    # ---- arm 2: the steady state is the capacity ----
    print("arm 2: is the mean energy pinned to the capacity?")
    caps = []
    for cap in (10.0, 20.0):
        row = run("sighted", "uniform", 0.0, cap)
        caps.append({"capacity": cap,
                     "energy_mean": row["energy_mean"],
                     "energy_max": row["energy_max"],
                     "residual": (row["energy_mean"] - cap)
                     if row["energy_mean"] is not None else None})
        print("  capacity=%.0f mean=%.4f residual=%+.6f"
              % (cap, row["energy_mean"] or 0.0,
                 (row["energy_mean"] or 0.0) - cap))

    add_series(result, "capacity_by_field",
               [r["alive"] for r in rows],
               [r["crowding"] for r in rows])
    add_condition(result, "capacity_by_field",
                  "population at 4000 steps, clamp at the end", {"points": rows})
    add_condition(result, "steady_state",
                  "mean energy against capacity, uniform, move_cost 0",
                  {"points": caps})

    # ---- controls ----
    alt = rows[0]
    uni = rows[1]

    # fires: the alternating field must still support more than the uniform
    # one. This is the recorded qualitative result and it must survive.
    fires = alt["alive"] > uni["alive"]
    add_control(result, "fires", fires,
                "alternating alive=%d against uniform alive=%d. The recorded "
                "result is that alternating supports more; if it does not, the "
                "clamp change broke the field law."
                % (alt["alive"], uni["alive"]))

    # silent: uniform must still give 40, the recorded number. If it moved,
    # the capacity was an artefact.
    silent = uni["alive"] == 40
    add_control(result, "silent", silent,
                "uniform alive=%d, recorded 40. A different number means the "
                "capacity was partly an artefact of the old clamp."
                % uni["alive"])

    # specific: the mean energy must be the capacity, not the old formula.
    # With the clamp last it is 10.0000; the old order gave 8.97.
    residual = abs(caps[0]["residual"]) if caps[0]["residual"] is not None else 999.0
    specific = residual < 1e-3
    add_control(result, "specific", specific,
                "uniform capacity 10: mean %.4f against capacity 10, residual "
                "%.6f. The old order gave 8.97; the new order must give 10.00."
                % (caps[0]["energy_mean"] or -1.0, residual))

    # ---- verdict ----
    if fires and silent and specific:
        set_verdict(result, "passed",
                    "The capacity did not move. Uniform still gives 40 and "
                    "alternating gives %d, with the clamp at the end. The mean "
                    "energy is now pinned to the capacity (residual %.6f), "
                    "which is what the new order says. The recorded capacity "
                    "of 40 in a uniform field is not an artefact of the old "
                    "clamp." % (alt["alive"], residual))
    elif not silent:
        set_verdict(result, "failed",
                    "The uniform capacity moved from 40 to %d. The capacity "
                    "was partly an artefact of the clamp, and every capacity "
                    "claim in the repo has to be re-derived." % uni["alive"])
    else:
        set_verdict(result, "failed",
                    "A control did not fire: fires=%s silent=%s specific=%s."
                    % (fires, silent, specific))

    add_limitation(result,
                   "One seed, one read budget, one maintenance, one regrow "
                   "rate.")
    add_limitation(result,
                   "Only the uniform and alternating fields are checked. The "
                   "gradient and moving fields are not.")
    add_limitation(result,
                   "This says the capacity of 40 in a uniform field survives "
                   "the clamp change. It does not explain why it is 40, nor "
                   "does it re-derive the 80 in the alternating field as a "
                   "law -- only that it is still larger.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
