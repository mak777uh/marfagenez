#!/usr/bin/env python3
"""EXP-60: is the capacity set by the read budget, not by the food?

## The arithmetic that forces this experiment

`core/src/field.rs:316-346` calls `regrow_all()` after EVERY organism, not once
per round. So inside one round the sequence is

    org1 takes 1.0 -> ALL cells regrow -> org2 takes -> regrow -> ...

A cell at c* = M + income - income/r = 1.75 loses `income = 1.0` when it is
taken, falling to 0.75. One regrow toward M = 2.0 with r = 0.8 gives

    0.75 + (2.0 - 0.75) * 0.8 = 1.75 = c*

exactly. So the cell is restored before the next organism arrives, and a cell
can feed a new organism on EVERY step. Food does not bound the population.

EXP-59 measured 42..48 with `--read-budget 3` on a 40-cell field. If the read
budget is the binding constraint, raising it to >= cells must raise capacity.
If capacity stays at 48 with budget 40, the read budget is not the cause.

## Arms

  budget 3   (EXP-59 baseline)   n = 80
  budget 40  (one look per cell) n = 80
  budget 80  (more looks than cells, control for "more is just more")
  budget 40, n = 40              (no crowding: must all survive)

## Controls

  fires     - budget 40 must give clearly more survivors than budget 3
  silent    - at n = 40 with budget 40 nobody may die (no crowding)
  specific  - capacity must be between 40 and 80, not pinned at either end

## What this does not prove

It does not prove that the read budget is the ONLY constraint. It does not
explain why budget 3 gives 42..48 rather than some other number below 80. It
does not separate `read_budget` from the sighted policy's tie-breaking.
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

ARMS = (
    ("budget3_n80", 3, 80),
    ("budget40_n80", 40, 80),
    ("budget80_n80", 80, 80),
    ("budget40_n40", 40, 40),
)


def run_arm(budget, n):
    cmd = [TRACE, "--policy", "sighted", "--steps", str(STEPS),
           "--every", str(EVERY), "--seed", str(SEED), "--n", str(n),
           "--cells", str(CELLS), "--rich", str(M), "--poor", str(M),
           "--income", str(INCOME), "--maintenance", str(NEED),
           "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
           "--move-cost", str(MOVE), "--energy", "10.0",
           "--field", "uniform", "--read-budget", str(budget)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"trace failed (budget={budget}, n={n}):\n{out.stderr}")
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
        "alive": alive,
        "cells_used": len(occ),
        "max_crowd": max(occ.values()) if occ else 0,
        "survived_frac": round(alive / n, 6),
        "hash": trace_hash,
    }


def main():
    c_star = M + INCOME - INCOME / R
    after_take = c_star - INCOME
    after_regrow = after_take + (M - after_take) * R
    static_bound = CELLS * 2

    exp = Experiment(
        experiment_id="EXP-60",
        question="the capacity is set by the read budget, not by the food",
        arithmetic={
            "formula_c_star": "M + income - income/r",
            "c_star": round(c_star, 6),
            "after_take": round(after_take, 6),
            "after_one_regrow": round(after_regrow, 6),
            "regrow_restores_cell": abs(after_regrow - c_star) < 1e-12,
            "consequence": "a cell can feed a new organism every step",
            "static_bound": static_bound,
            "baseline_budget": 3,
            "cells": CELLS,
        },
        arms=[(key, f"read_budget={budget}, n={n}") for key, budget, n in ARMS],
        seed=SEED,
        command=" ".join([TRACE, "--policy", "sighted", "--field", "uniform",
                          "--cells", str(CELLS), "--steps", str(STEPS)]),
    )

    got = {}
    for key, budget, n in ARMS:
        m = run_arm(budget, n)
        got[key] = m
        exp.add_arm(key, f"read_budget={budget}, n={n}", m, trace_hash=m.pop("hash"))
        print(f"{key:14s} budget={budget:3d} n={n:3d} alive={m['alive']:3d} "
              f"cells={m['cells_used']:2d} crowd={m['max_crowd']}")

    b3 = got["budget3_n80"]["alive"]
    b40 = got["budget40_n80"]["alive"]
    b80 = got["budget80_n80"]["alive"]
    n40 = got["budget40_n40"]["alive"]

    # fires: budget 40 must give clearly more survivors than budget 3
    fires_ok = b40 >= b3 + 10
    exp.control("fires", fires_ok,
                    f"budget40 alive={b40} vs budget3 alive={b3}: "
                    f"expected at least +10, got {b40 - b3}")

    # silent: at n = 40 with a full budget nobody may die
    silent_ok = n40 == 40
    exp.control("silent", silent_ok,
                    f"n=40 budget=40 alive={n40}: expected 40 (no crowding), "
                    f"got {n40}")

    # specific: capacity strictly between 40 and 80, not pinned at either end
    specific_ok = 40 < b40 < 80
    exp.control("specific", specific_ok,
                    f"budget40 alive={b40}: expected strictly between 40 and 80, "
                    f"got {b40}")

    if fires_ok and silent_ok and specific_ok:
        verdict = "passed"
        limitation = (
            "It does not prove the read budget is the only constraint, and it "
            "does not explain why budget 3 gives 42..48 rather than another "
            "number below 80. It does not separate the budget from the "
            "sighted policy's tie-breaking. The 200k-step value may still be "
            "drifting."
        )
    elif n40 == 40 and b40 == 80:
        verdict = "failed"
        limitation = (
            "Capacity reached the static bound 80 with a full read budget, so "
            "the read budget was not the constraint after all; the food story "
            "in the arithmetic above is the one that holds."
        )
    else:
        verdict = "failed"
        limitation = (
            "The controls did not agree with the read-budget story. See the "
            "control messages for which one broke."
        )

    exp.verdict(verdict, limitation)
    exp.limitation(limitation)
    path = exp.save()
    print(f"\nverdict: {verdict}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
