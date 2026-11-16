"""Does a field with peaks *and* a price for reading pose the memory question?

`docs/FINDING-155.md` answered "no" for two reasons it named itself: the field
was uniform (the richest cell is always adjacent) and reading was **free** (the
model had a budget on perception, not a price for it). Two independent reviews
said the same in `docs/REVIEW-emergence-notes-3.md` §1.3 and "Что остаётся
сделать". Cycle 52 closed both gaps in the model:

* `World::read_cost` -- every **neighbour** read costs energy, the own cell is
  free, `0.0` is the free-reading default and must not move one bit;
* `Field::peaks(cells, rich, poor, regrow, period)` -- one rich cell every
  `period` cells, so with `period >= 4` the next rich cell is outside the local
  window.

This experiment asks whether those two changes are enough, and the answer is
allowed to be no. What the grid *cannot* do is show a memory paying off: the
probe has no policy that reads less because it remembers.

The arithmetic is written into the record **before** the runs: see `arithmetic`
below, which includes the crossing inequality that decides whether a peak
outside the window is reachable, and the four predictions with the form in
which each one can fail.

    python3 checks/exp_memory_cost.py

Writes `results/memory-cost/run-*.json`.
"""

from __future__ import annotations

import json
import math
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
POOR = 0.2
STEPS = 20000
SEED = 3
CELLS = 24
CAPACITY = 10.0
ENERGY0 = 5.0
#: Where every arm starts. `0` is a rich cell of the `period = 6` field, which
#: privileges the arms that never move; `3` is poor and equidistant from the
#: peaks at 0 and 6, so "stay" and "look around" start from the same place.
START_CELL = 3

ARMS = ("oracle", "sighted", "intact", "stay", "random", "erased")
READ_BUDGETS = (1, 3)
COSTS = (0.0, 0.02, 0.05)

#: `m` is the upkeep per step: maintenance plus the repair bill. `income = m`,
#: exactly as in FINDING-155, so the only question left is whether the cell the
#: organism stands on has regrown by the time it returns.
POINTS = (("P_need=1", 1.0756), ("P_need=2", 1.7911))

#: name, probe field, period. `uniform` is 155's medium; `peaks2` puts a rich
#: cell every second cell (the nearest rich cell is always adjacent);
#: `peaks6` puts the next one six cells away, outside the local window.
FIELDS = (("uniform", "uniform", 0), ("peaks-2", "peaks", 2), ("peaks-6", "peaks", 6))


def p_need(m: float) -> int:
    return math.ceil(math.log(M / (M - m)) / (-math.log(1.0 - REGROW)))


def crossing_cost(maintenance: float) -> float:
    """Energy lost per step spent crossing one poor cell instead of upkeep."""
    return maintenance + DAMAGE_RATE * REPAIR_COST - POOR


def camper_holds(maintenance: float) -> bool:
    """Whether one organism standing still on a rich cell can pay its upkeep."""
    income = maintenance + DAMAGE_RATE * REPAIR_COST
    return M - income * (1.0 - REGROW) / REGROW >= maintenance


