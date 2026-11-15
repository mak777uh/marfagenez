"""EXP-144: does the `rho` window of FINDING-143 exist in `core`?

## The question

`docs/FINDING-143.md` claims a window in

    rho = damage_rate * repair_cost / income

inside `0.4 .. 0.8` where the *repair strategy* decides whether an organism
lives, and outside which it does not. The claim was made on a Python mock with
four repair policies (`none` / `worst` / `round` / `cheapest`) that do not
exist in `core`, and the script that produced it is not in the tree.

`core` has one scalar `damage`, all-or-nothing repair, and five movement
policies. So the question this script can ask is narrower than the finding's:

    in `core`, at which `rho` does the *movement policy* change the lifetime,
    and is the boundary of that set a property of the world or of the horizon?

## The arithmetic, before the run (AGENTS.md §1)

`Organism::step` (`core/src/organism.rs:418`) does, per step, in order:

1. `taken = min(resource, income)`   -- `resource` is what `Field::take` gave
2. `energy += taken`
3. `energy -= maintenance_cost`
4. `damage += damage_rate` (capped at 1)
5. repair iff `damage * repair_cost < energy`: `energy -= damage*repair_cost`,
   `damage = 0`
6. `energy = min(energy, capacity)`
7. death iff `energy <= 0 || damage >= 1`

An organism that repairs every step therefore pays `damage_rate * repair_cost`
per step and holds `damage = 0`. Its per-step energy change is

    delta = taken - maintenance_cost - damage_rate * repair_cost

If the cell always supplies the full `income` (`income <= M * r`, so the field
is never the limit), `taken = income` and

    delta = income - maintenance_cost - damage_rate * repair_cost

which is exactly `World::sustains()` (`core/src/organism.rs:297-301`). Dividing
by `income`:

    sustains  <=>  rho <= 1 - maintenance_cost / income

With `maintenance_cost = 0.6` and `income = 1.0` this is `rho <= 0.4` -- the
lower edge of the window claimed by FINDING-143. **The prediction this script
tests is that the lower edge is not a finding but `sustains()` under another
name, and that the upper edge is where the horizon ends.**

Two predictions, both falsifiable:

* **P1 (lower edge).** At `income = 1.0, maintenance = 0.6`, every point with
  `rho < 0.4` that satisfies `income <= M*r` is `alive` for every policy at
  every horizon; every point with `rho > 0.4` is dead by `damage` for every
  policy. The death cause changes exactly at `rho = 0.4`, not at `0.8`.
* **P2 (upper edge).** If the upper edge is the horizon, then doubling `T`
  doubles the number of points that are `alive`, because an `alive` point is
  one whose predicted death time `1/damage_rate` is longer than `T`.

The horizon is computed per point, not fixed: it is an **upper bound** on the
lifetime of the point (see `t_predicted()`), so that a point recorded `alive`
at `T` is alive for real and not cut off. The bound is a **maximum** of two
clocks, not a minimum, because a successful repair resets the damage: the
damage clock can fire later than the energy that pays for the repair, and
the horizon has to cover the later one.

## A third prediction: the upper edge is arithmetic too (P3)

Repair is all-or-nothing and happens on the step where the reserve covers the
whole damage. The damage grows by `damage_rate` per step and is capped at 1.0;
death is tested at the end of the step **after** the repair attempt
(`core/src/organism.rs:418-460`). So the organism has to afford one repair per
`ceil(1/damage_rate)` steps, and the most expensive such repair (at
`damage = 1.0`) costs exactly `repair_cost`. Over those steps it accumulates
`ceil(1/damage_rate) * (taken - maintenance_cost)` energy. Prediction:

    alive forever  <=>  ceil(1/damage_rate) * (taken - maintenance_cost) >= repair_cost

In terms of `rho` the window becomes

    rho <= (1 - maintenance_cost / income) * damage_rate * ceil(1/damage_rate)

— the `sustains()` edge multiplied by `damage_rate * ceil(1/damage_rate)`,
which is 1.0 for small `damage_rate` and approaches 2.0 as `damage_rate`
approaches 1. The strictness of the inequality is not settled by this grid:
`price < energy` in the code suggests `>`, but no grid point lands on equality
(`cadence_energy == repair_cost`), so both readings are recorded as the same
prediction here.

Note that this condition **subsumes** `sustains()`: `surplus >= dr*rc` implies
`rc <= surplus/dr <= ceil(1/dr)*surplus`. The lower edge of the window is the
`dr -> 0` limit of the upper edge, not a separate law.

## What is measured

For each grid point and each policy in `{stay, random, remember, memory,
sighted}`: lifetime (first step at which the organism is not alive, or `T` if
it survives), accumulated energy (sum of `energy` over the frames), and the
cause of death (`energy` / `damage` / `alive`).

The whole per-point table is written to the result under `points` (144 rows x
5 policies), with `repair_every`, `cadence_energy` and `predicted_cadence`
beside the measured lifetime and cause, so the verdict can be checked by
reading the record instead of re-running it.

A point where every policy has the same lifetime and the same accumulated
energy is **not measured**, not "no question": it is counted separately.

## Why a Rust probe and not `core/target/release/trace`

The `trace` binary records a frame every `every` steps, and on a point that
dies early `record` stops when `advance()` returns `None` -- so the trace holds
no frame with `alive == false` and the death step cannot be read off it. The
JSON also rounds every number to six decimals, which makes two policies that
differ in the seventh digit look identical.

`core/examples/rho_probe.rs` is a read-only probe: it builds the same `World`,
`Field` and `Life` the binary builds, advances step by step, and prints the
step at which each organism stopped being alive and which bound it hit. It
links against the existing library and changes nothing in `core/src`.

Run: python3 checks/exp_rho_window.py
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys

try:
    from checks.experiment import Experiment
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from checks.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "rho_probe")

SEED = 1
MAINT = 0.6
CAPACITY = 10.0
MOVE_COST = 0.0
ENERGY0 = 5.0
CELLS = 8
REGROW = 0.8

#: The field level `M`. The cell supplies `S = M * r` per step.
#:
#: `regrow` is fixed at 0.8, so a cell that was emptied last step refills to
#: `M * 0.8`. The guard `income <= M * r` therefore needs `M >= income / 0.8`,
#: which for `income = 1.5` is `M >= 1.875`. `M = 2.0` covers the whole grid,
#: so the field is never the limit and `taken = income` in every point.
#: That is deliberate: this script measures the arithmetic of the organism,
#: not the field. B3 is a separate sweep with `M` varied.
M_FIELD = 2.0

DAMAGE_RATES = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3)
INCOMES = (0.3, 0.5, 0.7, 0.9, 1.0, 1.5)
REPAIR_COSTS = (1.5, 6.0, 24.0, 48.0)

POLICIES = ("stay", "random", "remember", "memory", "sighted")
READ_BUDGET = {"sighted": 1}

#: The horizon is capped so that the whole grid finishes. The cap is recorded
#: in the result and any point that hits it is marked `horizon_capped`. It is
#: also the bound for a point that is not self-supporting but whose energy does
#: not fall on its own: no finite clock is known there, and this grid's finite
#: lifetimes are far below the cap (see `t_predicted`).
T_CAP = 20000

#: The measured horizon is `T` and `2T` (B2).
HORIZON_MULTIPLIERS = (1, 2)

#: Headroom over the computed bound. The bound is a real number, the death
#: step is an integer, and the death is checked after the repair attempt, so
#: two steps cover the rounding on both sides.
T_MARGIN = 2


def supply(m_field: float = M_FIELD, regrow: float = REGROW) -> float:
    """What an emptied cell can give in one step: `M * r`."""
    return m_field * regrow


def t_predicted(dr: float, rc: float, income: float, m_field: float = M_FIELD) -> int:
    """An upper bound on the lifetime of the point, in steps.

    The bound is built from the step order in `core/src/organism.rs:418-460`
    and must hold for every run, not for the typical one: a point recorded
    `alive` at `T` is then alive for real, not cut off.

    Before any repair the per-step change is

        surplus = taken - maintenance_cost

    and one repair of one step of damage costs `dr * rc`. Three regimes:

    * `surplus >= dr * rc`: self-supporting (`World::sustains()`). The damage
      is cleared every step and the energy never falls, so the lifetime is
      unbounded. `T_CAP` here would only repeat the same frame, so the horizon
      is one damage clock, `1/dr`: the step at which the damage would have
      reached 1.0 without the repair.
    * `surplus < 0` (`drain > 0`): the energy falls by at least `drain` per
      step whatever the organism does -- a repair only spends more -- so death
      by energy cannot come later than `capacity / drain`. The damage clock
      can be *shorter* than the lifetime (a successful repair resets the
      damage), so the horizon is the maximum of the two clocks. The old
      formula took the minimum, i.e. the first clock to fire, not the last
      one that matters.
    * `surplus >= 0` but `surplus < dr * rc`: the energy does not fall on its
      own, so the energy clock is unbounded and the horizon is `T_CAP`. The
      damage clock alone is not an upper bound here: a repair resets the
      damage, and it is the energy that pays for it that eventually runs out.
      The old formula charged `dr * rc` every step and so saw a drain that
      is not there, which cut the horizon short.
    """
    taken = min(income, supply(m_field))
    surplus = taken - MAINT
    if surplus >= dr * rc:
        return int(math.ceil(1.0 / dr)) + T_MARGIN
    energy_clock = CAPACITY / -surplus if surplus < 0 else math.inf
    clock = max(1.0 / dr, energy_clock)
    if math.isinf(clock):
        return T_CAP
    return int(math.ceil(clock)) + T_MARGIN


def rho(dr: float, rc: float, income: float) -> float:
    return dr * rc / income


def repair_every(dr: float) -> int:
    """How often a repair is needed, in steps: `ceil(1 / damage_rate)`.

    The damage grows by `dr` per step from 0 after a repair and is capped at
    1.0, so the step at which it reaches the cap is `ceil(1/dr)`. The epsilon
    absorbs binary floating point: `1/0.003` is `333.33...` in mathematics but
    the float product can land a hair above or below an integer, and a repair
    cadence off by one step is a different prediction, not a rounding detail.
    """
    return int(math.ceil(1.0 / dr - 1e-9))


def predicted_alive(dr: float, rc: float, income: float, m_field: float = M_FIELD) -> bool:
    """`World::sustains()` for the point, with the field limit applied."""
    taken = min(income, supply(m_field))
    return taken - MAINT >= dr * rc


def run_arm(
    policy: str,
    dr: float,
    rc: float,
    income: float,
    steps: int,
    cells: int = CELLS,
    regrow: float = REGROW,
    m_field: float = M_FIELD,
) -> dict:
    """Runs one (policy, point) through the probe and returns its metrics."""
    cmd = [
        PROBE,
        "--policy", policy,
        "--cells", str(cells),
        "--n", "1",
        "--start-cell", "0",
        "--steps", str(steps),
        "--seed", str(SEED),
        "--m", repr(m_field),
        "--regrow", repr(regrow),
        "--income", repr(income),
        "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc),
        "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST),
        "--energy", repr(ENERGY0),
        "--capacity", repr(CAPACITY),
        "--read-budget", str(READ_BUDGET.get(policy, 0)),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return metrics_from_probe(json.loads(out))


def metrics_from_probe(probe: dict) -> dict:
    """Lifetime, accumulated energy and cause of death, from the probe output."""
    return {
        "lifetime": int(probe["lifetime"]),
        "cause": probe["cause"],
        "energy_acc": round(float(probe["energy_acc"]), 9),
        "energy_end": round(float(probe["energy_end"]), 9),
        "taken_mean": round(float(probe["taken_mean"]), 9),
        "trace_hash": str(probe["hash"]),
    }


def classify(points: list[dict]) -> dict:
    """Splits the grid into alive / damage / energy / mixed points."""
    out = {"alive": [], "damage": [], "energy": [], "mixed": []}
    for p in points:
        causes = {a["cause"] for a in p["arms"].values()}
        if causes == {"alive"}:
            out["alive"].append(p)
        elif causes == {"damage"}:
            out["damage"].append(p)
        elif causes == {"energy"}:
            out["energy"].append(p)
        else:
            out["mixed"].append(p)
    return out


def arm_spread(arms: dict) -> dict:
    """How much the policies differ at one point."""
    lifes = [a["lifetime"] for a in arms.values()]
    accs = [a["energy_acc"] for a in arms.values()]
    return {
        "lifetime_min": min(lifes),
        "lifetime_max": max(lifes),
        "lifetime_distinct": len(set(lifes)),
        "energy_distinct": len(set(accs)),
        "distinguished": len(set(lifes)) > 1 or len(set(accs)) > 1,
    }


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"no probe at {PROBE}; build it: cd core && cargo build --release --example rho_probe")
        return 2

    # -- §1 arithmetic, written before any run ------------------------------
    arithmetic = {
        "rho": "damage_rate * repair_cost / income",
        "sustains": "taken - maintenance_cost >= damage_rate * repair_cost",
        "sustains_in_rho": "rho <= 1 - maintenance_cost / income",
        "taken": f"min(income, M * regrow) = min(income, {supply():g}) -- the field is never the limit on this grid",
        "lower_edge_at_income_1": 1.0 - MAINT / 1.0,
        "horizon": (
            "upper bound on the lifetime, +2 steps: sustaining -> "
            "ceil(1/damage_rate); drain = maintenance - taken > 0 -> "
            "ceil(max(1/damage_rate, capacity/drain)); drain <= 0 and not "
            "sustaining -> t_cap"
        ),
        "horizon_cap": T_CAP,
        "prediction_P1": "the death cause changes at rho = 1 - maint/income, not at 0.8",
        "prediction_P2": "if the upper edge is the horizon, alive points double when T doubles",
        "cadence": (
            "repair is all-or-nothing and needed once per ceil(1/damage_rate) "
            "steps; the repair at the damage cap costs repair_cost, so "
            "alive <=> ceil(1/damage_rate) * (taken - maintenance_cost) >= repair_cost"
        ),
        "cadence_in_rho": (
            "rho <= (1 - maintenance_cost/income) * damage_rate * ceil(1/damage_rate)"
        ),
        "cadence_strictness": (
            "`price < energy` in the code suggests a strict `>`, but no grid "
            "point is at equality on this grid, so strict and non-strict are "
            "the same prediction here"
        ),
        "prediction_P3": (
            "P3 replaces `sustains()` as the alive test: it implies it, and "
            "the upper edge of the window is the lower edge times "
            "damage_rate * ceil(1/damage_rate)"
        ),
    }

    arms = {p: (p, f"policy={p}") for p in POLICIES}
    exp = Experiment(
        experiment_id="rho-window",
        question=(
            "Does the rho window of FINDING-143 exist in core, and is its "
            "boundary a property of the world or of the horizon?"
        ),
        arithmetic=arithmetic,
        arms=arms,
        seed=SEED,
        command="python3 checks/exp_rho_window.py",
        parameters={
            "damage_rate": list(DAMAGE_RATES),
            "income": list(INCOMES),
            "repair_cost": list(REPAIR_COSTS),
            "maintenance_cost": MAINT,
            "capacity": CAPACITY,
            "move_cost": MOVE_COST,
            "energy0": ENERGY0,
            "cells": CELLS,
            "regrow": REGROW,
            "m_field": M_FIELD,
            "policies": list(POLICIES),
            "read_budget": READ_BUDGET,
            "horizon_multipliers": list(HORIZON_MULTIPLIERS),
            "t_cap": T_CAP,
        },
    )

    # -- the grid -----------------------------------------------------------
    points = []
    points_out = []
    for dr in DAMAGE_RATES:
        for income in INCOMES:
            for rc in REPAIR_COSTS:
                t_pred = t_predicted(dr, rc, income)
                capped = t_pred > T_CAP
                t_used = min(t_pred, T_CAP)
                every = repair_every(dr)
                taken = min(income, supply())
                cadence_energy = every * (taken - MAINT)
                row = {
                    "damage_rate": dr,
                    "income": income,
                    "repair_cost": rc,
                    "rho": round(rho(dr, rc, income), 9),
                    "t_predicted": t_pred,
                    "t_capped": capped,
                    "sustains": predicted_alive(dr, rc, income),
                    "taken": taken,
                    "repair_every": every,
                    "cadence_energy": round(cadence_energy, 9),
                    "predicted_cadence": cadence_energy >= rc,
                    "arms": {},
                    "horizons": {},
                }
                for mult in HORIZON_MULTIPLIERS:
                    t_run = min(t_pred * mult, T_CAP)
                    per_arm = {}
                    for pol in POLICIES:
                        per_arm[pol] = run_arm(pol, dr, rc, income, t_run)
                    row["horizons"][str(mult)] = {
                        "t_run": t_run,
                        "arms": per_arm,
                        "spread": arm_spread(per_arm),
                    }
                row["arms"] = row["horizons"]["1"]["arms"]
                points.append(row)
                points_out.append({
                    "damage_rate": dr,
                    "repair_cost": rc,
                    "income": income,
                    "rho": row["rho"],
                    "taken": row["taken"],
                    "sustains": row["sustains"],
                    "repair_every": row["repair_every"],
                    "cadence_energy": row["cadence_energy"],
                    "predicted_cadence": row["predicted_cadence"],
                    "t": t_used,
                    "t_predicted": t_pred,
                    "t_capped": capped,
                    "alive": all(a["cause"] == "alive" for a in row["arms"].values()),
                    "policies": {
                        pol: {
                            "lifetime": row["arms"][pol]["lifetime"],
                            "cause": row["arms"][pol]["cause"],
                            "energy_acc": row["arms"][pol]["energy_acc"],
                        }
                        for pol in POLICIES
                    },
                })
                print(
                    f"dr={dr:<6} income={income:<4} rc={rc:<5} "
                    f"rho={row['rho']:<8} T={t_used:<6} "
                    f"lifetimes={[row['arms'][p]['lifetime'] for p in POLICIES]} "
                    f"causes={[row['arms'][p]['cause'] for p in POLICIES]}",
                    flush=True,
                )

    # -- P3: the cadence condition against the measured life ----------------
    # Every point of the table is compared, not just the boundary ones: the
    # prediction is a biconditional, so a point predicted dead and recorded
    # alive refutes it as surely as the other way round.
    exp.result["points"] = points_out
    cadence_mismatch = [
        p for p in points_out if p["predicted_cadence"] != p["alive"]
    ]
    cadence_hits = sum(1 for p in points_out if p["predicted_cadence"])
    cadence_actual = sum(1 for p in points_out if p["alive"])
    cadence_equality = [
        p for p in points_out if p["cadence_energy"] == p["repair_cost"]
    ]
    p3 = not cadence_mismatch

    # -- P1: the death cause against `sustains()` ---------------------------
    mismatches = [
        p for p in points
        if (p["arms"]["stay"]["cause"] == "alive") != p["sustains"]
        and not p["t_capped"]
    ]
    p1 = not mismatches

    # -- P2: does doubling T double the alive set? --------------------------
    def all_alive(p: dict, mult: str) -> bool:
        return all(a["cause"] == "alive" for a in p["horizons"][mult]["arms"].values())

    alive1 = sum(1 for p in points if all_alive(p, "1"))
    alive2 = sum(1 for p in points if all_alive(p, "2"))
    p2 = alive2 == 2 * alive1

    # -- B1: does the boundary depend on rho or on a factor? ----------------
    # Points with the same rho but different damage_rate. If the boundary is
    # a function of rho alone, points at equal rho agree on `alive`.
    by_rho: dict[float, list[dict]] = {}
    for p in points:
        by_rho.setdefault(p["rho"], []).append(p)
    b1_groups = {
        r: [(p["damage_rate"], p["income"], p["repair_cost"], p["sustains"])
            for p in ps]
        for r, ps in sorted(by_rho.items())
        if len({p["sustains"] for p in ps}) > 1
    }
    b1 = not b1_groups

    # -- B2: the upper edge at T and 2T -------------------------------------
    def edge(mult: str) -> tuple[float, float]:
        """The largest rho that is alive at this horizon, and the smallest dead."""
        alive = [p["rho"] for p in points if all_alive(p, mult)]
        dead = [p["rho"] for p in points if not all_alive(p, mult)]
        return (min(dead) if dead else math.inf, max(alive) if alive else -math.inf)

    e1 = edge("1")
    e2 = edge("2")
    b2_moves = e1[1] != e2[1]

    # -- B3: does the window reproduce when capacity really varies? ---------
    # `M` is varied so that `M * regrow` crosses `income`: at `M = 0.5` the
    # cell supplies 0.4 per step, at `M = 2.0` it supplies 1.6.
    b3 = []
    for dr in (0.01, 0.1):
        for rc in (1.5, 6.0, 24.0):
            for income in (0.5, 1.0, 1.5):
                for m_field in (0.5, 1.0, 2.0):
                    t_pred = t_predicted(dr, rc, income, m_field)
                    capped = t_pred > T_CAP
                    t_used = min(t_pred, T_CAP)
                    per_arm = {}
                    for pol in ("stay", "random"):
                        per_arm[pol] = run_arm(pol, dr, rc, income, t_used, m_field=m_field)
                    b3.append({
                        "damage_rate": dr,
                        "repair_cost": rc,
                        "income": income,
                        "m_field": m_field,
                        "supply": round(supply(m_field), 9),
                        "field_limited": supply(m_field) < income,
                        "rho": round(rho(dr, rc, income), 9),
                        "t_predicted": t_pred,
                        "t_used": t_used,
                        "t_capped": capped,
                        "sustains": predicted_alive(dr, rc, income, m_field),
                        "arms": per_arm,
                        "spread": arm_spread(per_arm),
                    })
    b3_mismatch = [
        r for r in b3
        if (r["arms"]["stay"]["cause"] == "alive") != r["sustains"]
        and not r["t_capped"]
    ]
    b3_field_limited = [r for r in b3 if r["field_limited"]]
    b3_field_limited_mismatch = [r for r in b3_field_limited if r in b3_mismatch]

    # -- what the policies distinguish --------------------------------------
    distinguished = [p for p in points if p["horizons"]["1"]["spread"]["distinguished"]]
    same = [p for p in points if not p["horizons"]["1"]["spread"]["distinguished"]]
    same_alive = [p for p in same if all_alive(p, "1")]
    same_dead = [p for p in same if not all_alive(p, "1")]

    # -- record the arms ----------------------------------------------------
    # One arm per policy, summarised over the whole grid: the number of points
    # at which the policy was alive at `T`. The hash is the probe's FNV hash of
    # the run at the reference point (the defaults of `World::default()`).
    ref = next(p for p in points
               if p["damage_rate"] == 0.01 and p["income"] == 1.0 and p["repair_cost"] == 1.5)
    for pol in POLICIES:
        alive_count = sum(1 for p in points if p["arms"][pol]["cause"] == "alive")
        exp.add_arm(
            pol,
            f"policy={pol}",
            {
                "alive_points_at_T": alive_count,
                "points": len(points),
                "reference_rho": ref["rho"],
                "reference_lifetime": ref["arms"][pol]["lifetime"],
                "reference_cause": ref["arms"][pol]["cause"],
                "reference_energy_acc": ref["arms"][pol]["energy_acc"],
            },
            trace_hash=ref["arms"][pol]["trace_hash"],
        )

    # -- controls (§2) ------------------------------------------------------
    exp.control(
        "fires",
        bool(distinguished),
        f"{len(distinguished)} of {len(points)} points have policies with different "
        f"lifetime or accumulated energy; "
        f"{len(same)} points are identical across all {len(POLICIES)} policies",
    )
    # `silent`: the points where the arithmetic says every policy must be alive
    # forever. There the control must see no difference.
    silent_points = [p for p in points if p["sustains"] and not p["t_capped"]]
    silent_bad = [p for p in silent_points if not all_alive(p, "1")]
    exp.control(
        "silent",
        not silent_bad,
        f"{len(silent_points)} points satisfy sustains() and every policy is alive "
        f"at T in all of them" if not silent_bad else
        f"{len(silent_bad)} of {len(silent_points)} sustaining points have a dead policy",
    )
    # `specific`: the control must separate the mechanism from any other with
    # the same direction. Here: the death cause is `damage` exactly where
    # `sustains()` is false and the horizon is long enough to see it, and
    # `energy` nowhere else. A run where every death is `damage` would pass
    # `fires` too; this one requires the two causes to be separated by the
    # predicate.
    damage_where_predicted = [
        p for p in points if not p["sustains"] and not p["t_capped"]
        and p["arms"]["stay"]["cause"] == "damage"
    ]
    energy_where_predicted = [
        p for p in points if p["sustains"] and not p["t_capped"]
        and p["arms"]["stay"]["cause"] == "energy"
    ]
    specific_ok = not energy_where_predicted and bool(damage_where_predicted)
    exp.control(
        "specific",
        specific_ok,
        f"death by damage at {len(damage_where_predicted)} non-sustaining points, "
        f"death by energy at {len(energy_where_predicted)} sustaining points "
        f"(must be 0: a sustaining point cannot starve)",
    )

    # -- limitations (§6) ---------------------------------------------------
    exp.limitation(
        "core has no repair policies: `none`/`worst`/`round`/`cheapest` do not "
        "exist, so the strategy the finding measured cannot be reproduced. What "
        "is measured here is the movement policy, which is a different question."
    )
    exp.limitation(
        "the grid fixes `M = 2.0` and `regrow = 0.8`, so `taken = min(income, 1.6)` "
        "and the field is never the limit. This measures the arithmetic of the "
        "organism, not the field. B3 varies `M` separately and is reported apart."
    )
    exp.limitation(
        "the horizon is capped at T_CAP steps; points that hit the cap are marked "
        "`t_capped` and excluded from the P1 comparison."
    )
    exp.limitation(
        "the cadence law is tested on 6 damage rates, 4 repair costs and 6 "
        "incomes, one seed, one organism per point. It is a law about this "
        "grid and this step order, not about every `dr`: `ceil(1/dr)` has "
        "jumps, and no grid point sits exactly on `cadence_energy == "
        "repair_cost`, so the strictness of the inequality is not measured."
    )
    exp.limitation(
        "the per-point table is in `points` (144 rows x 5 policies), so the "
        "verdict is now checkable by reading the record; it still says nothing "
        "about a point outside the grid."
    )
    exp.limitation(
        "the horizon is an upper bound on the lifetime, not the lifetime: it is "
        "chosen so that no death inside it is missed, and the step it names is "
        "not the step of death. Where the point is perennial it is one damage "
        "clock; where the energy cannot fall on its own it is `T_CAP`."
    )
    exp.limitation(
        "one organism on a uniform field: no competition, no sharing, no memory "
        "content. A policy that differs here differs for movement alone."
    )
    exp.limitation(
        "two pairs of arms share a dynamics hash and are one arm, not two: "
        "`sighted` with `read_budget = 1` on a uniform field reads the cell it "
        "stands on and nothing else, which is `stay`; `memory` and `remember` "
        "differ only in what they do with a remembered value, and on a uniform "
        "field the remembered value never differs from the fresh one. Five "
        "policy names are three policy dynamics on this grid."
    )
    exp.expect_coincident("sighted", "stay")
    exp.expect_coincident("memory", "remember")

    # -- verdict (§4) -------------------------------------------------------
    reason = (
        f"P1 (lower edge = sustains()) {'confirmed' if p1 else 'refuted'}: "
        f"{len(mismatches)} of {len(points)} points disagree with the predicate. "
        f"P2 (upper edge = horizon) {'confirmed' if p2 else 'refuted'}: "
        f"{alive1} alive points at T, {alive2} at 2T. "
        f"B1 (boundary depends on rho alone) {'confirmed' if b1 else 'refuted'}: "
        f"{len(b1_groups)} rho values split across factors. "
        f"B2 (upper edge moves with T): {'yes' if b2_moves else 'no'}, "
        f"largest alive rho {e1[1]} at T and {e2[1]} at 2T. "
        f"P3 (alive <=> ceil(1/dr)*(taken-maint) >= rc) "
        f"{'confirmed' if p3 else 'refuted'}: {len(cadence_mismatch)} of "
        f"{len(points_out)} points disagree, {cadence_hits} predicted alive and "
        f"{cadence_actual} measured alive; {len(cadence_equality)} points at "
        f"equality, so this grid does not settle `>` against `>=`. "
        f"B3 (window reproduces when the field varies): "
        f"{'yes' if not b3_mismatch else 'no'}, {len(b3_mismatch)} of {len(b3)} "
        f"points disagree with the predicate "
        f"({len(b3_field_limited_mismatch)} of {len(b3_field_limited)} field-limited). "
        f"Policies distinguished at {len(distinguished)} of {len(points)} points; "
        f"{len(same_alive)} points identical because every policy is alive, "
        f"{len(same_dead)} because every policy is dead."
    )
    if exp.controls_passed() and exp.hashes_are_distinct():
        exp.verdict("passed", reason)
    else:
        exp.verdict("void", "VOID: " + reason)

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
