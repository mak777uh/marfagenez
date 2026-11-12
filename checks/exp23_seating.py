"""EXP-23: does random seating explain the "79 instead of 90" anomaly?

The question. `docs/FINDING-capacity-exact.md` recorded that `uniform` at
M = 4.0 gave 79 survivors where a stock formula predicted 90, and left the
gap unexplained. After EXP-22 established that `k_max` is a *count* (how many
organisms a cell feeds), the prediction changes: a cell feeds at most
`k_max` organisms, so with random seating the survivors should be

    sum over cells of min(occupancy, k_max)

The arithmetic, done before any run. At M = 4.0, income = 0.8, maintenance =
0.6, r = 0.8 the cell settles at c* = 3.8 and the takes are 0.8, 0.8, 0.8,
0.8, 0.0 -- so k_max = 4. At M = 2.25 the cell settles at c* = 2.05 and the
takes are 0.8, 0.8, 0.2 -- so k_max = 2.

The measurement. `--policy stay` never moves anyone, so the seating at step 1
is the seating that has to survive. We read the first frame to get the
occupancy histogram, sum min(occupancy, k_max), and compare with the last
frame's alive count. Two seatings are compared: random (the default) and
`--layout even` (exactly k per cell).

What this does not prove. It does not say the model is right about anything
outside this field. It does not cover movement: `stay` never moves, so a
moving organism could in principle escape an overcrowded cell, and this
experiment says nothing about that. It does not explain why `alternating` and
`uniform` gave identical numbers under random seating -- that is recorded as
an observation, not as a result.
"""

import collections
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

TRACE = os.path.join(ROOT, "core", "target", "release", "trace")
if not os.path.exists(TRACE):
    TRACE = os.path.join(ROOT, "core", "target", "release", "trace.exe")

INCOME = 0.8
MAINT = 0.6
R = 0.8
CELLS = 40
N = 160


def cell_settles(M, k, steps=4000):
    c = M
    for _ in range(steps):
        for _ in range(k):
            c -= min(INCOME, c)
        c = c + (M - c) * R
    return c


def k_max_predicted(M):
    def last_income(k):
        c = cell_settles(M, k)
        for _ in range(k - 1):
            c -= min(INCOME, c)
        return min(INCOME, c)

    k = 0
    while last_income(k + 1) >= MAINT - 1e-12:
        k += 1
        if k > 200:
            break
    return k


def run_trace(field, rich, poor, n, cells, layout, seed, steps):
    cmd = [
        TRACE,
        "--policy", "stay",
        "--n", str(n),
        "--cells", str(cells),
        "--field", field,
        "--rich", str(rich),
        "--poor", str(poor),
        "--regrow", str(R),
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", "0.0",
        "--move-cost", "0.0",
        "--capacity", "1000.0",
        "--energy", "10.0",
        "--feed",
        "--seed", str(seed),
        "--steps", str(steps),
        "--every", str(steps),
    ]
    if layout:
        cmd += ["--layout", layout]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-2000:])
    path = None
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            path = line.split(":", 1)[1].strip()
    if path is None:
        raise RuntimeError("no written: line in\n" + out.stdout[-2000:])
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def measure(field, rich, poor, layout, seed):
    """Seat once (1 step) to read occupancy, then run to the end."""
    seat = run_trace(field, rich, poor, N, CELLS, layout, seed, 1)
    occ = collections.Counter(s["cell"] for s in seat["frames"][0]["samples"])

    full = run_trace(field, rich, poor, N, CELLS, layout, seed, 3000)
    last = full["frames"][-1]
    alive = sum(1 for s in last["samples"] if s["alive"])
    occupied = len(set(s["cell"] for s in last["samples"] if s["alive"]))
    return {
        "occ": occ,
        "alive": alive,
        "occupied": occupied,
        "hash": full.get("hash"),
    }


