#!/usr/bin/env python3
"""EXP-52: the same capacity law, swept along income instead of maintenance.

EXP-32 checked the law

    cost  = maintenance + damage*repair
    k_max = 0                                    if income < cost
          = 1 + floor((M*r - cost)/income)        otherwise

by sweeping `maintenance`. One dimension is still one dimension: a formula can
match a sweep along one axis and be wrong along another, because `income`
appears in the formula twice — as the feasibility gate (`income < cost`) and
as the divisor (`(M*r - cost)/income`). Sweeping maintenance only exercises
the numerator.

This sweeps `income` with maintenance held at 0.6. It is the independent check.

Arithmetic first (PROTOCOL.md §1).

  cells = 40, capacity = 10, M = 2.0, r = 0.8,
  maintenance = 0.6, damage = 0.02, repair = 1.5, move = 0.1.

  cost       = 0.6 + 0.02*1.5 = 0.63        (fixed, because maintenance is)
  regrowth   = M*r - cost = 1.6 - 0.63 = 0.97

  Two thresholds, and they are different thresholds:

    feasibility gate:  income < 0.63  -> k_max = 0
    floor step:        income > 0.97  -> (0.97/income) < 1, so k_max = 1

  Predictions:

      income 0.60 -> 0.60 < 0.63  -> 0  ->  0 survivors
      income 0.70 -> 1 + floor(0.97/0.70) = 1 + 1 = 2 -> 80
      income 0.90 -> 1 + floor(0.97/0.90) = 1 + 1 = 2 -> 80
      income 0.95 -> 1 + floor(0.97/0.95) = 1 + 1 = 2 -> 80
      income 1.00 -> 1 + floor(0.97/1.00) = 1 + 0 = 1 -> 40
      income 1.20 -> 1 + floor(0.97/1.20) = 1 + 0 = 1 -> 40
      income 1.60 -> 1 + floor(0.97/1.60) = 1 + 0 = 1 -> 40

  The shape is not monotone. Capacity rises from 0 to 80 as income crosses
  0.63, holds at 80, then **falls** back to 40 as income crosses 0.97. Giving
  each organism more food lowers the number the field can hold, because the
  cap on one organism's take is also the divisor that decides how many
  organisms one cell's regrowth can pay for.

Two hypotheses:
  H1 (law):  both thresholds are real and the capacity is non-monotone in
             income — 0, then 80, then 40.
  H2 (fit):  the law matched the maintenance sweep by accident and does not
             describe the income axis; in particular the drop from 80 to 40
             is an artifact.

Told apart by the sweep. H2 predicts a monotone curve (more food, more
organisms) or a flat one; H1 predicts a rise and then a fall.

Control tests (PROTOCOL.md §2):
  fires    - the sweep must produce at least two different capacities
  silent   - income 0.90 must reproduce EXP-32's maintenance-0.6 point, since
             at income 0.8 and maintenance 0.6 EXP-32 measured 80; this arm is
             the same regime, so it must give 80 too
  specific - the curve must be non-monotone: it must rise and then fall. A
             monotone curve would pass a "capacity changes" control and must
             fail this one, because the fall is the whole claim
"""

import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment

ROOT = "/root/marfagenez"
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 40
M = 2.0
R = 0.8
MAINTENANCE = 0.6
DAMAGE = 0.02
REPAIR = 1.5
MOVE = 0.1
RICH = 2.4
POOR = 1.6
STEPS = 2000
SEED = 20250101
N = 160

INCOMES = [0.60, 0.70, 0.90, 0.95, 1.00, 1.20, 1.60]

COST = MAINTENANCE + DAMAGE * REPAIR


def k_max(income):
    """The law under test, written once so the arms and the control agree."""
    if income < COST:
        return 0
    return 1 + math.floor((M * R - COST) / income)


