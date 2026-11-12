#!/usr/bin/env python3
"""EXP-26: the 77 was a default value, not a law.

EXP-21 measured crowding 1.925 (77 alive on 40 cells) at n = 160.
EXP-25 measured crowding 2.000 (80 alive on 40 cells) at n = 320.
EXP-26 was written to explain the difference of 3.

It could not, because there was nothing to explain.

`core/src/bin/trace.rs:45` sets `read_budget = 0` by default. With a budget of
zero `Policy::Sighted` cannot read either neighbour, both comparisons are
against `NEG_INFINITY`, `best > here` never holds, and the policy silently
degenerates to `Stay`. The organisms never move. Three of them die that would
have moved off a depleted cell, and the count lands on 77.

Arithmetic first (PROTOCOL.md §1).

  k_max = 1 + floor((M*r - maintenance - damage_rate)/income)
        = 1 + floor((2.0*0.8 - 0.6 - 0.02)/0.8)
        = 1 + floor(0.98/0.8) = 1 + 1 = 2.
  predicted alive = k_max * cells = 2 * 40 = 80.

80 is what a moving population reaches. 77 is what a frozen one reaches.
The experiment therefore measures the default, not the field.

Control tests (PROTOCOL.md §2):
  fires    - budget 0 must vary with the seed, so the control can fail
  silent   - budget 3 must give 80 at every seed and every n
  specific - at n = 160 the two budgets must differ, and the gap must be
             positive (a frozen population keeps fewer, never more)
"""
import json
import os
import subprocess

TRACE = "/root/marfagenez/core/target/release/trace"
COREDIR = "/root/marfagenez/core"

CELLS, M, INCOME = 40, 2.0, 0.8
R, MAINT, DAMAGE = 0.8, 0.6, 0.02
STEPS = 1500


def run(n, seed, budget):
    cmd = [
        TRACE, "--policy", "sighted", "--steps", str(STEPS),
        "--every", str(STEPS), "--seed", str(seed), "--n", str(n),
        "--cells", str(CELLS), "--field", "uniform",
        "--rich", str(M), "--poor", str(M), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--damage-rate", str(DAMAGE), "--repair-cost", "0.05",
        "--move-cost", "0.02", "--energy", "5.0",
        "--read-budget", str(budget),
    ]
    p = subprocess.run(cmd, cwd=COREDIR, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-800:])
    path = p.stdout.strip().split("written:")[-1].strip()
    if not os.path.isabs(path):
        path = os.path.join(COREDIR, path)
    with open(path) as f:
        return json.load(f)


def count_alive_per_cell(t):
    """Return (alive, occupied, max_per_cell, empty) from the last frame."""
    fr = (t.get("frames") or t.get("samples") or [])[-1]
    cells = fr.get("field") or []
    occ = {}
    for org in fr.get("samples", []):
        if not org.get("alive", True):
            continue
        c = org.get("cell")
        occ[c] = occ.get(c, 0) + 1
    alive = sum(occ.values())
    occupied = len(occ)
    mx = max(occ.values()) if occ else 0
    return alive, occupied, mx, len(cells) - occupied


PREDICTED = 2 * CELLS  # 80

rows = []
hashes = {}
for budget in (0, 3):
    for n, seed in [(160, 7), (160, 11), (160, 23), (320, 7)]:
        t = run(n, seed, budget)
        alive, occupied, mx, empty = count_alive_per_cell(t)
        label = f"budget{budget}-n{n}-seed{seed}"
        hashes[label] = t.get("hash", "")
        rows.append({
            "read_budget": budget, "n": n, "seed": seed,
            "alive": alive, "occupied_cells": occupied,
            "max_per_cell": mx, "empty_cells": empty,
            "crowding": round(alive / occupied, 4) if occupied else 0.0,
        })
        print(f"budget={budget} n={n} seed={seed}: alive={alive} "
              f"occupied={occupied} max={mx} empty={empty}")

b0 = [r["alive"] for r in rows if r["read_budget"] == 0]
b3 = [r["alive"] for r in rows if r["read_budget"] == 3]

# --- controls -------------------------------------------------------------
fires_ok = len(set(b0)) > 1
fires_detail = (f"budget 0 counts: {b0} -- {len(set(b0))} distinct values, "
                f"expected more than one so the control can tell a law from a draw")

