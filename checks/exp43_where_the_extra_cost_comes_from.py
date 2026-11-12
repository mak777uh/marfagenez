# -*- coding: utf-8 -*-
"""EXP-43: where the 0.4 comes from on a step the organism did not choose.

EXP-42 put one organism on two cells and got drops of 0.2 AND 0.4 on steps where
the decision was "stay" and on steps where the move was refused.  That cannot be
the move cost: a still step has no move.

The trace records `damage`, and EXP-39 showed damage is 0.0 whenever energy is
plentiful.  The repair cost is `repair_cost * repaired`, and `repaired` is capped
by `damage`.  So the extra 0.2 must be repair - which means damage was NOT zero
on those steps.  Why?

`Organism::step` (core/src/organism.rs:157) does, in order:
  damage += damage_rate; repair if energy > 0; structure = 1 - damage; die if
  energy <= 0 or structure <= 0 or damage >= 1.

With damage_rate 0.2 and repair affordable, damage goes 0.2 -> cleared -> 0.2.
The repair of 0.2 units costs 0.2 * 0.5 = 0.1, not 0.2.  So a 0.4 drop is
`0.2 (maintenance) + 0.1 (repair) + 0.1 (?)`, or `0.2 + 0.2*0.5 + 0.1`.

Record `damage` and `energy` on every frame and read the drop against the damage
the organism carried INTO the step.  If drop = 0.2 + 0.5*damage_before, the cost
model is closed and EXP-42's "refused moves are paid" reading was wrong.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"

COMMON = ["--steps", "40", "--every", "1", "--capacity", "10",
          "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
          "--energy", "5", "--field", "uniform", "--seed", "1",
          "--income", "0", "--regrow", "0", "--policy", "random"]


def run(extra):
    out = subprocess.run([str(BIN)] + COMMON + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def table(r):
    frames = [f for f in r["frames"] if f["samples"][0]["alive"]]
    rows = []
    for a, b in zip(frames, frames[1:]):
        sa, sb = a["samples"][0], b["samples"][0]
        rows.append({
            "step": b["step"],
            "dir": sa["direction"],
            "moved": sa["cell"] != sb["cell"],
            "dmg_before": round(sa["damage"], 6),
            "dmg_after": round(sb["damage"], 6),
            "drop": round(sa["energy"] - sb["energy"], 6),
        })
    return rows


def main():
    arms = {}
    for cells in (2, 120):
        r = run(["--n", "1", "--cells", str(cells), "--move-cost", "0.2"])
        rows = table(r)
        arms[f"cells{cells}"] = rows
        print(f"cells {cells}:")
        for x in rows[:12]:
            print("  ", x)

    exp = Experiment(
        experiment_id="where-the-extra-cost-comes-from",
        question="Откуда берётся лишние 0.2 в шаге, если ход не оплачен движением?",
        arithmetic={
            "maintenance": "0.1",
            "repair": "repair_cost * damage_carried = 0.5 * damage_before",
            "predicted_drop": "0.1 + 0.5*damage_before + move_cost*moved",
        },
        arms={k: f"one organism, no food, {k}" for k in arms},
        seed=1,
        command="python3 checks/exp43_where_the_extra_cost_comes_from.py",
        parameters={"steps": 40, "capacity": 10, "damage_rate": 0.2,
                    "maintenance": 0.1, "repair_cost": 0.5, "energy": 5,
                    "field": "uniform", "income": 0, "regrow": 0,
                    "policy": "random", "move_cost": 0.2, "cells": "2 or 120"},
    )
    for key, rows in arms.items():
        exp.add_arm(key, key, {"rows": rows[:14], "n": len(rows)}, trace_hash=None)

    allrows = arms["cells2"] + arms["cells120"]
    pred = [round(0.1 + 0.5 * x["dmg_before"] + 0.2 * x["moved"], 6) for x in allrows]
    got = [x["drop"] for x in allrows]
    err = [round(g - p, 6) for g, p in zip(got, pred)]

    # Control 1 (fires): damage is not always zero - otherwise there is nothing
    # to explain and the model reduces to EXP-39.
    exp.control("fires", any(x["dmg_before"] > 1e-9 for x in allrows),
                f"damage before step: {sorted(set(x['dmg_before'] for x in allrows))}")

    # Control 2 (silent): on a step with no damage carried and no move, the drop
    # is exactly the maintenance cost.
    clean = [x["drop"] for x in allrows if x["dmg_before"] < 1e-9 and not x["moved"]]
    exp.control("silent", all(abs(d - 0.1) < 1e-9 for d in clean),
                f"no damage, no move: drops {sorted(set(clean))}, maintenance 0.1")

    # Control 3 (specific): the formula holds on every step.
    exp.control("specific", max(abs(e) for e in err) < 1e-9,
                f"max |drop - (0.1 + 0.5*damage + 0.2*moved)| = "
                f"{max(abs(e) for e in err):.2e} over {len(allrows)} steps")

    exp.limitation(
        "one organism, no food; the formula is fitted to the recorded damage, so it "
        "describes the cost given the damage, not why damage appears"
    )
    ok = max(abs(e) for e in err) < 1e-9
    exp.verdict("passed" if ok else "failed",
                "цена шага = 0.1 + 0.5*урон + 0.2*ход; лишнее — это ремонт, а не оплата отказа")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
