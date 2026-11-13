#!/usr/bin/env python3
"""EXP-21: is crowding = (M - income) / maintenance, or is that a fit?

The candidate law came from ONE measurement: crowding was 2.00 with
M = 2.0, income = 0.8, maintenance = 0.6, and (2.0 - 0.8) / 0.6 = 2.0.

That is the p = 0.2 mistake (LESSONS.md): a number read off the measurement
cannot fail to match it. A law must predict a DIFFERENT number first.

Arithmetic first (PROTOCOL.md §1). With M = 2.0, income = 0.8:
  maintenance 0.40 -> (2.0 - 0.8)/0.40 = 3.0  -> crowding 3
  maintenance 0.60 -> (2.0 - 0.8)/0.60 = 2.0  -> crowding 2   (already seen)
  maintenance 0.80 -> (2.0 - 0.8)/0.80 = 1.5  -> crowding 1
  maintenance 1.00 -> (2.0 - 0.8)/1.00 = 1.2  -> crowding 1
  maintenance 1.20 -> (2.0 - 0.8)/1.20 = 1.0  -> crowding 1

The competing law A (capacity = M*r/income, floor) predicts crowding
floor(2.0*r/0.8) = floor(2.5r) = 2 at r = 0.8, INDEPENDENT of maintenance.
So the two laws disagree sharply: A says crowding does not move when
maintenance moves, the candidate says it does.

Control tests (PROTOCOL.md §2):
  fires    - the metric must move when maintenance moves, if the candidate holds
  silent   - the metric must NOT move when only the seed changes
  specific - the metric must equal the candidate's prediction, not merely move

Verdicts (PROTOCOL.md §4): passed / failed / void / insensitive by construction.
"""
import subprocess, json, os, glob, sys, hashlib

TRACE = "/root/marfagenez/core/target/release/trace"
COREDIR = "/root/marfagenez/core"
OUT = "/root/marfagenez/results/crowding-law"

CELLS, M, INCOME = 40, 2.0, 0.8
RICH, POOR = 3.8, 0.2          # (3.8 + 0.2)/2 = 2.0
R, STEPS, N = 0.8, 1200, 160


def run(maintenance, seed=7):
    cmd = [TRACE, "--policy", "sighted", "--steps", str(STEPS), "--every", str(STEPS),
           "--n", str(N), "--cells", str(CELLS),
           "--capacity", "2.0",
           "--regrow", str(R),
           "--damage-rate", "0.02",
           "--income", str(INCOME), "--maintenance", str(maintenance),
           "--repair-cost", "0.05", "--move-cost", "0.02", "--energy", "5.0",
           "--field", "uniform", "--rich", str(RICH), "--poor", str(POOR),
           "--seed", str(seed)]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=COREDIR)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:800])
    files = sorted(glob.glob(os.path.join(COREDIR, "results", "sighted", "*.json")),
                   key=os.path.getmtime)
    d = json.load(open(files[-1]))
    fr = d["frames"][-1]
    samples = fr["samples"]
    alive = [s for s in samples if s["alive"]]
    occupied = {}
    for s in alive:
        occupied[s["cell"]] = occupied.get(s["cell"], 0) + 1
    crowd = (sum(occupied.values()) / len(occupied)) if occupied else 0.0
    blob = json.dumps(fr, sort_keys=True).encode()
    return {
        "maintenance": maintenance,
        "alive": len(alive),
        "occupied_cells": len(occupied),
        "crowding": round(crowd, 4),
        "field_mean": round(sum(fr["field"]) / len(fr["field"]), 4),
        "trace_hash": hashlib.sha256(blob).hexdigest()[:16],
    }


def predict_candidate(m):
    return (M - INCOME) / m


def predict_A():
    return M * R / INCOME


rows = []
print(f"{'maint':<7}{'pred_cand':<11}{'pred_A':<8}{'alive':<7}{'crowd':<8}{'cells':<7}{'hash':<18}")
for m in [0.40, 0.60, 0.80, 1.00, 1.20]:
    r = run(m)
    r["pred_candidate"] = round(predict_candidate(m), 4)
    r["pred_A"] = round(predict_A(), 4)
    rows.append(r)
    print(f"{m:<7.2f}{r['pred_candidate']:<11.2f}{r['pred_A']:<8.2f}"
          f"{r['alive']:<7}{r['crowding']:<8.2f}{r['occupied_cells']:<7}{r['trace_hash']:<18}")

os.makedirs(OUT, exist_ok=True)

# --- control: silent (seed change must not move the metric) ---
base = run(0.60, seed=7)
other = run(0.60, seed=11)
silent_ok = abs(base["crowding"] - other["crowding"]) < 1e-9
silent_detail = f"seed 7 crowd={base['crowding']}, seed 11 crowd={other['crowding']}"

# --- control: fires (the metric must move when maintenance moves) ---
crowds = [r["crowding"] for r in rows]
fires_ok = len(set(crowds)) > 1
fires_detail = f"crowding values across maintenance: {crowds}"

# --- control: specific (must match the candidate, not merely move) ---
specific_ok = all(abs(r["crowding"] - r["pred_candidate"]) < 0.05 for r in rows)
specific_detail = "; ".join(
    f"m={r['maintenance']:.2f} measured={r['crowding']:.2f} predicted={r['pred_candidate']:.2f}"
    for r in rows)

controls = {
    "fires": {"ok": fires_ok, "detail": fires_detail},
    "silent": {"ok": silent_ok, "detail": silent_detail},
    "specific": {"ok": specific_ok, "detail": specific_detail},
}

if fires_ok and silent_ok and specific_ok:
    verdict = "passed"
elif not fires_ok:
    verdict = "insensitive by construction"
else:
    verdict = "failed"

result = {
    "schema": "marfagenez.experiment-result.v2",
    "id": "EXP-21",
    "title": "is crowding = (M - income)/maintenance, or was that a fit?",
    "arithmetic": {
        "M": M, "income": INCOME, "r": R, "cells": CELLS,
        "candidate": "(M - income) / maintenance",
        "A": "floor(M*r/income), independent of maintenance",
    },
    "conditions": [{"name": "uniform field, sighted policy", "cells": CELLS,
                    "n": N, "steps": STEPS, "r": R, "income": INCOME}],
    "rows": rows,
    "controls": controls,
    "verdict": verdict,
    "limitations": [
        "One policy (sighted) and one field shape (uniform).",
        "The candidate was suggested by the crowding=2 measurement itself; the",
        "test is whether it predicts OTHER maintenance values, not whether it",
        "reproduces the one it came from.",
        "Crowding is measured on occupied cells only; a law about empty cells is",
        "not tested here.",
    ],
}

path = os.path.join(OUT, "run-exp21.json")
json.dump(result, open(path, "w"), indent=1)
print()
print(f"verdict: {verdict}")
print(f"fires={fires_ok} silent={silent_ok} specific={specific_ok}")
print(f"saved {path}")
