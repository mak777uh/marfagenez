"""Measure the rotation period T_rot directly.

EXP-55 derived the surplus gate from E_max > 0.13 * T_rot and inferred
T_rot in (62, 69) from where the gate sits. That is an inference, not a
measurement. This measures it.

Method: run with --every 1 so every step is a frame, then for each cell count
how many organisms are alive on it at each step. A cell with two occupants is
a double cell. The rotation period is the time between a cell becoming double
and becoming single again - i.e. how long a second occupant lasts before it
gets a cell of its own.

Samples carry no organism id, so this tracks cells, not individuals. That is
the limitation, and it is stated rather than papered over.

Arithmetic, before the run:
    second occupant loses 0.13/step, starts at E_max
    survival if it never moves: E_max / 0.13 steps
    at E_max 9: 69.2 steps; at E_max 8: 61.5 steps
    EXP-55 measured the gate between them, so T_rot should land in (61.5, 69.2)
    if the derivation is right.
"""

import json
import os
import subprocess
import sys

ROOT = "/root/marfagenez"
BIN = os.path.join(ROOT, "core", "target", "release", "trace")

INCOME = 1.2
M = 2.0
R = 0.8
MAINT = 0.6
DAMAGE = 0.02
REPAIR = 1.5
MOVE_COST = 0.10
CELLS = 40
N = 160
SEED = 20250101
STEPS = 3000

CSTAR = M + INCOME - INCOME / R
COST = MAINT + DAMAGE * REPAIR
SECOND = min(CSTAR - INCOME, INCOME)
LOSS = COST - SECOND


def run(emax, steps=STEPS):
    cmd = [
        BIN,
        "--policy", "sighted",
        "--steps", str(steps),
        "--every", "1",
        "--seed", str(SEED),
        "--n", str(N),
        "--cells", str(CELLS),
        "--capacity", str(emax),
        "--damage-rate", str(DAMAGE),
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--field", "uniform",
        "--rich", str(M + 0.4),
        "--poor", str(M - 0.4),
        "--regrow", str(R),
        "--move-cost", str(MOVE_COST),
        "--read-budget", "3",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"trace failed for E_max={emax}:\n{out.stderr}")
    path = out.stdout.strip().splitlines()[-1].split("written:", 1)[-1].strip()
    with open(os.path.join(ROOT, path)) as f:
        return json.load(f)


def occupancy_frames(data):
    """For each frame, how many alive organisms are on each cell."""
    frames = []
    for fr in data["frames"]:
        counts = {}
        for s in fr["samples"]:
            if s["alive"]:
                counts[s["cell"]] = counts.get(s["cell"], 0) + 1
        frames.append((fr["step"], counts))
    return frames


def rotation_periods(frames):
    """For each cell, the lengths of its double stretches.

    A stretch starts when a cell goes from <=1 occupant to >=2 and ends when
    it goes back to <=1. Its length is the number of steps the cell spent
    double. If the cell stays double to the end, the stretch is right-
    censored and is not counted (it has no measured end).
    """
    lengths = []
    open_since = {}
    prev = {}
    for step, counts in frames:
        for cell in set(prev) | set(counts):
            before = prev.get(cell, 0)
            now = counts.get(cell, 0)
            was_double = before >= 2
            is_double = now >= 2
            if is_double and not was_double:
                open_since[cell] = step
            elif was_double and not is_double and cell in open_since:
                lengths.append(step - open_since.pop(cell))
        prev = counts
    return lengths, open_since


def main():
    print(f"c* = {CSTAR:.4f}  second taker {SECOND:.3f}  loses {LOSS:.3f}/step")
    print(f"prediction from EXP-55: T_rot in ({8 / LOSS:.1f}, {9 / LOSS:.1f})")
    print()

    for emax in (8, 9, 10):
        data = run(emax)
        frames = occupancy_frames(data)
        lengths, still_open = rotation_periods(frames)

        alive_last = sum(
            1 for s in data["frames"][-1]["samples"] if s["alive"]
        )
        double_last = sum(1 for c, n in frames[-1][1].items() if n >= 2)

        print(f"E_max {emax}:  alive {alive_last}  double cells at end {double_last}")
        print(f"  frames {len(frames)}  completed double stretches {len(lengths)}"
              f"  still open {len(still_open)}")
        if lengths:
            lengths_sorted = sorted(lengths)
            mean = sum(lengths) / len(lengths)
            median = lengths_sorted[len(lengths_sorted) // 2]
            print(f"  stretch length: min {min(lengths)}  median {median}"
                  f"  mean {mean:.1f}  max {max(lengths)}")
            print(f"  survival if never moved: {emax / LOSS:.1f} steps")
            print(f"  mean stretch / survival = {mean / (emax / LOSS):.3f}")
        else:
            print("  no completed double stretches")
        print()


if __name__ == "__main__":
    main()
