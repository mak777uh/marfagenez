"""Is the capacity limit in the Rust code at all?

Runs the real `trace` binary on ONE cell with k organisms and reports the
survivors. Compares against the Python mirror. If they disagree, the mirror is
wrong and the mirror's law is worthless.
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


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=1500):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    for _ in range(T):
        for i in range(k):
            if not alive[i]:
                continue
            taken = min(field, income)
            field -= taken
            e[i] += taken
            e[i] -= maintenance
            dmg[i] = min(dmg[i] + damage_rate, 1.0)
            if e[i] > 0.0 and dmg[i] > 0.0:
                rep = min(e[i] / repair_cost, dmg[i])
                dmg[i] -= rep
                e[i] -= rep * repair_cost
            e[i] = min(e[i], capacity)
            if e[i] <= 0.0 or dmg[i] >= 1.0:
                alive[i] = False
        field = field + (M - field) * r
    return sum(alive)


for M, r, t, mc, d in [(2.0, 0.8, 0.6, 0.1, 0.0), (2.0, 0.8, 0.2, 0.1, 0.0)]:
    for k in (3, 5, 7, 10):
        meas = measure(1, k, M, r, t, mc, d)
        mir = run(M=M, r=r, income=t, maintenance=mc, repair_cost=1.5,
                  damage_rate=d, capacity=1000.0, k=k)
        print("M=%.1f income=%.2f k=%2d  rust=%2d  mirror=%2d  %s" %
              (M, t, k, meas, mir, "same" if meas == mir else "DIFFERENT"))
sys.exit(0)
