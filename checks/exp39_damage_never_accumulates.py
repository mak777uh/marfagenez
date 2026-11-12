# -*- coding: utf-8 -*-
"""EXP-39: damage never accumulates - repair is always affordable.

EXP-37 and EXP-38 both failed, and both failed in the same direction: the
measured death step was LATER than the energy budget predicted, and the gap grew
with move cost.  EXP-38 also showed `damage` is 0.0 in every recorded frame,
right up to the step of death.

That is not an artifact of the readout.  Reading `core/src/organism.rs:157`:

    damage = min(damage + damage_rate, 1.0)          # +0.2
    affordable = energy / repair_cost                 # energy / 0.5
    repaired = min(affordable, damage)
    energy -= repaired * repair_cost

`affordable` is `energy/0.5`, which is at least 2 while energy is at least 1.
`repaired` is capped by `damage`, which is at most 1.  So repair is ALWAYS
affordable, and damage is fully cleared every step.  `damage_rate` and
`repair_cost` therefore act as a fixed per-step energy cost of
`damage_rate * repair_cost`, and `damage` never becomes a cause of death.

The consequence: death is purely `energy <= 0`, and the per-step cost is

    maintenance + damage_rate*repair_cost + move_cost*moved

With energy 5 and no food: 5/0.2 = 25 steps if still, and 5/(0.2+move_cost) if
moving.  EXP-37 measured 26 and 22/18/15.  The still case is off by one (frame
numbering), but the moving cases are off by +2, +2.4, +2.5 - and the error grows
with move cost, which the frame-numbering explanation cannot produce.

Measure the energy trajectory directly.  If the per-step drop is exactly
`0.2 + move_cost`, the arithmetic is right and the death step is a bookkeeping
question.  If the drop is smaller, something is giving energy back.
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
        "--energy", "5", "--field", "uniform", "--n", "1", "--seed", "1",
        "--income", "0", "--regrow", "0"]


def run(extra):
    out = subprocess.run([str(BIN)] + LONE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def drops(r):
    """Per-step energy drops while alive."""
    es = [(f["step"], f["samples"][0]["energy"], f["samples"][0]["alive"])
          for f in r["frames"]]
    alive = [e for _, e, a in es if a]
    return [round(alive[i] - alive[i + 1], 6) for i in range(len(alive) - 1)]


def main():
    arms = {}
    for cost in (0.0, 0.2):
        r = run(["--policy", "random", "--move-cost", f"{cost:g}"])
        d = drops(r)
        arms[f"move{cost:g}"] = (d, r["hash"])
        print(f"move {cost:g}: drops {d}")

    exp = Experiment(
        experiment_id="damage-never-accumulates",
        question="Почему смерть наступает позже бюджета энергии?",
        arithmetic={
            "affordable": "energy/repair_cost >= 2 while energy >= 1",
            "repaired": "min(affordable, damage) = damage, always",
            "consequence": "damage is cleared every step; death is energy only",
            "step_cost": "maintenance + damage_rate*repair_cost = 0.1 + 0.1 = 0.2",
        },
        arms={k: f"one organism, no food, move cost {k}" for k in arms},
        seed=1,
        command="python3 checks/exp39_damage_never_accumulates.py",
        parameters={"cells": 120, "n": 1, "steps": 60, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "field": "uniform", "income": 0, "regrow": 0},
    )

    for key, (d, h) in arms.items():
        exp.add_arm(key, key.replace("_", " "),
                    {"drops": d[:6], "distinct_drops": sorted(set(d))},
                    trace_hash=h)

    still = arms["move0"][0]
    moving = arms["move0.2"][0]

    # Control 1 (fires): standing still costs exactly 0.2 per step.
    exp.control("fires", all(abs(x - 0.2) < 1e-9 for x in still),
                f"move 0: distinct drops {sorted(set(still))}, arithmetic 0.2")

    # Control 2 (silent): damage must be zero throughout, so it cannot be the
    # cause of death.  If a drop ever exceeds 0.2 the repair story is wrong.
    exp.control("silent", all(x <= 0.2 + 1e-9 for x in still),
                f"no step costs more than maintenance+repair: max {max(still)}")

    # Control 3 (specific): moving must cost exactly 0.2 + move_cost on the
    # steps where the organism moves, and 0.2 where it does not.  A single
    # average would hide this; the set of distinct drops must be {0.2, 0.4}.
    distinct = sorted(set(moving))
    exp.control("specific", distinct == [0.2, 0.4],
                f"move 0.2: distinct drops {distinct}, expected [0.2, 0.4]")

    exp.limitation(
        "one organism, no food; with food the same per-step cost applies but the "
        "organism can outlive the budget, so this says nothing about a fed field"
    )
    ok = (all(abs(x - 0.2) < 1e-9 for x in still)
          and all(x <= 0.2 + 1e-9 for x in still)
          and sorted(set(moving)) == [0.2, 0.4])
    exp.verdict("passed" if ok else "failed",
                "урон не накапливается: ремонт всегда по карману, смерть — только энергия")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
