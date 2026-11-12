#!/usr/bin/env python3
"""EXP-20: does field capacity jump when regrowth r moves continuously?

Arithmetic first (PROTOCOL.md §1):
  capacity per cell = floor(M*r/t0)
  uniform field: M = (rich + poor)/2, so --rich 3.8 --poor 0.2 gives M = 2.0
  t0 = income = 0.8, so M*r/t0 = 2.5*r
  r = 0.79 -> 2.5*0.79 = 1.975 -> floor 1 -> C = 40
  r = 0.80 -> 2.5*0.80 = 2.000 -> floor 2 -> C = 80
So C(r) = 40*floor(2.5r) has steps at r = 0.4, 0.8, 1.2, ...
A 0.01 change in r at the step DOUBLES the predicted field capacity.

PARAMETER TRAP (this cost one wrong run):
  `--damage-rate` is NOT r. It is the per-step damage rate.
  `--regrow` IS r.
  `--capacity` is the per-organism carry capacity, not the field M.
  `uniform` field M = (rich + poor)/2, so `--rich 2 --poor 0.2` gives M = 1.1,
  not 2.0. The first version of this experiment set M = 1.1 by accident and
  measured a field that was flat in r for that reason alone.

The question is not whether the arithmetic jumps (it does, by construction).
The question is whether the MEASUREMENT jumps at the same r, or whether the
field absorbs the jump smoothly because organisms already there keep living.
"""
import subprocess, json, os, glob

TRACE = "/root/marfagenez/core/target/release/trace"
COREDIR = "/root/marfagenez/core"
OUT = "/root/marfagenez/results/capacity-step"

RS = [0.70, 0.75, 0.78, 0.79, 0.795, 0.80, 0.805, 0.81, 0.85, 0.90]
CELLS, M, T0 = 40, 2.0, 0.8
RICH, POOR = 3.8, 0.2          # (3.8 + 0.2)/2 = 2.0


def run(r):
    """Run one trace and return the last frame."""
    cmd = [TRACE, "--policy", "sighted", "--steps", "1200", "--every", "1200",
           "--n", "160", "--cells", str(CELLS),
           "--capacity", "2.0",
           "--regrow", str(r),
           "--damage-rate", "0.02",
           "--income", str(T0), "--maintenance", "0.6",
           "--repair-cost", "0.05", "--move-cost", "0.02", "--energy", "5.0",
           "--field", "uniform", "--rich", str(RICH), "--poor", str(POOR),
           "--seed", "7"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=COREDIR)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:800])
    files = sorted(glob.glob(os.path.join(COREDIR, "results", "sighted", "*.json")),
                   key=os.path.getmtime)
    d = json.load(open(files[-1]))
    return d["frames"][-1]


rows = []
print(f"{'r':<7}{'M*r/t0':<9}{'pred_k':<8}{'pred_C':<8}{'alive':<7}{'crowd':<7}{'mean':<8}")
for r in RS:
    fr = run(r)
    alive = sum(1 for s in fr["samples"] if s["alive"])
    field = fr["field"]
    occ = {}
    for s in fr["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    crowd = max(occ.values()) if occ else 0
    ratio = M * r / T0
    pred_k = int(ratio)
    mean = sum(field) / len(field)
    rows.append({
        "r": r, "M_r_over_t0": round(ratio, 4),
        "predicted_per_cell": pred_k, "predicted_C": CELLS * pred_k,
        "measured_alive": alive, "measured_crowding": crowd,
        "field_mean": round(mean, 4),
    })
    print(f"{r:<7}{ratio:<9.4f}{pred_k:<8}{CELLS*pred_k:<8}{alive:<7}{crowd:<7}{mean:<8.4f}")

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "rows.json"), "w") as f:
    json.dump(rows, f, indent=2)

print("\nmeasured alive vs predicted C:")
mismatch = [(x["r"], x["predicted_C"], x["measured_alive"]) for x in rows
            if x["predicted_C"] != x["measured_alive"]]
if mismatch:
    print("  MISMATCH at r =", [m[0] for m in mismatch])
    for m in mismatch:
        print(f"    r={m[0]}  predicted {m[1]}  measured {m[2]}")
else:
    print("  exact agreement at all", len(rows), "points")

# sanity: the field mean must move with r, otherwise r is not wired in
means = [x["field_mean"] for x in rows]
print(f"\nfield mean spans {min(means):.4f} .. {max(means):.4f}"
      f"  ({'varies' if max(means) - min(means) > 1e-6 else 'FLAT - r not wired in'})")

print("\nwrote", os.path.join(OUT, "rows.json"))