def main():
    # The prediction, before any measurement.
    k4 = k_max_predicted(4.0)
    k225 = k_max_predicted(2.25)

    rows = []
    arms = []
    for label, field, rich, poor, layout, M in (
        ("random seating, M=4.0", "uniform", 4.0, 4.0, None, 4.0),
        ("even seating, M=4.0", "uniform", 4.0, 4.0, "even", 4.0),
        ("random seating, M=2.25", "uniform", 4.0, 0.5, None, 2.25),
        ("even seating, M=2.25", "uniform", 4.0, 0.5, "even", 2.25),
    ):
        r = measure(field, rich, poor, layout, seed=1)
        kmax = k_max_predicted(M)
        predicted = sum(min(v, kmax) for v in r["occ"].values())
        rows.append({
            "label": label, "M": M, "k_max": kmax,
            "alive": r["alive"], "occupied": r["occupied"],
            "predicted": predicted, "hash": r["hash"],
        })
        arms.append({
            "key": label.split(",")[0].replace(" ", "-") + "-M" + str(M),
            "label": label,
            "metrics": {"alive": r["alive"], "occupied": r["occupied"],
                        "predicted": predicted, "k_max": kmax},
            "trace_hash": r["hash"],
        })

    exp = Experiment(
        experiment_id="EXP-23",
        question="Does random seating explain the '79 instead of 90' anomaly?",
        arithmetic={
            "model": "stay never moves, so the step-1 seating must survive. "
            "A cell feeds at most k_max organisms, so survivors = "
            "sum over cells of min(occupancy, k_max). "
            "k_max from the take recursion: at M=4.0, c*=3.8, takes 0.8,0.8,0.8,0.8,0.0 -> k_max=4. "
            "At M=2.25, c*=2.05, takes 0.8,0.8,0.2 -> k_max=2. "
            "With 160 organisms randomly on 40 cells, some cells get 9 and some get 1, "
            "so min(occupancy, k_max) is strictly below 160 even when the field could hold 160.",
            "k_max_M4": k4,
            "k_max_M225": k225,
        },
        arms={a["key"]: a["label"] for a in arms},
        seed=1,
        command="python3 checks/exp23_seating.py",
        parameters={
            "income": INCOME, "maintenance": MAINT, "regrow": R,
            "cells": CELLS, "n": N, "steps": 3000, "feed": True,
        },
    )

    for a in arms:
        exp.add_arm(a["key"], a["label"], a["metrics"],
                    trace_hash=a["trace_hash"])

    exp.add_series("alive", [r["M"] for r in rows],
                   [float(r["alive"]) for r in rows])
    exp.add_series("predicted", [r["M"] for r in rows],
                   [float(r["predicted"]) for r in rows])

    rnd4 = [r for r in rows if r["M"] == 4.0 and "random" in r["label"]][0]
    even4 = [r for r in rows if r["M"] == 4.0 and "even" in r["label"]][0]
    rnd225 = [r for r in rows if r["M"] == 2.25 and "random" in r["label"]][0]
    even225 = [r for r in rows if r["M"] == 2.25 and "even" in r["label"]][0]

    # Control 1 (fires): random seating must lose organisms at M=4.0.
    exp.control(
        "fires",
        rnd4["alive"] < N,
        "random seating at M=4.0: %d of %d alive -- overcrowded cells kill"
        % (rnd4["alive"], N),
    )

    # Control 2 (silent): even seating at M=4.0 must kill nobody, because
    # k=4 is exactly k_max.
    exp.control(
        "silent",
        even4["alive"] == N,
        "even seating at M=4.0: %d of %d alive -- 4 per cell is exactly k_max"
        % (even4["alive"], N),
    )

    # Control 3 (specific): the prediction must match the measurement in both
    # regimes, and the two regimes must differ from each other.
    ok4 = abs(rnd4["alive"] - rnd4["predicted"]) <= 0
    ok225 = abs(rnd225["alive"] - rnd225["predicted"]) <= 0
    exp.control(
        "specific",
        ok4 and ok225 and rnd4["alive"] != rnd225["alive"],
        "random M=4.0: alive %d vs predicted %d; random M=2.25: alive %d vs "
        "predicted %d; even M=2.25: %d -- the two k_max give different counts"
        % (rnd4["alive"], rnd4["predicted"], rnd225["alive"],
           rnd225["predicted"], even225["alive"]),
    )

    exp.limitation(
        "One seed, `stay` only, no movement, no damage, one field shape. "
        "The prediction uses the same take recursion the model runs, so it is "
        "a consistency check, not an independent derivation. "
        "`alternating` gave the same numbers as `uniform` under random seating; "
        "that is recorded but not explained."
    )
    exp.verdict(
        "passed" if exp.controls_passed() else "failed",
        "random seating explains the anomaly: survivors = sum min(occupancy, k_max)"
        if exp.controls_passed() else "controls did not pass",
    )
    path = exp.save()
    print("saved:", path)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