def run(arm: str, maintenance: float, field: str, period: int,
        read_budget: int, read_cost: float) -> dict:
    income = round(maintenance + DAMAGE_RATE * REPAIR_COST, 10)
    cmd = [
        PROBE,
        "--arm", arm,
        "--cells", str(CELLS),
        "--m", str(M),
        "--regrow", str(REGROW),
        "--income", str(income),
        "--maintenance", str(maintenance),
        "--repair-cost", str(REPAIR_COST),
        "--damage-rate", str(DAMAGE_RATE),
        "--steps", str(STEPS),
        "--seed", str(SEED),
        "--threshold", "1.0",
        "--capacity", str(CAPACITY),
        "--energy", str(ENERGY0),
        "--read-budget", str(read_budget),
        "--read-cost", str(read_cost),
        "--start-cell", str(START_CELL),
        "--field", field,
    ]
    if field == "peaks":
        cmd += ["--period", str(period), "--poor", str(POOR)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"probe not built: {PROBE}")
        print("run: cd core && cargo build --release --example memory_probe")
        return 1

    reach = {
        "need_P1": round(POINTS[0][1] + DAMAGE_RATE * REPAIR_COST, 6),
        "need_P2": round(POINTS[1][1] + DAMAGE_RATE * REPAIR_COST, 6),
        "crossing_cost_per_poor_cell_P1": round(crossing_cost(POINTS[0][1]), 6),
        "crossing_cost_per_poor_cell_P2": round(crossing_cost(POINTS[1][1]), 6),
        "reserve": ENERGY0,
        "peak_distance_from_start": 3,
        "peak_reachable_P1": 3 * crossing_cost(POINTS[0][1]) < ENERGY0,
        "peak_reachable_P2": 3 * crossing_cost(POINTS[1][1]) < ENERGY0,
        "why_reachability_decides": (
            "a peak outside the window is worth something only if walking to it "
            "costs less than the reserve: d * (need - poor) against ENERGY0"
        ),
        "camper_sustains_P1": camper_holds(POINTS[0][1]),
        "camper_sustains_P2": camper_holds(POINTS[1][1]),
        "why_camper_matters": (
            "at income = upkeep a cell held by one organism settles at "
            "c* = M - income*(1-r)/r; if c* < income the organism starves while "
            "standing still, so only a point where the camper holds can host a "
            "resident organism"
        ),
    }

    arithmetic = {
        "question": (
            "on a field with peaks outside the visible window, and with a price "
            "for reading, does the medium pose the memory question it did not "
            "pose in FINDING-155"
        ),
        "model_change": (
            "read_cost charges every neighbour read (own cell free); "
            "Field::peaks puts one rich cell every `period` cells"
        ),
        "grid": (
            "P_need in {1,2} x field in {uniform, peaks-2, peaks-6} x "
            "read_budget in {1,3} x read_cost in {0.0,0.02,0.05} x "
            f"{len(ARMS)} arms, start cell {START_CELL}, seed {SEED}"
        ),
        "reachability": reach,
        "mde_note": (
            "with sigma = 1000 steps between seeds and a target effect of 250 "
            "steps, the formula asks for 251 arms per cell; the grid has 6, so a "
            "difference below 250 steps is `void`, not `failed`"
        ),
        "prediction": {
            "a_uniform_is_silent": (
                "on `uniform` at P_need=1 every arm lives to the horizon; on "
                "`uniform` at P_need=2 the oracle lives to the horizon while the "
                "random walk with a stay move dies early. 155's equality was "
                "between `oracle` and `erased` (the never-stay walker), so the "
                "brief's literal `oracle` vs `random` claim is expected to FAIL "
                "here: that is a correction to how 155 was summarised, not a new "
                "effect"
            ),
            "b_peaks_give_information_value": (
                "on `peaks-6` at P_need=1 the oracle should find a peak three "
                "cells away and outlive the arms that cannot see it (stay, "
                "random). This can fail, and the number that says why is the "
                "crossing cost above: the oracle leaves a cell that still pays "
                "the upkeep and pays the crossing before it reaches the peak"
            ),
            "c_price_presses_on_the_reader": (
                "at read_budget=3 a positive read_cost must shorten the life of "
                "the arms that read neighbours and leave the ones that do not "
                "(stay, random, erased) unchanged. The second half - `sighted` "
                "losing to `intact` - can hold only if a memory lets an organism "
                "read FEWER cells; here `intact` reads exactly the two "
                "neighbours `sighted` reads, so this half is expected to FAIL, "
                "and that failure is itself the result"
            ),
            "d_zero_price_has_no_such_difference": (
                "at read_cost=0 the rb=1 and rb=3 columns differ only by what is "
                "seen, never by what is paid: any lifetime difference between "
                "the same arm at two prices must vanish at 0.0"
            ),
        },
    }

    arms = {
        f"{fname}/rb{rb}/c{cost:.2f}/{arm}": (
            f"field={fname} read_budget={rb} read_cost={cost} arm={arm}"
        )
        for fname, _, _ in FIELDS
        for rb in READ_BUDGETS
        for cost in COSTS
        for arm in ARMS
    }

    exp = Experiment(
        experiment_id="memory-cost",
        question=(
            "does a priced read and a peaked field make the memory question askable"
        ),
        arithmetic=arithmetic,
        arms=arms,
        seed=SEED,
        command="python3 checks/exp_memory_cost.py",
        parameters={
            "m_field": M,
            "regrow": REGROW,
            "repair_cost": REPAIR_COST,
            "damage_rate": DAMAGE_RATE,
            "steps": STEPS,
            "cells": CELLS,
            "capacity": CAPACITY,
            "energy0": ENERGY0,
            "poor": POOR,
            "start_cell": START_CELL,
            "read_budgets": list(READ_BUDGETS),
            "read_costs": list(COSTS),
            "points": {name: m for name, m in POINTS},
            "fields": [name for name, _, _ in FIELDS],
            "arms": list(ARMS),
        },
    )

    cells: list[dict] = []
    for point_name, maintenance in POINTS:
        for fname, probe_field, period in FIELDS:
            for rb in READ_BUDGETS:
                for cost in COSTS:
                    row = {
                        "point": point_name,
                        "p_need": p_need(maintenance),
                        "field": fname,
                        "period": period,
                        "read_budget": rb,
                        "read_cost": cost,
                        "arms": {},
                    }
                    for arm in ARMS:
                        data = run(arm, maintenance, probe_field, period, rb, cost)
                        row["arms"][arm] = data
                        exp.add_arm(
                            f"{point_name}/{fname}/rb{rb}/c{cost:.2f}/{arm}",
                            f"{point_name} {fname} read_budget={rb} "
                            f"read_cost={cost} arm={arm}",
                            {
                                "lifetime": data["lifetime"],
                                "alive": data["alive"],
                                "cause": data["cause"],
                                "taken_mean": round(data["taken_mean"], 6),
                                "frac_rich": round(data["frac_rich"], 6),
                                "energy_end": round(data["energy_end"], 6),
                                "moves": data["moves"],
                            },
                            trace_hash=data["hash"],
                        )
                    cells.append(row)

    exp.result["cells"] = [
        {
            "point": c["point"],
            "p_need": c["p_need"],
            "field": c["field"],
            "read_budget": c["read_budget"],
            "read_cost": c["read_cost"],
            "lifetime": {a: c["arms"][a]["lifetime"] for a in ARMS},
            "frac_rich": {a: round(c["arms"][a]["frac_rich"], 4) for a in ARMS},
            "hash": {a: c["arms"][a]["hash"] for a in ARMS},
        }
        for c in cells
    ]

    def cell(point: str, field: str, rb: int, cost: float) -> dict:
        for c in cells:
            if (
                c["point"] == point
                and c["field"] == field
                and c["read_budget"] == rb
                and abs(c["read_cost"] - cost) < 1e-12
            ):
                return c["arms"]
        raise KeyError((point, field, rb, cost))

    # -- the table ----------------------------------------------------------
    for point_name, maintenance in POINTS:
        print(
            f"\n== {point_name} (m = {maintenance}, P_need by formula = "
            f"{p_need(maintenance)}) =="
        )
        print("%-8s rb cost " % "field" + "".join("%9s" % a for a in ARMS))
        for fname, _, _ in FIELDS:
            for rb in READ_BUDGETS:
                for cost in COSTS:
                    a = cell(point_name, fname, rb, cost)
                    print(
                        "%-8s %2d %.2f " % (fname, rb, cost)
                        + "".join("%9d" % a[x]["lifetime"] for x in ARMS)
                    )

    # -- controls -----------------------------------------------------------
    p1 = "P_need=1"
    p2 = "P_need=2"
    base = cell(p1, "peaks-6", 3, 0.0)

    fires = bool(
        base["sighted"]["alive"] and base["intact"]["alive"]
        and not base["stay"]["alive"]
    )
    exp.control(
        "fires",
        fires,
        "peaks-6, P_need=1, read_budget=3: the arms that can find a peak "
        f"(sighted {base['sighted']['lifetime']}, intact "
        f"{base['intact']['lifetime']}) live to the horizon while the one that "
        f"cannot move (stay {base['stay']['lifetime']}) starves, so the peaked "
        "field does separate policies",
    )

    silent = all(
        cell(p1, "uniform", rb, cost)[arm]["alive"]
        for rb in READ_BUDGETS
        for cost in COSTS
        for arm in ARMS
    )
    exp.control(
        "silent",
        silent,
        "uniform, P_need=1: every one of the "
        f"{len(READ_BUDGETS) * len(COSTS) * len(ARMS)} arm/budget/price "
        "combinations lives to the horizon, so the flat field gives no policy an "
        "advantage - FINDING-155's control, reproduced on the same probe",
    )

    rb1 = cell(p2, "uniform", 1, 0.05)["sighted"]["lifetime"]
    rb1_free = cell(p2, "uniform", 1, 0.0)["sighted"]["lifetime"]
    rb3 = cell(p2, "uniform", 3, 0.05)["sighted"]["lifetime"]
    rb3_free = cell(p2, "uniform", 3, 0.0)["sighted"]["lifetime"]
    exp.control(
        "specific",
        rb1 == rb1_free and rb3 < rb3_free,
        "uniform, P_need=2, sighted: at read_budget=1 no neighbour is read, so "
        f"the price is inert ({rb1_free} against {rb1}); at read_budget=3 the "
        f"same organism pays for two reads a step and dies earlier ({rb3_free} "
        f"against {rb3}). The only rule that changed between the two rows is how "
        "many neighbours are read, so the difference is the price of the read",
    )

    # PROTOCOL-0 п. 3: `mde` sits next to `arithmetic`, and an effect below it
    # is `void`, not `failed`. `sigma` is the between-seed spread of a lifetime
    # and `effect` is the smallest difference this record claims to see; the
    # grid has six arms per cell, so most of the tiny 5-vs-6 step differences
    # are `void` by this rule and the claims rest on horizon-sized contrasts.
    mde_arms = R.set_mde(exp.result, sigma=1000.0, effect=250.0)

    by_hash: dict[str, list[str]] = {}
    for key, h in exp.result["hashes"].items():
        by_hash.setdefault(h, []).append(key)
    collisions = [sorted(keys) for keys in by_hash.values() if len(keys) > 1]
    for group in collisions:
        exp.expect_coincident(*group)
    exp.result["coincident_groups"] = len(collisions)

    exp.limitation(
        "one seed and one start cell. The start was chosen (cell 3) so that the "
        "arms that never move do not start on a peak of the `period = 6` field; "
        "with the probe's default start of 0 they do, and `stay` then survives on "
        "a field where it should starve. That was seen in a pilot run and is "
        "recorded here rather than hidden."
    )
    exp.limitation(
        "the oracle is a POLICY, not a bound, on this field. In FINDING-155 it "
        "walked a uniform ring where one step was as good as another; here a step "
        "across a poor cell costs `need - poor`, so walking to the globally "
        "richest cell can be worse than staying on a cell that pays the upkeep. "
        "An oracle on a rough field is not an upper bound on information value."
    )
    exp.limitation(
        "`intact` and `sighted` read exactly the same two neighbours, so the "
        "price of reading cannot fall on them differently. A memory that lets an "
        "organism read FEWER cells is not implemented, and no number here can say "
        "what such a memory would be worth."
    )
    exp.limitation(
        "one organism, no competition, no sharing, movement on a ring while "
        "`Life` does not wrap: the same structural limits as FINDING-155."
    )
    exp.limitation(
        "`income = upkeep` by construction. At P_need=2 a cell held by one "
        "organism settles below the upkeep and the camper starves, so the two "
        "points are not two prices of one medium: they are two media, only one of "
        "which can support a stationary organism."
    )

    o6 = base["oracle"]["lifetime"]
    r6 = base["random"]["lifetime"]
    s6 = base["sighted"]["lifetime"]
    uni = cell(p2, "uniform", 3, 0.0)
    same_memory = base["sighted"]["hash"] == base["intact"]["hash"]
    reason = (
        "The peaked field does separate policies (peaks-6, P_need=1: sighted and "
        f"intact live {s6}, stay {base['stay']['lifetime']}, oracle {o6}, random "
        f"{r6}), so the medium is no longer silent. But the question it asks is "
        "not the memory question. (1) More information is WORSE: the oracle, "
        "which knows the globally richest cell, dies at "
        f"{o6} while the local rule lives {s6}, because it leaves a cell that "
        "pays the upkeep and spends the crossing on poor cells. (2) Memory adds "
        f"nothing: `intact` and `sighted` produce the same lifetime and "
        f"{'the same hash' if same_memory else 'a difference that is only the tie-break'}, "
        "because a memory slot does not save a single read - a look at the two "
        "neighbours costs the same whether or not something is remembered. "
        "(3) The price does bite (uniform, P_need=2, sighted: "
        f"{rb3_free} at read_cost=0 against {rb3} at 0.05, while at "
        f"read_budget=1, where no neighbour is read, it is {rb1_free} against "
        f"{rb1}), so the mechanism is real - it just presses on every reader "
        "equally. On `uniform` 155's equality is between oracle and erased "
        f"({uni['oracle']['lifetime']} against {uni['erased']['lifetime']}); the "
        "brief's oracle-vs-random claim does not reproduce and never did: the "
        f"stay-capable walker dies at {uni['random']['lifetime']}. So the answer "
        "to 'does the priced, peaked field pose the memory question' is NO, and "
        "`not applicable` is wrong for it: an effect exists, it is just not about "
        "memory. The verdict is `failed`."
    )
    exp.verdict("failed", "EXPLAINED: " + reason)

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(f"coincident hash groups: {len(collisions)}")
    print(f"mde: sigma=1000 steps, effect=250 steps -> {mde_arms} arms per cell")
    return 0


if __name__ == "__main__":
    sys.exit(main())
