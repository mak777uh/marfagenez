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

The horizon is computed per point, not fixed (the task, and
`.dsh-switchman/REVIEW-6-...md:40-68`):

    T = 1/damage_rate + capacity / (maintenance_cost - taken + damage_rate*repair_cost)

which is the damage clock plus the energy clock, whichever runs out first.

## What is measured

For each grid point and each policy in `{stay, random, remember, memory,
sighted}`: lifetime (first step at which the organism is not alive, or `T` if
it survives), accumulated energy (sum of `energy` over the frames), and the
cause of death (`energy` / `damage` / `alive`).

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
#: in the result and any point that hits it is marked `horizon_capped`.
T_CAP = 20000

#: The measured horizon is `T` and `2T` (B2).
HORIZON_MULTIPLIERS = (1, 2)


def supply(m_field: float = M_FIELD, regrow: float = REGROW) -> float:
    """What an emptied cell can give in one step: `M * r`."""
    return m_field * regrow


def t_predicted(dr: float, rc: float, income: float, m_field: float = M_FIELD) -> int:
    """The horizon a point needs, from the two clocks that can kill it.

    The damage clock is `1/dr` steps (damage reaches 1). The energy clock is
    `capacity / deficit` where `deficit = maint - taken + dr*rc` is the net
    drain per step; it is infinite when the point sustains itself.
    """
    taken = min(income, supply(m_field))
    deficit = MAINT - taken + dr * rc
    damage_clock = 1.0 / dr
    energy_clock = CAPACITY / deficit if deficit > 0 else math.inf
    return int(math.ceil(min(damage_clock, energy_clock))) + 1


def rho(dr: float, rc: float, income: float) -> float:
    return dr * rc / income


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
        "horizon": "ceil(min(1/damage_rate, capacity/(maintenance - taken + damage_rate*repair_cost))) + 1",
        "horizon_cap": T_CAP,
        "prediction_P1": "the death cause changes at rho = 1 - maint/income, not at 0.8",
        "prediction_P2": "if the upper edge is the horizon, alive points double when T doubles",
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
    for dr in DAMAGE_RATES:
        for income in INCOMES:
            for rc in REPAIR_COSTS:
                t_pred = t_predicted(dr, rc, income)
                capped = t_pred > T_CAP
                t_used = min(t_pred, T_CAP)
                row = {
                    "damage_rate": dr,
                    "income": income,
                    "repair_cost": rc,
                    "rho": round(rho(dr, rc, income), 9),
                    "t_predicted": t_pred,
                    "t_capped": capped,
                    "sustains": predicted_alive(dr, rc, income),
                    "taken": min(income, supply()),
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
                print(
                    f"dr={dr:<6} income={income:<4} rc={rc:<5} "
                    f"rho={row['rho']:<8} T={t_used:<6} "
                    f"lifetimes={[row['arms'][p]['lifetime'] for p in POLICIES]} "
                    f"causes={[row['arms'][p]['cause'] for p in POLICIES]}",
                    flush=True,
                )

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
        "one organism on a uniform field: no competition, no sharing, no memory "
        "content. A policy that differs here differs for movement alone."
    )

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
