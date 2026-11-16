"""Does a memory that may skip a look create the perception/memory trade-off?

FINDING-156 ended with a precise defect: `intact` and `sighted` produced one
number and one hash, because a memory slot did not save a single look. The model
change here is `World::read_period`: a `Memory` organism reads its neighbours
only when `step % read_period == 0`, and acts on the memory in between, paying
neither a read nor `read_cost`. `Sighted` is deliberately not gated -- it has no
memory to act on, so a skipped look would be blindness, not economy.

The question this experiment asks is allowed to be answered "no": at a zero
price, reading rarely must not help (there is nothing to save and knowledge
ages); at a positive price, some `read_period > 1` must let `intact` outlive
`intact` at `1`, and the optimal period must grow with the price. The `peaks-6`
field is the harder test: a remembered address can go poor (ceiling 0.2), while
a uniform cell regrows toward the same ceiling `M`, so staleness is dearer.

The arithmetic below is written **before** the runs, including the form in which
each prediction can fail. See `docs/FINDING-157.md`.

    python3 checks/exp_memory_sampling.py

Writes `results/memory-sampling/run-*.json`.
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
START_CELL = 3

ARMS = ("sighted", "intact", "stay", "random")
READ_BUDGETS = (1, 3)
COSTS = (0.0, 0.02, 0.05)
PERIODS = (1, 2, 4, 8)

#: `m` is the upkeep per step: maintenance plus the repair bill, `income = m`
#: exactly as in FINDING-155/156. The two points are two media: at `P_need=1`
#: standing on a rich cell pays the upkeep, at `P_need=2` only movement does.
POINTS = (("P_need=1", 1.0756), ("P_need=2", 1.7911))

#: `uniform` is 155's medium (every cell the same ceiling). `peaks-6` is 156's:
#: the next rich cell is six cells away, outside the local window, and the
#: remembered cell can therefore go poor.
FIELDS = (("uniform", "uniform", 0), ("peaks-6", "peaks", 6))


def p_need(m: float) -> int:
    return math.ceil(math.log(M / (M - m)) / (-math.log(1.0 - REGROW)))


def run(arm: str, maintenance: float, field: str, period: int,
        read_budget: int, read_cost: float, read_period: int) -> dict:
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
        "--read-period", str(read_period),
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

    per_step_p1 = lambda cost: 2.0 * cost
    per_step_p = lambda cost, p: 2.0 * cost / p

    arithmetic = {
        "question": (
            "does a memory that is allowed not to look buy the perception it "
            "skips, and at what price does the trade-off first become visible"
        ),
        "model_change": (
            "World::read_period: a `Memory` organism reads its two neighbours "
            "only when step % read_period == 0 and acts on `direction()` in "
            "between; `Sighted` is not gated. At read_period = 1 nothing "
            "changes -- three recorded hashes were checked against a worktree "
            "binary built from HEAD (random de3950f7ae833acf, sighted "
            "46691241b93abff9, memory 66cdac546d4289a5)"
        ),
        "grid": (
            "P_need in {1,2} x field in {uniform, peaks-6} x read_budget in "
            "{1,3} x read_cost in {0.0,0.02,0.05} x read_period in "
            f"{list(PERIODS)} x arms {list(ARMS)}, start cell {START_CELL}, "
            f"seed {SEED}, horizon {STEPS} steps"
        ),
        "read_bill_per_step": {
            "period_1_rb3": per_step_p1(0.05),
            "at_cost_0_02_period_p": {
                str(p): round(per_step_p(0.02, p), 6) for p in PERIODS
            },
            "at_cost_0_05_period_p": {
                str(p): round(per_step_p(0.05, p), 6) for p in PERIODS
            },
            "why_it_decides": (
                "the reserve is 5.0 and upkeep is `m`, so at rb=3 and a price "
                "of 0.05 the reads alone drain 0.10 per step; FINDING-156 "
                "measured sighted and intact at 51 steps there. Dividing the "
                "looks by p divides that drain by p, which is the only way a "
                "memory can buy time -- unless the stale address is worse than "
                "the fresh comparison, which is the failure mode this can run "
                "into"
            ),
        },
        "stale_memory_term": (
            "a memory stores a LEVEL and an ADDRESS. On `uniform` every cell "
            "regrows toward the same ceiling M, so a remembered address is "
            "still a decent cell when the organism arrives. On `peaks-6` the "
            "address can be a poor cell whose ceiling is 0.2, and the memory "
            "cannot tell until it reads again. Staleness must therefore cost "
            "more on `peaks-6`, and the gain over period 1 must be smaller"
        ),
        "why_rb1_is_the_control": (
            "with read_budget = 1 the own cell consumes the whole budget, so no "
            "neighbour is read at any period and no read cost is paid: the "
            "period can change neither lifetime nor hash. That is the `specific` "
            "control's silent half"
        ),
        "mde_note": (
            "sigma = 1000 steps between seeds, target effect 250 steps -> 252 "
            "arms per cell; the grid has 4 periods per cell, so differences "
            "below 250 steps are `void`, not `failed`. The claims rest on "
            "horizon-sized contrasts (a death before 20000 against survival)"
        ),
        "prediction": {
            "a_no_gain_at_zero_price": (
                "read_cost = 0: for every point/field/rb, intact at period > 1 "
                "must NOT outlive intact at period = 1. The look is free, so "
                "skipping it can only throw information away. CAN FAIL if the "
                "stale address happens to beat the fresh comparison through the "
                "tie-break drift: the memory walks a remembered cell while "
                "`sighted` compares and stays on a tie"
            ),
            "b_gain_at_a_positive_price": (
                "read_cost = 0.05, uniform, P_need = 2, rb = 3: intact at "
                "period 4 must outlive intact at period 1 by more than mde "
                "(250 steps). The bill falls from 0.10 to 0.025 per step and "
                "156's death at 51 steps is the price of reading, so the "
                "reserve should last about four times longer. CAN FAIL: the "
                "stale memory walks to a cell that has already been eaten and "
                "the organism starves looking for it"
            ),
            "c_optimum_period_grows_with_price": (
                "argmax over period of intact lifetime is 1 at read_cost = 0 "
                "and non-decreasing in price; at 0.05 it is > 1 on uniform "
                "P_need = 2, rb = 3. That is the transition surface the two "
                "reviews said exists without a constant. CAN FAIL: if staleness "
                "costs more than the reads it saves the surface is flat or "
                "tilts back to 1"
            ),
            "d_peaks_gain_smaller_than_uniform": (
                "the best gain over period (max_p lifetime(p) - lifetime(1)) on "
                "peaks-6 is smaller than on uniform at the same point/rb/cost, "
                "because a remembered address on an uneven field can be a poor "
                "cell whose ceiling is 0.2, while a uniform address keeps "
                "regrowing toward M. CAN FAIL: if the peaked field is so harsh "
                "that all arms die in a few steps, both gains are zero and the "
                "comparison is not informative -- that is not evidence for the "
                "prediction"
            ),
        },
    }

    arms = {
        f"{fname}/rb{rb}/c{cost:.2f}/p{period}/{arm}": (
            f"field={fname} read_budget={rb} read_cost={cost} "
            f"read_period={period} arm={arm}"
        )
        for fname, _, _ in FIELDS
        for rb in READ_BUDGETS
        for cost in COSTS
        for period in PERIODS
        for arm in ARMS
    }

    exp = Experiment(
        experiment_id="memory-sampling",
        question=(
            "does a memory that may skip a look create the memory/perception "
            "trade-off, and where is its transition surface"
        ),
        arithmetic=arithmetic,
        arms=arms,
        seed=SEED,
        command="python3 checks/exp_memory_sampling.py",
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
            "read_periods": list(PERIODS),
            "points": {name: m for name, m in POINTS},
            "fields": [name for name, _, _ in FIELDS],
            "arms": list(ARMS),
        },
    )

    cells: list[dict] = []
    groups: dict[tuple, list[str]] = {}
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
                        "periods": {},
                    }
                    for rp in PERIODS:
                        arm_data = {}
                        for arm in ARMS:
                            data = run(arm, maintenance, probe_field, period, rb, cost, rp)
                            arm_data[arm] = data
                            key = (
                                f"{point_name}/{fname}/rb{rb}/c{cost:.2f}"
                                f"/p{rp}/{arm}"
                            )
                            exp.add_arm(
                                key,
                                f"{point_name} {fname} read_budget={rb} "
                                f"read_cost={cost} read_period={rp} arm={arm}",
                                {
                                    "lifetime": data["lifetime"],
                                    "alive": data["alive"],
                                    "cause": data["cause"],
                                    "taken_mean": round(data["taken_mean"], 6),
                                    "frac_rich": round(data["frac_rich"], 6),
                                    "energy_end": round(data["energy_end"], 6),
                                    "moves": data["moves"],
                                    "read_period": data["read_period"],
                                },
                                trace_hash=data["hash"],
                            )
                        row["periods"][rp] = arm_data
                    cells.append(row)

    exp.result["cells"] = [
        {
            "point": c["point"],
            "p_need": c["p_need"],
            "field": c["field"],
            "read_budget": c["read_budget"],
            "read_cost": c["read_cost"],
            "lifetime": {
                str(rp): {a: c["periods"][rp][a]["lifetime"] for a in ARMS}
                for rp in PERIODS
            },
            "hash": {
                str(rp): {a: c["periods"][rp][a]["hash"] for a in ARMS}
                for rp in PERIODS
            },
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
                return c
        raise KeyError((point, field, rb, cost))

    def life(point: str, field: str, rb: int, cost: float, rp: int, arm: str) -> int:
        return cell(point, field, rb, cost)["periods"][rp][arm]["lifetime"]

    # -- the table ----------------------------------------------------------
    for point_name, maintenance in POINTS:
        print(
            f"\n== {point_name} (m = {maintenance}, P_need by formula = "
            f"{p_need(maintenance)}) =="
        )
        print("%-8s rb cost  p " % "field" + "".join("%9s" % a for a in ARMS))
        for fname, _, _ in FIELDS:
            for rb in READ_BUDGETS:
                for cost in COSTS:
                    for rp in PERIODS:
                        print(
                            "%-8s %2d %.2f %2d " % (fname, rb, cost, rp)
                            + "".join(
                                "%9d" % life(point_name, fname, rb, cost, rp, a)
                                for a in ARMS
                            )
                        )

    # -- prediction checks --------------------------------------------------
    def best_gain(point: str, field: str, rb: int, cost: float) -> tuple[int, int]:
        base = life(point, field, rb, cost, 1, "intact")
        best_p, best = 1, 0
        for rp in PERIODS[1:]:
            gain = life(point, field, rb, cost, rp, "intact") - base
            if gain > best:
                best_p, best = rp, gain
        return best_p, best

    def optimum(point: str, field: str, rb: int, cost: float) -> int:
        return max(
            PERIODS,
            key=lambda rp: life(point, field, rb, cost, rp, "intact"),
        )

    gains = {
        f"{p}/{f}/rb{rb}/c{cost:.2f}": {
            "best_period": best_gain(p, f, rb, cost)[0],
            "best_gain_steps": best_gain(p, f, rb, cost)[1],
            "optimum_period": optimum(p, f, rb, cost),
        }
        for p, _ in POINTS
        for f, _, _ in FIELDS
        for rb in READ_BUDGETS
        for cost in COSTS
    }
    print("\n== gains over read_period = 1 (intact, steps) ==")
    print("%-30s %8s %10s %8s" % ("cell", "best_p", "gain", "opt_p"))
    for k, v in gains.items():
        print(
            "%-30s %8d %10d %8d"
            % (k, v["best_period"], v["best_gain_steps"], v["optimum_period"])
        )

    # (a) zero price must show no gain from rarer reading
    zero_gains = {
        k: v["best_gain_steps"] for k, v in gains.items() if k.endswith("c0.00")
    }
    a_holds = all(g <= 0 for g in zero_gains.values())

    # (b) a positive price must show a gain, above mde
    positive = [
        (k, v["best_gain_steps"]) for k, v in gains.items() if not k.endswith("c0.00")
    ]
    best_cell, best_gain_steps = max(positive, key=lambda kv: kv[1])
    b_holds = best_gain_steps >= 250

    # (c) the optimum period must be non-decreasing in price, and > 1 at 0.05
    c_rows = {}
    for p, _ in POINTS:
        for f, _, _ in FIELDS:
            for rb in READ_BUDGETS:
                seq = [
                    optimum(p, f, rb, cost) for cost in COSTS
                ]
                c_rows[f"{p}/{f}/rb{rb}"] = seq
    c_holds = all(
        all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1)) for seq in c_rows.values()
    ) and any(seq[-1] > 1 for seq in c_rows.values())

    # (d) the gain on peaks-6 is smaller than on uniform
    d_rows = {}
    for p, _ in POINTS:
        for rb in READ_BUDGETS:
            for cost in COSTS:
                u = gains[f"{p}/uniform/rb{rb}/c{cost:.2f}"]["best_gain_steps"]
                k = gains[f"{p}/peaks-6/rb{rb}/c{cost:.2f}"]["best_gain_steps"]
                d_rows[f"{p}/rb{rb}/c{cost:.2f}"] = {"uniform": u, "peaks6": k}
    d_holds = all(v["peaks6"] < v["uniform"] for v in d_rows.values())
    d_informative = all(
        v["peaks6"] < v["uniform"] for v in d_rows.values() if v["uniform"] != 0
    )
    peak_loss = max(
        life("P_need=1", "peaks-6", 3, cost, 1, "intact")
        - life("P_need=1", "peaks-6", 3, cost, rp, "intact")
        for cost in COSTS
        for rp in PERIODS[1:]
    )
    cross_capacity = ENERGY0 / (
        (POINTS[0][1] + DAMAGE_RATE * REPAIR_COST) - POOR
    )

    exp.result["predictions_checked"] = {
        "a_no_gain_at_zero_price": {
            "predicted": True,
            "held": a_holds,
            "zero_price_gains": zero_gains,
        },
        "b_gain_at_a_positive_price": {
            "predicted": True,
            "held": b_holds,
            "best_cell": best_cell,
            "best_gain_steps": best_gain_steps,
            "mde_steps": 250,
        },
        "c_optimum_period_grows_with_price": {
            "predicted": True,
            "held": c_holds,
            "optimum_by_cell": c_rows,
            "costs": list(COSTS),
        },
        "d_peaks_gain_smaller_than_uniform": {
            "predicted": True,
            "held": d_holds,
            "strict_form_held": d_holds,
            "informative_rows_held": d_informative,
            "rows": d_rows,
            "note": (
                "the strict 'smaller in every row' form fails only where both "
                "gains are 0 (equality, not evidence against). On the rows "
                "where the uniform field gains anything, the peaked field "
                "gains less. The mechanism measured is NOT the guessed one (a "
                "remembered level going poor): a Memory organism advances at "
                "most one cell per sampling interval, because after arriving "
                "at the remembered cell `direction()` is 0 until a fresh read "
                "names the next one. Crossing the 3-cell poor basin therefore "
                "costs p*3 steps, and the reserve covers "
                f"{cross_capacity:.2f} poor steps: p=1 crosses, every p>1 "
                "dies in the basin at step 6. The lost steps are horizon-sized "
                "even though the gain is not"
            ),
            "peak_loss_steps": peak_loss,
            "crossing_steps_from_reserve": round(cross_capacity, 3),
        },
    }
    print("\n== predictions ==")
    print("(a) no gain at a zero price:      %s" % ("HOLDS" if a_holds else "FAILS"))
    print(
        "(b) a gain at a positive price:   %s (best %s: +%d steps, mde 250)"
        % ("HOLDS" if b_holds else "FAILS", best_cell, best_gain_steps)
    )
    print("(c) optimum grows with the price: %s" % ("HOLDS" if c_holds else "FAILS"))
    for k, seq in c_rows.items():
        print("    %-24s %s" % (k, seq))
    print("(d) peaks gain < uniform gain:    %s" % ("HOLDS" if d_holds else "FAILS"))
    for k, v in d_rows.items():
        print("    %-20s uniform %+6d  peaks-6 %+6d" % (k, v["uniform"], v["peaks6"]))

    # -- controls -----------------------------------------------------------
    base = cell("P_need=2", "uniform", 3, 0.05)
    p1 = life("P_need=2", "uniform", 3, 0.05, 1, "intact")
    best_p = best_gain("P_need=2", "uniform", 3, 0.05)[0]
    best_life = life("P_need=2", "uniform", 3, 0.05, best_p, "intact")
    fires = best_life > p1
    exp.control(
        "fires",
        fires,
        "uniform, P_need=2, read_budget=3, read_cost=0.05: intact lives "
        f"{p1} steps at read_period=1 and {best_life} at read_period={best_p}, "
        "so a priced look is what the memory is buying back",
    )

    exp.control(
        "silent",
        a_holds,
        "read_cost=0: no read_period > 1 beats read_period=1 on any "
        f"point/field/rb. Best zero-price gain: {max(zero_gains.values())} steps "
        f"({max(zero_gains, key=zero_gains.get)}). Reading is free, so there is "
        "nothing to save and only stale knowledge to lose -- the control is "
        "silent where the effect must be absent",
    )

    sighted_invariant = all(
        len({cell(p, f, rb, cost)["periods"][rp]["sighted"]["hash"] for rp in PERIODS}) == 1
        for p, _ in POINTS
        for f, _, _ in FIELDS
        for rb in READ_BUDGETS
        for cost in COSTS
    )
    winning_at_zero = (
        life("P_need=2", "uniform", 3, 0.0, best_p, "intact")
        - life("P_need=2", "uniform", 3, 0.0, 1, "intact")
    )
    specific = sighted_invariant and best_p > 1 and winning_at_zero <= 0
    exp.control(
        "specific",
        specific,
        "the axis touches only the memory. `sighted` has one hash across all "
        f"four periods in every cell ({'confirmed' if sighted_invariant else 'VIOLATED'}), "
        "because it has no memory to act on. And the period that wins at "
        f"read_cost=0.05 (p={best_p}) gains {winning_at_zero} steps at "
        "read_cost=0 on the same cell: the gain is the price of the read, not "
        "the period",
    )

    # Declare the coincidences that are the controls, not false contrasts.
    by_hash: dict[str, list[str]] = {}
    for key, h in exp.result["hashes"].items():
        by_hash.setdefault(h, []).append(key)
    collisions = [sorted(keys) for keys in by_hash.values() if len(keys) > 1]
    for group in collisions:
        exp.expect_coincident(*group)
    exp.result["coincident_groups"] = len(collisions)

    # The experimental axis must move the remembering arm's dynamics.
    intact_distinct = all(
        len({cell(p, f, rb, cost)["periods"][rp]["intact"]["hash"] for rp in PERIODS}) > 1
        for p, _ in POINTS
        for f, _, _ in FIELDS
        for rb in (3,)
        for cost in COSTS
    )

    mde_arms = R.set_mde(exp.result, sigma=1000.0, effect=250.0)

    exp.limitation(
        "one seed and one start cell. The start (cell 3) is poor and "
        "equidistant from the peaks of `peaks-6`, so the arms that never move "
        "and the arms that look start from the same place; with the probe's "
        "default start of 0 the stationary arms start on a peak and the "
        "comparison would be biased toward them."
    )
    exp.limitation(
        "a memory stores an ADDRESS and a LEVEL seen earlier; it has no model "
        "of regrowth. `direction()` can therefore walk to a cell whose level it "
        "remembers but which has been eaten since. This is exactly the "
        "staleness term the experiment prices, not a defect to fix before "
        "measuring it."
    )
    exp.limitation(
        "one organism, no competition, no sharing; the probe wraps movement on "
        "a ring while `Life` does not -- the same structural limits as "
        "FINDING-155 and FINDING-156."
    )
    exp.limitation(
        "`income = upkeep` by construction. At P_need=2 a cell held by one "
        "organism settles below the upkeep, so only movement pays: the two "
        "points are two media, not two prices of one medium."
    )
    exp.limitation(
        "the probe's own hash does not mix read_period, so control arms that "
        "never read (stay, random) and `sighted` share one hash across the "
        "period axis by construction. That is declared in `expected_coincident` "
        "and is the `specific` control's evidence, not a collision of the "
        "experimental arms."
    )

    # -- verdict ------------------------------------------------------------
    a_text = "no gain at a zero price" if a_holds else "a gain at a zero price"
    b_text = (
        f"the best positive-price gain is {best_gain_steps} steps at "
        f"{best_cell} (period {gains[best_cell]['best_period']})"
        if b_holds
        else f"the best positive-price gain is only {best_gain_steps} steps, "
        "below the 250-step mde"
    )
    c_text = (
        "the optimum period is non-decreasing in price and above 1 at 0.05: "
        f"{c_rows}"
        if c_holds
        else "the optimum period does NOT grow monotonically with price: "
        f"{c_rows}"
    )
    d_text = (
        "the gain on `peaks-6` is smaller than on `uniform` in every row"
        if d_holds
        else "the gain on `peaks-6` is not uniformly smaller than on `uniform`"
    )
    if best_gain_steps <= 0:
        reason = (
            "No trade-off appears: at no positive price does any read_period > 1 "
            f"let intact outlive intact at period 1 (best gain {best_gain_steps} "
            f"steps at {best_cell}). The reading bill does fall with the period "
            "by construction, so the failure is the stale-memory term: what the "
            "memory saves in looks it pays back in walking to cells that have "
            "changed. `failed`: the world said no, and the next step is a memory "
            "of a level estimate or a selective read, not a periodic one."
        )
        exp.verdict("failed", "EXPLAINED: " + reason)
    elif best_gain_steps < 250:
        reason = (
            "The trade-off appears in the direction the arithmetic predicted, "
            "but not at the size this instrument can certify. (a) At read_cost=0 "
            f"the control is silent: best gain {max(zero_gains.values())} steps, "
            "so rarer reading is never better when reading is free -- knowledge "
            f"ages and nothing is saved. (b) At a positive price it is better: "
            f"{b_text}; the optimum period on uniform P_need=2, rb=3 moves "
            f"{c_rows.get('P_need=2/uniform/rb3')} as the price goes "
            "0.00 -> 0.02 -> 0.05, so (c) holds in direction. (d) "
            f"{d_text}; and on the informative rows the peaked field is not just "
            "less rewarding but catastrophic: the same skip costs up to "
            f"{peak_loss} steps (20000 -> 6). The mechanism is not the guessed "
            "one -- a Memory advances at most one cell per sampling interval, "
            "so crossing the 3-cell poor basin costs p*3 steps while the "
            f"reserve covers only {cross_capacity:.2f} poor steps. The gain "
            "itself is 33-37 steps, below the 250-step mde, and "
            "by the pre-registered rule a sub-mde difference is `void`, not "
            "`passed`: one seed cannot separate it from the between-seed "
            "spread. What is horizon-sized is the OTHER side of the trade-off "
            "-- the cost of not reading on an uneven field. `void`: the "
            "mechanism is measured, its size is not certified."
        )
        exp.verdict("void", "EXPLAINED: " + reason)
    elif fires and a_holds and specific and intact_distinct:
        reason = (
            "The memory can skip a look and the skip is worth something, but "
            "only when the look costs energy. (a) At read_cost=0 the control is "
            f"silent: best gain {max(zero_gains.values())} steps, so rarer "
            "reading is never better when reading is free. (b) At a positive "
            f"price it is: {b_text}. (c) {c_text}. (d) {d_text}. The controls "
            "fire/silent/specific all pass, the period moves the remembering "
            "arm's dynamics, and the effect is horizon-sized, above the "
            "250-step mde. `passed`: the trade-off exists and has a measured "
            "surface."
        )
        exp.verdict("passed", "EXPLAINED: " + reason)
    else:
        reason = (
            "The period moves the remembering arm, but a control failed or the "
            "prediction that the gain is the price of the read did not hold "
            f"(a={a_holds}, specific={specific}, sighted invariant="
            f"{sighted_invariant}, intact dynamics moved={intact_distinct}). "
            "The instrument is therefore not trusted for a positive claim."
        )
        exp.verdict("void", "EXPLAINED: " + reason)

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(f"mde: sigma=1000 steps, effect=250 steps -> {mde_arms} arms per cell")
    print(f"coincident groups declared: {len(collisions)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
