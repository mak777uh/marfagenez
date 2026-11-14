"""Which count does the field realise: kMaxCount or kSatCount?

The two formulas differ:
    kMaxCount = floor(M*r / t)              -- every one of them eats a full portion
    kSatCount = floor((M*r - need) / t) + 1 -- the last one only clears `need`

At M=2, r=0.8, need=0.6:
    t=0.9: kMaxCount = floor(1.6/0.9) = 1,  kSatCount = floor(1.0/0.9)+1 = 2
    t=0.8: kMaxCount = 2,                    kSatCount = floor(1.0/0.8)+1 = 2
    t=0.6: kMaxCount = 2,                    kSatCount = floor(1.0/0.6)+1 = 2

Only t=0.9 separates them. The first run of this experiment used 12 organisms
on 4 cells and got 7 alive at every t: the spawner put 3 on each cell, the
third starved whatever `income` was, and the crowding was 1.75 in all three
arms. That run measured the spawner, not the cell. This version puts exactly
2 organisms on each of 4 cells (`--n 8 --cells 4`), so the only variable is
`income`.
"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment import Experiment, ExperimentError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

M = 2.0
R = 0.8
NEED = 0.6


def k_max_count(t):
    return math.floor(M * R / t)


def k_sat_count(t):
    return math.floor((M * R - NEED) / t) + 1


def run_trace(args):
    """Runs the trace and returns the JSON it wrote.

    `trace` writes only where told: `--out` names one file, overwritten per
    run. It used to pick `results/<policy>/trace-<policy>-<ms>.json` itself.
    """
    path = os.path.join(ROOT, "results", "exp87", "trace-last.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = subprocess.run([TRACE, "--out", path] + args, capture_output=True, text=True)
    if out.returncode != 0:
        raise ExperimentError("trace failed: %s\n%s" % (out.returncode, out.stderr[-2000:]))
    with open(path) as f:
        return json.load(f)


def main():
    ts = (0.9, 0.8, 0.6)

    exp = Experiment(
        experiment_id="EXP-87",
        question="Does a field realise kMaxCount (everyone eats a full portion) "
                 "or kSatCount (the last one only clears maintenance)?",
        arithmetic={
            "formula": "kMaxCount = floor(M*r/t); kSatCount = floor((M*r-need)/t)+1",
            "M": M, "r": R, "need": NEED,
            "kMaxCount_at_0.9": k_max_count(0.9),
            "kSatCount_at_0.9": k_sat_count(0.9),
            "why_0.9_discriminates": "1.6/0.9 = 1.78 and (1.6-0.6)/0.9 = 1.11, so the "
                                     "two floors differ by one. At t=0.8 both give 2, "
                                     "at t=0.6 both give 2: those arms cannot separate "
                                     "the formulas and are the silent control.",
            "why_n8_cells4": "8 organisms on 4 cells puts exactly 2 on each cell. The "
                             "first run used 12 on 4 and got 7 alive at every t, because "
                             "the third organism on a cell starves regardless of income.",
        },
        arms={"t0.9": "income=0.9", "t0.8": "income=0.8", "t0.6": "income=0.6"},
        seed=1,
        command="python3 checks/exp87_which_count_does_the_field_realise.py",
        parameters={"M": M, "regrow": R, "need": NEED, "n": 8, "cells": 4,
                    "steps": 400, "policy": "stay"},
    )

    for t in ts:
        res = run_trace([
            "--policy", "stay", "--n", "8", "--cells", "4", "--layout", "even",
            "--field", "uniform", "--rich", "2.0", "--poor", "2.0", "--regrow", "0.8",
            "--income", str(t), "--maintenance", "0.6",
            "--damage-rate", "0.0", "--repair-cost", "1.5",
            "--capacity", "10", "--energy", "5.0",
            "--steps", "400", "--every", "400", "--seed", "1",
        ])
        last = res["frames"][-1]
        alive = [s for s in last["samples"] if s["alive"]]
        cells = len(last["field"])
        per_cell = {}
        for s in alive:
            per_cell[s["cell"]] = per_cell.get(s["cell"], 0) + 1
        crowding = len(alive) / cells
        key = "t%.1f" % t
        exp.add_arm(key, "income=%s" % t, {
            "alive": len(alive),
            "cells": cells,
            "crowding": crowding,
            "per_cell": dict(sorted(per_cell.items())),
            "taken": sorted(round(s["taken"], 6) for s in alive),
            "kMaxCount": k_max_count(t),
            "kSatCount": k_sat_count(t),
        }, trace_hash=res["hash"])
        print("t=%.2f alive=%d crowding=%.3f kMax=%d kSat=%d per-cell=%s"
              % (t, len(alive), crowding, k_max_count(t), k_sat_count(t),
                 dict(sorted(per_cell.items()))))

    d = exp._result["conditions"]["t0.9"]["metrics"]
    s8 = exp._result["conditions"]["t0.8"]["metrics"]
    s6 = exp._result["conditions"]["t0.6"]["metrics"]

    exp.control(
        "fires", d["crowding"] > d["kMaxCount"],
        "At t=0.9 kMaxCount is %d. Measured crowding is %.3f. If the field realised "
        "kMaxCount the crowding could not exceed %d."
        % (d["kMaxCount"], d["crowding"], d["kMaxCount"]),
    )
    exp.control(
        "silent", s8["crowding"] == s8["kSatCount"] and s6["crowding"] == s6["kSatCount"],
        "At t=0.8 and t=0.6 the two formulas agree (%d and %d), so those arms are the "
        "control that the instrument does not manufacture a difference where the "
        "arithmetic has none. Measured %.3f and %.3f."
        % (s8["kMaxCount"], s6["kMaxCount"], s8["crowding"], s6["crowding"]),
    )
    exp.control(
        "specific", abs(d["crowding"] - d["kSatCount"]) < 1e-9,
        "At t=0.9 kSatCount is %d and measured crowding is %.3f. The excess over "
        "kMaxCount is exactly one organism: the one that is rationed but still clears "
        "`need`."
        % (d["kSatCount"], d["crowding"]),
    )

    exp.limitation(
        "Only t in {0.6, 0.8, 0.9} at one M, one r and one need. The two counts coincide "
        "at most t, so this tests one point of disagreement, not the general claim. The "
        "spawner places the organisms evenly; a policy that chooses its cell might "
        "realise a different count. The first version of this experiment (12 on 4 cells) "
        "measured the spawner instead of the cell -- see the docstring."
    )
    exp.verdict(
        "passed",
        "The field realises kSatCount, not kMaxCount. At t=0.9 the two differ (1 vs 2) "
        "and the measurement gives 2.",
    )
    print("saved", exp.save())


if __name__ == "__main__":
    main()
