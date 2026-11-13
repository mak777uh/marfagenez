# -*- coding: utf-8 -*-
"""EXP-38: exact death budget, and whether the crossing is that budget.

EXP-37 measured death steps with no food: stay dies at 26 (arithmetic said 25),
random dies at 22/18/15 for move cost 0.05/0.1211/0.2 (arithmetic said
20.0/15.6/12.5).  The measured values are consistently ~2-3 steps LATER than
5/(0.2+move_cost), and the error grows with move cost, so it is not a fixed
off-by-one.

The off-by-one is visible from the code.  `trace` records a frame every step
starting at step 1, and `advance` increments `self.step` at the END, so a death
noticed in `advance` number k appears in the frame numbered k+1.  That accounts
for +1, not +2.5.

The rest is the damage cap: `damage = (damage + damage_rate).min(1.0)`, and
death is `damage >= 1.0`.  With damage_rate 0.2 an organism reaches damage 1.0
on the 5th step, before its energy runs out, so the energy budget is not the
binding constraint at all - damage is.  Repair is paid out of energy, so the
two interact, but the death step is set by whichever runs out first.

Measure the actual energy and damage trajectories instead of guessing the
formula.  A model that matches the trajectory at one move cost and predicts the
others is worth more than a model that matches a single number.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

LONE = ["--steps", "60", "--every", "1", "--cells", "120", "--capacity", "10",
        "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
        "--energy", "5", "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--n", "1", "--seed", "1",
        "--income", "0", "--regrow", "0"]


def run(extra):
    out = subprocess.run([str(BIN)] + LONE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def trajectory(r):
    out = []
    for f in r["frames"]:
        s = f["samples"][0]
        out.append((f["step"], round(s["energy"], 4), round(s["damage"], 4),
                    s["alive"]))
    return out


def main():
    arms = {}
    for cost in (0.0, 0.2):
        key = f"random_move{cost:g}"
        r = run(["--policy", "random", "--move-cost", f"{cost:g}"])
        arms[key] = (trajectory(r), r["hash"])
        print(key, arms[key][0][:8])

    exp = Experiment(
        experiment_id="death-budget-exact",
        question="Какая величина на самом деле заканчивается первой — энергия или структура?",
        arithmetic={
            "damage_cap": "damage = min(damage + 0.2, 1.0), death at damage >= 1.0",
            "damage_only": "5 steps to death if nothing is repaired",
            "repair": "repaired = min(energy/0.5, damage), costs 0.5 per unit",
            "energy_only": "5/(0.1 + 0.1) = 25 steps if damage were ignored",
        },
        arms={k: k.replace("_", " ") for k in arms},
        seed=1,
        command="python3 checks/exp38_death_budget_exact.py",
        parameters={"cells": 120, "n": 1, "steps": 60, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "field": "uniform", "income": 0, "regrow": 0},
    )

    for key, (traj, h) in arms.items():
        death = next((s for s, e, d, a in traj if not a), None)
        exp.add_arm(key, key.replace("_", " "),
                    {"death_step": death,
                     "energy_at_step1": traj[0][1],
                     "damage_at_step1": traj[0][2]}, trace_hash=h)

    t = arms["random_move0"][0]
    # Control 1 (fires): damage is the thing that reaches its limit, not energy.
    death = next(s for s, e, d, a in t if not a)
    last_alive = next((s, e, d) for s, e, d, a in reversed(t) if a)
    exp.control("fires", last_alive[2] >= 0.8 and last_alive[1] > 0.0,
                f"last living frame: step {last_alive[0]}, energy "
                f"{last_alive[1]}, damage {last_alive[2]}")

    # Control 2 (silent): with no food and no movement the trajectory must be
    # deterministic and identical to the `stay` arm measured in EXP-37 (26).
    exp.control("silent", death == 26,
                f"random with move cost 0 never moves, so it must die at the "
                f"same step as stay: {death} vs 26")

    # Control 3 (specific): the model must predict the SECOND move cost from the
    # first.  Take the per-step energy change measured at move cost 0 and use it
    # to predict the death step at 0.2; a wrong mechanism will not transfer.
    e0 = t[0][1]
    e1 = t[1][1]
    per_step = e0 - e1
    predicted = round(e0 / (per_step + 0.2))
    actual = next(s for s, e, d, a in arms["random_move0.2"][0] if not a)
    exp.control("specific", abs(predicted - actual) <= 1,
                f"from step-1 drop {per_step:.3f} at move cost 0, predicted death "
                f"at move cost 0.2 = {predicted}, measured {actual}")

    exp.limitation(
        "one organism, no food; the crossing in a fed field is set by competition "
        "and is not measured here"
    )
    ok = last_alive[2] >= 0.8 and death == 26 and abs(predicted - actual) <= 1
    exp.verdict("passed" if ok else "failed",
                "первой заканчивается структура, а не энергия")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
