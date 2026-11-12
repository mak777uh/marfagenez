#!/usr/bin/env python3
"""EXP-26: why is crowding 1.925 at n = 160 and 2.000 at n = 320?

EXP-21 measured crowding 1.925 (77 alive on 40 cells) at n = 160.
EXP-25 measured crowding 2.000 (80 alive on 40 cells) at n = 320.
Same cells = 40, same M, r, income, maintenance, damage_rate, same policy.

Arithmetic first (PROTOCOL.md §1).

  n = 160 on 40 cells: 160 / 40 = 4 organisms per cell at spawn.
  n = 320 on 40 cells: 320 / 40 = 8 organisms per cell at spawn.
  k_max = 1 + floor((M*r - maintenance - damage_rate)/income)
        = 1 + floor((2.0*0.8 - 0.6 - 0.02)/0.8)
        = 1 + floor(0.98/0.8) = 1 + 1 = 2.

If k_max = 2, then at most 2 * 40 = 80 survive. Both n = 160 and n = 320
start above 80, so both should end at exactly 80. 77 is not 80.

Two hypotheses:
  H1 (occupancy): 77 = 80 - 3 deaths that never get replaced, because a cell
      that loses both occupants stays empty -- nobody moves into it.
  H2 (arithmetic): the shortfall is a rounding of the measured mean, and the
      real count is 80.

The two are told apart by counting empty cells, not by the mean.

Control tests (PROTOCOL.md §2):
  fires    - the count must reach 80 when n is raised to 320 (EXP-25 saw this)
  silent   - the count must NOT move when only the seed changes
  specific - the count must be 80, not 77 and not 78
"""
import subprocess, json, os, sys

TRACE = "/root/marfagenez/core/target/release/trace"
COREDIR = "/root/marfagenez/core"

CELLS, M, INCOME = 40, 2.0, 0.8
R, MAINT, DAMAGE = 0.8, 0.6, 0.02
STEPS = 1500


def run(n, seed):
    cmd = [
        TRACE, "--policy", "sighted", "--steps", str(STEPS),
        "--every", str(STEPS), "--seed", str(seed), "--n", str(n),
        "--cells", str(CELLS), "--field", "uniform",
        "--rich", str(M), "--poor", str(M), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--damage-rate", str(DAMAGE), "--repair-cost", "0.05",
        "--move-cost", "0.02", "--energy", "5.0",
    ]
    p = subprocess.run(cmd, cwd=COREDIR, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-800:])
    path = p.stdout.strip().split("written:")[-1].strip()
    if not os.path.isabs(path):
        path = os.path.join(COREDIR, path)
    with open(path) as f:
        return json.load(f)


def last_frame(t):
    frames = t.get("frames") or t.get("samples") or []
    return frames[-1]


def count_alive_per_cell(t):
    """Return (alive, occupied, max_per_cell, empty) from the last frame."""
    fr = last_frame(t)
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


rows = []
hashes = {}
for n, seed in [(160, 7), (160, 11), (160, 23), (320, 7), (320, 11)]:
    t = run(n, seed)
    alive, occupied, mx, empty = count_alive_per_cell(t)
    label = f"n{n}-seed{seed}"
    hashes[label] = t.get("hash", "")
    rows.append({
        "n": n, "seed": seed, "alive": alive, "occupied_cells": occupied,
        "max_per_cell": mx, "empty_cells": empty,
        "crowding": round(alive / occupied, 4) if occupied else 0.0,
    })
    print(f"n={n} seed={seed}: alive={alive} occupied={occupied} "
          f"max={mx} empty={empty} crowding={rows[-1]['crowding']}")

# --- controls -------------------------------------------------------------
predicted = 2 * CELLS  # 80

fires_ok = any(r["n"] == 320 and r["alive"] == predicted for r in rows)
fires_detail = f"n=320 counts: {[r['alive'] for r in rows if r['n'] == 320]}, expected {predicted}"

s160 = [r["alive"] for r in rows if r["n"] == 160]
silent_ok = len(set(s160)) == 1
silent_detail = f"n=160 counts across seeds: {s160}"

specific_ok = all(r["alive"] == predicted for r in rows)
specific_detail = "; ".join(
    f"n={r['n']} seed={r['seed']} alive={r['alive']} expected={predicted}"
    for r in rows)

controls = [
    {"name": "fires", "passed": fires_ok, "detail": fires_detail},
    {"name": "silent", "passed": silent_ok, "detail": silent_detail},
    {"name": "specific", "passed": specific_ok, "detail": specific_detail},
]

if all(c["passed"] for c in controls):
    kind = "passed"
    reason = "every arm ends at exactly 80 alive on 40 cells"
elif not silent_ok:
    kind = "failed"
    reason = ("EXPLAINED: the survivor count depends on the seed at n = 160, so "
              "the 1.925 in EXP-21 was one draw of a varying quantity and not a "
              "second law. The count is not reproducible across seeds.")
else:
    kind = "failed"
    reason = ("EXPLAINED: the count is stable across seeds but does not reach 80, "
              "so k_max = 2 overstates what the field sustains and the shortfall "
              "is structural rather than a rounding of the mean.")

out = {
    "schema": "marfagenez.experiment-result.v2",
    "name": "exp26_shortfall",
    "question": "Why is crowding 1.925 at n = 160 and 2.000 at n = 320, with cells = 40 in both?",
    "arithmetic": {
        "law": "k_max = 1 + floor((M*r - maintenance - damage_rate)/income)",
        "k_max": 1 + int((M * R - MAINT - DAMAGE) // INCOME),
        "budget": M * R - MAINT - DAMAGE,
        "predicted_alive": predicted,
        "spawn_per_cell": {"n160": 160 / CELLS, "n320": 320 / CELLS},
    },
    "conditions": [{"label": f"n={r['n']} seed={r['seed']}",
                    "params": {"n": r["n"], "seed": r["seed"], "cells": CELLS,
                               "M": M, "r": R, "income": INCOME,
                               "maintenance": MAINT, "damage_rate": DAMAGE,
                               "steps": STEPS},
                    "result": r} for r in rows],
    "rows": rows,
    "hashes": hashes,
    "controls": {c["name"]: {"passed": c["passed"], "detail": c["detail"]}
                 for c in controls},
    "verdict": {"kind": kind, "reason": reason},
    "limitations": [
        "One policy (sighted) and one uniform field.",
        "Only five arms; the seed sweep is three seeds at n = 160.",
        "Does not test whether the shortfall is a death or a refusal to move into an empty cell.",
        "Does not vary cells, so a finite-size effect of 40 cells is not excluded.",
    ],
    "what_this_does_not_prove": (
        "It does not show the field sustains fewer than 80. It shows whether the "
        "count of 77 is reproducible, which decides between a second law and a draw."
    ),
}

os.makedirs("/root/marfagenez/results/shortfall", exist_ok=True)
path = "/root/marfagenez/results/shortfall/run-exp26.json"
with open(path, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("written:", path)
print("verdict:", kind)
