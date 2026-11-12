"""Does eating make the organism leave its own cell?

EXP-63 found that a sighted organism on a uniform field moved 78 times in 199
steps, though `sighted` stays when its own cell is as rich as its neighbours. The
explanation offered was that the organism eats 1.200 from its cell, which drops
the cell to 0.500 before regrowth, so it makes its own cell the poorest one it can
see and then leaves.

That is a claim about a correlation and it can be measured: split every step into
"moved" and "stood still" and compare the `taken` on that step.

THE ARITHMETIC THAT MUST BE CHECKED FIRST

The decision is made BEFORE the eat, on the field as it stands at the start of the
step. So the `taken` recorded on a step is not the value the organism saw when it
decided. What it saw is the level of its own cell at the start of the step, which
is the level in the PREVIOUS frame, and the level of its neighbours in the
previous frame.

So the right comparison is: on a step where it moved, was its own cell (previous
frame) poorer than a neighbour (previous frame)? That is what `sighted` responds
to. The `taken` on the same step is a consequence of the decision, not its cause.

If the previous-frame own cell is poorer than a neighbour on the steps it moved,
and not poorer on the steps it stood still, the claim holds. If both look the
same, the claim is wrong and the moves come from somewhere else.

WHAT THIS DOES NOT DO

It does not show that eating is the only way a cell becomes poor. A neighbour
could be poor because another organism just ate from it.
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
STEPS = 8000
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
        "--field", "uniform",
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

    moved_rows = []
    still_rows = []

    for i in range(1, len(frames)):
        prev = frames[i - 1]
        now = frames[i]
        # only after the population has settled
        if now["step"] < 500:
            continue
        for a, b in zip(prev["samples"], now["samples"]):
            if not (a["alive"] and b["alive"]):
                continue
            cell = a["cell"]
            here = prev["field"][cell]
            left = prev["field"][cell - 1] if cell > 0 else None
            right = prev["field"][cell + 1] if cell + 1 < len(prev["field"]) else None
            best_nb = max(v for v in (left, right) if v is not None)
            richer = best_nb > here
            row = {
                "here": here,
                "best_nb": best_nb,
                "richer": richer,
                "taken": a["taken"],
                "mates": sum(
                    1 for x in prev["samples"]
                    if x["alive"] and x["cell"] == cell and x["slot"] != a["slot"]
                ),
            }
            if b["cell"] != cell:
                moved_rows.append(row)
            else:
                still_rows.append(row)

    print(f"steps after 500: moved {len(moved_rows)}, stood still {len(still_rows)}")

    for name, rows in (("moved", moved_rows), ("still", still_rows)):
        if not rows:
            continue
        n = len(rows)
        richer = sum(1 for r in rows if r["richer"])
        print(f"\n{name}: n {n}")
        print(f"  a neighbour was richer at the start of the step: "
              f"{richer} ({100*richer/n:.1f}%)")
        print(f"  own cell level, mean {sum(r['here'] for r in rows)/n:.4f}")
        print(f"  best neighbour level, mean {sum(r['best_nb'] for r in rows)/n:.4f}")
        print(f"  taken on that step, mean {sum(r['taken'] for r in rows)/n:.4f}")
        print(f"  mates on the cell, mean {sum(r['mates'] for r in rows)/n:.2f}")

    # The decisive comparison.
    if moved_rows and still_rows:
        m = sum(1 for r in moved_rows if r["richer"]) / len(moved_rows)
        s = sum(1 for r in still_rows if r["richer"]) / len(still_rows)
        print(f"\nmoved with a richer neighbour: {100*m:.1f}%")
        print(f"stood still with a richer neighbour: {100*s:.1f}%")
        print(f"difference: {100*(m-s):.1f} percentage points")

    # And what the organism's own cell looks like when it decides to move:
    # it is the cell it ate from on the previous step.
    print("\nown cell level at the moment of the decision:")
    for name, rows in (("moved", moved_rows), ("still", still_rows)):
        if not rows:
            continue
        buckets = {}
        for r in rows:
            k = round(r["here"], 2)
            buckets[k] = buckets.get(k, 0) + 1
        top = sorted(buckets.items(), key=lambda kv: -kv[1])[:5]
        print(f"  {name}: " + ", ".join(f"{v:.2f} n{n}" for v, n in top))


if __name__ == "__main__":
    main()
