"""How long does a shared cell stay shared, and how many share it?

The finding note on the late deaths says the longest double occupancy measured was
25 steps, and that nothing explains why it is 25 rather than 5 or 60. EXP-59 found
cells carrying 2 to 8 organisms at once.

This measures the occupancy directly: for every cell, over every run of
consecutive frames in which it carries more than one live organism, record the
length of the run and the peak number of organisms. Then ask whether the length
follows from the arrival and departure rates, which the trace can also give.

THE ARITHMETIC THAT MUST BE CHECKED FIRST

If a cell is shared for L steps and the organisms on it lose `share - 0.63` per
step, an organism that arrives with energy E dies after E / (0.63 - share) steps.
For the second taker on a poor cell the share is 0.08, so the loss is 0.55 and an
organism arriving with 7.37 dies in 13.4 steps. For the third it is 0.63 and the
same organism dies in 11.7 steps.

So a queue cannot be longer than about 13 steps unless organisms leave before
dying. The note's 25 is therefore either a run of occupancy that includes
organisms arriving and leaving, or a different quantity. This experiment separates
the two: it counts, for each run of sharing, how many of the organisms on the cell
at the start of the run are still on it at the end.

WHAT THIS DOES NOT DO

It does not explain the number. It measures the run lengths and the turnover, so
that the next question can be asked with a number instead of a guess.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment

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
COST = MAINT + 0.02 * REPAIR  # 0.63


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


def occupancy_runs(data):
    """Every maximal run of consecutive frames in which a cell carries >1 organism.

    Returns (length, peak count, slots at the start that are still there at the
    end, slots at the start).
    """
    frames = data["frames"]
    # occupancy[step_index][cell] = set of slots
    occ = []
    for f in frames:
        per = {}
        for s in f["samples"]:
            if s["alive"]:
                per.setdefault(s["cell"], set()).add(s["slot"])
        occ.append(per)

    runs = []
    n_cells = len(frames[0]["field"])
    for cell in range(n_cells):
        i = 0
        while i < len(occ):
            if len(occ[i].get(cell, ())) > 1:
                j = i
                while j + 1 < len(occ) and len(occ[j + 1].get(cell, ())) > 1:
                    j += 1
                start = occ[i][cell]
                peak = max(len(occ[k].get(cell, ())) for k in range(i, j + 1))
                end = occ[j][cell]
                runs.append((j - i + 1, peak, len(start & end), len(start)))
                i = j + 1
            else:
                i += 1
    return runs


def main():
    data = run(2.4, 1.6, STEPS, 1)
    runs = occupancy_runs(data)

    lengths = [r[0] for r in runs]
    peaks = [r[1] for r in runs]
    survived = [r[2] for r in runs]
    started = [r[3] for r in runs]

    print(f"runs of shared occupancy: {len(runs)}")
    print(f"length: min {min(lengths)} max {max(lengths)} "
          f"mean {sum(lengths)/len(lengths):.2f}")
    print(f"peak organisms on the cell: min {min(peaks)} max {max(peaks)} "
          f"mean {sum(peaks)/len(peaks):.2f}")
    total_start = sum(started)
    total_surv = sum(survived)
    print(f"of {total_start} organisms present at the start of a run, "
          f"{total_surv} are still there at the end ({100*total_surv/total_start:.1f}%)")

    # The distribution of lengths, bucketed.
    buckets = {}
    for L in lengths:
        b = "1" if L == 1 else "2-5" if L <= 5 else "6-10" if L <= 10 else "11-25" if L <= 25 else ">25"
        buckets[b] = buckets.get(b, 0) + 1
    print("length buckets:", dict(sorted(buckets.items())))

    # The arithmetic bound: how long can an organism survive on a shared cell?
    # Second taker loses 0.55/step, third loses 0.63/step. An organism with the
    # measured top energy of 7.37 dies in 7.37/0.55 = 13.4 or 7.37/0.63 = 11.7.
    top = 7.37
    bound_second = top / (COST - 0.08)
    bound_third = top / COST
    print(f"survival bound: second taker {bound_second:.1f} steps, "
          f"third {bound_third:.1f} steps")

    exp = Experiment(
        experiment_id="EXP-61",
        question=(
            "Is the 25-step sharing run a queue that survives, or a cell that keeps "
            "being reoccupied as organisms arrive and leave?"
        ),
        arithmetic={
            "cost": f"{MAINT} + 0.02*{REPAIR} = {COST}",
            "second_taker_loss": f"{COST} - 0.08 = {COST - 0.08}",
            "third_taker_loss": f"{COST}",
            "top_energy": str(top),
            "survival_bound_second": f"{top} / {COST - 0.08:.2f} = {bound_second:.1f} steps",
            "survival_bound_third": f"{top} / {COST:.2f} = {bound_third:.1f} steps",
            "claim": "a run longer than the survival bound cannot be one queue; "
                     "it must be reoccupation",
        },
        arms={"uniform": "rich=2.4 poor=1.6, field uniform"},
        seed=SEED,
        command="checks/exp61_occupancy_runs.py",
        parameters={"steps": STEPS, "n": N, "cells": CELLS, "every": 1},
    )

    # Control fires: shared occupancy must exist at all.
    fires = len(runs) > 0 and max(peaks) > 1
    exp.control(
        "fires", fires,
        f"{len(runs)} runs of shared occupancy, peak {max(peaks) if peaks else 0} "
        f"organisms on one cell",
    )

    # Control silent: a cell carrying one organism is not a run. If the counter
    # reported runs of length 1 with peak 1, it would be counting every cell.
    silent = min(peaks) > 1
    exp.control(
        "silent", silent,
        f"every run has peak > 1 (min peak {min(peaks) if peaks else 'none'}); a cell "
        f"with one organism is not a shared cell",
    )

    # Control specific: the longest run must be longer than the survival bound,
    # otherwise there is no puzzle -- a 25-step run inside a 13-step bound would
    # mean organisms survive on shared cells, which the loss line forbids.
    longest = max(lengths) if lengths else 0
    specific = longest > bound_second
    exp.control(
        "specific", specific,
        f"longest run {longest} steps vs survival bound {bound_second:.1f} steps; "
        f"a run beyond the bound cannot be one queue",
    )

    if fires and silent and specific:
        exp.verdict(
            "passed",
            f"the longest sharing run is {longest} steps, beyond the "
            f"{bound_second:.1f}-step survival bound of a second taker, and "
            f"{100*total_surv/total_start:.1f}% of the organisms present at the start "
            f"of a run are still there at the end. The run is reoccupation, not one "
            f"queue surviving",
        )
    else:
        exp.verdict(
            "failed",
            f"fires={fires} silent={silent} specific={specific}: longest run "
            f"{longest} vs bound {bound_second:.1f}",
        )

    exp.limitation(
        "One seed (20250101). The run length is a maximum over 40 cells and 8000 "
        "steps, so it is a tail, not a typical value."
    )
    exp.limitation(
        "The survival bound uses the top energy 7.37 measured in EXP-56; an organism "
        "that arrived with less energy has a shorter bound, so the bound is generous."
    )
    exp.limitation(
        "This does not explain why the run is 25 rather than 15 or 40. It only shows "
        "that a run of that length cannot be one queue."
    )
    exp.save()


if __name__ == "__main__":
    main()
