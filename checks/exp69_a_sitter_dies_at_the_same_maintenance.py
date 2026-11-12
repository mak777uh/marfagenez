"""EXP-69: a stay organism dies at the same maintenance as a mover.

The previous round registered two thresholds:

  mover: income - damage*repair          = 1.2 - 0.03 = 1.17
  sitter: c* - damage*repair = 1.7 - 0.03 = 1.67

and measured the collapse at 1.170068, calling it the mover's. That reading of
the sitter was wrong, and this experiment is built to show it.

`c* = 1.7` is the cell LEVEL a stay organism drives its own cell down to. It is
not the amount the organism takes. The take is `min(income, level)`. At the
fixed point the level is 1.7 and income is 1.2, so the take is 1.2 — the same
as a mover's. Subtracting a cost from a level is subtracting litres from
litres per step.

The corrected arithmetic:

  take at a stay organism's own fixed point = min(income, c*) = min(1.2, 1.7) = 1.2
  net per step                              = income - maintenance - damage*repair
  threshold                                 = 1.17, the same as a mover's

The two regimes separate only when the cell cannot supply a full income at its
fixed point, `c* < income`, which is `t > r*(M - income)/(1 - r) = 3.2` at these
settings. At income 1.2 that is not the case, so:

PRE-REGISTERED PREDICTION: `--policy stay` collapses at the same maintenance,
1.17 +- 1e-4, as `--policy sighted` did. If it collapses at 1.67 instead, the
units analysis above is wrong and the level really is the income.

The second half of this experiment varies `damage*repair` independently, which
the previous round listed as never having been done. The law says the threshold
moves with it one-for-one:

  threshold(damage, repair) = income - damage*repair

so doubling damage to 0.04 must move the threshold to 1.2 - 0.06 = 1.14, and
setting damage to 0 must move it to 1.2 exactly. That is three points on a line
whose slope is -1 in `damage*repair`.
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
M = 2.0
R = 0.8
MOVE = 0.10
N = 160
CELLS = 40
SEED = 20250101
E_MAX = 10
STEPS = 8000
EVERY = 8000

DAMAGE = 0.02
REPAIR = 1.5
PREDICTED = INCOME - DAMAGE * REPAIR          # 1.17
OLD_SITTER = 1.7 - DAMAGE * REPAIR            # 1.67


def run(policy, maint, damage=DAMAGE, repair=REPAIR, read_budget=3):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", policy, "--read-budget", str(read_budget),
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(STEPS), "--every", str(EVERY), "--seed", str(SEED),
        "--capacity", str(E_MAX), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(maint),
        "--damage-rate", repr(damage), "--repair-cost", repr(repair),
        "--move-cost", str(MOVE),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=1800)
    if out.returncode != 0:
        raise RuntimeError("trace failed (%s, m=%r, d=%r, rp=%r): %s"
                           % (policy, maint, damage, repair, out.stderr[-1200:]))
    after = set(os.listdir(trace_dir)) - before
    if not after:
        raise RuntimeError("no new trace for %s at m=%r" % (policy, maint))
    path = os.path.join(trace_dir, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    living = [s for s in last["samples"] if s["alive"]]
    energies = [s["energy"] for s in living]
    field = last["field"]
    return {
        "policy": policy,
        "maintenance": maint,
        "damage": damage,
        "repair": repair,
        "cost": maint + damage * repair,
        "alive": len(living),
        "occupied": len({s["cell"] for s in living}),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_min": min(energies) if energies else None,
        "field_mean": sum(field) / len(field),
        "field_min": min(field),
        "field_max": max(field),
    }


def bisect(policy, lo, hi, damage=DAMAGE, repair=REPAIR, res=1e-4, cap=22):
    trail = []
    for _ in range(cap):
        if hi - lo <= res:
            break
        mid = (lo + hi) / 2.0
        row = run(policy, mid, damage, repair)
        trail.append(row)
        print("  %-8s m=%.6f cost=%.6f alive=%3d Emean=%s field=%s"
              % (policy, mid, row["cost"], row["alive"],
                 "--" if row["energy_mean"] is None else "%.4f" % row["energy_mean"],
                 "%.4f..%.4f" % (row["field_min"], row["field_max"])))
        if row["alive"] > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0, trail


def main():
    result = new_result(
        "exp69-a-sitter-dies-at-the-same-maintenance",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "every": EVERY,
            "income": INCOME, "M": M, "regrow": R,
            "move_cost": MOVE, "field": "uniform", "rich": 2.4, "poor": 1.6,
            "e_max": E_MAX,
            "damage_repair_points": [[0.02, 1.5], [0.04, 1.5], [0.0, 1.5]],
            "policies": ["stay", "sighted"],
        },
        "python3 checks/exp69_a_sitter_dies_at_the_same_maintenance.py",
    )
    set_arithmetic(result, {
        "c_star": M + INCOME - INCOME / R,
        "take_at_fixed_point": min(INCOME, M + INCOME - INCOME / R),
        "predicted_threshold": PREDICTED,
        "old_sitter_prediction_wrong": OLD_SITTER,
        "why_old_was_wrong": "c* is a level, not a take; take = min(income, level)",
        "prediction": "stay collapses at 1.17, the same as sighted",
        "damage_law": "threshold = income - damage*repair, slope -1 in damage*repair",
    })

    # ---- arm 1: stay, bisect around the same threshold ----
    print("arm 1: stay, damage 0.02, repair 1.5")
    stay_th, stay_trail = bisect("stay", 1.1, 1.2)
    print("  stay threshold = %.6f (predicted %.6f)" % (stay_th, PREDICTED))

    # ---- arm 2: sighted, same bisection, for the comparison ----
    print("arm 2: sighted, damage 0.02, repair 1.5")
    sighted_th, sighted_trail = bisect("sighted", 1.1, 1.2)
    print("  sighted threshold = %.6f (predicted %.6f)" % (sighted_th, PREDICTED))

    # ---- arm 3: damage*repair varied, stay policy ----
    print("arm 3: stay, damage*repair varied")
    damage_points = [(0.02, 1.5), (0.04, 1.5), (0.0, 1.5)]
    line = []
    for d, rp in damage_points:
        pred = INCOME - d * rp
        th, trail = bisect("stay", pred - 0.1, pred + 0.1, d, rp)
        line.append({"damage": d, "repair": rp, "damage_repair": d * rp,
                     "predicted": pred, "measured": th,
                     "distance": abs(th - pred)})
        print("  d=%.2f rp=%.2f  d*rp=%.3f  predicted=%.6f measured=%.6f dist=%.6f"
              % (d, rp, d * rp, pred, th, abs(th - pred)))

    add_series(result, "stay_bisection", [r["maintenance"] for r in stay_trail],
               [float(r["alive"]) for r in stay_trail])
    add_condition(result, "stay_vs_sighted", "same settings, two policies", {
        "stay_threshold": stay_th,
        "sighted_threshold": sighted_th,
        "predicted": PREDICTED,
        "old_sitter_prediction": OLD_SITTER,
        "stay_trail": stay_trail,
        "sighted_trail": sighted_trail,
    })
    add_condition(result, "damage_line", "damage*repair 0.00, 0.03, 0.06", {
        "points": line,
    })

    # ---- controls ----
    # fires: stay must survive below the threshold. If stay organisms die
    # immediately for some other reason this stays silent.
    low = run("stay", 1.0)
    fires = low["alive"] > 0
    add_control(result, "fires", fires,
                "stay at maintenance 1.0: alive %d, energy mean %s, field %.4f..%.4f"
                % (low["alive"],
                   "--" if low["energy_mean"] is None else "%.4f" % low["energy_mean"],
                   low["field_min"], low["field_max"]))

    # silent: stay must die above the threshold.
    high = run("stay", 1.3)
    silent = high["alive"] == 0
    add_control(result, "silent", silent,
                "stay at maintenance 1.3: alive %d; the dying side is empty"
                % high["alive"])

    # specific: the stay threshold must be 1.17, NOT 1.67. This is the whole
    # point: a control that would pass at both thresholds is not specific.
    d_pred = abs(stay_th - PREDICTED)
    d_old = abs(stay_th - OLD_SITTER)
    specific = d_pred <= 1e-4 and d_old > 0.1
    add_control(result, "specific", specific,
                "stay threshold %.6f: distance to 1.17 is %.6f, distance to the "
                "old sitter prediction 1.67 is %.6f. The arm separates the two "
                "predictions." % (stay_th, d_pred, d_old))

    # ---- verdict ----
    max_line_err = max(p["distance"] for p in line)
    if specific and max_line_err <= 1e-4:
        set_verdict(result, "passed",
                    "A stay organism dies at %.6f, the same maintenance as a "
                    "mover (%.6f), not at the 1.67 the previous round registered. "
                    "c* = 1.7 is the cell level, and the take is min(income, "
                    "level) = 1.2. The threshold moves with damage*repair "
                    "one-for-one: measured %s against predicted %s."
                    % (stay_th, sighted_th,
                       ["%.6f" % p["measured"] for p in line],
                       ["%.6f" % p["predicted"] for p in line]))
    elif not specific:
        set_verdict(result, "failed",
                    "The stay threshold is %.6f. It is %.6f from 1.17 and %.6f "
                    "from 1.67. %s"
                    % (stay_th, d_pred, d_old,
                       "It lands on the old sitter prediction, so the level really "
                       "is being taken as the income and the units analysis in this "
                       "file is wrong."
                       if d_old < d_pred else
                       "It lands on neither, so the per-step net is not "
                       "income - maintenance - damage*repair."))
    else:
        set_verdict(result, "failed",
                    "The stay threshold matched, but the damage line did not: "
                    "worst error %.6f. The threshold is not income - "
                    "damage*repair." % max_line_err)

    add_limitation(result,
                   "One seed, one field shape, one E_max. The thresholds are "
                   "properties of these settings.")
    add_limitation(result,
                   "The trace samples only the last step, so the bisection "
                   "locates where the population is empty at step 8000, not "
                   "where it dies.")
    add_limitation(result,
                   "A stay organism's cell settles at c* = 1.7, above income 1.2, "
                   "so its take is capped by income and the two regimes coincide "
                   "here. The experiment does not test the regime where c* < "
                   "income (t > 3.2 at these settings), where the thresholds "
                   "would separate.")
    add_limitation(result,
                   "damage*repair was varied only through damage, with repair "
                   "fixed at 1.5. The law says only the product matters; this "
                   "does not separate the two factors.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