def run_arm(income):
    """Runs one arm; `trace` picks its own path and prints it as `written:`."""
    cmd = [
        TRACE,
        "--policy", "sighted",
        "--steps", str(STEPS),
        "--every", "100",
        "--seed", str(SEED),
        "--n", str(N),
        "--cells", str(CELLS),
        "--capacity", "10",
        "--damage-rate", str(DAMAGE),
        "--income", str(income),
        "--maintenance", str(MAINTENANCE),
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
        raise SystemExit(f"trace failed for income={income}:\n{out.stderr}")

    written, trace_hash = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            trace_hash = line.split(":", 1)[1].strip()
    if written is None:
        raise SystemExit(f"trace printed no `written:` line:\n{out.stdout}")

    with open(os.path.join(ROOT, written)) as f:
        data = json.load(f)
    frames = data.get("frames") or []
    samples = frames[-1]["samples"] if frames else []
    alive = sum(1 for s in samples if s.get("alive"))
    return {"alive": alive, "hash": trace_hash}


def main():
    arithmetic = {
        "cost": f"maintenance + damage*repair = {MAINTENANCE} + "
                f"{DAMAGE}*{REPAIR} = {COST}",
        "regrowth_after_cost": f"M*r - cost = {M * R} - {COST} = {M * R - COST}",
        "feasibility_threshold": f"income < {COST} -> k_max = 0",
        "floor_threshold": f"income > {M * R - COST} -> k_max = 1",
        "k_max": "0 if income < cost, else 1 + floor((M*r - cost)/income)",
        "shape": "non-monotone: 0 below cost, 2 between cost and M*r-cost, "
                 "1 above M*r-cost",
        "predictions": {f"{i:.2f}": k_max(i) * CELLS for i in INCOMES},
    }

    rows = []
    for income in INCOMES:
        r = run_arm(income)
        rows.append({
            "income": income,
            "alive": r["alive"],
            "predicted": k_max(income) * CELLS,
            "k_max_formula": k_max(income),
            "hash": r["hash"],
        })
        print(f"income {income:.2f}  alive {r['alive']:<5} "
              f"predicted {k_max(income) * CELLS:<5} hash {r['hash'][:16]}")

    exp = Experiment(
        experiment_id="EXP-52",
        question="Does the capacity law hold along income, where income is both "
                 "the feasibility gate and the divisor, or did EXP-32 only "
                 "exercise the numerator?",
        arithmetic=arithmetic,
        arms={f"i{i:.2f}": f"income {i:.2f}" for i in INCOMES},
        seed=SEED,
        command=" ".join([TRACE, "--policy sighted", "--field uniform",
                          f"--cells {CELLS}", f"--n {N}", f"--steps {STEPS}",
                          f"--maintenance {MAINTENANCE}", f"--rich {RICH}",
                          f"--poor {POOR}"]),
        parameters={
            "cells": CELLS, "M": M, "regrow": R, "maintenance": MAINTENANCE,
            "damage_rate": DAMAGE, "repair_cost": REPAIR, "move_cost": MOVE,
            "rich": RICH, "poor": POOR, "steps": STEPS, "n": N,
        },
    )

    for row in rows:
        exp.add_arm(
            key=f"i{row['income']:.2f}",
            label=f"income {row['income']:.2f}",
            metrics={
                "alive": row["alive"],
                "predicted_capacity": row["predicted"],
                "k_max_formula": row["k_max_formula"],
            },
            trace_hash=row["hash"],
        )

    caps = [r["alive"] for r in rows]
    preds = [r["predicted"] for r in rows]

    fires_ok = len(set(caps)) >= 2
    exp.control(
        "fires",
        fires_ok,
        f"measured capacities across income {INCOMES}: {caps}; "
        f"distinct values {sorted(set(caps))}",
    )

    base = next(r for r in rows if abs(r["income"] - 0.90) < 1e-9)
    silent_ok = base["alive"] == 80
    exp.control(
        "silent",
        silent_ok,
        f"income 0.90 gives {base['alive']} survivors; EXP-32 measured 80 at "
        f"maintenance 0.6 with income 0.8, which is the same regime "
        f"(both incomes are between cost {COST} and M*r-cost {M * R - COST}), "
        f"so the two experiments must agree",
    )

    # specific: the curve must rise and then fall. A monotone curve is the
    # failure mode H2 predicts, so it has to be able to fail here.
    peak = max(caps)
    peak_at = caps.index(peak)
    rose = peak > caps[0]
    fell = peak > caps[-1]
    specific_ok = rose and fell
    exp.control(
        "specific",
        specific_ok,
        f"capacity {caps} at incomes {INCOMES}: peak {peak} at income "
        f"{INCOMES[peak_at]:.2f}, first {caps[0]}, last {caps[-1]}. "
        f"rose={rose} fell={fell}. A monotone curve — more food, more "
        f"organisms — would fail this control, which is the shape H2 predicts.",
    )

    mismatches = [
        (r["income"], r["alive"], r["predicted"])
        for r in rows if r["alive"] != r["predicted"]
    ]

    if not mismatches and specific_ok:
        exp.verdict(
            "passed",
            f"the law holds along income at all {len(rows)} points: capacity is "
            f"{caps} against predicted {preds}, with two distinct thresholds — "
            f"0 below income {COST}, 2 between {COST} and {M * R - COST}, 1 above "
            f"{M * R - COST}. The curve is non-monotone: giving each organism "
            f"more food lowers the number the field holds",
        )
    else:
        exp.verdict(
            "failed",
            f"{len(mismatches)} of {len(rows)} points differ from prediction "
            f"(measured {caps}, predicted {preds}); non-monotone={specific_ok}",
        )

    exp.limitation(
        "Uniform field, sighted policy, read_budget 3, one seed, 2000 steps. "
        "The two thresholds are bracketed by 0.05-wide gaps (0.60/0.70 around "
        "0.63, and 0.95/1.00 around 0.97), so the exact threshold locations are "
        "not resolved beyond that. The non-monotone shape is measured, not "
        "explained: the file says the divisor and the gate are the same "
        "quantity, which is consistent with the shape but does not prove that "
        "is why the population falls. Nothing here says anything about a "
        "gradient field, where EXP-31 found sighting loses."
    )

    path = exp.save()
    print(f"\nsaved {path}")
    print(f"verdict: {exp.result['verdict']['kind']}")


if __name__ == "__main__":
    main()
