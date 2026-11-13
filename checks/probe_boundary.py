"""Why does checkerboard_split report on_poor = 19 and never 20?

The function marks a cell as a local max when field[c] >= left and >= right,
and as a local min when field[c] <= left and <= right. On an alternating field
of 40 cells every cell is one or the other, so on_max + on_min should be 60.

It reports on_max = 40, on_min = 19, total 59. One organism is unaccounted for.
This probe prints the boundary cells to find it.
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")


def run(field, rich, poor, n=80, cells=40, seed=7, steps=20000, every=2000, mc=0.05):
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(every), "--seed", str(seed), "--n", str(n),
           "--cells", str(cells), "--rich", str(rich), "--poor", str(poor),
           "--income", "1.0", "--maintenance", "0.6",
           "--damage-rate", "0.02", "--repair-cost", "0.5",
           "--move-cost", str(mc), "--energy", "10.0",
           "--field", field, "--read-budget", "3", "--memory-life", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(out.stderr)
    written = None
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
    return json.load(open(os.path.join(ROOT, written)))


tr = run("alternating", 2.4, 1.6)
fr = tr["frames"][-1]
field = fr["field"]
occ = {}
for s in fr["samples"]:
    if s["alive"]:
        occ[s["cell"]] = occ.get(s["cell"], 0) + 1

n = len(field)
print("cells:", n)
print("field[0:4]  :", [round(v, 3) for v in field[:4]])
print("field[-4:]  :", [round(v, 3) for v in field[-4:]])
print("occ[0:4]    :", [occ.get(i, 0) for i in range(4)])
print("occ[-4:]    :", [occ.get(i, 0) for i in range(n - 4, n)])

on_max = on_min = neither = 0
for c in range(n):
    left = field[c - 1] if c > 0 else -1e9
    right = field[c + 1] if c + 1 < n else -1e9
    k = occ.get(c, 0)
    if field[c] >= left and field[c] >= right:
        on_max += k
    elif field[c] <= left and field[c] <= right:
        on_min += k
    else:
        neither += k
        print("NEITHER at cell %d: field %.3f left %.3f right %.3f occ %d"
              % (c, field[c], left, right, k))

print("on_max %d, on_min %d, neither %d, total %d"
      % (on_max, on_min, neither, on_max + on_min + neither))
print("alive total:", sum(occ.values()))
