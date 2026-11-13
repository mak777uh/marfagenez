"""The crowding law, checked against the Rust binary on the grid that matters.

Law:
    supply = M * r                       (a cell emptied every step regrows to M*r)
    cost   = maintenance + damage_rate * repair_cost
    k_max  = 0                            if income < cost or supply < cost
             floor((supply - cost) / income) + 1   otherwise
    capacity = cells * k_max

The two cases the law gets wrong are both maintenance = 0, where an organism
that takes nothing still does not die. That is not a crowding limit, it is the
absence of a cost, and the law says so by refusing to answer (cost <= 0).
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
    if cost <= 0:
        return None
    supply = M * r
    if income < cost or supply < cost:
        return 0
    return int((supply - cost) // income) + 1


grid = [
    (2.0, 0.8, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.6, 0.5, 0.0),
    (2.0, 0.8, 0.2, 0.1, 0.0),
    (2.0, 0.8, 0.2, 0.5, 0.0),
    (2.0, 0.8, 1.0, 0.1, 0.0),
    (2.0, 0.8, 1.0, 0.7, 0.0),
    (2.0, 0.5, 0.6, 0.1, 0.0),
    (3.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.6, 0.1, 0.0),
    (4.0, 0.8, 0.9, 0.1, 0.0),
    (2.0, 0.9, 0.6, 0.1, 0.0),
    (2.0, 0.8, 0.8, 0.6, 0.02),
    (2.0, 0.8, 0.8, 0.6, 0.00),
    (3.0, 0.6, 0.5, 0.2, 0.0),
    (1.0, 0.8, 0.3, 0.1, 0.0),
]

print("%-4s %-4s %-6s %-6s %-5s | %-5s %-5s %s" %
      ("M", "r", "income", "maint", "dmg", "law", "meas", "ok"))
bad = 0
for M, r, t, mc, d in grid:
    cost = mc + d * 1.5
    pred = k_max_law(M, r, t, cost)
    if pred is None:
        print("%-4.1f %-4.1f %-6.2f %-6.2f %-5.2f | no law (cost <= 0)" %
              (M, r, t, mc, d))
        continue
    meas = measure(1, pred + 3, M, r, t, mc, d)
    ok = pred == meas
    if not ok:
        bad += 1
    print("%-4.1f %-4.1f %-6.2f %-6.2f %-5.2f | %-5d %-5d %s" %
          (M, r, t, mc, d, pred, meas, "yes" if ok else "NO"))
print("\nmismatches:", bad)
sys.exit(0)
