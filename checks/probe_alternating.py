"""Why does nothing move on an alternating field?

The sighted rule (core/src/life.rs:404-441) moves only when a neighbour is
strictly richer than the current cell. On an alternating field every cell has
one rich and one poor neighbour, so an organism on a POOR cell should move
toward the rich one, and an organism on a RICH cell should stay.

EXP-64 measured moving = 0 on the alternating field with 60 alive and 20
doubled cells. That means every organism sits on a rich cell.

This is a probe, not an experiment: it prints the field and the occupancy of
the last frame so the claim can be read directly.
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")


def run(field, rich, poor, n=80, cells=40, steps=20000, every=2000, mc=0.05):
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(every), "--seed", "7", "--n", str(n),
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


def report(name, trace):
    fr = trace["frames"][-1]
    field = fr["field"]
    occ = {}
    dirs = {}
    for s in fr["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
            dirs[s["cell"]] = s.get("direction", 0)
    print("\n=== %s ===" % name)
    print("alive %d, occupied cells %d, doubled %d"
          % (sum(occ.values()), len(occ), sum(1 for v in occ.values() if v >= 2)))
    print("field:", " ".join("%.2f" % v for v in field))
    line = []
    for c in range(len(field)):
        k = occ.get(c, 0)
        line.append("." if k == 0 else str(k))
    print("occ:  ", " ".join("%2s" % x for x in line))
    # how many organisms stand on a cell that is a local maximum
    on_peak = 0
    on_valley = 0
    for c, k in occ.items():
        left = field[c - 1] if c > 0 else -1e9
        right = field[c + 1] if c + 1 < len(field) else -1e9
        if field[c] >= left and field[c] >= right:
            on_peak += k
        elif field[c] <= left and field[c] <= right:
            on_valley += k
    print("organisms on a local max: %d, on a local min: %d" % (on_peak, on_valley))
    moving = sum(1 for s in fr["samples"] if s["alive"] and s.get("direction", 0) != 0)
    print("moving at last frame: %d" % moving)


if __name__ == "__main__":
    report("alternating 2.4/1.6", run("alternating", 2.4, 1.6))
    report("gradient 2.4->1.6", run("gradient", 2.4, 1.6))
    report("uniform 2.0", run("uniform", 2.0, 2.0))
