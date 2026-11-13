"""EXP-59: the capacity of the field is about 48, not 80.

## The question

EXP-57 measured 46 survivors at `n = 80` and the static bound was computed as
`cells * k_max = 40 * 2 = 80`. The note `FINDING-static-count-is-a-ceiling.md`
was then rewritten because the population was *below* the bound, not above it.
But "below the bound" left the obvious question unasked: **is the bound
reachable at all?**

Every previous capacity measurement started at `n = 80` or above. If the field
can hold 80, then starting at 80 should lose nobody. It loses 34. That is
already a contradiction, and it was sitting in plain sight.

## Arithmetic before the run

`M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.0`, `cells = 40`,
`move_cost = 0.05`, `damage_rate = 0.02`, `repair_cost = 0.5`.

A single occupant reaches the steady cell value

    c* = M + income - income/r = 2 + 1 - 1.25 = 1.75

and takes `min(1.75, income) = 1.0`. Its net per step is
`1.0 - 0.6 - 0.05 - 0.02*0.5 = +0.34`, so it thrives.

A second occupant eats what the first left. The cell is at 1.75 when the step
starts, the first takes 1.0, so the second gets at most 0.75. Its net is

    0.75 - 0.6 - 0.05 - 0.01 = +0.09

which is positive but thin. If the second occupant arrives late in a step, or
the cell is still recovering from a previous double occupancy, it gets closer
to `M*r - income = 0.6`, and its net becomes

    0.6 - 0.6 - 0.05 - 0.01 = -0.06

which is a slow death.

So the prediction is: **the field holds 40 comfortably, admits a few second
occupants on the best cells, and refuses the rest.** Capacity should land well
below 80 and above 40. I predict 45-50.

## Prediction

`alive(n)` is flat at `n` for `n <= 40`, then saturates at 45-50 for `n >= 50`.

## What this does not prove

It does not say *which* cells admit a second occupant, and it does not say the
saturation value is a sharp capacity rather than a slow leak. The 200k-step
horizon is long enough for the fast deaths but the earlier 10M-step run showed
the count still drifting down by one or two. The saturation value is therefore
an upper estimate of the long-run capacity.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

M = 2.0
R = 0.8
NEED = 0.6
INCOME = 1.0
CELLS = 40
MOVE = 0.05
DAMAGE = 0.02
REPAIR = 0.5
STEPS = 200000
EVERY = 2000
SEED = 1

NS = (10, 20, 30, 40, 50, 60, 70, 80, 120, 160)


def run_arm(n):
    cmd = [TRACE, "--policy", "sighted", "--steps", str(STEPS),
           "--every", str(EVERY), "--seed", str(SEED), "--n", str(n),
           "--cells", str(CELLS), "--rich", str(M), "--poor", str(M),
           "--income", str(INCOME), "--maintenance", str(NEED),
           "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
           "--move-cost", str(MOVE), "--energy", "10.0",
           "--field", "uniform", "--read-budget", "3"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"trace failed for n={n}:\n{out.stderr}")
    written, trace_hash = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            trace_hash = line.split(":", 1)[1].strip()
    d = json.load(open(written))
    last = d["frames"][-1]
    alive = sum(1 for s in last["samples"] if s["alive"])
    occ = {}
    for s in last["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    return {
        "n": n,
        "alive": alive,
        "cells_used": len(occ),
        "max_crowd": max(occ.values()) if occ else 0,
        "survived_frac": alive / n,
        "hash": trace_hash,
    }


def main():
    # Arithmetic, computed here so it is printed next to the measurement.
    c_single = M + INCOME - INCOME / R
    t_first = min(c_single, INCOME)
    t_second = c_single - t_first
    net_single = t_first - NEED - MOVE - DAMAGE * REPAIR
    net_second = t_second - NEED - MOVE - DAMAGE * REPAIR
    net_floor = (M * R - INCOME) - NEED - MOVE - DAMAGE * REPAIR
    k_max = 1 + int((M * R - INCOME) // NEED)
    static_bound = CELLS * k_max

    exp = Experiment(
        experiment_id="EXP-59",
        question="the capacity of the field is about 48, not 80",
        arithmetic={
            "formula_c_single": "M + income - income/r",
            "c_single": round(c_single, 6),
            "t_first": round(t_first, 6),
            "t_second": round(t_second, 6),
            "net_single": round(net_single, 6),
            "net_second": round(net_second, 6),
            "net_floor": round(net_floor, 6),
            "k_max": k_max,
            "static_bound": static_bound,
        },
        arms={str(n): f"n={n}" for n in NS},
        seed=SEED,
        command="python3 checks/exp59_capacity_sweep.py",
    )

    arms = {}
    for n in NS:
        r = run_arm(n)
        arms[str(n)] = r
        exp.add_arm(str(n), f"n={n}", r, trace_hash=r["hash"])
        print(f"n={n:>4} alive={r['alive']:>4} cells={r['cells_used']:>3} "
              f"crowd={r['max_crowd']} hash={r['hash']}")

    # Control 1: fires. If the field could hold the static bound, starting at
    # 40 would already be at half capacity and the sweep would never saturate.
    sat = max(r["alive"] for r in arms.values())
    fires_ok = sat < static_bound
    exp.control("fires", fires_ok,
                f"peak alive {sat} against static bound {static_bound}; "
                f"the bound is {'unreached' if fires_ok else 'reached'}")

    # Control 2: silent. Below the number of cells nothing should die: every
    # organism gets its own cell and takes the full income.
    below = [r for r in arms.values() if r["n"] <= CELLS]
    silent_ok = all(r["alive"] == r["n"] for r in below)
    exp.control("silent", silent_ok,
                "for n <= cells every organism survives: "
                + ", ".join(f"n={r['n']} alive={r['alive']}" for r in below))

    # Control 3: specific. The saturation must be the same for every n above
    # the cell count, and it must be strictly between cells and the bound. If
    # the number just tracked n, nothing saturates and the claim is empty.
    above = [r["alive"] for r in arms.values() if r["n"] > CELLS]
    spread = max(above) - min(above)
    specific_ok = (CELLS < min(above) and max(above) < static_bound
                   and spread <= 8)
    exp.control("specific", specific_ok,
                f"for n > cells alive ranges {min(above)}..{max(above)} "
                f"(spread {spread}), strictly between {CELLS} and "
                f"{static_bound}")

    passed = fires_ok and silent_ok and specific_ok
    exp.verdict(
        "passed" if passed else "failed",
        f"capacity saturates at {min(above)}-{max(above)} for n > {CELLS}, "
        f"not at the static bound {static_bound}",
    )
    exp.limitation(
        "The saturation value is an upper estimate: the 10M-step run showed "
        "the count still drifting down by one or two. The experiment does not "
        "identify which cells admit a second occupant, and it does not separate "
        "the move cost from the damage cost as the reason the second occupant "
        "fails."
    )
    path = exp.save()
    print("written:", path)


if __name__ == "__main__":
    main()
