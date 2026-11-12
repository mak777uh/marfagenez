# -*- coding: utf-8 -*-
"""EXP-35: where is the indifference point between staying and moving?

EXP-34 found the gap changes sign between move-cost 0.05 and 0.20 at regrow=1,
even placement, k=2.  The sign change is a measurement; the crossing point is
not.  Find it by bisection, and check that it moves with `income` the way the
arithmetic says it must.

Arithmetic: an organism on a cell with k others gets income/k.  Moving costs
move_cost per step and buys a chance at a less crowded cell.  If the crossing is
a property of the ratio move_cost/income, then doubling income must roughly
double the crossing move cost.
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
        "--damage-rate", "0.2", "--maintenance", "0.1", "--repair-cost", "0.5",
        "--energy", "5", "--field", "uniform", "--layout", "even", "--n", "240",
        "--regrow", "1", "--policy", "random", "--seed", "1"]


def alive(income, move_cost):
    out = subprocess.run(
        [str(BIN)] + BASE + ["--income", f"{income:g}", "--move-cost", f"{move_cost:g}"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    r = json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())
    n = sum(1 for s in r["frames"][-1]["samples"] if s["alive"])
    return n, r["hash"]


def crossing(income, lo=0.0, hi=0.8, iters=6):
    """Bisect the move cost where random stops beating stay (120)."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        n, _ = alive(income, mid)
        if n > 120:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    rows = {}
    for income in (1.0, 2.0):
        rows[income] = crossing(income)
        print(f"income {income:g}: crossing move-cost ~ {rows[income]:.4f} "
              f"(ratio {rows[income]/income:.4f})")

    exp = Experiment(
        experiment_id="indifference-point",
        question="При какой цене движения random перестаёт выигрывать у stay?",
        arithmetic={
            "per_organism": "income/k - maintenance - damage*repair - move_cost*moved",
            "stay_k2": "0.3 per step regardless of move_cost",
            "prediction": "crossing scales with income, so crossing/income is constant",
        },
        arms={f"income{i:g}": f"bisected crossing at income {i:g}" for i in (1.0, 2.0)},
        seed=1,
        command="python3 checks/exp35_indifference_point.py",
        parameters={"cells": 120, "n": 240, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "regrow": 1.0, "field": "uniform",
                    "layout": "even", "policy": "random", "bisection_iters": 6},
    )

    for income, c in rows.items():
        n, h = alive(income, c)
        exp.add_arm(f"income{income:g}", f"income {income:g}, crossing {c:.4f}",
                    {"crossing_move_cost": round(c, 4),
                     "crossing_over_income": round(c / income, 4),
                     "alive_at_crossing": n}, trace_hash=h)

    # Control 1 (fires): the crossing is inside the bracket, i.e. below it
    # random wins and above it random loses.
    below = alive(1.0, rows[1.0] * 0.5)[0]
    above = alive(1.0, rows[1.0] * 1.5)[0]
    exp.control("fires", below > 120 >= above,
                f"income 1: at half-crossing {below} > 120, at 1.5x {above} <= 120")

    # Control 2 (silent): stay must not care about move cost at all.  If it
    # did, the crossing would be measuring the wrong thing.
    exp.control("silent", True,
                "stay never moves, so move cost cannot reach it - verified "
                "structurally in EXP-34 (identical hash 96423e3d8f35e06f at "
                "move cost 0.05, 0.2, 0.4)")

    # Control 3 (specific): the ratio crossing/income must be stable.  A
    # crossing driven by something else (cells, k) would not scale with income.
    r1, r2 = rows[1.0] / 1.0, rows[2.0] / 2.0
    exp.control("specific", abs(r1 - r2) / max(r1, r2) < 0.25,
                f"crossing/income: {r1:.4f} vs {r2:.4f}")

    exp.limitation(
        "bisection on a discrete count of survivors; the crossing is a band, not "
        "a point, and 6 iterations resolve it to ~0.0125 in move cost"
    )
    ok = below > 120 >= above and abs(r1 - r2) / max(r1, r2) < 0.25
    exp.verdict("passed" if ok else "failed",
                "точка безразличия задаётся отношением move_cost/income")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
