# -*- coding: utf-8 -*-
"""EXP-41: the organism is a nomad - p_move is 2/3, not 1/2.

EXP-40 failed on one arm only (move cost 0.2: predicted 16.22, measured 15) and
passed on the other three to 0.00.  The prediction used `p_move` measured over
ALL alive frames, but the organism is not a coin: `Policy::Random` draws a
direction from three values, and a direction of 0 means "stay".  If the draw is
uniform over {-1, 0, +1} then `p_move = 2/3`.

Measured: 0.600 / 0.632 / 0.643 / 0.636.  Those are not 2/3 either - they are
the fraction of steps on which the organism actually MOVED, and a move can be
blocked (edge of the field) or cancelled.  With 120 cells and 1 organism the
edge is rare, so the deficit is probably the draw itself.

Two things to separate:
  1. how often the policy CHOOSES a non-zero direction (a property of the
     organism);
  2. how often the organism actually changes cell (a property of the field).

The trace records both: `direction` is the decision, `cell` is the outcome.
Compare them.  If chosen > moved, the field is refusing moves.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

BASE = ["--steps", "60", "--every", "1", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
        "--energy", "5", "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--n", "1", "--seed", "1",
        "--income", "0", "--regrow", "0", "--policy", "random"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def analyse(r):
    frames = [f for f in r["frames"] if f["samples"][0]["alive"]]
    chosen = sum(1 for f in frames if f["samples"][0]["direction"] != 0)
    moved = 0
    for a, b in zip(frames, frames[1:]):
        if a["samples"][0]["cell"] != b["samples"][0]["cell"]:
            moved += 1
    n = len(frames) - 1
    return {"alive_frames": len(frames), "steps": n,
            "chosen": chosen, "moved": moved,
            "p_choose": round(chosen / n, 4), "p_move": round(moved / n, 4),
            "hash": r["hash"]}


def main():
    arms = {}
    for cost in (0.0, 0.2):
        r = run(["--move-cost", f"{cost:g}"])
        arms[f"move{cost:g}"] = analyse(r)
        print(f"move {cost:g}: {arms[f'move{cost:g}']}")

    exp = Experiment(
        experiment_id="nomad-two-thirds",
        question="Организм решает двигаться в 2/3 шагов или в 1/2? И совпадает ли решение с перемещением?",
        arithmetic={
            "draw": "Policy::Random draws from {-1, 0, +1}; if uniform, p_choose = 2/3",
            "p_move": "p_choose minus moves the field refuses",
            "death": "5 / (0.2 + move_cost*p_move) + 1",
        },
        arms={k: f"one organism, no food, move cost {k}" for k in arms},
        seed=1,
        command="python3 checks/exp41_nomad_two_thirds.py",
        parameters={"cells": 120, "n": 1, "steps": 60, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "field": "uniform", "income": 0, "regrow": 0,
                    "policy": "random"},
    )
    for key, a in arms.items():
        exp.add_arm(key, key.replace("_", " "), a, trace_hash=a.pop("hash"))

    pc = [a["p_choose"] for a in arms.values()]
    pm = [a["p_move"] for a in arms.values()]

    # Control 1 (fires): the choice is not 1/2 - a coin would give 0.5 and the
    # whole "nomad" reading would be wrong.
    exp.control("fires", all(abs(x - 0.5) > 0.05 for x in pc),
                f"p_choose {pc} vs coin 0.5")

    # Control 2 (silent): the field does not refuse moves here (1 organism,
    # 120 cells), so chosen and moved must agree on the same run.
    exp.control("silent", all(a["chosen"] == a["moved"] for a in arms.values()),
                f"chosen vs moved: {[(a['chosen'], a['moved']) for a in arms.values()]}")

    # Control 3 (specific): p_move sits near 2/3, not near 1/2.
    exp.control("specific", all(abs(x - 2 / 3) < 0.08 for x in pm),
                f"p_move {pm} vs 2/3 = 0.667")

    exp.limitation(
        "one organism, no food, one seed; 60 steps gives ~25 samples, so p_move is "
        "known to about +-0.05 and the 2/3 reading is consistent with, not proof of, "
        "a uniform three-way draw"
    )
    ok = all(abs(x - 0.5) > 0.05 for x in pc) and all(a["chosen"] == a["moved"] for a in arms.values()) \
        and all(abs(x - 2 / 3) < 0.08 for x in pm)
    exp.verdict("passed" if ok else "failed",
                "выбор направления не монетка: p_move около 2/3, поле ходы не отказывает")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
