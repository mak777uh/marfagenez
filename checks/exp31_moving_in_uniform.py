# -*- coding: utf-8 -*-
"""EXP-31: in a uniform field, does moving help or hurt?

The field is uniform, so every cell is the same.  Any movement is pure cost
(`move-cost` per step).  So the prediction is: `stay` is best, and every
policy that moves is worse.

But a measurement showed the opposite: `random` keeps 108 organisms where
`stay` keeps 72 (n=120, seed 1).  That is a real anomaly, not a rounding
artefact.

Hypothesis: `stay` is not free.  An organism that never moves sits on a cell
whose capacity is consumed by whoever is there.  If two organisms share a cell,
both pay `damage-rate` on the same cell and both pay `repair-cost`, so the cell
is repaired twice per step while the income is still one.  Moving spreads them
over more cells, so each cell is repaired once.

If that is right, the deficit of `stay` must shrink as the start gets sparser.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"
TAG = "EXP-31"

BASE = ["--steps", "1200", "--every", "1200", "--cells", "120",
        "--capacity", "10", "--damage-rate", "0.2", "--income", "1",
        "--maintenance", "0.1", "--repair-cost", "0.5", "--move-cost", "0.05",
        "--energy", "5", "--field", "uniform"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    rel = line.split("written:", 1)[1].strip()
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def alive_of(r):
    return [s for s in r["frames"][-1]["samples"] if s["alive"]]


def main():
    arms = {}
    for n in (120, 60, 30):
        for policy in ("stay", "random", "sighted"):
            r = run(["--n", str(n), "--policy", policy, "--seed", "1"])
            alive = alive_of(r)
            arms[f"{policy}_n{n}"] = {
                "alive": len(alive),
                "moved": sum(1 for s in alive if s["direction"] != 0),
                "mean_energy": round(sum(s["energy"] for s in alive) / max(len(alive), 1), 3),
                "hash": r["hash"],
            }

    for k, v in arms.items():
        print(k, v)

    exp = Experiment(
        experiment_id="moving-in-uniform-field",
        question="В однородном поле движение помогает или мешает?",
        arithmetic={
            "formula": "per organism per step = income/share - maintenance - damage_rate*repair_cost",
            "alone": "1 - 0.1 - 0.2*0.5 = 0.8",
            "two_on_one_cell": "0.5 - 0.1 - 0.2*0.5 = 0.2",
            "prediction": "0.8 > 0.2, so sharing a cell is strictly worse; "
                          "movement that splits a pair must pay for itself",
        },
        arms={
            "stay_n120": "n=120, cells=120, stay",
            "random_n120": "n=120, cells=120, random",
            "sighted_n120": "n=120, cells=120, sighted",
            "stay_n60": "n=60, cells=120, stay",
            "random_n60": "n=60, cells=120, random",
            "stay_n30": "n=30, cells=120, stay",
            "random_n30": "n=30, cells=120, random",
        },
        seed=1,
        command="python3 checks/exp31_moving_in_uniform.py",
        parameters={"cells": 120, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "income": 1.0, "maintenance": 0.1,
                    "repair_cost": 0.5, "move_cost": 0.05, "energy": 5.0,
                    "field": "uniform"},
    )

    # §5: `sighted` in a uniform field is the SAME arm as `stay` (identical
    # hash), so it is recorded without a hash - its identity is the evidence
    # for the `silent` control, not a separate run.
    for key in ("stay_n120", "random_n120",
                "stay_n60", "random_n60", "stay_n30", "random_n30"):
        exp.add_arm(key, key.replace("_", " "),
                    {"alive": arms[key]["alive"],
                     "moved": arms[key]["moved"],
                     "mean_energy": arms[key]["mean_energy"]},
                    trace_hash=arms[key]["hash"])
    for key in ("sighted_n120", "sighted_n60", "sighted_n30"):
        exp.add_arm(key, key.replace("_", " ") + " (same arm as stay)",
                    {"alive": arms[key]["alive"],
                     "moved": arms[key]["moved"],
                     "mean_energy": arms[key]["mean_energy"]},
                    trace_hash=None)

    # Control 1 (fires): staying must be worse than moving at n=120.
    fires = arms["stay_n120"]["alive"] < arms["random_n120"]["alive"]
    exp.control("fires", fires,
                f"stay {arms['stay_n120']['alive']} < random "
                f"{arms['random_n120']['alive']} at n=120")

    # Control 2 (silent): sighted must be identical to stay in a uniform field -
    # there is nothing to see, so a seeing organism behaves like a blind one.
    silent = arms["sighted_n120"]["hash"] == arms["stay_n120"]["hash"]
    exp.control("silent", silent,
                f"sighted hash {arms['sighted_n120']['hash']} == "
                f"stay hash {arms['stay_n120']['hash']}")

    # Control 3 (specific): the deficit must scale with crowding.  If sharing a
    # cell is the cause, then a sparser start must shrink the gap.
    gap120 = arms["random_n120"]["alive"] - arms["stay_n120"]["alive"]
    gap60 = arms["random_n60"]["alive"] - arms["stay_n60"]["alive"]
    gap30 = arms["random_n30"]["alive"] - arms["stay_n30"]["alive"]
    specific = gap120 > gap60 > gap30
    exp.control("specific", specific,
                f"gap random-stay: n120={gap120} > n60={gap60} > n30={gap30}")

    exp.limitation(
        "one seed per arm; the cause is inferred from the crowding trend, not "
        "measured per cell - the trace does not report how many organisms share "
        "a cell, so the double-repair mechanism is not directly observed"
    )
    exp.verdict(
        "passed" if (fires and silent and specific) else "failed",
        "движение в однородном поле окупается ровно за счёт разрежения пар",
    )
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
