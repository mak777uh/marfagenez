# -*- coding: utf-8 -*-
"""EXP-31: in a uniform field, does moving help or hurt?

The field is uniform, so every cell is the same.  Any movement is pure cost
(`move-cost` per step).  So the prediction is: `stay` is best, and every
policy that moves is worse.

But a measurement showed the opposite: `random` keeps 108 organisms where
`stay` keeps 72 (n=120, seed 1).  That is a real anomaly, not a rounding
artefact.

Hypothesis: `stay` is not free.  An organism that never moves sits on a cell
whose capacity is consumed by whoever is there.  If two organisms share a cell,
both pay `damage-rate` on the same cell and both pay `repair-cost`, so the cell
is repaired twice per step while the income is still one.  Moving spreads them
over more cells, so each cell is repaired once.

If that is right, the deficit of `stay` must shrink as the start gets sparser.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checks.experiment import Experiment  # noqa: E402

BIN = ROOT / "core/target/release/trace"
TAG = "EXP-31"

# The two levels `--field uniform` averages. Written as constants so the
# regime arithmetic below uses the same numbers the command line does.
RICH = 2.0
POOR = 0.2

BASE = ["--steps", "1200", "--every", "1200", "--cells", "120",
        "--capacity", "10", "--damage-rate", "0.2", "--income", "1",
        "--maintenance", "0.1", "--repair-cost", "0.5", "--move-cost", "0.05",
        "--energy", "5", "--field", "uniform", "--rich", str(RICH),
        "--poor", str(POOR)]


def run(extra):
    # `sighted` with a read budget of zero cannot see: `best > here` is never
    # true and the policy silently becomes `stay`. The binary refuses that now,
    # so the budget has to be given here.
    extra = list(extra)
    if "sighted" in extra:
        extra += ["--read-budget", "3"]
    out = subprocess.run([str(BIN)] + BASE + extra, cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if "written:" in l][0]
    rel = line.split("written:", 1)[1].strip()
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def alive_of(r):
    return [s for s in r["frames"][-1]["samples"] if s["alive"]]


def main():
    # The level and the regime, written down rather than assumed.
    # `--field uniform` builds every cell at (rich + poor) / 2 = M.
    M = (RICH + POOR) / 2.0
    REGROW = 0.8
    INCOME = 1.0
    # An occupied cell is taken to zero whenever income >= M*r, and then it can
    # only regrow from 0, so it settles at M*r. A cell vacated one step ago
    # holds that value plus one regrowth toward M.
    starved = M * REGROW
    vacated = starved + (M - starved) * REGROW
    regime = "starved" if INCOME >= starved else "saturated"
    print(f"M={M} regrow={REGROW} income={INCOME} -> M*r={starved:.4f} "
          f"{vacated=:.4f} regime={regime}")

    arms = {}
    for n in (120, 60, 30):
        for policy in ("stay", "random", "sighted"):
            r = run(["--n", str(n), "--policy", policy, "--seed", "1"])
            alive = alive_of(r)
            arms[f"{policy}_n{n}"] = {
                "alive": len(alive),
                "moved": sum(1 for s in alive if s["direction"] != 0),
                "mean_energy": round(sum(s["energy"] for s in alive) / max(len(alive), 1), 3),
                "hash": r["hash"],
            }

    for k, v in arms.items():
        print(k, v)

    exp = Experiment(
        experiment_id="moving-in-uniform-field",
        question="В однородном поле движение помогает или мешает?",
        arithmetic={
            "formula": "occupied cell: take min(income, c), then regrow c + (M - c)*r",
            "M": f"(rich + poor) / 2 = ({RICH} + {POOR}) / 2 = {M}",
            "starved_regime": f"c* = M*r = {M}*{REGROW} = {starved:.4f} "
                              f"(holds when income >= M*r; here {INCOME} >= {starved:.4f})",
            "saturated_regime": f"c* = M + income - income/r = "
                                f"{M} + {INCOME} - {INCOME}/{REGROW} = "
                                f"{M + INCOME - INCOME / REGROW:.4f} (does NOT hold here)",
            "vacated_cell": f"{starved:.4f} + (M - {starved:.4f})*r = {vacated:.4f} "
                            f"after one empty step",
            "prediction": "stay is pinned at M*r and takes the whole cell every step; "
                          f"sighted moves onto a vacated cell holding {vacated:.4f}, "
                          f"which is {vacated / starved:.1%} more. So sighted must keep "
                          "MORE organisms than stay, and the field must not be flat.",
        },
        arms={
            "stay_n120": "n=120, cells=120, stay",
            "random_n120": "n=120, cells=120, random",
            "sighted_n120": "n=120, cells=120, sighted",
            "stay_n60": "n=60, cells=120, stay",
            "random_n60": "n=60, cells=120, random",
            "stay_n30": "n=30, cells=120, stay",
            "random_n30": "n=30, cells=120, random",
        },
        seed=1,
        command="python3 checks/exp31_moving_in_uniform.py",
        parameters={"cells": 120, "steps": 1200, "capacity": 10,
                    "damage_rate": 0.2, "income": INCOME, "maintenance": 0.1,
                    "repair_cost": 0.5, "move_cost": 0.05, "energy": 5.0,
                    "field": "uniform", "rich": RICH, "poor": POOR,
                    "regrow": REGROW, "M": M, "regime": regime,
                    "M_times_regrow": round(starved, 4)},
    )

    # §5: `sighted` in a uniform field is the SAME arm as `stay` (identical
    # hash), so it is recorded without a hash - its identity is the evidence
    # for the `silent` control, not a separate run.
    for key in ("stay_n120", "random_n120",
                "stay_n60", "random_n60", "stay_n30", "random_n30"):
        exp.add_arm(key, key.replace("_", " "),
                    {"alive": arms[key]["alive"],
                     "moved": arms[key]["moved"],
                     "mean_energy": arms[key]["mean_energy"]},
                    trace_hash=arms[key]["hash"])
    for key in ("sighted_n120", "sighted_n60", "sighted_n30"):
        exp.add_arm(key, key.replace("_", " ") + " (same arm as stay)",
                    {"alive": arms[key]["alive"],
                     "moved": arms[key]["moved"],
                     "mean_energy": arms[key]["mean_energy"]},
                    trace_hash=None)

    # Control 1 (fires): staying must be worse than moving at n=120.
    fires = arms["stay_n120"]["alive"] < arms["random_n120"]["alive"]
    exp.control("fires", fires,
                f"stay {arms['stay_n120']['alive']} < random "
                f"{arms['random_n120']['alive']} at n=120")

    # Control 2 (silent): the field is NOT flat after one step, so `sighted`
    # and `stay` must NOT hash the same. This control used to assert the
    # opposite and it fired. The reason is arithmetic: an occupied cell is
    # taken to zero every step (income 1.0 > M*r = 0.88), so it can only
    # regrow from 0 and settles at M*r = 0.88; a cell that has been empty for
    # one step holds 0.88 + (1.1 - 0.88)*0.8 = 1.056. `sighted` moves onto the
    # richer 1.056 and `stay` cannot. See
    # `docs/FINDING-the-field-was-never-uniform.md`.
    #
    # So the silent control here is the opposite: the two arms must differ.
    silent = arms["sighted_n120"]["hash"] != arms["stay_n120"]["hash"]
    exp.control("silent", silent,
                f"field is not flat (occupied {starved:.4f} = M*r, vacated "
                f"{vacated:.4f}), so sighted hash {arms['sighted_n120']['hash']} "
                f"must differ from stay hash {arms['stay_n120']['hash']}")

    # Control 3 (specific): the deficit must scale with crowding.  If sharing a
    # cell is the cause, then a sparser start must shrink the gap.
    gap120 = arms["random_n120"]["alive"] - arms["stay_n120"]["alive"]
    gap60 = arms["random_n60"]["alive"] - arms["stay_n60"]["alive"]
    gap30 = arms["random_n30"]["alive"] - arms["stay_n30"]["alive"]
    specific = gap120 > gap60 > gap30
    exp.control("specific", specific,
                f"gap random-stay: n120={gap120} > n60={gap60} > n30={gap30}")

    exp.limitation(
        "one seed per arm; the two-level field is read from the final frame only "
        "(the trace records one frame at --every 1200), and the regime boundary "
        "income = M*r is inferred from the arithmetic, not measured by sweeping "
        "income across it. The 0.8912 value (a cell entered this step) was checked "
        "by hand on one frame, not tracked per cell."
    )
    exp.verdict(
        "passed" if (fires and silent and specific) else "failed",
        "движение в «однородном» поле окупается потому, что поле не однородно: "
        f"занятая клетка стоит на M*r = {starved:.4f}, а освободившаяся — на "
        f"{vacated:.4f}. Стоять на месте — это голодать, а не экономить.",
    )
    print("saved:", exp.save())


if __name__ == "__main__":
    main()
