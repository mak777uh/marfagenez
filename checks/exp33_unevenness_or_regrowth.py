# -*- coding: utf-8 -*-
"""EXP-33: is the advantage of `random` unevenness, or movement itself?

EXP-31: random placement, `stay` 72 vs `random` 108.
EXP-32: even placement, `stay` 120 vs `random` 132 at k=2.

Both times `random` won.  The explanation offered for EXP-31 was "random
placement is uneven, and movement smooths it".  But EXP-32 has NO unevenness -
every cell starts with exactly two - and `random` still won by 12.

So either the explanation is wrong, or movement does something else.  The
candidate: an organism that moves leaves its cell and eats somewhere else, so
the cell it left gets a step of regrowth.  Standing still means eating the same
cell every step, and the cell never recovers.

Test: make regrowth fast.  If the advantage is "leave the cell alone so it
recovers", then at high `regrow` standing still should stop being a loss and
`random` should stop winning.
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
        "--damage-rate", "0.2", "--income", "1", "--maintenance", "0.1",
        "--repair-cost", "0.5", "--move-cost", "0.05", "--energy", "5",
        "--field", "uniform", "--rich", "2.0", "--poor", "0.2", "--layout", "even", "--n", "240"]


def run(extra):
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    return json.loads((ROOT / line.split("written:", 1)[1].strip()).read_text())


def stats(r):
    alive = [s for s in r["frames"][-1]["samples"] if s["alive"]]
    n = len(alive)
    return n, round(sum(s["energy"] for s in alive) / max(n, 1), 3), r["hash"]


def main():
    arms = {}
    for regrow in (0.2, 0.5, 0.9):
        for policy in ("stay", "random"):
            key = f"{policy}_regrow{regrow:g}"
            arms[key] = stats(run(["--policy", policy, "--regrow", f"{regrow:g}",
                                   "--seed", "1"]))
    for key, v in arms.items():
        print(key, v)

    exp = Experiment(
        experiment_id="unevenness-or-regrowth",
        question="Почему random выигрывает в однородном поле при равной раскладке?",
        arithmetic={
            "steady_state": "cell value settles where regrow*(ceil - c) = taken",
            "taken": "min(income, cell) per organism on the cell",
            "prediction": "if the gain is 'leaving the cell to recover', then a "
                          "fast regrow makes the gap vanish",
        },
        arms={f"{p}_regrow{r:g}": f"even k=2, regrow={r:g}, {p}"
              for r in (0.2, 0.5, 0.9) for p in ("stay", "random")},
        seed=1,
        command="python3 checks/exp33_unevenness_or_regrowth.py",
        parameters={"cells": 120, "n": 240, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "income": 1, "maintenance": 0.1,
                    "repair_cost": 0.5, "move_cost": 0.05, "energy": 5,
                    "field": "uniform", "layout": "even"},
    )

    for key, (n, mean, h) in arms.items():
        exp.add_arm(key, key.replace("_", " "), {"alive": n, "mean_energy": mean},
                    trace_hash=h)

    gap_low = arms["random_regrow0.2"][0] - arms["stay_regrow0.2"][0]
    gap_mid = arms["random_regrow0.5"][0] - arms["stay_regrow0.5"][0]
    gap_high = arms["random_regrow0.9"][0] - arms["stay_regrow0.9"][0]

    # Control 1 (fires): the effect exists at the baseline regrow.
    exp.control("fires", gap_low > 0,
                f"regrow 0.2: random {arms['random_regrow0.2'][0]} > "
                f"stay {arms['stay_regrow0.2'][0]}")

    # Control 2 (silent): at fast regrow the cell is refilled almost completely
    # every step, so leaving it buys nothing.  The gap must close.
    exp.control("silent", gap_high <= 0,
                f"regrow 0.9: gap {gap_high}")

    # Control 3 (specific): the gap must fall monotonically in regrow.  A
    # different cause (movement cost, say) would not care about regrow at all.
    exp.control("specific", gap_low > gap_mid > gap_high,
                f"gap by regrow: 0.2:{gap_low} > 0.5:{gap_mid} > 0.9:{gap_high}")

    exp.limitation(
        "one seed; `regrow` also changes the cell's steady-state level, so the "
        "gap could shrink because both arms get richer rather than because "
        "leaving a cell stopped mattering"
    )
    exp.verdict(
        "passed" if (gap_low > 0 and gap_high <= 0 and gap_low > gap_mid > gap_high)
        else "failed",
        "преимущество движения — уход с клетки, а не сама скорость",
    )
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
