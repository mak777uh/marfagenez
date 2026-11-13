# -*- coding: utf-8 -*-
"""EXP-37: the crossing at 0.1211 is a death threshold, not an economics one.

EXP-36 found the move cost where `random` stops beating `stay` is flat at 0.1211
for every income from 1.5 to 3.  Arithmetic said income should not matter at all
in that range, so the flatness is not the puzzle - the LEVEL is: arithmetic put
the threshold at 0.85 for income 2, measurement says 0.1211.

Reading `core/src/organism.rs:157` gives the missing piece.  An organism dies if
`energy <= 0` OR `damage >= 1.0`.  Damage grows by `damage_rate` every step
(0.2 here) and is repaired only out of leftover energy:

    energy -= maintenance                       (0.1)
    affordable = energy / repair_cost            (energy / 0.5)
    repaired   = min(affordable, damage)
    energy    -= repaired * repair_cost

So a step costs `maintenance + damage_rate*repair_cost = 0.1 + 0.1 = 0.2` while
energy lasts.  With starting energy 5, an organism that eats NOTHING survives
5/0.2 = 25 steps.  An organism that moves pays `move_cost` per step, so its
budget per step is `0.2 + move_cost` and it survives `5/(0.2+move_cost)` steps.

Prediction, if the crossing is where a mover's survival time drops below the
time it takes to find food: move_cost ~ 0.1211 gives 5/0.3211 = 15.6 steps.
Test it directly - turn off the field entirely and count how long a single
organism survives at each move cost.  If the crossing is a death threshold, the
survival time must fall the same way.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

# One organism, no neighbours to share with, field that never refills.
# `--rich` and `--poor` are both given because `uniform` is built as
# `(rich + poor) / 2`; leaving them at their defaults would silently build the
# field at M = 1.1, a level nobody chose.  `--regrow 0` then freezes it, so the
# level only matters as a starting value.
LONE = ["--steps", "1200", "--every", "1", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
        "--energy", "5", "--field", "uniform", "--rich", "2.0", "--poor", "0.2",
        "--n", "1", "--seed", "1"]


def run(extra):
    out = subprocess.run([str(BIN)] + LONE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def death_step(r):
    """First frame where the organism is not alive, or None."""
    for f in r["frames"]:
        if not f["samples"][0]["alive"]:
            return f["step"]
    return None


def main():
    rows = {}
    for cost in (0.0, 0.05, 0.1211, 0.2):
        for policy in ("stay", "random"):
            key = f"{policy}_move{cost:g}"
            r = run(["--policy", policy, "--move-cost", f"{cost:g}",
                     "--income", "0", "--regrow", "0"])
            rows[key] = (death_step(r), r["hash"])
            print(key, rows[key])

    exp = Experiment(
        experiment_id="crossing-is-death",
        question="Точка безразличия 0.1211 — экономика или порог смерти?",
        arithmetic={
            "step_cost": "maintenance + damage_rate*repair_cost = 0.1 + 0.1 = 0.2",
            "lone_survival_no_food": "energy / step_cost = 5/0.2 = 25 steps",
            "with_move_cost": "5/(0.2 + move_cost)",
            "prediction": "stay dies at 25; random dies at 5/(0.2+move_cost)",
            "frame_numbering": "death inside advance #k is first seen in frame k+1, "
                               "so the measured step is the budget + 1",
        },
        arms={k: k.replace("_", " ") for k in rows},
        seed=1,
        command="python3 checks/exp37_crossing_is_death.py",
        parameters={"cells": 120, "n": 1, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "field": "uniform", "income": 0, "regrow": 0},
    )

    for key, (d, h) in rows.items():
        exp.add_arm(key, key.replace("_", " "), {"death_step": d}, trace_hash=h)

    # `stay` never moves, so `move_cost` cannot touch it: the four `stay` arms
    # are one run by construction.  Saying so turns a §5 collision into the
    # finding itself -- the price of movement is inert for a standing organism.
    exp.expect_coincident(*[k for k in rows if k.startswith("stay_")])

    # Control 1 (fires): with no food and no movement the organism dies, and at
    # the step the arithmetic names.  The prediction is 25 + 1 because death
    # inside advance #25 is first visible in frame 26 (see `arithmetic`).
    exp.control("fires", rows["stay_move0"][0] == 26,
                f"stay, no food: dies at step {rows['stay_move0'][0]}, "
                f"arithmetic says 25 + 1 frame")

    # Control 2 (silent): a mover with no food must die EARLIER, not later.
    # Moving cannot feed an organism in an empty field.
    exp.control("silent", rows["random_move0.2"][0] < rows["stay_move0"][0],
                f"random move 0.2 dies at {rows['random_move0.2'][0]} < "
                f"stay {rows['stay_move0'][0]}")

    # Control 3 (specific): the death step must follow 5/(0.2+move_cost)+1, not
    # just be "earlier".  Checked at three costs.
    preds = {c: 5.0 / (0.2 + c) + 1.0 for c in (0.0, 0.05, 0.1211, 0.2)}
    ok = all(abs(rows[f"random_move{c:g}"][0] - preds[c]) <= 1.0
             for c in (0.05, 0.1211, 0.2))
    exp.control("specific", ok,
                "; ".join(f"move {c:g}: died {rows[f'random_move{c:g}'][0]} vs "
                          f"predicted {preds[c]:.1f}" for c in (0.05, 0.1211, 0.2)))

    exp.limitation(
        "one organism, no food at all; this measures the death threshold, not "
        "the competition that sets the crossing in a fed field.  The prediction "
        "assumes the organism moves on every step, which `random` does not do, "
        "so the moving arms are only checked to within one step."
    )
    exp.verdict("passed" if ok and rows["stay_move0"][0] == 26 else "failed",
                "смерть наступает по бюджету energy/(step_cost+move_cost), "
                "с точностью кадра: 5/(0.2+move_cost) + 1")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
