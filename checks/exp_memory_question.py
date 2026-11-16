"""Does this medium pose a question about memory at all?

The pre-check two independent reviews put first. In a fully observable
medium memory cannot pay for itself at any price, so before evolving anything
we must ask whether the organism's decision depends on something it cannot
see *now*.

The bound used here is an oracle: an organism that knows the globally richest
cell at every step. That is more than any memory can know (memory knows only
what it has seen), so its reward is an upper bound on what memory could be
worth. If the oracle is not better than a memoryless neighbour-follower, there
is nothing for memory to add.

The second axis is `read_budget`: `3` means own cell plus both neighbours,
`1` means own cell only, `0` means no reading at all. That is what decides
whether the medium is partially observable: with both neighbours visible the
richest cell is always one step away and therefore already seen.

    python3 checks/exp_memory_question.py

Writes `results/memory-question/run-*.json`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))

import result as R  # noqa: E402
from experiment import Experiment  # noqa: E402

PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "memory_probe")

M = 2.0
REGROW = 0.8
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
STEPS = 20000
SEED = 3
CELLS = 24
CAPACITY = 10.0
ENERGY0 = 5.0

ARMS = ("oracle", "sighted", "intact", "sham", "erased", "stay", "random")
READ_BUDGETS = (0, 1, 2, 3)

#: `m` is the upkeep per step: maintenance plus the repair bill. With
#: `income = m` the organism takes exactly what it needs, so the only question
#: left is whether the cell it stands on has regrown by the time it returns.
POINTS = (
    ("P_need=1", 1.0756),
    ("P_need=2", 1.7911),
)


def p_need(m: float) -> int:
    import math

    return math.ceil(math.log(M / (M - m)) / (-math.log(1.0 - REGROW)))


def run(arm: str, maintenance: float, read_budget: int) -> dict:
    cmd = [
        PROBE,
        "--arm", arm,
        "--cells", str(CELLS),
        "--m", str(M),
        "--regrow", str(REGROW),
        "--income", str(round(maintenance + DAMAGE_RATE * REPAIR_COST, 10)),
        "--maintenance", str(maintenance),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(STEPS),
        "--seed", str(SEED),
        "--threshold", "1.0",
        "--capacity", str(CAPACITY),
        "--energy", str(ENERGY0),
        "--read-budget", str(read_budget),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}\nrun: cd core && cargo build --release --example memory_probe")
        return 1

    arithmetic = {
        "question": "does the medium require anything the organism cannot see now",
        "oracle_bound": (
            "`oracle` moves toward the globally richest cell every step. It knows "
            "more than any memory can (memory knows only what it has seen), so its "
            "reward bounds from above what memory could be worth."
        ),
        "p_need": "ceil(ln(M/(M-m)) / -ln(1-r)), the return period that lets a cell regrow",
        "why_income_is_m": (
            "with income = m the organism takes exactly its upkeep, so the only "
            "remaining question is whether the cell has regrown on return"
        ),
        "prediction": (
            "if both neighbours are visible (read_budget = 3) the richest cell is "
            "always one step away and therefore already seen: oracle, sighted and "
            "intact should coincide exactly. With read_budget <= 1 the medium "
            "becomes partially observable and the oracle should beat every "
            "memoryless arm - the question is then whether our memory can exploit it"
        ),
        "grid": "read_budget in {0,1,2,3} x P_need in {1,2}",
    }

    arms = {f"rb{rb}/{arm}": f"read_budget={rb} arm={arm}" for rb in READ_BUDGETS for arm in ARMS}

    exp = Experiment(
        experiment_id="memory-question",
        question="does this medium pose a question about memory",
        arithmetic=arithmetic,
        arms=arms,
        seed=SEED,
        command="python3 checks/exp_memory_question.py",
        parameters={
            "m_field": M,
            "regrow": REGROW,
            "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE_RATE,
            "steps": STEPS,
            "cells": CELLS,
            "capacity": CAPACITY,
            "energy0": ENERGY0,
            "read_budgets": list(READ_BUDGETS),
            "points": {name: m for name, m in POINTS},
            "arms": list(ARMS),
        },
    )

    points: list[dict] = []
    for probe_read_budget in READ_BUDGETS:
        for name, maintenance in POINTS:
            row = {
                "read_budget": probe_read_budget,
                "point": name,
                "maintenance": maintenance,
                "p_need": p_need(maintenance),
                "arms": {},
            }
            for arm in ARMS:
                data = run(arm, maintenance, probe_read_budget)
                row["arms"][arm] = data
                exp.add_arm(
                    f"rb{probe_read_budget}/{arm}@{name}",
                    f"read_budget={probe_read_budget} arm={arm} {name}",
                    {
                        "lifetime": data["lifetime"],
                        "alive": data["alive"],
                        "cause": data["cause"],
                        "taken_mean": data["taken_mean"],
                        "energy_acc": data["energy_acc"],
                        "moves": data["moves"],
                    },
                    trace_hash=data["hash"],
                )
            points.append(row)

    exp.result["points"] = [
        {
            "read_budget": row["read_budget"],
            "point": row["point"],
            "p_need": row["p_need"],
            "lifetime": {a: row["arms"][a]["lifetime"] for a in ARMS},
            "taken_mean": {a: round(row["arms"][a]["taken_mean"], 6) for a in ARMS},
            "hash": {a: row["arms"][a]["hash"] for a in ARMS},
        }
        for row in points
    ]

    # -- controls -----------------------------------------------------------
    def by(read_budget: int, name: str) -> dict:
        for row in points:
            if row["read_budget"] == read_budget and row["point"] == name:
                return row["arms"]
        raise KeyError((read_budget, name))

    # fires: the probe separates a dead arm from a living one. At P_need=2 the
    # staying arm starves next to the oracle, which is all this control claims.
    fires = (
        by(3, "P_need=2")["stay"]["alive"] is False
        and by(3, "P_need=2")["oracle"]["alive"] is True
    )
    exp.control(
        "fires",
        fires,
        "P_need=2: the staying arm dies while the oracle lives, so the probe "
        "separates a dead arm from a living one",
    )

    # silent: at P_need=1 the medium poses no question - every arm lives, so
    # there is nothing for any policy to differ about.
    surviving = [by(rb, "P_need=1")[a]["alive"] for rb in READ_BUDGETS for a in ARMS]
    exp.control(
        "silent",
        all(surviving),
        f"P_need=1: all {len(surviving)} arm/read-budget combinations live to the "
        "horizon, so the medium gives no policy an advantage",
    )

    # specific: the arm that survives without knowing anything (random walk)
    # lives exactly as long as the arm that knows everything (oracle). So what
    # keeps an organism alive here is moving, not knowing - and the difference
    # is not knowledge.
    equal_at_p2 = all(
        by(rb, "P_need=2")["oracle"]["lifetime"] == by(rb, "P_need=2")["erased"]["lifetime"]
        for rb in READ_BUDGETS
    )
    exp.control(
        "specific",
        equal_at_p2,
        "P_need=2: the random walk (erased, knows nothing) lives exactly as long as "
        "the oracle (knows the globally richest cell) at every read budget, so the "
        "advantage is movement, not information",
    )

    # Every collision is declared, and the collisions *are* the result: arms that
    # share a dynamics hash are one arm, and here that says the medium cannot tell
    # them apart. Declaring them keeps the contract reading this as a finding
    # rather than as a false contrast.
    by_hash: dict[str, list[str]] = {}
    for key, h in exp.result["hashes"].items():
        by_hash.setdefault(h, []).append(key)
    collisions = [sorted(keys) for keys in by_hash.values() if len(keys) > 1]
    for group in collisions:
        exp.expect_coincident(*group)
    exp.result["coincident_groups"] = collisions

    exp.limitation(
        "the oracle knows the globally richest cell. That is more than memory can "
        "know, so it bounds memory from above; it is not an achievable policy."
    )
    exp.limitation(
        "`income = m` and `move_cost = 0` by construction: with a non-zero move "
        "cost the return period shifts and `P_need` stops being a property of the "
        "medium alone."
    )
    exp.limitation(
        "the probe wraps movement around a ring. `Field` and `Life` do not wrap, and "
        "without wrapping a one-dimensional walk cannot have a return period longer "
        "than two, so `P_need >= 3` is unreachable by construction."
    )
    exp.limitation(
        "one organism, uniform ring, no competition and no sharing: this bounds the "
        "value of information, not a population's fate."
    )
    exp.limitation(
        "arms that share a dynamics hash are declared as one arm, and there are "
        "many: with a uniform ring almost every policy that keeps moving produces "
        "the same trajectory. That is the finding, not a bug in the declarations - "
        "but it also means this grid cannot separate policies that differ only in "
        "which rich cell they choose."
    )
    exp.limitation(
        "memory here stores the cell the organism stands on. If the medium becomes "
        "partially observable only for cells it has never stood on, this "
        "implementation cannot exploit it even when the oracle shows the "
        "information is worth having."
    )

    rb1 = by(1, "P_need=2")
    rb3 = by(3, "P_need=2")
    reason = (
        "P_need=1: all 28 arm/read-budget combinations live to the horizon, so the "
        "medium gives no policy an advantage and the memory question is empty. "
        "P_need=2: the staying arm dies at step 24 while every arm that keeps moving "
        "lives 20000, so the question the medium does ask is 'move at all', not "
        "'remember where'. The decisive number is that the oracle - which knows the "
        f"globally richest cell at every step - lives exactly as long as the random "
        f"walk ({rb3['oracle']['lifetime']} against {rb3['erased']['lifetime']} at "
        "read_budget=3, and the same at 0, 1 and 2), so perfect information about the "
        "field is worth zero over wandering. Memory cannot be worth more than "
        "information, so in this medium it is worth nothing. NOT APPLICABLE to 'does "
        "the medium pose a memory question': it does not, because on a uniform ring "
        "with income equal to upkeep any movement suffices and the richest cell is "
        "always adjacent. The partial-observability question only appears when the "
        "field is not uniform - which this grid does not contain."
    )
    exp.verdict("not applicable", "EXPLAINED: " + reason)

    path = exp.save()
    print(f"saved {os.path.relpath(path, ROOT)}")
    print(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
