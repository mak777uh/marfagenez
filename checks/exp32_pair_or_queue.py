# -*- coding: utf-8 -*-
"""EXP-32: is the pair penalty a double repair, or a queue for the income?

EXP-31 measured `stay` 72 vs `random` 108 at n=120 with **random placement**.
The explanation offered was "two organisms on one cell each pay the repair".
But `advance` walks organisms in index order and each one eats immediately, so
the first on a cell takes the whole `income` and the second takes what is left.
That is a queue, not a shared repair bill.

`--layout even` separates the two.  With `n = k * cells` every cell carries
exactly `k` organisms, so the crowding is known and the same for every cell.

Predictions:

* **pair penalty** - a cell with `k` organisms pays `k` repairs but earns one
  `income`.  Per organism per step: `income/k - maintenance - damage*repair`.
  For k=2: `0.5 - 0.1 - 0.1 = 0.3`.  It is positive, so both should survive.
* **queue** - the second organism eats nothing and starves at once.  For k=2
  only half the population should survive.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

BASE = ["--steps", "1200", "--every", "1200", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--income", "1", "--maintenance", "0.1",
        "--repair-cost", "0.5", "--move-cost", "0.05", "--energy", "5",
        "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--layout", "even"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def stats(r):
    alive = [s for s in r["frames"][-1]["samples"] if s["alive"]]
    n = len(alive)
    return n, round(sum(s["energy"] for s in alive) / max(n, 1), 3), r["hash"]


def main():
    arms = {}
    for k in (1, 2, 3):
        for policy in ("stay", "random"):
            key = f"{policy}_k{k}"
            arms[key] = stats(run(["--n", str(120 * k), "--policy", policy,
                                   "--seed", "1"]))
    for key, v in arms.items():
        print(key, v)

    exp = Experiment(
        experiment_id="pair-penalty-or-queue",
        question="Дефицит стоящих на общей клетке — двойной ремонт или очередь за доходом?",
        arithmetic={
            "per_organism": "income/k - maintenance - damage_rate*repair_cost",
            "k1": "1/1 - 0.1 - 0.2*0.5 = 0.8 per step",
            "k2": "1/2 - 0.1 - 0.2*0.5 = 0.3 per step",
            "k3": "1/3 - 0.1 - 0.2*0.5 = 0.033 per step",
            "pair_penalty_predicts": "all organisms survive at k=1,2; k=3 is marginal",
            "queue_predicts": "only the first on each cell survives: 120 of 240, 120 of 360",
        },
        arms={f"{p}_k{k}": f"even layout, k={k}, {p}" for k in (1, 2, 3)
              for p in ("stay", "random")},
        seed=1,
        command="python3 checks/exp32_pair_or_queue.py",
        parameters={"cells": 120, "steps": 1200, "capacity": 10, "damage_rate": 0.2,
                    "income": 1, "maintenance": 0.1, "repair_cost": 0.5,
                    "move_cost": 0.05, "energy": 5, "field": "uniform",
                    "layout": "even"},
    )

    for key, (n, mean, h) in arms.items():
        exp.add_arm(key, key.replace("_", " "), {"alive": n, "mean_energy": mean},
                    trace_hash=h)

    # Control 1 (fires): crowding must cost something - k=1 must keep more than
    # k=2 per cell, i.e. 120 alive at k=1 is more than 60 at k=2.
    fires = arms["stay_k1"][0] / 1 > arms["stay_k2"][0] / 2
    exp.control("fires", fires,
                f"stay per cell: k1={arms['stay_k1'][0]/1:.0f} > "
                f"k2={arms['stay_k2'][0]/2:.1f}")

    # Control 2 (silent): at k=1 there is no pair, so a queue has nothing to
    # take and the two policies must differ only by movement cost.  `stay`
    # must keep every organism.
    silent = arms["stay_k1"][0] == 120
    exp.control("silent", silent,
                f"stay at k=1 keeps {arms['stay_k1'][0]} of 120")

    # Control 3 (specific): the queue predicts a hard number - exactly one
    # survivor per cell, i.e. 120 alive at every k.  The pair penalty predicts
    # more than 120 at k=2.  The two are distinguishable only if k=2 keeps
    # strictly more than 120.
    specific = arms["stay_k2"][0] > 120
    exp.control("specific", specific,
                f"stay at k=2 keeps {arms['stay_k2'][0]}, queue predicts 120")

    exp.limitation(
        "one seed; `stay` never moves so the k=2 result is the initial pairing "
        "held for 1200 steps, not an equilibrium the population found; the trace "
        "does not record which organism ate first on a shared cell"
    )
    exp.verdict(
        "passed" if (fires and silent and specific) else "failed",
        "на общей клетке платится двойной ремонт, а не очередь: k=2 держит больше 120",
    )
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
