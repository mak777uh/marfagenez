"""The real crowding law.

Measured take sequence on one cell (M = 2, income = 0.6, regrow r = 0.8):
organisms 1 and 2 gain 0.5/step, organism 3 gains 0.3, organisms 4 and 5 lose
0.1. The field stays at 1.6.

That is exactly the field's own equilibrium: a cell that is emptied every step
regrows to M*(1 - (1-r)^?) ... no. Let us solve it.

Let the cell be at level L at the start of a step, and k organisms each try to
take `income`. The first takes min(L, income), the second takes
min(L - income, income), and so on. Then the cell regrows to
    L' = (L - total_taken) + (M - (L - total_taken)) * r.

At the fixed point L' = L, so total_taken = (M - L) * r. With L = 1.6, M = 2,
r = 0.8: total_taken = 0.32. But the measured total is 0.5+0.5+0.3 = 1.3.

So the field is NOT at a fixed point of that recursion. Something else is going
on -- dump the raw cell level per step.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/marfagenez")
TRACE = ROOT / "core" / "target" / "release" / "trace"


def run(cells, n, M, r, t, maintenance, damage, steps, every=1):
    cmd = [str(TRACE), "--cells", str(cells), "--n", str(n),
           "--policy", "stay", "--steps", str(steps), "--every", str(every),
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
    return json.loads(written.read_text())


d = run(1, 5, 2.0, 0.8, 0.6, 0.1, 0.0, 8)
print("keys:", list(d.keys()))
print("frame keys:", list(d["frames"][0].keys()))
for i, fr in enumerate(d["frames"][:8]):
    print(i, {k: v for k, v in fr.items() if k != "samples"})
sys.exit(0)
