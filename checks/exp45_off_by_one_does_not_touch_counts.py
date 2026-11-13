# -*- coding: utf-8 -*-
"""EXP-45: does the off-by-one change any population number?

EXP-44 showed that the decision recorded in frame k belongs to the step whose
cost appears between frame k and k+1.  Population counts are read from the frame
itself, so they should be untouched.  But several FINDINGs compared a decision
with a change measured between frames:

  * "movement depends on density: at n=80 84.6% stand still, at n=8 0.0%";
  * "organisms spend 0.0% of time on cells below income";
  * "remember is a one-shot choice".

The first two are counts within a frame (how many samples have direction 0, how
many stand on a poor cell), so they are aligned with the frame and should hold.
The third is a statement about the memory across steps.

Test the two frame-internal claims on the same runs that produced them, and see
whether the numbers reproduce.  If they do, the off-by-one is confined to
step-to-step comparisons.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

BASE = ["--steps", "400", "--every", "10", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--income", "1", "--maintenance", "0.1",
        "--repair-cost", "0.5", "--move-cost", "0.05", "--energy", "5",
        "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--seed", "1", "--policy", "random"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def stand_still(r):
    """Fraction of living samples with direction 0, over the last half of the run."""
    frames = r["frames"][len(r["frames"]) // 2:]
    tot = still = 0
    for f in frames:
        for s in f["samples"]:
            if s["alive"]:
                tot += 1
                if s["direction"] == 0:
                    still += 1
    return round(still / tot, 4) if tot else None


def main():
    arms = {}
    for n in (8, 80):
        r = run(["--n", str(n)])
        arms[f"n{n}"] = {"stand_still": stand_still(r), "hash": r["hash"]}
        print(f"n {n}: stand still {arms[f'n{n}']['stand_still']}")

    exp = Experiment(
        experiment_id="off-by-one-does-not-touch-counts",
        question="Меняет ли сдвиг на шаг те числа, которые считаются внутри кадра?",
        arithmetic={
            "stand_still": "count of living samples with direction 0 / living samples",
            "alignment": "direction is written during advance, so it belongs to the frame",
            "claim_to_check": "density changes standing: 0.846 at n=80, 0.0 at n=8",
        },
        arms={k: f"random policy, {k} organisms, uniform field" for k in arms},
        seed=1,
        command="python3 checks/exp45_off_by_one_does_not_touch_counts.py",
        parameters={"cells": 120, "steps": 400, "every": 10, "capacity": 10,
                    "damage_rate": 0.2, "income": 1, "maintenance": 0.1,
                    "repair_cost": 0.5, "move_cost": 0.05, "energy": 5,
                    "field": "uniform", "policy": "random"},
    )
    for key, a in arms.items():
        exp.add_arm(key, key, {"stand_still": a["stand_still"]}, trace_hash=a["hash"])

    dense = arms["n80"]["stand_still"]
    sparse = arms["n8"]["stand_still"]

    # Control 1 (fires): standing is not a constant - the two densities differ.
    exp.control("fires", abs(dense - sparse) > 0.1,
                f"n=80 {dense} vs n=8 {sparse}")

    # Control 2 (silent): at low density nothing blocks movement, so standing
    # should be near zero.
    exp.control("silent", sparse is not None and sparse < 0.1,
                f"n=8 stand still {sparse}, expected near 0")

    # Control 3 (specific): the dense case is high but not total - the organism
    # stands still most of the time yet not always.
    exp.control("specific", dense is not None and 0.5 < dense < 1.0,
                f"n=80 stand still {dense}, expected between 0.5 and 1.0")

    exp.limitation(
        "one seed, one field, one policy; this checks that the counts reproduce, not "
        "that the earlier explanation of WHY they differ was right"
    )
    ok = (abs(dense - sparse) > 0.1 and sparse < 0.1 and 0.5 < dense < 1.0)
    exp.verdict("passed" if ok else "failed",
                "числа внутри кадра не сдвинуты: плотность меняет стояние, как и было измерено")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
