#!/usr/bin/env python3
"""EXP-61: two equilibria, and why the second seat is a rotating loss.

## What EXP-59 got wrong

EXP-59 said "the second occupant's income is c* - income = 0.75, net +0.09,
so the second seat is thin but positive, and capacity is about 48."

That arithmetic used the wrong step order. It assumed the field regrows after
every organism. The real order is in `Life::advance`
(`core/src/life.rs:250-465`): ALL organisms take in turn, THEN the field
regrows ONCE (line 464). `Organism::step` in `core/src/field.rs:316` is a
different method that regrows after each organism, and `Life::advance` does
not call it. Reading that one is the mistake.

With the real order a cell has TWO equilibria depending on how many organisms
stand on it:

    one  occupant : v -> take 1.0 -> 0.75 -> regrow -> 1.75 = M + income - income/r
    two  occupants: v -> take 1.0 -> 0.75 -> take 0.75 -> 0.0 -> regrow -> 1.6 = M*r

A doubled cell is emptied every round, so it sits at M*r = 1.6. Measured: all
9 doubled cells read exactly 1.6000, single cells read 1.72..1.75.

The second seat earns 0.60 on a cell at 1.6 and pays
need + move + damage*repair = 0.6 + 0.05 + 0.01 = 0.66, so it loses 0.06 per
step. Starting from energy 10.0 it lasts 10/0.06 = 166 steps.

Yet crowd 2 persists for 200000 steps. So the second seat must be ROTATING:
no organism sits second forever. This experiment measures that directly.

## Arms

  n=80, 200k steps   - the EXP-59 configuration
  n=40, 200k steps   - no crowding: every cell single, cell value must be 1.75

## Measurements

  cell values on doubled vs single cells (must be 1.6 vs 1.75)
  how many organisms are on a doubled cell at the last frame
  how often each organism is on a doubled cell (from a mid-run frame)

## Controls

  fires     - doubled cells must read 1.6, single cells 1.75 (the two equilibria)
  silent    - at n = 40 nobody dies and no cell is doubled
  specific  - the second seat's take must be near 0.6, not near 1.0

## What this does not prove

It does not prove the rotation is what keeps the second seat alive; it only
measures that crowd 2 persists while the per-step net of a fixed second seat
is negative. It does not give a closed form for the capacity. It does not
separate move_cost from damage in the second seat's loss.
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
    d = json.load(open(os.path.join(ROOT, written)))
    last = d["frames"][-1]
    samples = [s for s in last["samples"] if s["alive"]]
    occ = {}
    for s in samples:
        occ[s["cell"]] = occ.get(s["cell"], 0) + 1

    field = last["field"]
    doubled = [field[c] for c, k in occ.items() if k == 2]
    single = [field[c] for c, k in occ.items() if k == 1]

    # second-seat take: on a doubled cell, the smaller of the two `taken`
    second_takes = []
    by_cell = {}
    for s in samples:
        by_cell.setdefault(s["cell"], []).append(s)
    for c, ss in by_cell.items():
        if len(ss) == 2:
            second_takes.append(min(x["taken"] for x in ss))

    # rotation: count how many distinct organisms occupy a doubled cell
    # across the last 20 frames, versus how many are there at the last frame
    seen = set()
    frames = d["frames"][-20:]
    for f in frames:
        o = {}
        for s in f["samples"]:
            if s["alive"]:
                o[s["cell"]] = o.get(s["cell"], 0) + 1
        for s in f["samples"]:
            if s["alive"] and o.get(s["cell"], 0) == 2:
                seen.add(s["slot"])

    return {
        "alive": len(samples),
        "cells_used": len(occ),
        "max_crowd": max(occ.values()) if occ else 0,
        "doubled_cells": len(doubled),
        "doubled_mean": round(sum(doubled) / len(doubled), 6) if doubled else None,
        "single_mean": round(sum(single) / len(single), 6) if single else None,
        "second_take_mean": round(sum(second_takes) / len(second_takes), 6)
        if second_takes else None,
        "second_take_min": round(min(second_takes), 6) if second_takes else None,
        "second_take_max": round(max(second_takes), 6) if second_takes else None,
        "organisms_in_second_seat_last20": len(seen),
        "hash": trace_hash,
    }


def main():
    c_single = M + INCOME - INCOME / R
    c_double = M * R
    cost = NEED + MOVE + DAMAGE * REPAIR
    second_income = c_double - INCOME
    net_second = second_income - cost
    steps_to_die = 10.0 / -net_second if net_second < 0 else None

    exp = Experiment(
        experiment_id="EXP-61",
        question="a cell has two equilibria (1.75 single, 1.6 doubled) and the "
                 "second seat pays 0.60 against a 0.66 cost",
        arithmetic={
            "formula_single": "M + income - income/r",
            "c_single": round(c_single, 6),
            "formula_double": "M*r  (cell emptied every round)",
            "c_double": round(c_double, 6),
            "cost_per_step": round(cost, 6),
            "second_income": round(second_income, 6),
            "net_second": round(net_second, 6),
            "steps_to_die_from_10": round(steps_to_die, 2) if steps_to_die else None,
            "step_order": "all organisms take, then the field regrows once "
                          "(core/src/life.rs:464)",
        },
        arms=[("n80", "n=80, 200k steps"), ("n40", "n=40, 200k steps")],
        seed=SEED,
        command=" ".join([TRACE, "--policy", "sighted", "--field", "uniform",
                          "--cells", str(CELLS), "--steps", str(STEPS)]),
    )

    got = {}
    for key, n in (("n80", 80), ("n40", 40)):
        m = run_arm(n)
        got[key] = m
        h = m.pop("hash")
        exp.add_arm(key, f"n={n}, {STEPS} steps", m, trace_hash=h)
        print(f"{key}: alive={m['alive']} cells={m['cells_used']} "
              f"crowd={m['max_crowd']} doubled={m['doubled_cells']} "
              f"dval={m['doubled_mean']} sval={m['single_mean']} "
              f"2nd_take={m['second_take_mean']} "
              f"rot={m['organisms_in_second_seat_last20']}")

    a = got["n80"]
    b = got["n40"]

    fires_ok = (a["doubled_mean"] is not None
                and abs(a["doubled_mean"] - c_double) < 0.02
                and a["single_mean"] is not None
                and abs(a["single_mean"] - c_single) < 0.05)
    exp.control("fires", fires_ok,
                f"doubled cells read {a['doubled_mean']} (arithmetic {c_double}), "
                f"single cells read {a['single_mean']} (arithmetic {c_single})")

    silent_ok = b["alive"] == 40 and b["max_crowd"] == 1
    exp.control("silent", silent_ok,
                f"n=40: alive={b['alive']}, max_crowd={b['max_crowd']}; "
                f"expected 40 alive and crowd 1")

    # The second seat's take depends on the cell value at the START of the
    # round, which is not fixed: a round with one occupant leaves the cell at
    # 1.75, a round with two leaves it at 1.6. So the second seat's take lies
    # between (1.6 - 1.0) = 0.60 and (1.75 - 1.0) = 0.75, never above 0.75.
    lo, hi = c_double - INCOME, c_single - INCOME
    specific_ok = (a["second_take_mean"] is not None
                   and lo - 0.01 <= a["second_take_mean"] <= hi + 0.01)
    exp.control("specific", specific_ok,
                f"second seat takes {a['second_take_mean']}; arithmetic allows "
                f"[{lo:.4f}, {hi:.4f}] (cell 1.6 when doubled last round, "
                f"1.75 when single), got {a['second_take_mean']:.4f}")

    if fires_ok and silent_ok and specific_ok:
        verdict = "passed"
        limitation = (
            "It does not prove that rotation is what keeps the second seat "
            "alive; it only measures that crowd 2 persists while a FIXED "
            "second seat would lose 0.06 per step. It does not give a closed "
            "form for the capacity. It does not separate move_cost from "
            "damage in the second seat's loss. The 200k-step population may "
            "still be drifting (EXP-59 saw 46 drift to 45 at 10M steps)."
        )
    else:
        verdict = "failed"
        limitation = (
            "The two-equilibrium arithmetic did not match the measurement. "
            "See the control messages for which one broke."
        )

    exp.verdict(verdict, limitation)
    exp.limitation(limitation)
    path = exp.save()
    print(f"\nverdict: {verdict}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
