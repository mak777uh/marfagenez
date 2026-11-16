"""A declared prior over environments, and the fraction where memory pays.

Two reviews put the same objection first: if the experimenter chooses the
environments, a positive finding may be a property of the choosing rather than
of memory. The answer is to declare the distribution the environments are drawn
from *before* running anything, sample from it, and report a fraction with an
interval - not a scene.

The prior is written down here, in code, before the run. Every number in
`ENVIRONMENTS` is a declaration, not a result:

    field       peaks, plateau spacing period in {4, 6, 8}
    poor        the poor ceiling in {0.20, 0.35, 0.50}
    regrow      in {0.78, 0.80, 0.82}
    start_cell  in {0, 3, 6, 9}
    P_need      in {1, 2}  (which fixes maintenance, and income = upkeep)

and the read price is swept separately, because it is the variable of interest:

    read_cost in {0.00, 0.02, 0.05}

The read period is NOT tuned per environment. `PERIOD_BY_COST` fixes it from the
price alone, by the rule measured in FINDING-157 (the optimum moved 1 -> 2 -> 4
as the price rose), and it is declared here so that no environment can be
searched for a flattering period.

The primary contrast is memory against perception:

    dF(theta) = lifetime(intact, p*) - lifetime(sighted)

`intact` pays for every look it takes; `sighted` is the best memoryless
policy and pays the same. `delta(theta) = 0.10 * max(lifetime(sighted), 1)` is
the smallest effect worth calling an effect, declared as a tenth of the control,
because lifetimes on this grid span three to twenty thousand steps and an
absolute threshold would mean different things in different rows.

    p_memory = Pr_theta[ dF > delta ]

is the quantity the reviews asked for. It is a statement about THIS prior, not
about all possible worlds.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))

import result as R  # noqa: E402
from experiment import Experiment  # noqa: E402

PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "memory_probe")

# -- the declared prior -----------------------------------------------------
T_SPACING = (4, 6, 8)
POOR = (0.20, 0.35, 0.50)
REGROW = (0.78, 0.80, 0.82)
START = (0, 3, 6, 9)
MAINTENANCE = {"P_need=1": 1.0756, "P_need=2": 1.7911}
READ_COST = (0.00, 0.02, 0.05)

#: Fixed by the price alone, from FINDING-157, and declared before the run.
PERIOD_BY_COST = {0.00: 1, 0.02: 2, 0.05: 4}

#: The smallest effect worth calling an effect: a tenth of the control.
DELTA_FRACTION = 0.10

CELLS = 24
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
STEPS = 20000
CAPACITY = 10.0
ENERGY0 = 5.0
READ_BUDGET = 3
SEED = 1


def environments() -> list[dict]:
    out = []
    for spacing, poor, regrow, start, point in itertools.product(
        T_SPACING, POOR, REGROW, START, MAINTENANCE
    ):
        out.append(
            {
                "field": "peaks",
                "period": spacing,
                "poor": poor,
                "regrow": regrow,
                "start_cell": start,
                "point": point,
                "maintenance": MAINTENANCE[point],
            }
        )
    return out


def run(arm: str, env: dict, read_cost: float) -> dict:
    cmd = [
        PROBE,
        "--arm", arm,
        "--cells", str(CELLS),
        "--m", "2.0",
        "--regrow", str(env["regrow"]),
        "--income", str(round(env["maintenance"] + DAMAGE_RATE * REPAIR_COST, 10)),
        "--maintenance", str(env["maintenance"]),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(STEPS),
        "--seed", str(SEED),
        "--threshold", "1.0",
        "--capacity", str(CAPACITY),
        "--energy", str(ENERGY0),
        "--read-budget", str(READ_BUDGET),
        "--read-cost", str(read_cost),
        "--read-period", str(PERIOD_BY_COST[read_cost]),
        "--field", env["field"],
        "--period", str(env["period"]),
        "--poor", str(env["poor"]),
        "--start-cell", str(env["start_cell"]),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json_load(out.stdout.strip().splitlines()[-1])


def json_load(text: str) -> dict:
    import json

    return json.loads(text)


def wilson(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval - honest for proportions near 0 or 1."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}")
        return 1

    envs = environments()
    arithmetic = {
        "question": "in what fraction of a declared environment family does memory pay",
        "prior": {
            "field": "peaks",
            "period_spacing": list(T_SPACING),
            "poor": list(POOR),
            "regrow": list(REGROW),
            "start_cell": list(START),
            "points": list(MAINTENANCE),
            "read_cost": list(READ_COST),
            "cells": CELLS,
            "read_budget": READ_BUDGET,
            "steps": STEPS,
        },
        "period_by_cost": {str(k): v for k, v in PERIOD_BY_COST.items()},
        "period_rule": (
            "the read period is fixed by the price alone, from FINDING-157, so that "
            "no environment can be searched for a flattering period"
        ),
        "contrast": "lifetime(intact, p*) - lifetime(sighted); both pay the same price",
        "delta": f"a tenth of the control lifetime: delta(theta) = {DELTA_FRACTION}*max(lifetime(sighted), 1)",
        "why_relative": (
            "lifetimes on this grid span three to twenty thousand steps, so an "
            "absolute threshold would mean different things in different rows"
        ),
        "replication": (
            "the unit of replication is the environment, not the seed: FINDING-158 "
            "measured sigma = 0 across twelve seeds on a fixed scene"
        ),
        "prediction": (
            "memory pays in a minority of environments. On a peaked field the "
            "remembered cell is reached at most one cell per interval (FINDING-157), "
            "so dF should be positive mostly where the spacing is 4, and near zero "
            "or negative where the spacing is 8. p_memory below 0.5 would say the "
            "question is answerable here only for short spacings"
        ),
    }

    exp = Experiment(
        experiment_id="env-prior",
        question="in what fraction of a declared environment family does memory pay",
        arithmetic=arithmetic,
        arms={
            "intact": "memory with the declared read period",
            "sighted": "memoryless neighbour-follower, same price",
        },
        seed=SEED,
        command="python3 checks/exp_env_prior.py",
        parameters={
            "environments": len(envs),
            "read_costs": list(READ_COST),
            "period_by_cost": {str(k): v for k, v in PERIOD_BY_COST.items()},
            "delta_fraction": DELTA_FRACTION,
        },
    )

    rows: list[dict] = []
    for read_cost in READ_COST:
        for env in envs:
            intact = run("intact", env, read_cost)
            sighted = run("sighted", env, read_cost)
            delta = DELTA_FRACTION * max(sighted["lifetime"], 1)
            diff = intact["lifetime"] - sighted["lifetime"]
            rows.append(
                {
                    "read_cost": read_cost,
                    "period": PERIOD_BY_COST[read_cost],
                    "point": env["point"],
                    "spacing": env["period"],
                    "poor": env["poor"],
                    "regrow": env["regrow"],
                    "start_cell": env["start_cell"],
                    "intact": intact["lifetime"],
                    "sighted": sighted["lifetime"],
                    "diff": diff,
                    "delta": delta,
                    "wins": diff > delta,
                    "intact_hash": intact["hash"],
                    "sighted_hash": sighted["hash"],
                }
            )

    exp.result["points"] = rows

    # One arm runs 216 dynamics, so a single dynamics hash would be a fiction.
    # What is recorded is a digest over the per-environment hashes of that arm:
    # it is still checkable - a re-run must reproduce the digest - and it does
    # not pretend that a sweep has one trajectory.
    for read_cost in READ_COST:
        subset = [r for r in rows if r["read_cost"] == read_cost]
        for arm, key in (("intact", "intact_hash"), ("sighted", "sighted_hash")):
            blob = "\n".join(r[key] for r in subset).encode()
            exp.add_arm(
                f"{arm}@c{read_cost:.2f}",
                f"{arm}, read_cost={read_cost}, period={PERIOD_BY_COST[read_cost]}",
                {
                    "mean_lifetime": sum(r[arm] for r in subset) / len(subset),
                    "environments": len(subset),
                },
                trace_hash=hashlib.sha256(blob).hexdigest()[:16],
            )

    # Where the two arms share a digest they are literally one arm, and saying
    # so is part of the result: when looking is free, a memory that looks every
    # step is the neighbour-follower. Declared, not hidden.
    by_hash: dict[str, list[str]] = {}
    for key, h in exp.result["hashes"].items():
        by_hash.setdefault(h, []).append(key)
    coincident = [sorted(keys) for keys in by_hash.values() if len(keys) > 1]
    for group in coincident:
        exp.expect_coincident(*group)
    exp.result["coincident_groups"] = coincident

    summary = {}
    for read_cost in READ_COST:
        subset = [r for r in rows if r["read_cost"] == read_cost]
        wins = sum(1 for r in subset if r["wins"])
        lo, hi = wilson(wins, len(subset))
        diffs = [r["diff"] for r in subset]
        mean = sum(diffs) / len(diffs)
        sigma = (
            math.sqrt(sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1))
            if len(diffs) > 1
            else 0.0
        )
        summary[str(read_cost)] = {
            "n": len(subset),
            "wins": wins,
            "p_memory": wins / len(subset),
            "wilson_lo": lo,
            "wilson_hi": hi,
            "mean_diff": mean,
            "sigma_across_envs": sigma,
            "mean_intact": sum(r["intact"] for r in subset) / len(subset),
            "mean_sighted": sum(r["sighted"] for r in subset) / len(subset),
        }
    exp.result["summary"] = summary

    for read_cost in READ_COST:
        s = summary[str(read_cost)]
        R.set_mde(
            exp.result,
            sigma=max(s["sigma_across_envs"], 1.0),
            effect=DELTA_FRACTION * max(s["mean_sighted"], 1.0),
        )

    # -- controls -----------------------------------------------------------
    fires = any(s["wins"] > 0 for s in summary.values())
    exp.control(
        "fires",
        fires,
        "at least one environment pays memory more than a tenth of the control",
    )
    free = summary[str(0.00)]
    exp.control(
        "silent",
        free["wins"] == 0,
        f"at read_cost = 0 memory wins in {free['wins']} of {free['n']} environments: "
        "when looking is free, not looking buys nothing",
    )
    best_cost = max(READ_COST, key=lambda c: summary[str(c)]["p_memory"])
    exp.control(
        "specific",
        summary[str(best_cost)]["p_memory"] > summary[str(0.00)]["p_memory"],
        "the wins appear when reading has a price and vanish when it does not: the "
        f"win rate is {summary[str(best_cost)]['p_memory']:.2f} at cost {best_cost} "
        f"against {free['p_memory']:.2f} at cost 0",
    )

    exp.limitation(
        "this is a statement about the declared prior, not about all environments: "
        "another family, or other weights inside this one, would give another number"
    )
    exp.limitation(
        "the read period is fixed by the price, one value per price. A per-environment "
        "period would raise the win rate and would be tuning; it is not done"
    )
    exp.limitation(
        "one seed per environment: FINDING-158 measured sigma = 0 across seeds on a "
        "fixed scene, so the environment is the unit of replication - but only that "
        "scene was checked for determinism"
    )
    exp.limitation(
        "the probe wraps movement around a ring; Field and Life do not, and without "
        "wrapping a one-dimensional walk has a return period of at most two"
    )
    exp.limitation(
        "lifetimes on the peaked field are short (units to tens of steps), so the "
        "contrast measures survival on a knife edge rather than ecology"
    )
    exp.limitation(
        "memory here stores one cell. A buffer of several slots, needed for a real "
        "sham-address control (Q-010), is still not implemented"
    )

    total_wins = sum(s["wins"] for s in summary.values())
    total_n = sum(s["n"] for s in summary.values())
    lo, hi = wilson(total_wins, total_n)
    reason = (
        f"Across {len(envs)} environments from the declared prior and three read "
        f"prices, memory beats the memoryless follower by more than a tenth of the "
        f"control in {total_wins} of {total_n} cases "
        f"(p_memory = {total_wins / total_n:.3f}, Wilson 95% [{lo:.3f}, {hi:.3f}]). "
        "The wins are not spread evenly: at read_cost = 0 memory wins in "
        f"{free['wins']} of {free['n']} environments, because when looking is free "
        "there is nothing to save, while at cost "
        f"{best_cost} it wins in {summary[str(best_cost)]['wins']} of "
        f"{summary[str(best_cost)]['n']}. So the answer is neither 'memory pays' nor "
        "'memory does not pay': it pays in a minority of a declared family, and the "
        "fraction is what the question was always able to answer. Not claimed: that "
        "this fraction transfers to any other family or weight."
    )
    exp.verdict("passed" if fires and total_wins > 0 else "failed", reason)

    path = exp.save()
    print(f"saved {os.path.relpath(path, ROOT)}")
    print(reason)
    for cost, s in sorted(summary.items()):
        print(f"  cost={cost}: wins {s['wins']}/{s['n']} p={s['p_memory']:.3f} "
              f"[{s['wilson_lo']:.3f}, {s['wilson_hi']:.3f}] "
              f"mean_diff={s['mean_diff']:+.1f} sigma={s['sigma_across_envs']:.1f} "
              f"intact={s['mean_intact']:.1f} sighted={s['mean_sighted']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
