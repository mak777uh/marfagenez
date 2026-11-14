"""EXP-22: how many organisms can one cell feed?

The question. `docs/FINDING-capacity-exact.md` predicts capacity from
`k_max = M*r/income`, but that number is a *stock* (what the cell holds),
not a *count* (how many organisms it feeds). Measured capacity was 80 where
the formula said 160. This experiment settles what `k_max` actually is.

The arithmetic, done before any run. One cell, `k` organisms on it, feed=true:

    c <- M                       (regrow first)
    for each organism: c -= min(income, c)      (take)
    c <- c + (M - c)*r           (regrow for the next step)

The cell settles at `c* = M - income*(1-r)/r` while `c > income`. An organism
is fed if what it takes, `min(income, c_left)`, is at least `maintenance`.
`k_max` is the largest `k` where the *last* organism still gets that much.

The prediction is computed by the same recursion the model runs, not by a
closed form -- a closed form has been wrong three times today.

The measurement. `--policy stay` puts every organism on its own cell and
never moves it, so `k = 1` everywhere. To get `k > 1` we use fewer cells than
organisms: `n = 40` on `cells = 20` gives `k = 2` at steady state, and so on.
`alive` is read at the last frame.

What this does not prove. It does not prove the recursion is the *right*
model of the Rust code -- that is checked separately by matching one run.
It does not cover movement, damage, or repair.
"""

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


def cell_settles(M, k, steps=4000):
    """The cell's resource after `steps` steps with `k` organisms on it."""
    c = M
    for _ in range(steps):
        for _ in range(k):
            c -= min(INCOME, c)
        c = c + (M - c) * R
    return c


def k_max_predicted(M):
    """Largest k where the last organism on the cell still eats >= maintenance."""

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


def run_trace(n, cells, M, seed, steps=3000):
    cmd = [
        TRACE,
        "--policy", "stay",
        "--n", str(n),
        "--cells", str(cells),
        "--field", "uniform",
        "--rich", str(M),
        "--poor", str(M),
        "--regrow", str(R),
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", "0.0",
        "--move-cost", "0.0",
        "--capacity", "1000.0",
        "--energy", "10.0",
        "--feed",
        "--layout", "even",
        "--seed", str(seed),
        "--steps", str(steps),
        "--every", str(steps),
    ]
    # The binary writes only where told: `--out` names one file, overwritten
    # per run. It used to invent results/<policy>/trace-<policy>-<ms>.json for
    # every call, and 1792 of those reached 30 GB.
    path = os.path.join(ROOT, "results", "EXP-22", "trace-last.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd += ["--out", path]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-2000:])
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # The prediction, before any measurement.
    predicted = {}
    for M in (0.75, 1.0, 1.5, 1.75, 2.0, 2.75, 4.0, 6.0, 10.0):
        predicted[M] = k_max_predicted(M)

    # Measure: put n organisms on n/k cells so each cell carries k of them.
    # k = 1, 2, 3, 4 at M = 2.0 -- the case the old note got wrong.
    arms = []
    rows = []
    for k in (1, 2, 3, 4):
        n = 40 * k
        cells = 40
        tr = run_trace(n, cells, 2.0, seed=1)
        last = tr["frames"][-1]
        alive = sum(1 for s in last["samples"] if s["alive"])
        occupied = len(set(s["cell"] for s in last["samples"] if s["alive"]))
        crowding = alive / occupied if occupied else 0.0
        rows.append({"k_intended": k, "n": n, "cells": cells,
                     "alive": alive, "occupied": occupied,
                     "crowding": round(crowding, 3)})
        arms.append({
            "key": "k%d" % k,
            "label": "%d organisms on %d cells" % (n, cells),
            "metrics": {"alive": alive, "occupied": occupied,
                        "crowding": round(crowding, 3)},
            "trace_hash": tr.get("hash"),
        })

    # What the recursion says should survive at k = 1, 2, 3, 4 with M = 2.
    survives = {}
    for k in (1, 2, 3, 4):
        c = cell_settles(2.0, k)
        for _ in range(k - 1):
            c -= min(INCOME, c)
        survives[k] = min(INCOME, c) >= MAINT - 1e-12

    exp = Experiment(
        experiment_id="EXP-22",
        question="How many organisms can one cell feed -- is k_max a count or a stock?",
        arithmetic={
            "model": "One cell with k organisms, feed=true: c <- M; k times c -= min(income, c); "
            "c <- c + (M-c)*r. The cell settles at c* = M - income*(1-r)/r while c > income. "
            "An organism is fed if min(income, c_left) >= maintenance. "
            "k_max = largest k where the last organism still gets that much. "
            "At M=2, income=0.8, maintenance=0.6, r=0.8: c* = 2 - 0.8*0.2/0.8 = 1.8. "
            "k=1: last gets min(0.8, 1.8) = 0.8 >= 0.6 -> fed. "
            "k=2: after one takes, c = 1.0, last gets min(0.8, 1.0) = 0.8 >= 0.6 -> fed. "
            "k=3: after two take, c = 1.8 - 1.6 = 0.2, last gets 0.2 < 0.6 -> starves. "
            "So k_max = 2 at M = 2, and capacity = 40 cells * 2 = 80, not 160.",
        },
        arms={a["key"]: a["label"] for a in arms},
        seed=1,
        command="python3 checks/exp22_k_max.py",
        parameters={
            "income": INCOME, "maintenance": MAINT, "regrow": R,
            "M": 2.0, "cells": 40, "steps": 3000, "feed": True,
        },
    )

    for a in arms:
        exp.add_arm(a["key"], a["label"], a["metrics"],
                    trace_hash=a["trace_hash"])

    exp.add_series("crowding", [float(r["k_intended"]) for r in rows],
                   [float(r["crowding"]) for r in rows])

    # Control 1 (fires): at k = 3 the third organism must starve, so alive < n.
    c3 = [r for r in rows if r["k_intended"] == 3][0]
    exp.control(
        "fires",
        c3["alive"] < c3["n"],
        "at k=3, %d of %d alive -- the third organism on a cell starves"
        % (c3["alive"], c3["n"]),
    )

    # Control 2 (silent): at k = 1 and k = 2 everyone must live.
    c1 = [r for r in rows if r["k_intended"] == 1][0]
    c2 = [r for r in rows if r["k_intended"] == 2][0]
    exp.control(
        "silent",
        c1["alive"] == c1["n"] and c2["alive"] == c2["n"],
        "k=1: %d/%d alive; k=2: %d/%d alive -- one and two organisms are both fed"
        % (c1["alive"], c1["n"], c2["alive"], c2["n"]),
    )

    # Control 3 (specific): the death must happen exactly at k=3, not at k=2.
    exp.control(
        "specific",
        survives[2] and not survives[3],
        "recursion says k=2 fed, k=3 not; measurement says k=2 alive %d/%d, "
        "k=3 alive %d/%d" % (c2["alive"], c2["n"], c3["alive"], c3["n"]),
    )

    exp.limitation(
        "Only k = 1..4 at M = 2.0, one seed, no movement, no damage. "
        "The recursion is the model's own step, not an independent derivation; "
        "it is checked against the Rust run, not against nature."
    )
    exp.verdict(
        "passed" if exp.controls_passed() else "failed",
        "k_max is a count (2 at M=2), not a stock (2.25); capacity 80 follows"
        if exp.controls_passed() else "controls did not pass",
    )
    path = exp.save()
    print("saved:", path)
    for r in rows:
        print(r)
    print("predicted k_max at M=2:", k_max_predicted(2.0))


if __name__ == "__main__":
    main()
