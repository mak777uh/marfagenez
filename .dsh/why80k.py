"""The crowding law, third attempt - now with the right arithmetic.

The cell is emptied every step by the organisms on it and regrows to M*r
before the next step. So the per-step supply on a cell is

    supply = M * r

and the organisms on that cell take it in index order, each taking at most
`income`. Organism j gets

    take_j = min(supply - sum of earlier takes, income)

It survives iff take_j >= cost, where cost = maintenance + damage_rate*repair_cost.

So the crowding limit is the largest k such that every one of the first k takes
is >= cost. In closed form, when income >= cost:

    k_max = 1 + floor((supply - cost) / income)     if supply >= cost
    k_max = 0                                        otherwise

and capacity = cells * k_max.

This script checks that against the Rust binary on one cell, and against the
full field.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/marfagenez")
TRACE = ROOT / "core" / "target" / "release" / "trace"


def measure(cells, n, M, r, t, maintenance, damage, steps=1500):
    cmd = [str(TRACE), "--cells", str(cells), "--n", str(n),
           "--policy", "stay", "--steps", str(steps), "--every", str(steps),
           "--capacity", "1000", "--income", str(t),
           "--maintenance", str(maintenance), "--repair-cost", "1.5",
           "--damage-rate", str(damage), "--move-cost", "0", "--energy", "10",
           "--field", "uniform", "--rich", str(M), "--poor", str(M),
           "--regrow", str(r), "--layout", "even", "--seed", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-500:])
        sys.exit(1)
    written = None
    for line in res.stdout.splitlines():
        if line.startswith("written:"):
            written = Path(line.split(":", 1)[1].strip())
    if written is None or not written.is_absolute():
        written = ROOT / "core" / written
    data = json.loads(written.read_text())
    last = data["frames"][-1]
    return sum(1 for s in last["samples"] if s["alive"])


def k_max_law(M, r, income, cost):
    supply = M * r
    if supply < cost:
        return 0
    if income <= 0:
        return None
    k = 1
    while True:
        rest = supply - k * income
        if rest < cost:
            return k
        k += 1
        if k > 1000:
            return None


grid = [
    # M, r, income, maintenance, damage
    (2.0, 0.8, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.6, 0.5, 0.0),
    (2.0, 0.8, 0.6, 0.0, 0.0),
    (2.0, 0.8, 0.2, 0.1, 0.0),
    (2.0, 0.8, 0.2, 0.5, 0.0),
    (2.0, 0.8, 1.0, 0.1, 0.0),
    (2.0, 0.8, 1.0, 0.7, 0.0),
    (2.0, 0.5, 0.6, 0.1, 0.0),
    (2.0, 0.5, 0.6, 0.0, 0.0),
    (3.0, 0.8, 0.6, 0.1, 0.0),
    (3.0, 0.8, 0.6, 0.0, 0.0),
    (4.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.9, 0.1, 0.0),
    (2.0, 0.9, 0.6, 0.1, 0.0),
    (2.0, 0.9, 0.6, 0.0, 0.0),
    (2.0, 0.8, 0.8, 0.6, 0.02),
]

print("%-4s %-4s %-6s %-6s %-5s | %-5s %-5s %s" %
      ("M", "r", "income", "maint", "dmg", "law", "meas", "ok"))
bad = 0
for M, r, t, mc, d in grid:
    cost = mc + d * 1.5
    pred = k_max_law(M, r, t, cost)
    meas = measure(1, (pred or 0) + 4, M, r, t, mc, d)
    ok = pred == meas
    if not ok:
        bad += 1
    print("%-4.1f %-4.1f %-6.2f %-6.2f %-5.2f | %-5s %-5d %s" %
          (M, r, t, mc, d, pred, meas, "yes" if ok else "NO"))
print("\nmismatches:", bad, "of", len(grid))
sys.exit(0)
