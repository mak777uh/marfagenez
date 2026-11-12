# -*- coding: utf-8 -*-
"""EXP-34: is the advantage of `random` over `stay` unevenness, or regrowth?

EXP-31: random placement, stay 72 vs random 108.
EXP-32: even placement k=2, stay 120 vs random 132.

EXP-33 asked whether the gain is "leaving the cell so it recovers", by varying
`regrow`.  It FAILED, and for a reason worth keeping: raising `regrow` helps
`stay` far more than `random` (stay stays at 120, random goes 43 -> 133), so the
gap goes -77 -> -19 -> +13.  That is not the predicted shape, and the `fires`
control failed too, which means the baseline itself did not reproduce.

So the question is reopened with the baseline fixed.  The difference between
this run and EXP-32's setup is `regrow`: EXP-32 used the default, which is 1.0.
At regrow 1.0 the cell is refilled completely every step, so the cell state is
irrelevant and only the per-organism cost matters.

Test: at regrow 1.0, vary `move_cost`.  If `random` wins because it smooths
unevenness, the win must survive a high move cost.  If `random` wins because
moving is cheap, the win must vanish when moving gets expensive.
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
        "--repair-cost", "0.5", "--energy", "5", "--field", "uniform",
        "--layout", "even", "--n", "240", "--regrow", "1"]


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
    costs = (0.05, 0.2, 0.4)
    arms = {}
    for cost in costs:
        for policy in ("stay", "random"):
            key = f"{policy}_move{cost:g}"
            arms[key] = stats(run(["--policy", policy, "--move-cost", f"{cost:g}",
                                   "--seed", "1"]))
    for key, v in arms.items():
        print(key, v)

    exp = Experiment(
        experiment_id="unevenness-or-move-cost",
        question="Почему random выигрывает у stay при равной раскладке и regrow=1?",
        arithmetic={
            "per_organism": "income/k - maintenance - damage*repair - move_cost*moved",
            "k2_stay": "1/2 - 0.1 - 0.1 = 0.3 per step",
            "k2_random": "0.3 - 0.05*moved_fraction",
            "prediction": "if the win is unevenness-smoothing, it survives high "
                          "move cost; if it is cheap movement, it dies",
        },
        arms={f"{p}_move{c:g}": f"even k=2, regrow=1, move-cost={c:g}, {p}"
              for c in costs for p in ("stay", "random")},
        seed=1,
        command="python3 checks/exp34_unevenness_or_move_cost.py",
        parameters={"cells": 120, "n": 240, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "income": 1, "maintenance": 0.1,
                    "repair_cost": 0.5, "energy": 5, "regrow": 1.0,
                    "field": "uniform", "layout": "even"},
    )

    # `stay` never moves, so move cost cannot reach it: all three stay arms are
    # one arm (§5).  Record it once, without a hash, and say so.
    stay_hash = arms["stay_move0.05"][2]
    exp.add_arm("stay", "even k=2, regrow=1, stay (move cost is not used)",
                {"alive": arms["stay_move0.05"][0],
                 "mean_energy": arms["stay_move0.05"][1]}, trace_hash=None)
    for c in costs:
        n, mean, h = arms[f"random_move{c:g}"]
        exp.add_arm(f"random_move{c:g}", f"even k=2, regrow=1, move-cost={c:g}, random",
                    {"alive": n, "mean_energy": mean}, trace_hash=h)

    gap = {c: arms[f"random_move{c:g}"][0] - arms[f"stay_move{c:g}"][0] for c in costs}

    # Control 1 (fires): the baseline reproduces EXP-32 (stay 120, random 132).
    exp.control("fires", arms["stay_move0.05"][0] == 120 and gap[0.05] > 0,
                f"move 0.05: stay {arms['stay_move0.05'][0]}, "
                f"random {arms['random_move0.05'][0]} (EXP-32: 120, 132)")

    # Control 2 (silent): at the highest cost a mover must eat more than it
    # gains.  Expected: the gap closes or inverts.
    exp.control("silent", gap[0.4] <= 0, f"move 0.4: gap {gap[0.4]}")

    # Control 3 (specific): the gap must fall monotonically in move cost.  A
    # cause unrelated to movement cost would not care.
    exp.control("specific", gap[0.05] > gap[0.2] > gap[0.4],
                f"gap by move cost: 0.05:{gap[0.05]} > 0.2:{gap[0.2]} > 0.4:{gap[0.4]}")

    exp.limitation(
        "one seed; `stay` is identical at every move cost by construction (it "
        "never moves), so the monotonicity control is really a statement about "
        "`random` alone"
    )
    ok = arms["stay_move0.05"][0] == 120 and gap[0.05] > 0 and gap[0.4] <= 0 \
        and gap[0.05] > gap[0.2] > gap[0.4]
    exp.verdict("passed" if ok else "failed",
                "выигрыш random — плата за движение, а не размывание неравномерности")
    print("saved:", exp.save())
    print("stay hash (one arm):", stay_hash)


if __name__ == "__main__":
    main()
