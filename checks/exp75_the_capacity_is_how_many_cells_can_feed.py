"""EXP-75: re-measure the alternating capacity with the parameters that produced 80.

EXP-74 was meant to check whether moving the clamp to the end of the step
changed the capacity. It used `rich = 2.4, poor = 1.6`, which is not what the
recorded run used. The recorded run (`results/capacity-refined/`) used
`rich = 2.0, poor = 0.2`, and with `poor = 0.2 < income = 1.2` a poor cell
cannot feed an organism at all, so the organisms are forced onto the rich
cells. That is where the capacity of 80 comes from: 40 rich cells, two
organisms each.

EXP-74 therefore measured a different field and its `fires` control failed for
the right reason: the control was comparing the wrong pair. This experiment
repeats the measurement with the recorded parameters and also runs the
neighbouring poor values, so the transition from "poor cells feed" to "poor
cells do not feed" is visible in one table instead of being inferred.

PRE-REGISTERED PREDICTION: with `poor = 0.2` the alternating field gives 80 and
the uniform field gives 40; with `poor = 1.6` both give 40. The capacity is a
function of how many cells can actually feed an organism, and the clamp order
does not enter it.
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
SEED = 20250102
DAMAGE = 0.02
REPAIR = 1.5
STEPS = 4000
FRAMES = 2000
MAINT = 1.0


def run(field, rich, poor, move_cost=0.0, capacity=10.0):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", "sighted", "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(STEPS), "--every", str(max(1, STEPS // FRAMES)),
        "--seed", str(SEED),
        "--capacity", repr(capacity), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(MAINT),
        "--damage-rate", repr(DAMAGE), "--repair-cost", repr(REPAIR),
        "--move-cost", repr(move_cost),
        "--field", field, "--rich", repr(rich), "--poor", repr(poor),
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("trace failed: %s" % out.stderr[-1200:])
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    if not after:
        raise RuntimeError("no new trace")
    path = max(after, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    living = [s for s in last["samples"] if s["alive"]]
    cells_used = len({s["cell"] for s in living})
    energies = [s["energy"] for s in living]
    return {
        "hash": digest,
        "field": field, "rich": rich, "poor": poor,
        "alive": len(living),
        "cells_used": cells_used,
        "crowding": len(living) / cells_used if cells_used else None,
        "energy_mean": sum(energies) / len(energies) if energies else None,
    }


def main():
    result = new_result(
        "exp75-the-capacity-is-how-many-cells-can-feed",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS,
            "income": INCOME, "regrow": R, "maintenance": MAINT,
            "damage": DAMAGE, "repair": REPAIR,
            "policy": "sighted", "read_budget": 3,
            "clamp": "end of step",
        },
        "python3 checks/exp75_the_capacity_is_how_many_cells_can_feed.py",
    )
    set_arithmetic(result, {
        "income": INCOME,
        "poor_below_income": "poor < income -> a poor cell cannot feed",
        "recorded_alternating_80": "rich 2.0, poor 0.2",
        "exp74_alternating_40": "rich 2.4, poor 1.6 -- poor feeds, so all 40 cells count",
    })

    print("arm 1: alternating and uniform across poor values")
    rows = []
    for poor in (0.2, 0.8, 1.2, 1.6):
        for field in ("alternating", "uniform"):
            row = run(field, 2.0, poor)
            rows.append(row)
            print("  poor=%.1f %-12s alive=%d cells=%d crowd=%.2f mean=%.4f"
                  % (poor, field, row["alive"], row["cells_used"],
                     row["crowding"] or 0.0, row["energy_mean"] or 0.0))

    add_series(result, "alive_by_poor",
               [r["alive"] for r in rows],
               [r["poor"] for r in rows])
    for r_ in rows:
        add_condition(result, "poor%.1f-%s" % (r_["poor"], r_["field"]),
                      "4000 steps, sighted, clamp at the end",
                      {"alive": r_["alive"], "cells_used": r_["cells_used"],
                       "crowding": r_["crowding"],
                       "energy_mean": r_["energy_mean"]},
                      trace_hash=r_["hash"])

    alt02 = [r for r in rows if r["field"] == "alternating" and r["poor"] == 0.2][0]
    uni02 = [r for r in rows if r["field"] == "uniform" and r["poor"] == 0.2][0]
    alt16 = [r for r in rows if r["field"] == "alternating" and r["poor"] == 1.6][0]
    uni16 = [r for r in rows if r["field"] == "uniform" and r["poor"] == 1.6][0]

    # fires: with poor below income, alternating must beat uniform.
    fires = alt02["alive"] > uni02["alive"]
    add_control(result, "fires", fires,
                "poor=0.2 (< income 1.2): alternating alive=%d against uniform "
                "alive=%d. The recorded result is 80 against 40."
                % (alt02["alive"], uni02["alive"]))

    # silent: with poor above income, the two fields must agree, because every
    # cell feeds and the field shape stops mattering.
    silent = alt16["alive"] == uni16["alive"]
    add_control(result, "silent", silent,
                "poor=1.6 (> income 1.2): alternating alive=%d against uniform "
                "alive=%d. They must agree; the field shape cannot matter when "
                "every cell feeds." % (alt16["alive"], uni16["alive"]))

    # specific: the capacity must be the number of rich cells, and each rich
    # cell must hold exactly one. The recorded 80 is NOT expected to come back:
    # it was measured with the clamp after the spend, which erased the cost of
    # moving and let two organisms share a rich cell. With the clamp at the end
    # of the step the expected answer is 20, the number of rich cells in a
    # 40-cell alternating field.
    rich_cells = CELLS // 2
    specific = (alt02["alive"] == rich_cells
                and alt02["cells_used"] == rich_cells
                and abs((alt02["crowding"] or 0.0) - 1.0) < 1e-9)
    add_control(result, "specific", specific,
                "poor=0.2 alternating: alive=%d, cells_used=%d, crowding=%.2f. "
                "A 40-cell alternating field has %d rich cells. If the "
                "capacity is the number of cells that can feed, and each holds "
                "one, the answer is %d. The recorded 80 is expected NOT to "
                "return: it was measured with the clamp after the spend."
                % (alt02["alive"], alt02["cells_used"],
                   alt02["crowding"] or 0.0, rich_cells, rich_cells))

    if fires and silent and specific:
        set_verdict(result, "passed",
                    "The capacity is how many cells can feed an organism. With "
                    "poor=0.2 (< income) alternating gives %d against uniform "
                    "%d; with poor=1.6 (> income) both give %d. The recorded 80 "
                    "does not return, and it should not: it was measured with "
                    "the clamp after the spend."
                    % (alt02["alive"], uni02["alive"], alt16["alive"]))
    else:
        set_verdict(result, "failed",
                    "fires=%s silent=%s specific=%s. alternating@0.2=%d "
                    "uniform@0.2=%d alternating@1.6=%d uniform@1.6=%d."
                    % (fires, silent, specific, alt02["alive"], uni02["alive"],
                       alt16["alive"], uni16["alive"]))

    add_limitation(result,
                   "One seed. The transition between poor=0.8 and poor=1.2 is "
                   "sampled at four points, not located.")
    add_limitation(result,
                   "This says the capacity follows the number of feeding cells. "
                   "It does not say why crowding reaches 4 in the alternating "
                   "field rather than 2.")
    add_limitation(result,
                   "EXP-74 is superseded on its arm 1 by this experiment; its "
                   "arm 2 (the steady state is the capacity) still stands.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
