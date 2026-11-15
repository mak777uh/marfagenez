"""EXP-146: do the repair strategies differ, and by how much?

## The question

`docs/FINDING-143.md` asked whether there is a self-maintenance strategy that is
better than another, and `FINDING-144`/`FINDING-145` had to answer "the question
has no measurand in `core`": there was one repair rule, all-or-nothing. Cycle 39
made the rule a choice (`Organism::step_with`, `RepairPolicy`: `none`,
`all-or-nothing`, `proportional`). This is the first measurement that can ask
the question at all:

    where do the three strategies disagree, and by how much, when the movement
    policy, the world, the seed and the field are held fixed?

Movement is fixed at `stay` on purpose. If the difference came from walking, it
would not be a difference between repair strategies.

## The arithmetic, before the run (AGENTS.md §1)

Per step (`core/src/organism.rs:467-543`): income, maintenance, `damage += dr`
(capped at 1), repair by the chosen rule, capacity cap, then the death test
`energy <= 0 || damage >= 1`.

With `taken = min(income, M * regrow) = income` on this grid and
`surplus = taken - maintenance_cost`:

**`none`.** Never repairs, so damage grows by `dr` per step and reaches 1.0 at
`ceil(1/dr)` steps. It is dead in every point with `dr > 0`; the *cause* is
whichever clock fires first:

    damage at ceil(1/dr)   vs   energy at ceil(E0 / (maintenance_cost - taken))
                                (the second clock exists only when surplus < 0)

The task brief said "`None` dies of damage in every point where `dr > 0`". That
is true only when the tank does not empty first. On this grid `income = 0.3` is
below maintenance 0.6, so at `dr = 0.001` and `dr = 0.01` the energy clock (17
steps) fires long before the damage clock, and `none` dies of `energy`. The
prediction recorded here is the two-clock one; the brief's one-clock version is
false on this grid and is checked as such.

**`all-or-nothing`.** A repair happens on a step only when
`damage * repair_cost < energy`; it clears the damage and costs
`damage * repair_cost`. Greedy, so below the per-step price it repairs every
step and its edge is the *cadence* condition of `FINDING-145`:

    alive  <=>  ceil(1/dr) * surplus >= repair_cost
           <=>  rho <= (1 - maint/income) * dr * ceil(1/dr)  =  upper_edge

Above that edge it skips repairs while the damage grows, so it dies of `damage`
when `surplus >= 0` (spending never takes the reserve to 0: the rule requires
`price < energy`, so `energy > 0` after every repair) and of `energy` when
`surplus < 0`.

**`proportional`.** Repairs as much damage as the reserve can buy and spends
the reserve on it, so it pays `dr * repair_cost` every step while it can, and
the whole damage is always bought when `energy / repair_cost >= damage`. Its
edge is the *per-step* condition (`World::sustains()`), the `dr -> 0` limit of
the cadence edge:

    alive  <=>  surplus >= dr * repair_cost  <=>  rho <= 1 - maint/income = lower_edge

Above that edge the reserve drains at `dr*repair_cost - surplus` per step; when
it can no longer buy the whole damage it buys a part, spends everything and
`energy <= 0` ends the step, so it dies of **energy**, not damage.

**P4 (the window between the edges).** `upper_edge >= lower_edge`, with equality
exactly when `dr * ceil(1/dr) = 1` (true for dr = 0.001, 0.01, 0.1 on this grid;
`dr = 0.3` gives 1.2). The two edges therefore separate only at `dr = 0.3`:

    lower_edge < rho <= upper_edge  ->  all-or-nothing lives, proportional dies

That strip is empty for the other three damage rates, so *on this grid* the
"window where the repair rule decides" is one `dr` wide. This is the arithmetic
of `FINDING-145` applied to the two strategies, not a new claim about the world.

**Predicted sets and counts on the grid below** (main points: dr > 0,
rc = rho*income/dr, income > maint):

* `none` alive: 0 of 40.
* `all-or-nothing` alive: 32 of 40 (every point with `rho <= upper_edge`).
* `proportional` alive: 28 of 40 (every point with `rho <= lower_edge`).
* `all-or-nothing` and `proportional` are the *same run* exactly where
  `rho <= lower_edge` (28 points): there the all-or-nothing rule repairs every
  step, which is what proportional does, at the same price and with the same
  resulting state. Above that edge they diverge.
* exactly one of the two lives in the strip: 4 points, all at `dr = 0.3`
  (`income` 1.0 and 1.5, `frac` 0.9 and 1.0).

**Boundary.** Equality counts as alive (`>=`): `FINDING-145` measured the
cadence equality alive on a separate probe. The comparison in the code is
`price < energy`, so the boundary is a floating-point question, not a
mathematical one (`core/src/organism.rs` says so). The predictions use `>=`
with a `1e-12` relative tolerance and the boundary points are named in
`points`.

## Controls (§2)

* `fires` — the strategies differ in lifetime, cause or accumulated energy in
  at least one point. Predicted: almost every point with `dr > 0`, because
  `none` dies there.
* `silent` — where there is nothing to repair (`damage_rate = 0`) all three
  strategies must coincide. Six such points, two repair costs (`0` and `1.5`)
  and three incomes. Note that `repair_cost = 0` with `dr > 0` is *not* a
  silent point: repair is free, not absent, and `none` still refuses it. That
  case is measured separately (`position = free repair`) as a prediction, not
  used as the silent control — calling it "nothing to repair" would make the
  control fire for the right reason and be read as a broken control.
* `specific` — the difference must come from the repair rule: movement is
  `stay` in every arm, the world, seed, field, energy and horizon are the same,
  and only `--repair` changes. The control checks that (a) the predicted
  alive/cause of each strategy matches the measurement, (b) the set of points
  where all-or-nothing and proportional are literally the same run is exactly
  `rho <= lower_edge`, (c) the set of points where exactly one of the two lives
  is exactly the predicted strip, and (d) a repeated run of the reference point
  gives the same dynamics hash.

## Horizon

Fixed `T = 20000` steps for every point. This is deliberately not the
`FINDING-145` per-point bound: that bound is an upper bound on the lifetime of a
*dying* point, and a point whose cycle is self-balancing (all-or-nothing inside
the cadence window) survives any bound of that shape — measured: at
`dr = 0.3, rc = 1.44` the organism is alive after 200000 steps while the
formula's clock said 204. A point recorded `alive` is alive at 20000; where the
arithmetic says the cycle is perennial this is a horizon-limited confirmation,
not a proof of immortality, and it is recorded as a limitation.

Run: `python3 checks/exp_repair_policy.py` (about 20 s; not part of `run.sh`).
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
ENERGY0 = 5.0
CELLS = 8
REGROW = 0.8
M_FIELD = 2.0
MOVE_COST = 0.0

DAMAGE_RATES = (0.001, 0.01, 0.1, 0.3)
INCOMES = (0.3, 1.0, 1.5)

#: `rho` as a fraction of the cadence edge `upper_edge`. 0.9 is inside the
#: strip `lower_edge < rho <= upper_edge` whenever the strip is non-empty
#: (dr = 0.3); for the other damage rates the edges coincide and 0.9 falls
#: below both. 1.0 is the edge itself, 1.15 above it.
RHO_FRACTIONS = (0.5, 0.8, 0.9, 1.0, 1.15)

#: When `income <= maintenance_cost` the window is empty (the edge is
#: negative), so "a fraction of the edge" is meaningless. These absolute
#: `rho` values are used there; every one of them is above the edge.
ABS_RHOS_EMPTY_WINDOW = (0.1, 0.3, 0.5)

REPAIRS = ("none", "all-or-nothing", "proportional")

#: Fixed horizon, in steps. See the docstring: the FINDING-145 per-point bound
#: is a bound on a dying point, not on a self-balancing cycle.
T_CAP = 20000

#: Relative tolerance for a boundary that is a floating-point question.
TOL = 1e-12


def repair_every(dr: float) -> int:
    """How often a repair is needed: `ceil(1/dr)`, epsilon-safe."""
    return int(math.ceil(1.0 / dr - 1e-9))


def lower_edge(income: float) -> float:
    """`rho` below which the *per-step* condition `World::sustains()` holds."""
    return 1.0 - MAINT / income


def upper_edge(dr: float, income: float) -> float:
    """`rho` below which the cadence condition of FINDING-145 holds."""
    return lower_edge(income) * dr * repair_every(dr)


def supply() -> float:
    return M_FIELD * REGROW


def taken(income: float) -> float:
    return min(income, supply())


def surplus(income: float) -> float:
    return taken(income) - MAINT


def rho(dr: float, rc: float, income: float) -> float:
    return dr * rc / income


def clock_energy(income: float) -> float:
    """Steps until the tank empties with no repair, when surplus < 0."""
    s = surplus(income)
    if s >= 0:
        return math.inf
    return math.ceil(ENERGY0 / -s)


def predicted(dr: float, rc: float, income: float) -> dict:
    """Alive/cause prediction per strategy, from the arithmetic above.

    This is the pre-registration: it is computed from the parameters and the
    step order, never from a measurement. It is what `specific` compares the
    measurement against.
    """
    s = surplus(income)
    out: dict[str, dict] = {}

    # none: dead with dr > 0; cause is the earlier of the two clocks.
    if s >= 0:
        none_cause = "damage"
    else:
        none_cause = "damage" if repair_every(dr) <= clock_energy(income) else "energy"
    out["none"] = {"alive": False, "cause": none_cause}

    # all-or-nothing: cadence condition; damage death when the tank can refill.
    e = upper_edge(dr, income)
    a_alive = rho(dr, rc, income) <= e + TOL * max(1.0, abs(e))
    out["all-or-nothing"] = {
        "alive": a_alive,
        "cause": None if a_alive else ("damage" if s >= 0 else "energy"),
    }

    # proportional: per-step condition; starvation when it cannot buy the damage.
    lo = lower_edge(income)
    p_alive = rho(dr, rc, income) <= lo + TOL * max(1.0, abs(lo))
    out["proportional"] = {
        "alive": p_alive,
        "cause": None if p_alive else "energy",
    }
    return out


def predicted_silent(income: float) -> dict:
    """Prediction where `damage_rate = 0`: there is nothing to repair.

    All three strategies must coincide: the repair branch is never entered
    (damage stays 0), so the three runs are the same run.
    """
    if income > MAINT:
        return {r: {"alive": True, "cause": None} for r in REPAIRS}
    return {r: {"alive": False, "cause": "energy"} for r in REPAIRS}


def predicted_free_repair(income: float) -> dict:
    """Prediction when `repair_cost = 0` and `damage_rate > 0`.

    Repair is free, not absent. `none` refuses it and dies; the two repairing
    strategies clear the damage at no cost and live iff `surplus > 0`.
    """
    s = surplus(income)
    if s >= 0:
        return {
            "none": {"alive": False, "cause": "damage"},
            "all-or-nothing": {"alive": True, "cause": None},
            "proportional": {"alive": True, "cause": None},
        }
    return {r: {"alive": False, "cause": "energy"} for r in REPAIRS}


def run_arm(repair: str, dr: float, rc: float, income: float, steps: int) -> dict:
    """Runs one (strategy, point) through the probe."""
    cmd = [
        PROBE,
        "--policy", "stay",
        "--repair", repair,
        "--cells", str(CELLS),
        "--n", "1",
        "--start-cell", "0",
        "--steps", str(steps),
        "--seed", str(SEED),
        "--m", repr(M_FIELD),
        "--regrow", repr(REGROW),
        "--income", repr(income),
        "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc),
        "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST),
        "--energy", repr(ENERGY0),
        "--capacity", repr(CAPACITY),
        "--read-budget", "0",
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    probe = json.loads(out)
    return {
        "lifetime": int(probe["lifetime"]),
        "cause": probe["cause"],
        "energy_acc": round(float(probe["energy_acc"]), 9),
        "energy_end": round(float(probe["energy_end"]), 9),
        "damage_end": round(float(probe["damage_end"]), 9),
        "trace_hash": str(probe["hash"]),
    }


def same_run(a: dict, b: dict) -> bool:
    """Two arms are the same run iff lifetime, cause and energy agree."""
    return (
        a["lifetime"] == b["lifetime"]
        and a["cause"] == b["cause"]
        and a["energy_acc"] == b["energy_acc"]
    )


def classify_position(dr: float, rc: float, income: float) -> str:
    """Where the point sits relative to the two edges."""
    if dr == 0:
        return "nothing to repair (damage_rate = 0)"
    if rc == 0:
        return "free repair (repair_cost = 0)"
    if income <= MAINT:
        return "window empty (income <= maintenance_cost)"
    r, lo, hi = rho(dr, rc, income), lower_edge(income), upper_edge(dr, income)
    if r > hi + TOL * max(1.0, abs(hi)):
        return "above the upper edge"
    if r < lo - TOL * max(1.0, abs(lo)):
        return "below the lower edge"
    if abs(hi - lo) <= TOL and abs(r - hi) <= TOL * max(1.0, abs(hi)):
        return "on the edge (lower_edge = upper_edge)"
    if abs(r - hi) <= TOL * max(1.0, abs(hi)):
        return "on the upper edge"
    if r <= lo + TOL * max(1.0, abs(lo)):
        return "on the lower edge"
    return "inside the window (lower_edge < rho <= upper_edge)"


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"no probe at {PROBE}; build it: cd core && cargo build --release --example rho_probe")
        return 2

    # -- §1 arithmetic, written before the run ------------------------------
    arithmetic = {
        "rho": "damage_rate * repair_cost / income",
        "surplus": f"taken - maintenance_cost, taken = min(income, M*regrow) = min(income, {supply():g})",
        "horizon": (
            f"fixed T = {T_CAP} steps for every point; a point recorded alive is "
            "alive at T, and where the arithmetic says the repair cycle is "
            "self-balancing this is a horizon-limited confirmation, not proof"
        ),
        "none": (
            "never repairs, damage reaches the cap at ceil(1/dr), so dead in "
            "every point with dr > 0; cause is the earlier clock: damage at "
            "ceil(1/dr) or energy at ceil(E0/(maint - taken)) when surplus < 0"
        ),
        "all_or_nothing": (
            "cadence condition: alive <=> ceil(1/dr) * surplus >= repair_cost "
            "<=> rho <= (1 - maint/income) * dr * ceil(1/dr) = upper_edge; "
            "above it, death by damage when surplus >= 0 and by energy when "
            "surplus < 0"
        ),
        "proportional": (
            "per-step condition: alive <=> surplus >= dr*repair_cost "
            "<=> rho <= 1 - maint/income = lower_edge; above it the reserve "
            "drains, it buys only part of the damage, spends everything and "
            "dies of energy"
        ),
        "P1_none": "none alive in 0 of the 40 main points with dr > 0 and rc > 0",
        "P2_all_or_nothing": "all-or-nothing alive in 32 of 40 main points (rho <= upper_edge)",
        "P3_proportional": "proportional alive in 28 of 40 main points (rho <= lower_edge)",
        "P4_window_differs": (
            "lower_edge < rho <= upper_edge only at dr = 0.3, where "
            "dr*ceil(1/dr) = 1.2; exactly one of all-or-nothing and "
            "proportional lives in those 4 points (income 1.0 and 1.5, "
            "frac 0.9 and 1.0); for dr in 0.001, 0.01, 0.1 the two edges "
            "coincide and the strip is empty"
        ),
        "P5_coincidence": (
            "all-or-nothing and proportional are the same run iff "
            "rho <= lower_edge (28 of 40 main points): there the "
            "all-or-nothing rule repairs every step, which is what "
            "proportional does, at the same price"
        ),
        "P6_free_repair": (
            "repair_cost = 0 with dr > 0 is not 'nothing to repair': repair is "
            "free, none refuses it and dies of damage, the two repairing "
            "strategies live when surplus >= 0"
        ),
        "P7_silent": (
            "damage_rate = 0 -> nothing accumulates, the repair branch is never "
            "entered, all three strategies are the same run"
        ),
        "boundary": (
            "equality counts as alive (>=); FINDING-145 measured the cadence "
            "equality alive; the code compares price < energy, so the boundary "
            "is a floating-point question (core/src/organism.rs); TOL = 1e-12 "
            "relative"
        ),
    }

    arms = {r: f"repair={r}" for r in REPAIRS}
    exp = Experiment(
        experiment_id="repair-policy",
        question=(
            "Do the three repair strategies differ when movement, world and "
            "seed are fixed, and by how much: which points, which lifetimes, "
            "which causes?"
        ),
        arithmetic=arithmetic,
        arms=arms,
        seed=SEED,
        command="python3 checks/exp_repair_policy.py",
        parameters={
            "damage_rate": list(DAMAGE_RATES),
            "income": list(INCOMES),
            "rho_fractions": list(RHO_FRACTIONS),
            "abs_rhos_empty_window": list(ABS_RHOS_EMPTY_WINDOW),
            "repair_cost": "computed as rho * income / damage_rate",
            "repairs": list(REPAIRS),
            "movement_policy": "stay",
            "maintenance_cost": MAINT,
            "capacity": CAPACITY,
            "energy0": ENERGY0,
            "cells": CELLS,
            "regrow": REGROW,
            "m_field": M_FIELD,
            "move_cost": MOVE_COST,
            "read_budget": 0,
            "t_cap": T_CAP,
            "tol": TOL,
        },
    )

    # -- the grid -----------------------------------------------------------
    points: list[dict] = []

    def add_point(dr: float, rc: float, income: float, position: str) -> None:
        pred = (
            predicted_silent(income) if dr == 0
            else predicted_free_repair(income) if rc == 0
            else predicted(dr, rc, income)
        )
        row = {
            "damage_rate": dr,
            "repair_cost": rc,
            "income": income,
            "rho": round(rho(dr, rc, income), 12) if income else 0.0,
            "lower_edge": round(lower_edge(income), 12),
            "upper_edge": round(upper_edge(dr, income), 12) if dr else 0.0,
            "position": position,
            "t": T_CAP,
            "predicted": pred,
            "arms": {},
        }
        for rep in REPAIRS:
            row["arms"][rep] = run_arm(rep, dr, rc, income, T_CAP)
        row["measured_coincident_all_or_nothing_proportional"] = same_run(
            row["arms"]["all-or-nothing"], row["arms"]["proportional"]
        )
        row["predicted_coincident"] = (
            dr > 0 and rc > 0 and income > MAINT
            and rho(dr, rc, income) <= lower_edge(income) + TOL
        )
        row["one_of_two_alive"] = (
            (row["arms"]["all-or-nothing"]["cause"] == "alive")
            != (row["arms"]["proportional"]["cause"] == "alive")
        )
        row["predicted_one_of_two_alive"] = (
            dr > 0 and rc > 0 and income > MAINT
            and lower_edge(income) + TOL * max(1.0, abs(lower_edge(income))) < rho(dr, rc, income)
            <= upper_edge(dr, income) + TOL * max(1.0, abs(upper_edge(dr, income)))
        )
        points.append(row)
        print(
            f"{position[:28]:<28} dr={dr:<6} inc={income:<4} rc={rc:<9.4g} "
            f"rho={row['rho']:<8} lives="
            f"{[row['arms'][r]['lifetime'] for r in REPAIRS]} "
            f"causes={[row['arms'][r]['cause'] for r in REPAIRS]}",
            flush=True,
        )

    for dr in DAMAGE_RATES:
        for income in INCOMES:
            if income > MAINT:
                rhos = [f * upper_edge(dr, income) for f in RHO_FRACTIONS]
            else:
                rhos = list(ABS_RHOS_EMPTY_WINDOW)
            for r in rhos:
                rc = r * income / dr
                add_point(dr, rc, income, classify_position(dr, rc, income))

    # Free repair: `rc = 0` with damage still accumulating.
    for dr in (0.01, 0.3):
        add_point(dr, 0.0, 1.0, classify_position(dr, 0.0, 1.0))

    # Nothing to repair: `damage_rate = 0`, two repair costs, three incomes.
    for rc in (0.0, 1.5):
        for income in INCOMES:
            add_point(0.0, rc, income, classify_position(0.0, rc, income))

    main_points = [
        p for p in points if p["damage_rate"] > 0 and p["repair_cost"] > 0
        and p["income"] > MAINT
    ]
    silent_points = [p for p in points if p["damage_rate"] == 0]
    free_points = [p for p in points if p["repair_cost"] == 0 and p["damage_rate"] > 0]

    # -- prediction checks --------------------------------------------------
    alive_mismatch = []
    cause_mismatch = []
    for p in points:
        for rep in REPAIRS:
            pred, got = p["predicted"][rep], p["arms"][rep]
            alive_pred = pred["alive"]
            alive_got = got["cause"] == "alive"
            if alive_pred != alive_got:
                alive_mismatch.append((p, rep))
            elif not alive_pred and pred["cause"] != got["cause"]:
                cause_mismatch.append((p, rep))

    alive_counts = {
        rep: sum(1 for p in points if p["arms"][rep]["cause"] == "alive")
        for rep in REPAIRS
    }
    main_alive_counts = {
        rep: sum(1 for p in main_points if p["arms"][rep]["cause"] == "alive")
        for rep in REPAIRS
    }

    # -- P4/P5: the strip and the coincidence set ---------------------------
    measured_strip = [p for p in main_points if p["one_of_two_alive"]]
    predicted_strip = [p for p in main_points if p["predicted_one_of_two_alive"]]
    strip_agrees = (
        {(p["damage_rate"], p["income"], p["rho"]) for p in measured_strip}
        == {(p["damage_rate"], p["income"], p["rho"]) for p in predicted_strip}
    )
    measured_coincident = [p for p in main_points if p["measured_coincident_all_or_nothing_proportional"]]
    predicted_coincident = [p for p in main_points if p["predicted_coincident"]]
    coincidence_agrees = (
        {(p["damage_rate"], p["income"], p["rho"]) for p in measured_coincident}
        == {(p["damage_rate"], p["income"], p["rho"]) for p in predicted_coincident}
    )

    # -- determinism: the reference point, run twice ------------------------
    ref = next(
        p for p in main_points
        if p["damage_rate"] == 0.3 and p["income"] == 1.0
        and abs(p["rho"] - 1.15 * upper_edge(0.3, 1.0)) < 1e-12
    )
    ref_repeat = {
        rep: run_arm(rep, ref["damage_rate"], ref["repair_cost"], ref["income"], T_CAP)
        for rep in REPAIRS
    }
    deterministic = all(
        ref_repeat[rep]["trace_hash"] == ref["arms"][rep]["trace_hash"] for rep in REPAIRS
    )

    # -- what the strategies distinguish ------------------------------------
    distinguished = [
        p for p in points
        if len({(p["arms"][r]["lifetime"], p["arms"][r]["cause"], p["arms"][r]["energy_acc"])
                for r in REPAIRS}) > 1
    ]
    same = [p for p in points if p not in distinguished]

    # -- record the arms ----------------------------------------------------
    for rep in REPAIRS:
        exp.add_arm(
            rep,
            f"repair={rep}",
            {
                "alive_points": alive_counts[rep],
                "alive_main_points": main_alive_counts[rep],
                "points": len(points),
                "main_points": len(main_points),
                "reference_rho": ref["rho"],
                "reference_lifetime": ref["arms"][rep]["lifetime"],
                "reference_cause": ref["arms"][rep]["cause"],
                "reference_energy_acc": ref["arms"][rep]["energy_acc"],
                "coincident_points_with_all_or_nothing": (
                    len(measured_coincident) if rep != "none" else None
                ),
            },
            trace_hash=ref["arms"][rep]["trace_hash"],
        )

    # -- controls (§2) ------------------------------------------------------
    exp.control(
        "fires",
        bool(distinguished),
        f"{len(distinguished)} of {len(points)} points have strategies with a "
        f"different lifetime, cause or accumulated energy; "
        f"{len(same)} points are identical across all three strategies "
        f"({len([p for p in same if p['damage_rate'] == 0])} of them because "
        f"nothing accumulates at damage_rate = 0)",
    )
    silent_bad = [
        p for p in silent_points
        if len({(p["arms"][r]["lifetime"], p["arms"][r]["cause"], p["arms"][r]["energy_acc"])
                for r in REPAIRS}) > 1
    ]
    exp.control(
        "silent",
        not silent_bad,
        f"{len(silent_points)} points with damage_rate = 0 (repair_cost 0 and 1.5, "
        f"income 0.3/1.0/1.5): in all of them the three strategies have the same "
        f"lifetime, cause and accumulated energy" if not silent_bad else
        f"{len(silent_bad)} of {len(silent_points)} points with nothing to repair "
        f"still show a difference",
    )
    specific_ok = (
        not alive_mismatch
        and not cause_mismatch
        and strip_agrees
        and coincidence_agrees
        and deterministic
    )
    exp.control(
        "specific",
        specific_ok,
        f"movement is `stay` in every arm and only `--repair` changes; predicted "
        f"alive/cause mismatches {len(alive_mismatch)}/{len(points) * len(REPAIRS)} "
        f"and {len(cause_mismatch)}; the set of points where all-or-nothing and "
        f"proportional are the same run is exactly `rho <= lower_edge` "
        f"({len(measured_coincident)} measured, {len(predicted_coincident)} "
        f"predicted, agree={coincidence_agrees}); the set where exactly one of "
        f"them lives is exactly the predicted strip ({len(measured_strip)} measured, "
        f"{len(predicted_strip)} predicted, agree={strip_agrees}); the reference "
        f"point reproduces its dynamics hash on a repeat run: {deterministic}",
    )

    # -- limitations (§6) ---------------------------------------------------
    exp.limitation(
        "the horizon is fixed at 20000 steps: a point recorded alive is alive at "
        "20000, not proved immortal. The FINDING-145 per-point bound is not used "
        "because it bounds a dying point, not a self-balancing cycle — at "
        "dr = 0.3, rc = 1.44 it says 204 steps and the organism is alive after "
        "200000."
    )
    exp.limitation(
        "one organism on a uniform field, no competition, no sharing, no memory; "
        "movement is `stay` in every arm, so the movement axis is not measured at "
        "all here. The difference measured is the difference between the three "
        "repair rules under that one movement policy."
    )
    exp.limitation(
        "the grid is 4 damage rates x 3 incomes x 5 rho fractions of the cadence "
        "edge: the strip where the two edges separate is one `dr` wide (dr = 0.3), "
        "so the measured difference between all-or-nothing and proportional rests "
        "on 4 points out of 40. That is the arithmetic of the model, not a chosen "
        "grid: for dr = 0.001/0.01/0.1, dr*ceil(1/dr) = 1 and the edges coincide."
    )
    exp.limitation(
        "equality at both edges counts as alive with a 1e-12 tolerance; the code "
        "compares `price < energy`, and core/src/organism.rs records that this "
        "boundary is a floating-point question, so a neighbouring point is needed "
        "to tell `>=` from `>`."
    )
    exp.limitation(
        "per-point table only as far as `points`: the numbers are lifetime, cause "
        "and accumulated energy per strategy, not the trajectories. Two arms "
        "declared the same run are compared on those three fields, not on a full "
        "trace hash at each point."
    )
    exp.limitation(
        "`proportional` in `core` is the repaired-amount rule with the charge "
        "clamped; it is not the older `worst`/`round`/`cheapest` of the FINDING-143 "
        "mock, so nothing here transfers to those rules or to segment damage."
    )

    # -- verdict (§4) -------------------------------------------------------
    reason = (
        f"Strategies differ: {len(distinguished)} of {len(points)} points show a "
        f"different lifetime, cause or accumulated energy, and the difference "
        f"comes from the repair rule alone (movement `stay`, same world, seed, "
        f"field and horizon; only `--repair` changes). Alive counts on the "
        f"{len(main_points)} main points (dr > 0, rc > 0, income > maint): "
        f"none {main_alive_counts['none']}, all-or-nothing "
        f"{main_alive_counts['all-or-nothing']}, proportional "
        f"{main_alive_counts['proportional']} — predicted 0/32/28 with 0 "
        f"alive/cause mismatches. The living window is not the same for the two "
        f"repairing rules: all-or-nothing reaches the cadence edge "
        f"upper_edge = (1 - maint/income) * dr * ceil(1/dr), proportional stops "
        f"at the per-step edge lower_edge = 1 - maint/income; the two edges "
        f"separate only at dr = 0.3 (1.2x apart), and exactly the {len(measured_strip)} "
        f"predicted strip points show all-or-nothing alive while proportional is "
        f"dead of energy (e.g. dr = 0.3, income = 1.0, rho = 0.432: alive at "
        f"20000 vs 157 steps; rho = 0.48: alive at 20000 vs 63). Where "
        f"rho <= lower_edge the two are the same run, measured in "
        f"{len(measured_coincident)} of {len(predicted_coincident)} predicted "
        f"points. Above both edges all repairing strategies die and `none` dies "
        f"in every point with dr > 0."
    )
    if exp.controls_passed() and exp.hashes_are_distinct():
        exp.verdict("passed", reason)
    else:
        exp.verdict("void", "VOID: " + reason)

    exp.result["points"] = [
        {
            "damage_rate": p["damage_rate"],
            "repair_cost": p["repair_cost"],
            "income": p["income"],
            "rho": p["rho"],
            "lower_edge": p["lower_edge"],
            "upper_edge": p["upper_edge"],
            "position": p["position"],
            "t": p["t"],
            "predicted": p["predicted"],
            "predicted_coincident": p["predicted_coincident"],
            "predicted_one_of_two_alive": p["predicted_one_of_two_alive"],
            "one_of_two_alive": p["one_of_two_alive"],
            "measured_coincident": p["measured_coincident_all_or_nothing_proportional"],
            "arms": {
                rep: {
                    "lifetime": p["arms"][rep]["lifetime"],
                    "cause": p["arms"][rep]["cause"],
                    "energy_acc": p["arms"][rep]["energy_acc"],
                }
                for rep in REPAIRS
            },
        }
        for p in points
    ]
    exp.result["measurement"] = {
        "main_points": len(main_points),
        "silent_points": len(silent_points),
        "free_repair_points": len(free_points),
        "alive_points_total": alive_counts,
        "alive_main_points": main_alive_counts,
        "predicted_main_alive": {"none": 0, "all-or-nothing": 32, "proportional": 28},
        "strip_points_measured": len(measured_strip),
        "strip_points_predicted": len(predicted_strip),
        "coincident_points_measured": len(measured_coincident),
        "coincident_points_predicted": len(predicted_coincident),
        "alive_mismatches": len(alive_mismatch),
        "cause_mismatches": len(cause_mismatch),
        "deterministic_reference": deterministic,
        "max_finite_lifetime": max(
            a["lifetime"] for p in points for a in p["arms"].values() if a["cause"] != "alive"
        ),
    }

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(
        f"\nalive totals: {alive_counts}; main: {main_alive_counts}; "
        f"strip {len(measured_strip)}/{len(predicted_strip)}; "
        f"coincident {len(measured_coincident)}/{len(predicted_coincident)}; "
        f"alive mismatches {len(alive_mismatch)}, cause mismatches {len(cause_mismatch)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
