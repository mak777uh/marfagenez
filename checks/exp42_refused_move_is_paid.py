# -*- coding: utf-8 -*-
"""EXP-42: the decision and the move disagree at the edge of the field.

EXP-41 found that on both arms `chosen > moved` by exactly 1: 15 chosen, 14
moved; 9 chosen, 8 moved.  So the field refused one move per run.

Reading `core/src/life.rs:423`:

    if direction != 0 && r.organism.spend(r.move_cost) {
        let nc = r.cell as i64 + direction as i64;
        if nc >= 0 && (nc as usize) < cells { r.cell = nc as usize; }
    }

The move cost is paid BEFORE the bounds check.  An organism at cell 0 that
chooses -1 pays `move_cost` and stays put.  With one organism on 120 cells and
about 15 moves per run, the chance of ever standing at an edge is small, so one
refusal per run is about right - but "about right" is not a measurement.

Test: put the organism at the edge explicitly and see whether it pays for a move
it does not make.  Two ways to force it:

  * `--n 2 --cells 2` - both cells are edges, every move is refused;
  * `--n 1 --cells 2` - same, with one organism.

If the cost is charged for a refused move, the energy falls by
`0.2 + move_cost` on steps where the cell does not change.  If the cost is not
charged, the energy falls by 0.2 only.  The trace has both numbers: `cell` and
`energy`.
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


def classify(r, move_cost):
    """Split steps into (chose a move, cell changed, energy drop)."""
    frames = [f for f in r["frames"] if f["samples"][0]["alive"]]
    refused, taken, still = [], [], []
    for a, b in zip(frames, frames[1:]):
        sa, sb = a["samples"][0], b["samples"][0]
        drop = round(sa["energy"] - sb["energy"], 6)
        if sa["direction"] == 0:
            still.append(drop)
        elif sa["cell"] == sb["cell"]:
            refused.append(drop)
        else:
            taken.append(drop)
    return {"refused_drops": sorted(set(refused)), "taken_drops": sorted(set(taken)),
            "still_drops": sorted(set(still)),
            "n_refused": len(refused), "n_taken": len(taken), "n_still": len(still)}


def main():
    arms = {}
    # two cells: every cell is an edge
    for cost in (0.0, 0.2):
        r = run(["--n", "1", "--cells", "2", "--move-cost", f"{cost:g}"])
        c = classify(r, cost)
        arms[f"edge{cost:g}"] = c
        print(f"edge, move {cost:g}: {c}")
    # 120 cells: edges are rare
    r = run(["--n", "1", "--cells", "120", "--move-cost", "0.2"])
    arms["wide0.2"] = classify(r, 0.2)
    print(f"wide, move 0.2: {arms['wide0.2']}")

    exp = Experiment(
        experiment_id="refused-move-is-paid",
        question="Платит ли организм за ход, который поле не дало сделать?",
        arithmetic={
            "step_still": "0.1 + 0.2*0.5 = 0.2",
            "step_moved": "0.2 + move_cost",
            "refused_move": "if charged: 0.2 + move_cost; if not: 0.2",
        },
        arms={k: f"one organism, no food, {k}" for k in arms},
        seed=1,
        command="python3 checks/exp42_refused_move_is_paid.py",
        parameters={"steps": 40, "capacity": 10, "damage_rate": 0.2,
                    "maintenance": 0.1, "repair_cost": 0.5, "energy": 5,
                    "field": "uniform", "income": 0, "regrow": 0,
                    "policy": "random", "cells": "2 or 120"},
    )
    for key, a in arms.items():
        exp.add_arm(key, key, a, trace_hash=None)

    edge = arms["edge0.2"]

    # Control 1 (fires): on two cells the organism really does try moves that
    # the field refuses - otherwise the question is not being asked.
    exp.control("fires", edge["n_refused"] > 0,
                f"two cells, move 0.2: {edge['n_refused']} refused moves out of "
                f"{edge['n_refused'] + edge['n_taken']}")

    # Control 2 (silent): a still step always costs 0.2, whatever the field.
    exp.control("silent", edge["still_drops"] in ([], [0.2]),
                f"still drops on two cells: {edge['still_drops']}")

    # Control 3 (specific): a refused move costs the same as a taken one.
    exp.control("specific", edge["refused_drops"] == edge["taken_drops"] == [0.4],
                f"refused {edge['refused_drops']} vs taken {edge['taken_drops']}")

    exp.limitation(
        "two cells is the extreme case; the wide-field arm only shows that refusals "
        "are rare there, not that they are absent"
    )
    ok = edge["n_refused"] > 0 and edge["refused_drops"] == edge["taken_drops"] == [0.4]
    exp.verdict("passed" if ok else "failed",
                "отказанный ход оплачивается как сделанный: цена платится до проверки границы")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