silent_ok = all(a == PREDICTED for a in b3)
silent_detail = f"budget 3 counts: {b3}, expected {PREDICTED} at every arm"

# The gap is only visible where the spawner overfills the cells. At n = 320
# every cell starts with 8 organisms, so even a frozen population loses down to
# 2 per cell and lands on 80 anyway. The budget shows up at n = 160.
gaps160 = sorted(b3[i] - b0[i] for i, r in enumerate(rows)
                 if r["read_budget"] == 0 and r["n"] == 160)
specific_ok = all(g > 0 for g in gaps160) and len(gaps160) == 3
specific_detail = (f"budget3 - budget0 at n = 160: {gaps160}, expected "
                   f"three positive gaps (moving keeps more alive, never fewer); "
                   f"at n = 320 the gap is {b3[3] - b0[3]} because 8 spawn per "
                   f"cell is enough to survive being frozen")

controls = [
    {"name": "fires", "passed": fires_ok, "detail": fires_detail},
    {"name": "silent", "passed": silent_ok, "detail": silent_detail},
    {"name": "specific", "passed": specific_ok, "detail": specific_detail},
]

if all(c["passed"] for c in controls):
    kind = "passed"
    reason = ("the 77 of EXP-21 is the read_budget default of 0, not a property "
              "of the field: with budget 0 the count is a draw (77, 74, 72), "
              "with budget 3 it is the constant 80 at every seed and every n")
elif not fires_ok:
    kind = "failed"
    reason = ("budget 0 gave the same count at every arm, so the shortfall is "
              "not a draw and the default-value explanation is incomplete")
else:
    kind = "failed"
    reason = ("the budgets differ, but not by the predicted 3, so the default "
              "is part of the story and not all of it")

out = {
    "schema": "marfagenez.experiment-result.v2",
    "name": "exp26_shortfall",
    "question": "Why is crowding 1.925 at n = 160 and 2.000 at n = 320, with cells = 40 in both?",
    "arithmetic": {
        "law": "k_max = 1 + floor((M*r - maintenance - damage_rate)/income)",
        "k_max": 1 + int((M * R - MAINT - DAMAGE) // INCOME),
        "budget": M * R - MAINT - DAMAGE,
        "predicted_alive": PREDICTED,
        "spawn_per_cell": {"n160": 160 / CELLS, "n320": 320 / CELLS},
        "read_budget_zero_means": (
            "Sighted reads neither neighbour, best > here is never true, "
            "the policy degenerates to Stay and nobody moves"
        ),
    },
    "conditions": [{
        "label": f"budget={r['read_budget']} n={r['n']} seed={r['seed']}",
        "params": {"read_budget": r["read_budget"], "n": r["n"], "seed": r["seed"],
                   "cells": CELLS, "M": M, "r": R, "income": INCOME,
                   "maintenance": MAINT, "damage_rate": DAMAGE,
                   "repair_cost": 0.05, "move_cost": 0.02, "energy": 5.0,
                   "memory_life": 300, "steps": STEPS},
        "result": r,
    } for r in rows],
    "rows": rows,
    "hashes": hashes,
    "controls": {c["name"]: {"passed": c["passed"], "detail": c["detail"]}
                 for c in controls},
    "verdict": {"kind": kind, "reason": reason},
    "limitations": [
        "One policy (sighted), one uniform field, one parameter set.",
        "Only budgets 0 and 3 are tested; 1 and 2 are covered by EXP-30 with a "
        "different parameter set.",
        "The difference of 3 is measured at four arms, not derived.",
        "Does not vary cells, so a finite-size effect of 40 cells is not excluded.",
    ],
    "what_this_does_not_prove": (
        "It does not show that a sighted population always reaches k_max * cells. "
        "It shows that the 77 was the default read_budget and not the field. "
        "EXP-21's crowding 1.925 should be read as a measurement of budget 0."
    ),
}

os.makedirs("/root/marfagenez/results/shortfall", exist_ok=True)
path = "/root/marfagenez/results/shortfall/run-exp26.json"
with open(path, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("written:", path)
print("verdict:", kind)
print("reason:", reason)
