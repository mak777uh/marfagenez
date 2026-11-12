"""EXP-22: the crowding law.

k_max = 1 + floor((M*r - maintenance) / income)

Derived from the code, not fitted to data:

  `Life::advance` (core/src/life.rs:429-441) draws for every organism first
  and calls `regrow_all()` once, after the loop. So on one cell with k
  organisms the draws are sequential with no regrowth between them.

  At steady state the cell is drained to zero and regrows from zero to M*r,
  so the step starts at c = M*r.  (Measured: r=0.70 -> field = 1.400 = 2*0.7.)

  The i-th organism gets min(income, M*r - (i-1)*income), so the k-th
  survives iff M*r - (k-1)*income >= maintenance.

Why the previous candidate `floor(M*r/income)` was wrong: it ignores
maintenance, so it puts the 1->2 jump at r = income/M = 0.80, while the
measurement puts it between 0.65 and 0.70.  The new law puts it at
r = (income + maintenance)/M = 0.70.

The point of this experiment is that the law is checked on parameters that
played no part in deriving it. If it only reproduced the r-sweep it came
from, it would be the `p = 0.2` mistake again (LESSONS.md).
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from result import Experiment  # noqa: E402

CORE = "/root/marfagenez/core"
TRACE = os.path.join(CORE, "target/release/trace")
OUT = "/root/marfagenez/results/crowding-law"


def k_max_law(M, r, income, maintenance):
    """1 + floor((M*r - maintenance)/income), clamped at 0."""
    if M * r < maintenance:
        return 0
    return 1 + int((M * r - maintenance) / income)


def run(M, r, income, maintenance, cells, n, steps, seed, policy="stay"):
    cmd = [TRACE, "--policy", policy, "--steps", str(steps), "--every", str(steps),
           "--n", str(n), "--cells", str(cells), "--capacity", str(M),
           "--regrow", str(r), "--damage-rate", "0.02",
           "--income", str(income), "--maintenance", str(maintenance),
           "--repair-cost", "0.05", "--move-cost", "0.02", "--energy", str(M),
           "--field", "uniform", "--rich", str(2 * M), "--poor", "0.0",
           "--seed", str(seed)]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=CORE)
    if p.returncode != 0:
        raise RuntimeError(f"trace failed: {p.stderr[-800:]}")
    path = os.path.join(CORE, "results", policy, "trace.json")
    with open(path) as f:
        d = json.load(f)
    frame = d["frames"][-1]
    alive = [s for s in frame["samples"] if s["alive"]]
    occ = {}
    for s in alive:
        occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    return {
        "alive": len(alive),
        "cells_occupied": len(occ),
        "max_per_cell": max(occ.values()) if occ else 0,
        "field_min": min(frame["field"]),
        "field_max": max(frame["field"]),
        "trace_hash": d.get("hash") or d.get("trace_hash") or "",
    }


# ---------------------------------------------------------------- arithmetic
# The prediction for every arm, computed before any trace runs.
ARMS = [
    # (M, r, income, maintenance) -- the first two are the derivation set,
    # the rest are new.
    (2.0, 0.65, 0.8, 0.6),   # derivation: jump is just below
    (2.0, 0.70, 0.8, 0.6),   # derivation: jump is exactly here
    (2.0, 0.80, 0.8, 0.6),   # derivation
    (2.0, 0.80, 0.4, 0.6),   # NEW: income halved -> k_max = 1+floor(1.0/0.4) = 3
    (2.0, 0.80, 1.2, 0.6),   # NEW: income up -> k_max = 1+floor(1.0/1.2) = 1
    (3.0, 0.60, 0.8, 0.6),   # NEW: M up -> k_max = 1+floor(1.0/0.8) = 2
    (2.0, 0.90, 0.8, 1.0),   # NEW: maintenance up -> k_max = 1+floor(0.8/0.8) = 2
    (2.0, 0.90, 0.8, 1.2),   # NEW: maintenance up more -> k_max = 1+floor(0.6/0.8) = 1
]

CELLS = 40
N = 8 * CELLS           # saturated: 8 organisms per cell at the start
STEPS = 1500
SEED = 7

exp = Experiment(
    name="exp22_crowding_law",
    question="Does k_max = 1 + floor((M*r - maintenance)/income) hold on "
             "parameters that did not take part in deriving it?",
    arithmetic={},
)

predicted = []
for (M, r, inc, mnt) in ARMS:
    predicted.append(k_max_law(M, r, inc, mnt))
exp.arithmetic["predicted_k_max"] = predicted
exp.arithmetic["law"] = "k_max = 1 + floor((M*r - maintenance)/income)"
exp.arithmetic["jump_r"] = "r = (income + maintenance)/M"
exp.arithmetic["derivation"] = (
    "life.rs:429-441 draws for every organism, then regrow_all() once. "
    "On one cell the draws are sequential with no regrowth between them. "
    "The cell is drained to zero and regrows to M*r, so the step starts at "
    "c = M*r and the i-th organism gets min(income, M*r - (i-1)*income)."
)
exp.arithmetic["saturation"] = f"n = {N} = 8 x {CELLS} cells, so every cell starts crowded"

print(f"{'M':<5}{'r':<6}{'inc':<6}{'mnt':<6}{'pred':<6}{'meas':<6}{'alive':<7}{'field'}")
results = []
for (M, r, inc, mnt), pred in zip(ARMS, predicted):
    got = run(M, r, inc, mnt, CELLS, N, STEPS, SEED)
    results.append({"M": M, "r": r, "income": inc, "maintenance": mnt,
                    "predicted": pred, **got})
    print(f"{M:<5.2f}{r:<6.2f}{inc:<6.2f}{mnt:<6.2f}{pred:<6}{got['max_per_cell']:<6}"
          f"{got['alive']:<7}{got['field_max']:.4f}")

exp.arithmetic["measured"] = [
    {k: v for k, v in r.items() if k != "trace_hash"} for r in results
]

# ---------------------------------------------------------------- controls
# fires: the derivation arms must reproduce the known jump (1,2,2).
# silent: a field with no crowding pressure (n = cells) must give 1 per cell
#         regardless of r -- the law must not invent crowding where there is none.
# specific: the law must beat the old law A on the new arms.
deriv = results[:3]
fires = [r["max_per_cell"] for r in deriv] == [1, 2, 2]

silent_arm = run(2.0, 0.80, 0.8, 0.6, CELLS, CELLS, STEPS, SEED)
silent = silent_arm["max_per_cell"] == 1

new_arms = results[3:]
law_hits = sum(1 for r in new_arms if r["predicted"] == r["max_per_cell"])
old_hits = sum(1 for r in new_arms
               if int(r["M"] * r["r"] / r["income"]) == r["max_per_cell"])
specific = law_hits > old_hits

exp.add_control("fires", fires,
                f"derivation arms give max_per_cell = {[r['max_per_cell'] for r in deriv]}, "
                f"expected [1, 2, 2]")
exp.add_control("silent", silent,
                f"n = cells = {CELLS} (no crowding pressure) gives "
                f"max_per_cell = {silent_arm['max_per_cell']}, expected 1")
exp.add_control("specific", specific,
                f"on the 5 arms that did not take part in deriving it: "
                f"new law {law_hits}/5, old law floor(M*r/income) {old_hits}/5")

# ---------------------------------------------------------------- verdict
all_arms = results + [silent_arm]
ok = all(r["predicted"] == r["max_per_cell"] for r in results)
if fires and silent and specific and ok:
    verdict = "passed"
elif not (fires or silent or specific):
    verdict = "void"
else:
    verdict = "failed"

exp.set_verdict(
    verdict,
    limitation=(
        "The law assumes the cell is drained to zero each step, which needs "
        "k*income >= M*r. It says nothing about what happens when the "
        "population is too sparse to keep a cell drained, and it says nothing "
        "about movement: a moving population redistributes and the per-cell "
        "count becomes a distribution, not a single number. It also assumes "
        "energy is a buffer that can absorb a deficit for a while -- the "
        "measured energies at r=0.70 drift down (1.399 -> 0.200 over 1200 "
        "steps), so 'max_per_cell = 2' is a quasi-steady state, not a "
        "permanent one. The law predicts the count, not how long it lasts."
    ),
    what_this_does_not_prove=(
        "It does not prove the Lean model matches the Rust model. It does not "
        "prove anything about a field that is not uniform. It does not prove "
        "that k_max is the only thing that matters for capacity -- the "
        "measured `alive` varies with seed (72-78) while max_per_cell stays 2."
    ),
)

os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "run-exp22.json")
exp.save(path)
print()
print("verdict:", verdict)
print("saved:", path)
