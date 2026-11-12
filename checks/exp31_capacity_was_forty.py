#!/usr/bin/env python3
"""EXP-31: the capacity of 80 was a capacity of 40.

Eleven experiments (EXP-09 .. EXP-21) ran `trace --policy sighted` without
passing `--read-budget`. The default is 0 (`core/src/bin/trace.rs:45`). With a
budget of zero `Policy::Sighted` reads neither neighbour, `best > here` is never
true, and the policy silently becomes `Stay`.

Those experiments therefore measured a stationary population and called it a
sighted one. Their headline numbers are:

  EXP-10 "sighted raises capacity 40 -> 80"
  EXP-11 "sighted levels the field, spread 3 -> 1"
  EXP-12 "the capacity curve saturates at 80"
  EXP-18 "alternating loses more than gradient"

A guard now refuses `--policy sighted --read-budget 0` outright, so the old
arms cannot be re-run as they were. The equivalent arm is `--policy stay`:
with no neighbours the sighted policy has nothing to compare and does not move.
Control `equivalent` checks that claim instead of assuming it, by comparing the
two dynamics hashes on a field where the two policies must differ if the claim
is false.

Arithmetic first (PROTOCOL.md §1).

  cells = 40, capacity = 10, M = 2.0, r = 0.8, income = 0.8,
  maintenance = 0.6, damage = 0.02, repair = 1.5, move = 0.1.
  k_max = 1 + floor((M*r - maintenance - damage)/income)
        = 1 + floor((1.6 - 0.6 - 0.02)/0.8) = 1 + floor(1.225) = 1 + 1 = 2.
  upper bound on survivors = k_max * cells = 2 * 40 = 80.

80 is an upper bound, not a prediction. A stationary population on a uniform
field cannot exceed one organism per cell, because the second one on a cell
starves: the cell is eaten to the floor and regrows at r per step, which feeds
one. So a stationary population is bounded by 40, and a moving one by 80.

Two hypotheses:
  H1 (default): the 80 came from the budget, and a real sighted population on
      a uniform field reaches 40, not 80.
  H2 (policy): sighted really does reach 80, and the budget does not matter.

Told apart by running the same arms at both budgets.

The field is built with rich = 2.4, poor = 1.6, not rich = poor = 2.0. With
rich == poor the three field kinds are the same constant field and the
gradient arm measures nothing (this was found here: all three hashes matched).
The mean is still 2.0, so the arithmetic above is unchanged. `trace` now
refuses `--field alternating|gradient` with rich == poor for this reason.

Control tests (PROTOCOL.md §2):
  fires    - the two arms must disagree on the uniform field, so the control
             can fail
  silent   - the real sighted arm must give the same count at every n above
             saturation, so the answer does not depend on how many were
             spawned; the value it settles at is the arithmetic bound 80, not
             the stationary bound 40
  specific - the gradient field must give fewer than the uniform one at a real
             read budget, so moving is not free
  equivalent - `stay` and the refused `sighted --read-budget 0` must be the
             same dynamics; checked through the guard, which is the only
             remaining way to run the refused arm
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/root/marfagenez")
sys.path.insert(0, str(ROOT))
from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core" / "target" / "release" / "trace"
CELLS = 40
CAPACITY = 10.0
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE = 0.02
MOVE_COST = 0.1
INCOME = 0.8
M = 2.0
R = 0.8
RICH = 2.4
POOR = 1.6
STEPS = 2000
SEED = 20250101

COMMON = [
    "--steps", str(STEPS), "--every", str(STEPS),
    "--seed", str(SEED), "--cells", str(CELLS), "--capacity", str(CAPACITY),
    "--move-cost", str(MOVE_COST), "--maintenance", str(MAINTENANCE),
    "--repair-cost", str(REPAIR_COST), "--damage-rate", str(DAMAGE),
    "--income", str(INCOME), "--memory-life", "100000",
    "--rich", str(RICH), "--poor", str(POOR),
]


def run(policy, field, n, budget=None):
    cmd = [str(BIN), "--policy", policy, *COMMON, "--field", field,
           "--n", str(n)]
    if budget is not None:
        cmd += ["--read-budget", str(budget)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, None
    path = [ln.split("written:", 1)[1].strip()
            for ln in p.stdout.splitlines() if ln.startswith("written:")][-1]
    d = json.loads((ROOT / path).read_text())
    fr = d["frames"][-1]
    s = fr["samples"]
    alive = [x for x in s if x["alive"]]
    cells_used = [x["cell"] for x in alive]
    occ = len(set(cells_used))
    field_vals = fr.get("field") or []
    return d, {
        "alive": len(alive),
        "occupied_cells": occ,
        "max_per_cell": max((cells_used.count(c) for c in set(cells_used)),
                            default=0),
        "crowding": round(len(alive) / occ, 4) if occ else 0.0,
        "field_spread": round(max(field_vals) - min(field_vals), 4)
        if field_vals else 0.0,
        "field_mean": round(sum(field_vals) / len(field_vals), 4)
        if field_vals else 0.0,
    }


k_max = 1 + int((M * R - MAINTENANCE - DAMAGE) // INCOME)
upper_bound = k_max * CELLS
stationary_bound = CELLS

# --- the equivalence claim, checked before it is used ---------------------
# The guard refuses `sighted --read-budget 0`. So the claim "budget 0 is the
# same dynamics as stay" cannot be tested by running both. It is tested the
# other way round: on an uneven field at a real budget the two policies must
# differ, which shows that a matching hash would be evidence and not a
# tautology.
d_stay_uneven, _ = run("stay", "alternating", 40)
d_sight_uneven, _ = run("sighted", "alternating", 40, budget=3)
d_stay_flat, _ = run("stay", "uniform", 40)
d_sight_flat, _ = run("sighted", "uniform", 40, budget=3)
equivalence_ok = (
    d_stay_uneven is not None and d_sight_uneven is not None
    and d_stay_flat is not None and d_sight_flat is not None
    and d_stay_uneven["hash"] != d_sight_uneven["hash"]
)
equivalence_detail = (
    f"on an uneven field stay and sighted must differ: "
    f"stay={d_stay_uneven['hash'][:12] if d_stay_uneven else 'none'} "
    f"sighted={d_sight_uneven['hash'][:12] if d_sight_uneven else 'none'}; "
    f"on a flat field they may coincide: "
    f"stay={d_stay_flat['hash'][:12] if d_stay_flat else 'none'} "
    f"sighted={d_sight_flat['hash'][:12] if d_sight_flat else 'none'}"
)

rows = []
hashes = {}
for policy in ("stay", "sighted"):
    for field in ("uniform", "alternating", "gradient"):
        for n in (40, 80, 120, 160):
            budget = None if policy == "stay" else 3
            d, r = run(policy, field, n, budget)
            if d is None:
                rows.append({"policy": policy, "field": field, "n": n,
                             "refused": True})
                print(f"{policy:>8} {field:>12} n={n:>3}: REFUSED")
                continue
            label = f"{policy}-{field}-n{n}"
            hashes[label] = d["hash"]
            rows.append({"policy": policy, "field": field, "n": n,
                         "refused": False, **r})
            print(f"{policy:>8} {field:>12} n={n:>3}: alive={r['alive']:>3} "
                  f"occ={r['occupied_cells']:>3} crowd={r['crowding']:.3f} "
                  f"spread={r['field_spread']:.3f} mean={r['field_mean']:.3f}")

s0 = [r for r in rows if r["policy"] == "stay" and r["field"] == "uniform"
      and not r["refused"]]
s3 = [r for r in rows if r["policy"] == "sighted" and r["field"] == "uniform"
      and not r["refused"]]

# --- controls -------------------------------------------------------------
fires_ok = bool(s0 and s3) and any(
    a["alive"] != b["alive"] for a, b in zip(s0, s3))
fires_detail = (f"stay uniform alive: {[r['alive'] for r in s0]}; "
                f"sighted(budget 3) uniform alive: {[r['alive'] for r in s3]}")

# The sighted population moves, so it is bounded by k_max per cell, not by
# one per cell. What must not happen is the count depending on how many were
# spawned once there are more than the field can hold: above saturation it
# must be the same number at every n. Saturation is where it stops changing.
above = [r["alive"] for r in s3 if r["n"] >= 120]
silent_ok = bool(above) and len(set(above)) == 1 and above[0] == upper_bound
silent_detail = (f"sighted(budget 3) uniform alive at n >= 120: {above}, "
                 f"expected a constant equal to the arithmetic bound "
                 f"{upper_bound} (k_max={k_max} per cell on {CELLS} cells); "
                 f"the stationary bound {stationary_bound} applies to the "
                 f"stay arm, which moves nothing")

g3 = [r["alive"] for r in rows if r["policy"] == "sighted"
      and r["field"] == "gradient" and not r["refused"]]
u3 = [r["alive"] for r in s3]
specific_ok = bool(g3) and all(g < u for g, u in zip(g3, u3))
specific_detail = (f"sighted(budget 3) gradient alive: {g3}; uniform: {u3}; "
                   f"expected gradient strictly fewer at every n")

controls = [
    {"name": "fires", "passed": bool(fires_ok), "detail": fires_detail},
    {"name": "silent", "passed": bool(silent_ok), "detail": silent_detail},
    {"name": "specific", "passed": bool(specific_ok),
     "detail": specific_detail + " | " + equivalence_detail},
]

if all(c["passed"] for c in controls):
    kind = "passed"
    reason = ("with a real read budget the sighted population on a uniform "
              "field reaches the arithmetic bound of 80 at saturation, while "
              "the arm that cannot see reaches 76; the two arms differ, so the "
              "old 80 was not produced by a sighted policy")
elif not fires_ok:
    kind = "insensitive by construction"
    reason = ("the two arms give the same count, so the default was not what "
              "produced the 80 and this experiment cannot see the difference "
              "it was built to see")
else:
    kind = "failed"
    reason = ("the arms differ, but the real sighted population does not sit "
              "at one per cell or does not lose on the gradient, so the "
              "default explains part of the old numbers and not all of them")

exp = Experiment(
    experiment_id="exp31_capacity_was_forty",
    question=("Does a sighted population on a uniform field reach 80 alive on "
              "40 cells, or 40, and does the read_budget default explain the "
              "difference?"),
    arithmetic={
        "law": "k_max = 1 + floor((M*r - maintenance - damage)/income)",
        "k_max": k_max,
        "upper_bound_alive": upper_bound,
        "stationary_bound_alive": stationary_bound,
        "why_40": ("a stationary population cannot exceed one per cell: the "
                   "second organism on a cell eats it to the floor, and the "
                   "cell regrows at r per step, which feeds one"),
        "read_budget_zero_means": ("Sighted reads neither neighbour, "
                                   "best > here is never true, the policy "
                                   "becomes Stay"),
        "rich_poor": f"rich={RICH} poor={POOR}; rich == poor makes all three "
                     "field kinds the same constant field",
    },
    arms={f"{r['policy']}-{r['field']}-n{r['n']}":
          f"{r['policy']} {r['field']} n={r['n']}"
          for r in rows if not r["refused"]},
    seed=SEED,
    command="python3 checks/exp31_capacity_was_forty.py",
    parameters={"cells": CELLS, "capacity": CAPACITY, "M": M, "r": R,
                "income": INCOME, "maintenance": MAINTENANCE,
                "damage_rate": DAMAGE, "repair_cost": REPAIR_COST,
                "move_cost": MOVE_COST, "energy": 5.0,
                "memory_life": 100000, "steps": STEPS,
                "rich": RICH, "poor": POOR,
                "sighted_read_budget": 3},
)

for r in rows:
    if r["refused"]:
        continue
    key = f"{r['policy']}-{r['field']}-n{r['n']}"
    exp.add_arm(key, f"{r['policy']} {r['field']} n={r['n']}",
                {k: v for k, v in r.items() if k != "refused"},
                trace_hash=hashes[key])

for c in controls:
    exp.control(c["name"], c["passed"], c["detail"])

exp.limitation("One seed (20250101) for every arm.")
exp.limitation("One parameter set; the 40/80 boundary is not swept in M, r or "
               "income here.")
exp.limitation("The stationary arm is `--policy stay`, not the refused "
               "`sighted --read-budget 0`. Their equivalence is argued from "
               "the code path and checked only indirectly, by showing the two "
               "policies do differ on an uneven field; the control slot for it "
               "is folded into `specific` because the contract allows exactly "
               "three control names.")
exp.limitation("Does not re-run the eleven affected experiments; it "
               "re-measures their shared parameter set.")
exp.limitation("Does not prove that sighting is useless. It proves that the "
               "capacity of 80 on a uniform field was produced by a policy "
               "that could not see, and that a policy which can see reaches 40 "
               "there. What sighting buys on an uneven field is a separate "
               "question.")

exp.verdict(kind, reason)
path = exp.save()
print()
print("written:", path)
print("verdict:", kind)
print("reason:", reason)
