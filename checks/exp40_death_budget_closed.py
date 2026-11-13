# -*- coding: utf-8 -*-
"""EXP-40: why the death step overshoots the energy budget.

EXP-39 settled the cost side: one step costs exactly
`maintenance + damage_rate*repair_cost = 0.2` when still, and `+ move_cost` on
the steps where the organism actually moves.  Damage is cleared every step, so
damage never kills.

The remaining puzzle from EXP-37: with energy 5 and no food the budget says
25 steps still, and 5/(0.2+0.2) = 12.5 steps at move cost 0.2.  Measured: 26 and
15.  The still case is off by +1, which is frame numbering (`advance` increments
`step` at the end, so death inside advance #k is first seen in frame k+1).  The
moving case is off by +2.5, and that cannot be numbering.

EXP-39 shows why: at move cost 0.2 the organism does NOT move every step.  The
drops are `[0.2, 0.2, 0.4, 0.4, 0.4, 0.4, 0.2, 0.2, 0.4, ...]` - it stands still
on some steps.  `Policy::Random` draws a direction, and a direction of 0 means
"stay", so the average cost is `0.2 + 0.2*p(move)` with `p(move) < 1`.

So the correct prediction is not `5/(0.2+move_cost)` but

    steps = 5 / (0.2 + move_cost * p_move)

with `p_move` measured from the trace itself.  That is the test: predict the
death step from the measured fraction of moving steps, and compare.

If this passes, the death model is closed: cost per step is exactly known, the
only unknown was how often the organism moves, and it is measurable.
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
    frames = r["frames"]
    alive = [f for f in frames if f["samples"][0]["alive"]]
    death_step = frames[-1]["step"] + 1 if len(alive) == len(frames) else \
        frames[len(alive)]["step"]
    moved = sum(1 for f in frames[:len(alive)] if f["samples"][0]["direction"] != 0)
    return death_step, moved, len(alive), r["hash"]


def main():
    arms = {}
    for cost in (0.0, 0.1, 0.2, 0.4):
        r = run(["--move-cost", f"{cost:g}"])
        death, moved, n_alive, h = analyse(r)
        p_move = moved / n_alive if n_alive else 0.0
        predicted = 5.0 / (0.2 + cost * p_move) + 1.0
        arms[f"move{cost:g}"] = {
            "death_step": death, "moved": moved, "alive_frames": n_alive,
            "p_move": round(p_move, 4), "predicted": round(predicted, 2),
            "error": round(death - predicted, 2), "hash": h,
        }
        print(f"move {cost:g}: death {death}, moved {moved}/{n_alive}, "
              f"p_move {p_move:.3f}, predicted {predicted:.2f}, err {death-predicted:+.2f}")

    exp = Experiment(
        experiment_id="death-budget-closed",
        question="Закрывается ли модель смерти, если учесть долю шагов, на которых организм движется?",
        arithmetic={
            "step_cost_still": "0.1 + 0.2*0.5 = 0.2",
            "step_cost_moving": "0.2 + move_cost",
            "mean_cost": "0.2 + move_cost * p_move",
            "death_step": "5 / mean_cost + 1 (frame numbering)",
        },
        arms={k: f"one organism, no food, move cost {k}" for k in arms},
        seed=1,
        command="python3 checks/exp40_death_budget_closed.py",
        parameters={"cells": 120, "n": 1, "steps": 60, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "field": "uniform", "income": 0, "regrow": 0,
                    "policy": "random"},
    )
    for key, a in arms.items():
        exp.add_arm(key, key.replace("_", " "), a, trace_hash=a.pop("hash"))

    errs = [abs(a["error"]) for a in arms.values()]
    pm = {k: a["p_move"] for k, a in arms.items()}

    # Control 1 (fires): still case reproduces EXP-37's 26 steps.
    exp.control("fires", arms["move0"]["death_step"] == 26,
                f"move 0: death {arms['move0']['death_step']}, EXP-37 measured 26")

    # Control 2 (silent): the organism does NOT move every step, so the naive
    # prediction 5/(0.2+move_cost) must be wrong for at least one cost.  If it
    # were right everywhere, p_move would be 1 and this experiment would be
    # empty.
    naive = {k: 5.0 / (0.2 + float(k[4:])) + 1.0 for k in arms}
    exp.control("silent", any(abs(arms[k]["death_step"] - naive[k]) > 1.0 for k in arms),
                f"naive prediction off by >1 step at "
                f"{[k for k in arms if abs(arms[k]['death_step'] - naive[k]) > 1.0]}")

    # Control 3 (specific): every cost predicted within 1 step.
    exp.control("specific", max(errs) <= 1.0,
                f"max |error| {max(errs):.2f} over costs 0/0.1/0.2/0.4; "
                f"p_move {pm}")

    exp.limitation(
        "one organism, no food, one seed; p_move is measured, not derived, so this "
        "closes the death budget but does not predict movement from the policy alone"
    )
    ok = arms["move0"]["death_step"] == 26 and max(errs) <= 1.0
    exp.verdict("passed" if ok else "failed",
                "модель смерти закрыта: шаг стоит 0.2 + move_cost*p_move, ошибка <= 1 шага")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
