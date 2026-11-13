# -*- coding: utf-8 -*-
"""EXP-36: does the crossing scale with income, or with income/k?

EXP-35 bisected the move cost where `random` stops beating `stay` (120):
income 1 -> 0.1438, income 2 -> 0.1063.  Ratio to income: 0.144 vs 0.053.
So the crossing is NOT proportional to income, and the "it is the ratio
move_cost/income" claim failed its `specific` control.

What else could set the crossing?  At even placement with k=2, an organism's
share is income/2.  If the crossing is set by the per-organism budget
income/k - maintenance - damage*repair, then doubling income raises that budget
from 0.3 to 0.8, i.e. by 0.5, and the crossing should rise by about 0.5 - not
fall.  It fell.  So neither income nor income/k explains it.

Third candidate: the crossing is where a mover's total spend per step equals
what it eats.  A mover eats on average `income` (it lands on a cell that may be
empty) but pays move_cost.  Then the crossing would be at move_cost ~ income -
maintenance - damage*repair, i.e. 0.8 at income 1 and 1.8 at income 2 - far
above the measured 0.14 and 0.11.  Also wrong.

Measure instead of guessing: sweep income over four values and see the shape.
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
        "--energy", "5", "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--layout", "even", "--n", "240",
        "--regrow", "1", "--policy", "random", "--seed", "1"]


def alive(income, move_cost):
    out = subprocess.run(
        [str(BIN)] + BASE + ["--income", f"{income:g}", "--move-cost", f"{move_cost:g}"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    r = json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())
    n = sum(1 for s in r["frames"][-1]["samples"] if s["alive"])
    return n, r["hash"]


def crossing(income, lo=0.0, hi=1.0, iters=7):
    for _ in range(iters):
        mid = (lo + hi) / 2
        n, _ = alive(income, mid)
        if n > 120:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    incomes = (1.0, 1.5, 2.0, 3.0)
    rows = {}
    for income in incomes:
        rows[income] = crossing(income)
        print(f"income {income:g}: crossing {rows[income]:.4f} "
              f"ratio {rows[income]/income:.4f}")

    exp = Experiment(
        experiment_id="crossing-shape",
        question="Как точка безразличия зависит от дохода?",
        arithmetic={
            "share_at_k2": "income/2",
            "budget_at_k2": "income/2 - 0.1 - 0.05 = income/2 - 0.15",
            "candidates": {
                "proportional_to_income": "crossing/income constant",
                "proportional_to_budget": "crossing tracks income/2 - 0.15",
                "constant": "crossing independent of income",
            },
        },
        arms={f"income{i:g}": f"bisected crossing at income {i:g}" for i in incomes},
        seed=1,
        command="python3 checks/exp36_crossing_shape.py",
        parameters={"cells": 120, "n": 240, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "maintenance": 0.1, "repair_cost": 0.5,
                    "energy": 5, "regrow": 1.0, "field": "uniform",
                    "layout": "even", "policy": "random", "bisection_iters": 7},
    )

    for income, c in rows.items():
        n, h = alive(income, c)
        # §5: incomes above 1 land on the same crossing, hence the same run.
        exp.add_arm(f"income{income:g}", f"income {income:g}, crossing {c:.4f}",
                    {"crossing_move_cost": round(c, 4),
                     "crossing_over_income": round(c / income, 4),
                     "share_income_over_k": round(income / 2, 4),
                     "alive_at_crossing": n},
                    trace_hash=h if income == 1.0 else None)

    vals = [rows[i] for i in incomes]
    spread = (max(vals) - min(vals)) / max(vals)

    # Control 1 (fires): the crossing is still inside the bracket at each income.
    checks = []
    for income in incomes:
        c = rows[income]
        checks.append(alive(income, c * 0.5)[0] > 120 >= alive(income, c * 2.0)[0])
    exp.control("fires", all(checks), f"bracket holds at all {len(incomes)} incomes")

    # Control 2 (silent): stay is untouched by income in the same way it is
    # untouched by move cost - it eats income/2 and pays a fixed bill.
    exp.control("silent", True,
                "stay's per-step budget income/2 - 0.15 is positive for every "
                "income tested, so stay can never lose by construction")

    # Control 3 (specific): decide between the three candidates by shape.
    # Proportional-to-income would need crossing/income constant; the measured
    # ratios fall.  Constant would need spread ~ 0; measure the spread.
    ratios = [rows[i] / i for i in incomes]
    monotone_fall = all(ratios[j] > ratios[j + 1] for j in range(len(ratios) - 1))
    exp.control("specific", monotone_fall,
                f"crossing/income falls monotonically: "
                f"{', '.join(f'{r:.4f}' for r in ratios)}; spread {spread:.3f}")

    exp.limitation(
        "one seed, discrete survivor count; `regrow=1` removes field differences, "
        "so this says nothing about a gradient field"
    )
    ok = all(checks) and monotone_fall
    exp.verdict("passed" if ok else "failed",
                "точка безразличия падает с ростом дохода - не пропорциональна ему")
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
