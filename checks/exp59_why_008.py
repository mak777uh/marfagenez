"""Why does the narrow field show a share of 0.08 when min(1.6-1.2,1.2)=0.4?

EXP-58 found a share of 0.080 with 168 samples on the narrow field, where the
arithmetic says a poor cell of level 1.6 feeds min(1.6, 1.2) = 1.2 to the first
taker. A share of 0.08 means the cell held 0.08 at the moment of the take, not
1.6.

The guess: the cell was eaten empty on the previous step and regrew by
regrow = 0.8 of the gap, or the cell is shared by two organisms and the first
took most of it.

The measurement: for every sample with a share near 0.08, print the cell's level
in the SAME frame, the number of organisms on that cell, and the cell's level in
the next frame. If the cell's level is ~0.08 then the cell was nearly empty and
the share is simply what was there. If the cell's level is ~1.6 then take() is
not returning min(cell, income) and the model is wrong.

This is a diagnostic, not a contract experiment: it prints and does not pass or
fail. The number it produces decides what the next experiment should ask.
"""

import json
import os
import subprocess
import sys
import time

CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

INCOME = 1.2
MAINT = 0.6
REPAIR = 1.5
MOVE = 0.10
STEPS = 3000
SEED = 20250101
N = 160
CELLS = 40


def run(rich, poor, steps, every):
    time.sleep(1.1)
    cmd = [
        TRACE,
        "--n", str(N), "--cells", str(CELLS),
        "--rich", str(rich), "--poor", str(poor),
        "--regrow", "0.8",
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--damage-rate", "0.02",
        "--steps", str(steps), "--every", str(every),
        "--seed", str(SEED),
        "--policy", "sighted",
        "--read-budget", "3",
        "--capacity", "8",
        "--field", "alternating",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr[-2000:])
    written = [
        line.split(":", 1)[1].strip()
        for line in out.stdout.splitlines()
        if line.startswith("written:")
    ][0]
    path = os.path.join(CORE, written)
    if os.path.exists(path) and os.path.getmtime(path) < time.time() - 5:
        raise SystemExit(f"refusing a stale file: {path}")
    return json.load(open(path))


def main():
    data = run(2.4, 1.6, STEPS, 1)
    frames = data["frames"]

    # For each share, what was the cell's level and how many organisms shared it?
    rows = []
    for a, b in zip(frames, frames[1:]):
        after = {s["slot"]: s for s in b["samples"]}
        # How many live organisms stand on each cell in frame a?
        crowd = {}
        for s in a["samples"]:
            if s["alive"]:
                crowd[s["cell"]] = crowd.get(s["cell"], 0) + 1
        for s in a["samples"]:
            if not s["alive"]:
                continue
            nxt = after.get(s["slot"])
            if nxt is None or not nxt["alive"]:
                continue
            share = round(nxt["taken"], 3)
            if abs(share - 0.08) > 0.005:
                continue
            # The cell the share came from is the cell in frame b.
            level_b = b["field"][nxt["cell"]]
            level_a = a["field"][s["cell"]]
            rows.append((a["step"], s["slot"], s["cell"], nxt["cell"],
                         round(level_a, 4), round(level_b, 4),
                         crowd.get(s["cell"], 0), share))

    print(f"samples with share near 0.08: {len(rows)}")
    print("step  slot  cell_a cell_b  level_a  level_b  crowd  share")
    for r in rows[:25]:
        print("  ".join(str(x) for x in r))

    levels_a = [r[4] for r in rows]
    levels_b = [r[5] for r in rows]
    crowds = [r[6] for r in rows]
    print()
    print(f"level in frame a: min {min(levels_a):.4f} max {max(levels_a):.4f} "
          f"mean {sum(levels_a)/len(levels_a):.4f}")
    print(f"level in frame b: min {min(levels_b):.4f} max {max(levels_b):.4f} "
          f"mean {sum(levels_b)/len(levels_b):.4f}")
    print(f"crowd on cell_a: {sorted(set(crowds))}")

    # The same for a share of 0.000, which should be a cell that was empty.
    zeros = []
    for a, b in zip(frames, frames[1:]):
        after = {s["slot"]: s for s in b["samples"]}
        for s in a["samples"]:
            if not s["alive"]:
                continue
            nxt = after.get(s["slot"])
            if nxt is None or not nxt["alive"]:
                continue
            if abs(nxt["taken"]) > 1e-9:
                continue
            zeros.append((a["step"], s["slot"], s["cell"], nxt["cell"],
                          round(a["field"][s["cell"]], 4),
                          round(b["field"][nxt["cell"]], 4)))
    print()
    print(f"samples with share 0.000: {len(zeros)}")
    print("step  slot  cell_a cell_b  level_a  level_b")
    for r in zeros[:10]:
        print("  ".join(str(x) for x in r))
    zl = [r[4] for r in zeros]
    print(f"level in frame a for zero shares: min {min(zl):.4f} max {max(zl):.4f} "
          f"mean {sum(zl)/len(zl):.4f}")


if __name__ == "__main__":
    main()
