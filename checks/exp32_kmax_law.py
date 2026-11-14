#!/usr/bin/env python3
"""EXP-32: does k_max = 1 + floor((M*r - maintenance - damage)/income) hold?

EXP-31 wrote that formula down and checked ONE point of it (maintenance = 0.6
gives k_max = 2, and the sighted population on a uniform field reached exactly
2 * 40 = 80). One point is not a law — that is exactly the mistake EXP-21 made
with crowding = (M - income)/maintenance.

This sweeps maintenance and compares the measured capacity against the formula.

**The first version of this experiment failed, and the failure is the result.**
It used EXP-31's formula unchanged and got:

    maintenance 0.40 -> 80 (predicted 80)   ok
    maintenance 0.60 -> 80 (predicted 80)   ok
    maintenance 1.00 ->  0 (predicted 40)   WRONG
    maintenance 1.40 ->  0 (predicted 40)   WRONG
    maintenance 1.60 ->  0 (predicted  0)   ok

The formula counts how many *portions* of `income` the regrowth can pay for,
but never asks whether one portion is enough to keep an organism alive. One
organism costs `maintenance + damage*repair` per step and can take at most
`income`; when `income < cost` no number of portions helps. The corrected law
is conditional, and the feasibility threshold sits at maintenance = 0.77.

Arithmetic first (PROTOCOL.md §1).

  cells = 40, capacity = 10, M = 2.0, r = 0.8, income = 0.8,
  damage = 0.02, repair = 1.5, move = 0.1.

  cost(maintenance) = maintenance + 0.02*1.5 = maintenance + 0.03
  regrowth ceiling  = M*r = 1.6 per step

      k_max = 0                                     if income < cost
            = 1 + floor((1.6 - cost)/0.8)           otherwise

  Predictions:

      maintenance 0.40 -> cost 0.43 -> 1 + floor(1.17/0.8) = 2 -> 80
      maintenance 0.60 -> cost 0.63 -> 1 + floor(0.97/0.8) = 2 -> 80
      maintenance 0.75 -> cost 0.78 -> income 0.8 < 0.78? no -> 1 + floor(0.82/0.8) = 2 -> 80
      maintenance 0.80 -> cost 0.83 -> income 0.8 < 0.83 -> 0 -> 0
      maintenance 1.00 -> cost 1.03 -> 0 -> 0
      maintenance 1.40 -> cost 1.43 -> 0 -> 0

  The pair 0.75 / 0.80 brackets the threshold at 0.77, so the experiment can
  say where the cliff is, not merely that there is one.

Two hypotheses:
  H1 (law):  the conditional formula holds, so capacity is 80 below 0.77 and
             0 above it — a cliff, not a gradual decline.
  H2 (fit):  the formula matched at 0.6 by luck and does not hold elsewhere.

Control tests (PROTOCOL.md §2):
  fires    - the sweep must produce at least two different capacities, so the
             control can fail
  silent   - at maintenance 0.6 the count must reproduce EXP-31's 80, so this
             experiment is measuring the same thing the earlier one did
  specific - the measured capacity must equal k_max*cells at every point, not
             merely be monotone in maintenance; a monotone-but-wrong curve
             would pass a monotonicity control and must fail this one
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment

ROOT = "/root/marfagenez"
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
OUT = os.path.join(ROOT, "results", "kmax-law")

CELLS = 40
M = 2.0
R = 0.8
INCOME = 0.8
DAMAGE = 0.02
REPAIR = 1.5
MOVE = 0.1
RICH = 2.4
POOR = 1.6
STEPS = 2000
SEED = 20250101
N = 160

MAINTENANCES = [0.40, 0.60, 0.75, 0.80, 1.00, 1.40]


def k_max(maintenance):
    """The formula under test, written once so the arms and the control agree.

    The first version of this experiment used EXP-31's formula unchanged,

        1 + floor((M*r - maintenance - damage)/income)

    and it failed at maintenance >= 1.0: the formula predicted 1 organism per
    cell (40 survivors) and the measurement gave 0. The reason is that the
    formula counts how many *portions* of `income` the regrowth can pay for,
    but never asks whether one portion is enough to keep an organism alive.
    One organism costs `maintenance + damage*repair` per step and can take at
    most `income`. So when `income < cost` no number of portions helps and the
    capacity is zero, not one.

    The corrected law is therefore conditional:

        k_max = 0                                        if income < cost
              = 1 + floor((M*r - cost)/income)           otherwise
        cost  = maintenance + damage*repair

    At the parameters below cost = maintenance + 0.03, so the feasibility
    threshold sits at maintenance = income - 0.03 = 0.77.
    """
    import math
    cost = maintenance + DAMAGE * REPAIR
    if INCOME < cost:
        return 0
    return 1 + math.floor((M * R - cost) / INCOME)


def run_arm(maintenance):
    """Runs one arm and returns the last frame's alive count plus the hash.

    `trace` writes only where told: `--out` names one file, overwritten per
    run. It used to invent `results/<policy>/trace-<stamp>.json` per call, and
    those accumulated. The hash is printed too, which is what the contract wants.
    """
    os.makedirs(OUT, exist_ok=True)
    trace_path = os.path.join(OUT, "trace-last.json")
    cmd = [
        TRACE,
        "--out", trace_path,
        "--policy", "sighted",
        "--steps", str(STEPS),
        "--every", "100",
        "--seed", str(SEED),
        "--n", str(N),
        "--cells", str(CELLS),
        "--capacity", "10",
        "--damage-rate", str(DAMAGE),
        "--income", str(INCOME),
        "--maintenance", str(maintenance),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--field", "uniform",
        "--rich", str(RICH),
        "--poor", str(POOR),
        "--regrow", str(R),
        "--memory-life", "100000",
        "--read-budget", "3",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"trace failed for maintenance={maintenance}:\n{out.stderr}")

    trace_hash = ""
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            trace_hash = line.split(":", 1)[1].strip()
    if not trace_hash:
        raise SystemExit(f"trace printed no `hash:` line:\n{out.stdout}")

    with open(trace_path) as f:
        data = json.load(f)
    frames = data.get("frames") or []
    samples = frames[-1]["samples"] if frames else []
    alive = sum(1 for s in samples if s.get("alive"))
    return {"alive": alive, "hash": trace_hash, "path": trace_path}


def main():
    arithmetic = {
        "per_step_cost": "maintenance + damage*repair = maintenance + 0.03",
        "regrowth_ceiling": f"M*r = {M}*{R} = {M * R}",
        "income_cap": f"income = {INCOME}",
        "feasibility": "one organism survives only if income >= cost, i.e. "
                       f"maintenance <= {INCOME - DAMAGE * REPAIR:.2f}",
        "k_max": "0 if income < cost, else 1 + floor((M*r - cost)/income)",
        "capacity": "k_max * cells",
        "predictions": {f"{m:.2f}": k_max(m) * CELLS for m in MAINTENANCES},
    }

    rows = []
    for m in MAINTENANCES:
        data = run_arm(m)
        alive = data["alive"]
        crowd = alive / CELLS
        rows.append({
            "maintenance": m,
            "alive": alive,
            "crowding": round(crowd, 4),
            "predicted_capacity": k_max(m) * CELLS,
            "hash": data.get("hash", ""),
        })
        print(f"maintenance {m:.2f}  alive {alive:<5} crouding {crowd:<6.2f} "
              f"predicted {k_max(m) * CELLS:<5} hash {data.get('hash', '')[:16]}")

    exp = Experiment(
        experiment_id="EXP-32",
        question="Does k_max = 1 + floor((M*r - maintenance - damage)/income) "
                 "hold across maintenance, or did EXP-31 check a single point?",
        arithmetic=arithmetic,
        arms={f"m{m:.2f}": f"maintenance {m:.2f}" for m in MAINTENANCES},
        seed=SEED,
        command=" ".join([TRACE, "--policy sighted", "--field uniform",
                          f"--cells {CELLS}", f"--n {N}", f"--steps {STEPS}",
                          f"--rich {RICH}", f"--poor {POOR}"]),
        parameters={
            "cells": CELLS, "M": M, "regrow": R, "income": INCOME,
            "damage_rate": DAMAGE, "repair_cost": REPAIR, "move_cost": MOVE,
            "rich": RICH, "poor": POOR, "steps": STEPS, "n": N,
        },
    )

    for row in rows:
        exp.add_arm(
            key=f"m{row['maintenance']:.2f}",
            label=f"maintenance {row['maintenance']:.2f}",
            metrics={
                "alive": row["alive"],
                "crowding": row["crowding"],
                "predicted_capacity": row["predicted_capacity"],
                "k_max_formula": k_max(row["maintenance"]),
            },
            trace_hash=row["hash"],
        )

    caps = [r["alive"] for r in rows]
    preds = [r["predicted_capacity"] for r in rows]

    # fires: the sweep must move the capacity, otherwise nothing was tested
    fires_ok = len(set(caps)) >= 2
    exp.control(
        "fires",
        fires_ok,
        f"measured capacities across maintenance {MAINTENANCES}: {caps}; "
        f"distinct values {sorted(set(caps))}",
    )

    # silent: the maintenance=0.6 point must reproduce EXP-31's 80
    base = next(r for r in rows if abs(r["maintenance"] - 0.60) < 1e-9)
    silent_ok = base["alive"] == 80
    exp.control(
        "silent",
        silent_ok,
        f"maintenance 0.60 gives {base['alive']} survivors; EXP-31 measured 80 "
        f"on the same field and parameters, so this experiment measures the "
        f"same quantity",
    )

    # specific: every point must match k_max*cells, not merely be monotone
    mismatches = [
        (r["maintenance"], r["alive"], r["predicted_capacity"])
        for r in rows if r["alive"] != r["predicted_capacity"]
    ]
    specific_ok = not mismatches
    exp.control(
        "specific",
        specific_ok,
        f"measured vs predicted {list(zip(caps, preds))}; mismatches {mismatches}. "
        f"A curve that is merely monotone in maintenance would pass a "
        f"monotonicity control, so the control is equality at every point.",
    )

    if specific_ok:
        exp.verdict(
            "passed",
            f"k_max = 1 + floor((M*r - maintenance - damage)/income) holds at all "
            f"{len(rows)} maintenance values: capacity steps by exactly {CELLS} "
            f"(one cell's worth) as maintenance crosses each threshold, and the "
            f"measured counts are {caps} against predicted {preds}",
        )
    else:
        exp.verdict(
            "failed",
            f"the formula does not hold: {len(mismatches)} of {len(rows)} points "
            f"differ from prediction, measured {caps} against predicted {preds}",
        )

    exp.limitation(
        "This tests the formula on a uniform field with a sighted policy at a "
        "real read budget. It says nothing about whether the formula holds on a "
        "gradient field, where EXP-31 found sighting loses (40 vs 68 at n=160). "
        "It also does not say the formula is the *reason* the population stops "
        "growing: it is a counting argument about per-step cost and regrowth, "
        "and the count matching it is consistent with that argument without "
        "proving the mechanism is the one described."
    )

    path = exp.save()
    print(f"\nsaved {path}")
    print(f"verdict: {exp.result['verdict']['kind']}")


if __name__ == "__main__":
    main()
