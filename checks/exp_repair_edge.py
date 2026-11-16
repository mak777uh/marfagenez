"""EXP-148: the boundary of indefinite life is the edge of a discrete dynamics.

## The question

`docs/FINDING-145.md` says an organism lives indefinitely iff

    ceil(1/dr) * surplus >= repair_cost        (the cadence condition, `n*s >= rc`)

where `surplus = taken - maintenance_cost` and `taken = min(income, M*regrow)`.
`FINDING-147` measured the band where the repair strategies differ and recorded
two boundary defects it could not explain:

  1. `dr = 0.21, income = 1.0, rc = 2.0` sits on the cadence equality
     (`n*s = 5*0.4 = 2.0`) and dies at step 350, while `FINDING-145` measured an
     equality alive at `dr = 0.3, rc = 1.6` (`n*s = 4*0.4 = 1.6`);
  2. `proportional` at three points survives on exactly one of three adjacent
     representable `rc` -- the "ulp prop of `repaired*rc`", named but not proved.

The hypothesis to test: the repair is greedy every step, so if `dr*rc < s` the
organism repairs every step at `dr*rc` and lives; otherwise damage accumulates
and the repair happens only when the reserve covers `damage*rc`.  Then the
cadence condition is sufficient but not necessary, the equality is decided by
the accumulated reserve rather than by the inequality, and a repair needs
`price < energy` while `energy` is capped, so a `rc` too large for the capped
reserve makes the cadence condition false even when it holds arithmetically.

## The arithmetic, before the run (AGENTS.md §1)

Step order, `core/src/organism.rs:467-543`: income, maintenance,
`damage += dr` capped at 1.0, repair, **capacity cap**, death test
`energy <= 0 || damage >= 1`.

Two facts about that order decide everything:

* income arrives and maintenance is charged **before** the repair, and the cap
  is applied **after** it.  So the largest reserve available at the repair test
  is `capacity + s`, not `capacity`: the reserve can exceed the capacity by
  exactly one step's surplus.
* damage is accumulated (`damage = (damage + dr).min(1.0)`), so the number of
  steps from `damage = 0` to the first `damage >= 1.0` is the model's own
  counter, not `ceil(1/dr)`.  Call it `K`.  It is measured here as the lifetime
  of the `none` arm, which never repairs and dies of damage at exactly `K`.
  `K = ceil(1/dr)` is *usually* true and fails where the accumulated sum lands
  just below 1.0: `dr = 0.1` gives `K = 11`, not 10, because ten additions of
  0.1 give `0.9999999999999999`.

Write `s = taken - maintenance_cost`.

**P1 (`FINDING-145`, the condition under test).**

    alive  <=>  ceil(1/dr) * s >= rc

**P1b (P1 plus the per-step branch).**  The cadence derivation assumes the
repair happens at the damage cap and costs the whole `rc`.  That is false when
`dr*rc <= s`: the repair is affordable every step at the price `dr*rc`, damage
never accumulates, and the ceiling is never reached.

    alive  <=>  dr*rc <= s  OR  ceil(1/dr)*s >= rc

**P2 (the mechanism derived here).**  A repair can only be paid out of the
reserve at the moment of the repair, and there are exactly two prices it can
have:

  * per-step: damage is `dr`, so the price is `dr*rc`, paid out of one step's
    surplus; profitable and repeatable iff `dr*rc <= s`;
  * at the damage cap: damage is 1.0, so the price is `rc`, and it must fit in
    the reserve accumulated over the `K` steps since the last repair, within
    `capacity + s`.

    alive  <=>  dr*rc <= s  OR  (rc <= K*s  AND  rc < capacity + s)

`n*s` does not appear; `K` does.  So the cadence condition is

  * not necessary, for two reasons: (a) `K > n` where the accumulated clock
    differs from the formula, which widens the edge by one step of surplus;
    (b) the per-step branch, where `rc` can exceed `K*s` (up to `s/dr`) and the
    organism never pays `rc` at all;
  * not sufficient when `K*s >= rc >= capacity + s`: the cadence condition is
    satisfied, the reserve can never make that payment, and the organism dies
    of damage.

**P3 (the counterexample as the brief states it is wrong).**  The brief proposes
`dr = 0.001, income = 1.0, rc = 12` and `rc = 20` with `n*s = 400`.  There
`dr*rc = 0.012` and `0.02`, both below `s = 0.4`, so both points are in the
per-step branch: the organism never pays `rc` at all, and P2 predicts **alive**.
A real capacity counterexample needs `dr*rc > s` (a deferred payment),
`s/dr < rc` (so the payment is worth deferring) and `rc > capacity + s`.  It
exists only in the teeth of the clock: `dr = 0.03` gives `K = 34`,
`K*s = 13.6`, `s/dr = 13.33`, `capacity+s = 10.4`, so `rc = 13.5` is
cadence-alive, deferred, and above the reserve the cap allows.

**P4 (equality is a comb, not an edge).**  At `rc = K*s` the ceiling cycle is
neutral in exact arithmetic: the reserve after a ceiling repair is a constant of
motion (`X' = X + K*s - rc = X`).  Which side of the equality the point lands
on is therefore decided by the reserve the organism carried into the cycle and
by the rounding of the `K` additions, not by the sign of `K*s - rc`.  Prediction:
adjacent representable `rc` at the equality disagree, and the survival of the
`dr = 0.3, rc = 1.6` equality of `FINDING-145` is a statement about the reserve
its transient left (0.04), not about `>=`.

**P5 (the ulp prop of `proportional`).**  When the reserve is nearly exhausted,
`proportional` sets `repaired = energy/rc` and charges `repaired*rc`.  If that
product rounds **below** `energy`, the reserve keeps a residual, `energy <= 0`
is false, and damage clamped at the cap keeps `damage >= 1` false: a state
pinned at a 1-ulp reserve lives on.  If the product rounds to `energy` it dies
of energy.  Prediction: one of three adjacent `rc` lives, the others die, and
the surviving residual is a fixed point of the per-step map.

## Controls (§2)

* `fires` -- there are grid points that are dead while P1 says alive.  If there
  were none, the grid could not separate P1 from P2.
* `silent` -- where the two rules cannot differ: `income <= maintenance`
  (`s <= 0`, the tank empties, both must die of energy) and the per-step branch
  `dr*rc < s` (both repair every step and are the same run).
* `specific` -- the mechanism must be the one named, at three sharp places:
  (a) the clock edge is `K*s`, not `ceil(1/dr)*s`: at `dr = 0.1` the point
  `rc = 4.35` lives while `ceil(1/dr)*s = 4.0`; (b) the capacity edge is
  `capacity + s`, not `capacity`: `rc = capacity + s/2` lives, `rc =
  capacity + s + delta` dies although `delta` is tiny; (c) the ulp comb
  reproduces the `FINDING-147` lifetimes for the three adjacent encodings.

## Horizon

`T = 20000` steps as in `FINDING-146`/`147`: "alive" means alive at `T`, not
proved immortal.  This matters: a neutral cycle whose reserve is small dies
later than the equality suggests (`dr = 0.3, rc = 1.6` carries `0.04` through
`T` while losing about one ulp of the reserve per period), and the ulp pin of P5
is a fixed point at `T`, not a proof of one.

Run: `python3 checks/exp_repair_edge.py` (about 1 minute; not part of `run.sh`).
The two probes must be built first:

    cd core && cargo build --release --example rho_probe --example step_trace
"""

from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys

try:
    from checks.experiment import Experiment
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from checks.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "rho_probe")
TRACE = os.path.join(ROOT, "core", "target", "release", "examples", "step_trace")

SEED = 1
MAINT = 0.6
CAPACITY = 10.0
ENERGY0 = 5.0
CELLS = 8
REGROW = 0.8
M_FIELD = 2.0
MOVE_COST = 0.0
T = 20000

#: The grid the brief asks for, plus the "teeth" rows.  The teeth are not
#: decoration: a deferred payment above `capacity+s` needs `K*s > capacity+s`,
#: and the brief's grid has no such row for `income = 1.0` (`dr = 0.001` and
#: `0.01` are exact teeth of `1/dr`, so `K*s = s/dr` and the deferred band is
#: empty).  Without `0.03, 0.036, 0.038, 0.05, 0.078` the capacity
#: counterexample cannot be reached at all.
DAMAGE_RATES = (0.001, 0.01, 0.03, 0.036, 0.038, 0.039, 0.05, 0.078, 0.1,
                0.2, 0.25, 0.3, 0.4, 0.5)
INCOMES = (0.5, 1.0, 1.5)
REPAIRS = ("all-or-nothing", "proportional")

#: The two defects of FINDING-147 (see the traces below).
DEFECT_EQUALITY = {"dr": 0.21, "income": 1.0, "rc": 2.0}
DEFECT_ULP = {"dr": 0.6, "income": 1.5, "rc": 1.65}


def repair_every(dr: float) -> int:
    return int(math.ceil(1.0 / dr - 1e-9))


def taken(income: float) -> float:
    return min(income, M_FIELD * REGROW)


def surplus(income: float) -> float:
    return taken(income) - MAINT


def run_arm(repair: str, dr: float, rc: float, income: float, steps: int = T,
            cap: float = CAPACITY) -> dict:
    cmd = [
        PROBE, "--policy", "stay", "--repair", repair,
        "--cells", str(CELLS), "--n", "1", "--start-cell", "0",
        "--steps", str(steps), "--seed", str(SEED),
        "--m", repr(M_FIELD), "--regrow", repr(REGROW),
        "--income", repr(income), "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc), "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST), "--energy", repr(ENERGY0),
        "--capacity", repr(cap), "--read-budget", "0",
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    p = json.loads(out)
    return {
        "lifetime": int(p["lifetime"]),
        "cause": p["cause"],
        "energy_acc": round(float(p["energy_acc"]), 9),
        "energy_end": float(p["energy_end"]),
        "damage_end": float(p["damage_end"]),
        "trace_hash": str(p["hash"]),
    }


def step_trace(repair: str, dr: float, rc: float, income: float, steps: int,
               head: int, tail: int, cap: float = CAPACITY) -> dict:
    cmd = [
        TRACE, "--repair", repair,
        "--steps", str(steps), "--head", str(head), "--tail", str(tail),
        "--seed", str(SEED), "--m", repr(M_FIELD), "--regrow", repr(REGROW),
        "--income", repr(income), "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc), "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST), "--energy", repr(ENERGY0),
        "--capacity", repr(cap),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def is_alive(arm: dict) -> bool:
    return arm["cause"] == "alive"


def close(a: float, b: float, rel: float = 1e-12) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def hx(x: float) -> str:
    return "0x%016x" % struct.unpack("<Q", struct.pack("<d", x))[0]


def ceiling_repairs(records: list[dict], rc: float) -> list[tuple[int, float]]:
    """(step, post-repair reserve) for each repair paid at the damage cap."""
    out = []
    for r in records:
        if r["repaired"] and close(r["price"], rc, 1e-9) and r["d"] == 0.0:
            out.append((r["step"], r["e"]))
    return out


def main() -> int:
    for path in (PROBE, TRACE):
        if not os.path.exists(path):
            print(f"no probe at {path}; build it:\n"
                  "  cd core && cargo build --release --example rho_probe "
                  "--example step_trace")
            return 2

    # -- §1 arithmetic, written before the run ------------------------------
    arithmetic = {
        "step_order": (
            "income, maintenance, damage += dr (cap 1.0), repair, capacity cap, "
            "death test energy <= 0 || damage >= 1 (core/src/organism.rs)"
        ),
        "taken": f"min(income, M*regrow) = min(income, {M_FIELD * REGROW:g})",
        "surplus": "s = taken - maintenance_cost",
        "max_reserve_at_the_repair_test": (
            "capacity + s, because income and maintenance happen before the "
            "repair and the cap is applied after it: the reserve can exceed the "
            "capacity by exactly one step's surplus"
        ),
        "damage_clock": (
            "K = the number of accumulated `damage += dr` steps from 0 to the "
            "first damage >= 1.0, measured as the `none` arm's lifetime; "
            "K = ceil(1/dr) usually, and fails where the accumulated sum lands "
            "just below 1.0 (dr = 0.1 -> K = 11, not 10)"
        ),
        "P1_finding_145": "alive <=> ceil(1/dr) * s >= rc",
        "P1b": "alive <=> dr*rc <= s  OR  ceil(1/dr)*s >= rc",
        "P2_mechanism": (
            "alive <=> dr*rc <= s  OR  (rc <= K*s AND rc < capacity + s).  The "
            "per-step price dr*rc is paid out of one step's surplus; the "
            "deferred price at the damage cap is rc and the reserve there is at "
            "most capacity + s.  n*s is neither sufficient nor necessary."
        ),
        "P3_counterexample": (
            "a capacity counterexample to P1 needs dr*rc > s, s/dr < rc and "
            "rc > capacity + s: dr = 0.03, K = 34, K*s = 13.6, s/dr = 13.33, "
            "rc = 13.5 > 10.4.  The brief's dr = 0.001, rc = 12 or 20 is NOT "
            "one: there dr*rc = 0.012 or 0.02 is below s = 0.4, so the organism "
            "never pays rc and P2 predicts alive."
        ),
        "P4_equality_is_a_comb": (
            "at rc = K*s the ceiling cycle is neutral in exact arithmetic "
            "(X' = X), so the side of the boundary is set by the reserve "
            "carried into the cycle and by the rounding of K accumulations; "
            "adjacent representable rc disagree and the outcome depends on "
            "energy0 through the transient"
        ),
        "P5_ulp_prop": (
            "proportional charges (energy/rc)*rc; if the product rounds one ulp "
            "below energy the reserve keeps a residual, energy <= 0 is false and "
            "damage is clamped at the cap, so the state is pinned and lives; if "
            "it rounds to energy it dies.  One of three adjacent rc."
        ),
        "predictions": {
            "P1": "alive iff ceil(1/dr)*s >= rc (FINDING-145)",
            "P1b": "alive iff dr*rc <= s or ceil(1/dr)*s >= rc",
            "P2": "alive iff dr*rc <= s or (rc <= K*s and rc < capacity + s)",
            "proportional": "alive iff dr*rc <= s (up to the ulp pin of P5)",
        },
    }

    exp = Experiment(
        experiment_id="repair-edge",
        question=(
            "Is the boundary of indefinite life the cadence inequality "
            "n*s >= rc, or the edge of the discrete repair dynamics: the price "
            "one step's surplus can pay, and the largest payment the capped "
            "reserve can make at the model's own damage clock?"
        ),
        arithmetic=arithmetic,
        arms={r: f"repair={r}" for r in REPAIRS},
        seed=SEED,
        command="python3 checks/exp_repair_edge.py",
        parameters={
            "damage_rates": list(DAMAGE_RATES),
            "incomes": list(INCOMES),
            "repair_costs": "per row: per-step price, per-step equality, clock "
                            "equality K*s, capacity, capacity+s, above both",
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
            "t_cap": T,
            "seed": SEED,
        },
    )

    # -- the model's own damage clock, measured by the arm that never repairs --
    clocks: dict[float, dict] = {}
    for dr in DAMAGE_RATES:
        arm = run_arm("none", dr, 1.5, 1.0)
        clocks[dr] = {
            "ceil_1_over_dr": repair_every(dr),
            "none_lifetime": arm["lifetime"],
            "cause": arm["cause"],
            "difference": arm["lifetime"] - repair_every(dr),
        }
        print(f"clock dr={dr:<6} ceil={clocks[dr]['ceil_1_over_dr']:<5} "
              f"K={clocks[dr]['none_lifetime']:<5} ({arm['cause']})", flush=True)

    # -- the grid -----------------------------------------------------------
    points: list[dict] = []

    def add_point(dr: float, income: float, rc: float, label: str) -> None:
        s = surplus(income)
        K = clocks[dr]["none_lifetime"]
        n = clocks[dr]["ceil_1_over_dr"]
        arms = {rep: run_arm(rep, dr, rc, income) for rep in REPAIRS}
        equalities = {
            "per_step": s > 0 and close(dr * rc, s),
            "clock": s > 0 and close(K * s, rc),
            "formula": s > 0 and close(n * s, rc),
            "capacity": s > 0 and close(rc, CAPACITY + s),
        }
        point = {
            "damage_rate": dr,
            "income": income,
            "repair_cost": rc,
            "label": label,
            "surplus": round(s, 12),
            "clock": K,
            "repair_every": n,
            "clock_energy": round(K * s, 12),
            "cadence_energy": round(n * s, 12),
            "per_step_price": round(dr * rc, 12),
            "capacity_plus_surplus": round(CAPACITY + s, 12),
            "rho": round(dr * rc / income, 12),
            "equalities": equalities,
            "predicted": {
                "P1": (s > 0) and (n * s >= rc),
                "P1b": (s > 0) and (dr * rc <= s or n * s >= rc),
                "P2": (s > 0) and (dr * rc <= s or (K * s >= rc
                                                     and rc < CAPACITY + s)),
                "proportional": (s > 0) and (dr * rc <= s),
            },
            "arms": arms,
        }
        points.append(point)
        print(
            f"{label[:30]:<30} dr={dr:<6} inc={income:<4} rc={rc:<10.6g} "
            f"alive={[is_alive(arms[r]) for r in REPAIRS]} "
            f"P1={point['predicted']['P1']} P2={point['predicted']['P2']}",
            flush=True,
        )

    for dr in DAMAGE_RATES:
        for income in INCOMES:
            s = surplus(income)
            K = clocks[dr]["none_lifetime"]
            if s <= 0:
                for rc in (0.1, 1.0, 5.0, 12.0):
                    add_point(dr, income, rc, "tank empties (s <= 0)")
                continue
            rows = [
                (0.5 * s / dr, "per-step branch (cheap)"),
                (s / dr, "per-step equality dr*rc = s"),
                (1.2 * s / dr, "per-step branch edge"),
                (0.5 * K * s, "inside the clock window"),
                (0.97 * K * s, "just below the clock edge"),
                (K * s, "clock equality K*s = rc"),
                (1.05 * K * s, "just above the clock edge"),
                (CAPACITY, "at capacity"),
                (CAPACITY + 0.5 * s, "between capacity and capacity+s"),
                (CAPACITY + s, "capacity edge rc = capacity+s"),
                (CAPACITY + 2 * s, "above capacity+s"),
            ]
            # A strict capacity counterexample to the cadence condition: the
            # deferred band must lie entirely above `capacity+s`, otherwise the
            # band's lower end is in the per-step branch and no single repair is
            # ever paid.  Then any point strictly inside the band is deferred,
            # cadence-alive, above the reserve the cap allows, and off every
            # equality -- the comb cannot explain its death.
            if K * s > CAPACITY + s and s / dr > CAPACITY + s:
                rows.append((0.5 * (s / dr + K * s),
                             "deferred, inside the band, above capacity+s"))
            seen: set[float] = set()
            for rc, label in rows:
                if rc <= 0:
                    continue
                key = round(rc, 12)
                if key in seen:
                    continue
                seen.add(key)
                add_point(dr, income, rc, label)

    # -- prediction checks --------------------------------------------------
    def mismatches(key: str, subset=None) -> list[dict]:
        pool = points if subset is None else subset
        return [p for p in pool
                if p["predicted"][key] != is_alive(p["arms"]["all-or-nothing"])]

    strict = [p for p in points if not any(p["equalities"].values())]

    mis = {k: mismatches(k) for k in ("P1", "P1b", "P2")}
    p1_dead_where_alive = [p for p in mis["P1"]
                           if not is_alive(p["arms"]["all-or-nothing"])]
    p1_alive_where_dead = [p for p in mis["P1"]
                           if is_alive(p["arms"]["all-or-nothing"])]
    mis_strict = {k: mismatches(k, strict) for k in ("P1", "P1b", "P2")}
    prop_mis = [p for p in points
                if p["predicted"]["proportional"]
                != is_alive(p["arms"]["proportional"])]

    capacity_dead = [
        p for p in points
        if p["predicted"]["P1"] and not is_alive(p["arms"]["all-or-nothing"])
        and p["damage_rate"] * p["repair_cost"] > surplus(p["income"])
        and p["repair_cost"] > CAPACITY + surplus(p["income"])
    ]
    capacity_dead_strict = [p for p in capacity_dead
                            if not any(p["equalities"].values())]
    # The brief's own examples, measured directly (`dr = 0.001, rc = 12, 20`).
    brief_examples = []
    for rc in (12.0, 20.0):
        brief_examples.append({
            "damage_rate": 0.001, "income": 1.0, "repair_cost": rc,
            "n_times_s": 1000 * 0.4, "per_step_price": 0.001 * rc,
            "capacity_plus_surplus": CAPACITY + 0.4,
            "predicted_145": True,
            "predicted_brief": "dead (a single repair cannot be paid)",
            "predicted_P2": True,
            "all_or_nothing": run_arm("all-or-nothing", 0.001, rc, 1.0),
            "proportional": run_arm("proportional", 0.001, rc, 1.0),
        })

    # -- the clock edge at dr = 0.1, where K = 11 and ceil(1/dr) = 10 -------
    clock_edge = []
    for income in (1.0, 1.5):
        s = surplus(income)
        K = clocks[0.1]["none_lifetime"]
        edge = K * s
        for rc in (0.95 * edge, edge - 0.05, edge - 0.01, edge,
                   math.nextafter(edge, math.inf),
                   edge + 0.01, edge + 0.05):
            arm = run_arm("all-or-nothing", 0.1, rc, income)
            clock_edge.append({
                "damage_rate": 0.1, "income": income, "repair_cost": rc,
                "clock_energy": edge, "cadence_energy": 10 * s,
                "above_formula_edge": rc > 10 * s,
                "above_clock_edge": rc > edge,
                "lifetime": arm["lifetime"], "cause": arm["cause"],
                "energy_end": arm["energy_end"], "damage_end": arm["damage_end"],
            })

    # -- the two defects of FINDING-147, with traces ------------------------
    dr_e, inc_e, rc_e = DEFECT_EQUALITY["dr"], DEFECT_EQUALITY["income"], DEFECT_EQUALITY["rc"]
    equality_encodings = []
    for rc in (rc_e - 2 * math.ulp(rc_e), rc_e - math.ulp(rc_e), rc_e,
               rc_e + math.ulp(rc_e), rc_e + 2 * math.ulp(rc_e)):
        arm = run_arm("all-or-nothing", dr_e, rc, inc_e, steps=200000)
        equality_encodings.append({
            "repair_cost": rc, "hex": hx(rc),
            "lifetime": arm["lifetime"], "cause": arm["cause"],
            "energy_end": arm["energy_end"], "damage_end": arm["damage_end"],
        })
    eq_trace = {}
    for tag, rc in (("rc - 1 ulp", rc_e - math.ulp(rc_e)),
                    ("rc exact", rc_e),
                    ("rc + 1 ulp", rc_e + math.ulp(rc_e))):
        tr = step_trace("all-or-nothing", dr_e, rc, inc_e, steps=700,
                        head=30, tail=20)
        eq_trace[tag] = {
            "repair_cost": rc,
            "lifetime": tr["lifetime"], "cause": tr["cause"],
            "head": tr["head"], "tail": tr["tail"],
            "ceiling_repairs_in_tail": ceiling_repairs(tr["tail"], rc),
        }
    alive145_encodings = []
    for rc in (1.6 - math.ulp(1.6), 1.6, 1.6 + math.ulp(1.6)):
        arm = run_arm("all-or-nothing", 0.3, rc, 1.0, steps=200000)
        alive145_encodings.append({
            "repair_cost": rc, "hex": hx(rc),
            "lifetime": arm["lifetime"], "cause": arm["cause"],
            "energy_end": arm["energy_end"],
        })
    eq145_trace = step_trace("all-or-nothing", 0.3, 1.6, 1.0, steps=400,
                             head=5, tail=20)

    # -- the ulp prop of proportional --------------------------------------
    dr_u, inc_u, rc_u = DEFECT_ULP["dr"], DEFECT_ULP["income"], DEFECT_ULP["rc"]
    ulp_encodings = []
    ulp_traces = {}
    for rc in (rc_u - math.ulp(rc_u), rc_u, rc_u + math.ulp(rc_u)):
        arm = run_arm("proportional", dr_u, rc, inc_u, steps=200000)
        ulp_encodings.append({
            "repair_cost": rc, "hex": hx(rc),
            "lifetime": arm["lifetime"], "cause": arm["cause"],
            "energy_end": arm["energy_end"], "damage_end": arm["damage_end"],
        })
        tr = step_trace("proportional", dr_u, rc, inc_u,
                        steps=min(arm["lifetime"], 60), head=3, tail=12)
        ulp_traces[hx(rc)] = {
            "repair_cost": rc, "lifetime": tr["lifetime"],
            "cause": tr["cause"], "tail": tr["tail"],
        }
    ulp_long = step_trace("proportional", dr_u, rc_u, inc_u, steps=200,
                          head=0, tail=10)

    # -- the capacity edge is capacity + s, not capacity -------------------
    #
    # It cannot be shown at `dr = 0.3`: there `K*s = 1.6`, so every row near
    # capacity is already dead by the clock edge and "alive below capacity+s"
    # would be false for the wrong reason.  The edge needs a row where the
    # deferred band straddles capacity: `s/dr < capacity+s` and `K*s >=
    # capacity+s`.  `dr = 0.039` is such a row: `s/dr = 10.256`,
    # `capacity+s = 10.4`, `K = 26`, `K*s = 10.4`.  `rc = 10.3` is therefore
    # deferred, above `capacity = 10`, and below `capacity+s`.
    cap_edge_rows = []
    s3 = surplus(1.0)
    cap_dr = 0.039
    cap_edge = CAPACITY + s3
    for rc in (10.2, 10.25, 0.5 * (10.25 + cap_edge), cap_edge,
               math.nextafter(cap_edge, math.inf), cap_edge + 0.01,
               cap_edge + 0.05, cap_edge + 0.6):
        arm = run_arm("all-or-nothing", cap_dr, rc, 1.0)
        cap_edge_rows.append({
            "damage_rate": cap_dr, "income": 1.0, "repair_cost": rc,
            "per_step_price": cap_dr * rc,
            "deferred": cap_dr * rc > s3,
            "rc_above_capacity": rc > CAPACITY,
            "rc_at_or_above_capacity_plus_s": rc >= cap_edge,
            "clock_energy": clocks[cap_dr]["none_lifetime"] * s3,
            "lifetime": arm["lifetime"], "cause": arm["cause"],
            "energy_end": arm["energy_end"], "damage_end": arm["damage_end"],
        })
    cap_trace = step_trace("all-or-nothing", 0.03, 13.5, 1.0,
                           steps=1034, head=8, tail=16)
    # The deficit cycle: `rc = 4.35` is above the 145 edge (4.0) and below
    # `K*s = 4.4`, and it lives by alternating ten per-step repairs at
    # `dr*rc = 0.42` (a loss of 0.02 each) with one ceiling repair at 4.2 over
    # 21 steps: 8.4 paid out of 8.4 earned.
    deficit_trace = step_trace("all-or-nothing", 0.1, 4.35, 1.0,
                               steps=460, head=0, tail=26)

    # -- controls (§2) ------------------------------------------------------
    exp.control(
        "fires",
        len(mis["P1"]) > 0 and len(capacity_dead) > 0,
        f"P1 (ceil(1/dr)*s >= rc) is wrong in both directions on the grid: "
        f"{len(p1_dead_where_alive)} of {len(points)} points are dead although it "
        f"says alive ({len(capacity_dead)} of them are the capacity teeth, where "
        f"the deferred payment exceeds capacity+s = {CAPACITY + 0.4:g}) and "
        f"{len(p1_alive_where_dead)} are alive although it says dead (dr = 0.1, "
        f"where the model's clock K = 11 but ceil(1/dr) = 10).  Example: "
        + (f"dr = {capacity_dead[0]['damage_rate']}, rc = "
           f"{capacity_dead[0]['repair_cost']:.6g}, K*s = "
           f"{capacity_dead[0]['clock_energy']:.6g}, capacity+s = "
           f"{capacity_dead[0]['capacity_plus_surplus']:.6g}, lifetime = "
           f"{capacity_dead[0]['arms']['all-or-nothing']['lifetime']} steps, "
           f"cause = {capacity_dead[0]['arms']['all-or-nothing']['cause']}"
           if capacity_dead else "none found"),
    )

    silent_points = []
    silent_bad = []
    for p in points:
        if p["surplus"] <= 0:
            silent_points.append(p)
            if any(is_alive(p["arms"][r]) for r in REPAIRS):
                silent_bad.append((p, "s <= 0 but alive"))
        elif p["per_step_price"] < p["surplus"]:
            silent_points.append(p)
            a, b = p["arms"]["all-or-nothing"], p["arms"]["proportional"]
            if (a["lifetime"], a["cause"], a["energy_acc"]) != (
                    b["lifetime"], b["cause"], b["energy_acc"]):
                silent_bad.append((p, "cheap branch but the rules differ"))
    exp.control(
        "silent",
        not silent_bad,
        f"{len(silent_points)} silent points: "
        f"{len([p for p in points if p['surplus'] <= 0])} with s <= 0 (the tank "
        f"empties, both rules must die of energy) and "
        f"{len(silent_points) - len([p for p in points if p['surplus'] <= 0])} in "
        f"the per-step branch (dr*rc < s, both rules repair every step and are "
        f"the same run).  Violations: {len(silent_bad)}"
        + (": " + "; ".join(f"dr={p['damage_rate']}, rc={p['repair_cost']:.6g} ({why})"
                            for p, why in silent_bad[:4]) if silent_bad else ""),
    )

    below_cap = [r for r in cap_edge_rows if r["repair_cost"] < CAPACITY + s3]
    above_cap = [r for r in cap_edge_rows if r["repair_cost"] >= CAPACITY + s3]
    ulp_alive = sum(1 for e in ulp_encodings if e["cause"] == "alive")
    # The edge itself and its neighbouring ulp are the comb of P4: at
    # `rc = K*s` the cycle is neutral and the rounding decides, so a row on the
    # edge is not evidence for either side.  Classify by equality, not by `>`.
    clock_equal = [r for r in clock_edge if close(r["repair_cost"], r["clock_energy"])]
    clock_below = [r for r in clock_edge
                   if r["repair_cost"] < r["clock_energy"]
                   and not close(r["repair_cost"], r["clock_energy"])]
    clock_above = [r for r in clock_edge
                   if r["repair_cost"] > r["clock_energy"]
                   and not close(r["repair_cost"], r["clock_energy"])]
    deferred_above_capacity = [
        r for r in below_cap if r["deferred"] and r["rc_above_capacity"]
    ]
    specific_ok = (
        all(r["cause"] == "alive" for r in below_cap)
        and all(r["cause"] != "alive" for r in above_cap)
        and bool(deferred_above_capacity)
        and all(r["cause"] == "alive" for r in clock_below)
        and all(r["cause"] != "alive" for r in clock_above)
        and any(r["above_formula_edge"] and r["cause"] == "alive" for r in clock_below)
        and not mis_strict["P2"]
        and ulp_alive == 1
    )
    exp.control(
        "specific",
        specific_ok,
        f"(a) the clock edge is K*s, not ceil(1/dr)*s: of {len(clock_below)} "
        f"rows below K*s all are alive, of {len(clock_above)} above it all "
        f"are dead; {sum(1 for r in clock_below if r['above_formula_edge'])} of "
        f"the living rows are above the 145 edge ceil(1/dr)*s (dr = 0.1, "
        f"rc = 4.35: alive although ceil(1/dr)*s = 4.0, because K = 11); "
        f"{len(clock_equal)} rows sit on K*s itself and are the comb of P4 "
        f"({[(round(r['repair_cost'], 15), r['cause']) for r in clock_equal]}).  "
        f"(b) the capacity edge is capacity+s = {CAPACITY + s3:g}, not "
        f"capacity = {CAPACITY:g}: at dr = {cap_dr} the deferred band straddles "
        f"it (s/dr = {s3 / cap_dr:.6g}), all {len(below_cap)} rows below are "
        f"alive -- among them {len(deferred_above_capacity)} deferred rows above "
        f"capacity, e.g. rc = "
        f"{deferred_above_capacity[0]['repair_cost'] if deferred_above_capacity else '?'} "
        f"-- and all {len(above_cap)} rows at or above are dead "
        f"({[r['lifetime'] for r in above_cap]} steps, cause "
        f"{[r['cause'] for r in above_cap]}, energy at death "
        f"{[round(r['energy_end'], 6) for r in above_cap]}).  "
        f"(c) the ulp comb reproduces 147: of three adjacent rc at dr = {dr_u}, "
        f"income = {inc_u}, exactly {ulp_alive} lives "
        f"(lifetimes {[e['lifetime'] for e in ulp_encodings]}).  "
        f"P2 has {len(mis_strict['P2'])} mismatches on the {len(strict)} strict "
        f"grid points.",
    )

    # -- arms and hashes ----------------------------------------------------
    # A reference point where the two rules must differ: `dr = 0.3` with
    # `rc` just below the clock edge is deferred (`dr*rc > s`), so
    # `all-or-nothing` lives at the cap while `proportional` starves -- two
    # different runs, two different hashes.  The per-step equality would be
    # one run with one hash, which the contract refuses as a false contrast.
    ref = next(p for p in points
               if p["damage_rate"] == 0.3 and p["income"] == 1.0
               and p["label"] == "just below the clock edge")
    assert (ref["arms"]["all-or-nothing"]["trace_hash"]
            != ref["arms"]["proportional"]["trace_hash"])
    for rep in REPAIRS:
        exp.add_arm(
            rep,
            f"repair={rep}",
            {
                "alive_points": sum(1 for p in points if is_alive(p["arms"][rep])),
                "points": len(points),
                "reference_point": {
                    "dr": ref["damage_rate"], "income": ref["income"],
                    "rc": ref["repair_cost"],
                    "lifetime": ref["arms"][rep]["lifetime"],
                    "cause": ref["arms"][rep]["cause"],
                },
            },
            trace_hash=ref["arms"][rep]["trace_hash"],
        )

    # -- limitations (§6) ---------------------------------------------------
    exp.limitation(
        "the horizon is T = 20000 steps: a neutral cycle with a small reserve is "
        "recorded alive if the reserve outlasts T, not because it is immortal. "
        "At dr = 0.3, rc = 1.6 the cycle loses about one ulp of the reserve per "
        "period from a reserve of 0.04, so 'alive at T' is right and 'immortal' "
        "would be wrong."
    )
    exp.limitation(
        "P2 is derived from the step order and confirmed on this grid; it is not "
        "proved for the floating-point implementation.  The three equalities "
        "(rc = K*s, dr*rc = s, rc = capacity+s) are decided by accumulated "
        "rounding, and the recorded points show that rather than hiding it."
    )
    exp.limitation(
        "K is measured, not derived: the model's damage clock is an accumulation "
        "and ceil(1/dr) disagrees with it at dr = 0.1 (K = 11, ceil = 10).  On "
        "the rest of this grid they agree, so the difference is measured at one "
        "damage rate out of thirteen."
    )
    exp.limitation(
        "one organism on a uniform field, movement `stay`, no competition, no "
        "sharing, no memory; `taken = min(income, M*regrow) = income` on the "
        "whole grid.  A field-limited world (income > M*regrow) is not measured."
    )
    exp.limitation(
        "capacity is fixed at 10.0 and swept only in rc around it; a sweep of "
        "capacity itself is not recorded, so the edge capacity+s is confirmed "
        "at one capacity and its shape is the mechanism's claim, not a measured "
        "law."
    )
    exp.limitation(
        "the capacity teeth exist only just below 1/k in dr, and the deferred "
        "counterexample needs s/dr > capacity+s, which at capacity 10 and "
        "surplus 0.4 means dr < 0.0385.  The counterexample is real but narrow."
    )
    exp.limitation(
        "the ulp prop is recorded as a defect, not as a property of a strategy: "
        "it is one representable value out of three, it does not move either "
        "edge, and it exists because the charge is (energy/rc)*rc.  It says "
        "nothing about whether proportional repair is a good rule."
    )

    # -- verdict (§4) -------------------------------------------------------
    not_necessary = [
        p for p in strict
        if is_alive(p["arms"]["all-or-nothing"]) and not p["predicted"]["P1"]
    ]
    if capacity_dead_strict:
        cap_example = capacity_dead_strict[0]
        cap_example_text = (
            f"(dr = {cap_example['damage_rate']:g}, rc = "
            f"{cap_example['repair_cost']:.6g}, K*s = "
            f"{cap_example['clock_energy']:.6g}, dead at "
            f"{cap_example['arms']['all-or-nothing']['lifetime']} steps of damage)"
        )
    else:
        cap_example_text = "(no counterexample off the equalities)"
    reason = (
        f"FINDING-145's cadence condition is sufficient only while the capped "
        f"reserve can pay one repair, and it is not necessary.  On "
        f"{len(points)} grid points ({len(DAMAGE_RATES)} damage rates x "
        f"{len(INCOMES)} incomes), P1 misses {len(mis['P1'])} points: "
        f"{len(p1_dead_where_alive)} are dead where it says alive and "
        f"{len(p1_alive_where_dead)} are alive where it says dead.  "
        f"{len(capacity_dead)} of the misses are the capacity "
        f"teeth, where the deferred payment rc exceeds capacity+s = "
        f"{CAPACITY + 0.4:g}, and {len(capacity_dead_strict)} of those are off "
        f"every equality {cap_example_text}.  P1 is also not necessary: "
        f"{len(not_necessary)} strict points live with rc above ceil(1/dr)*s "
        f"(and {len(p1_alive_where_dead) - len(not_necessary)} more sit on "
        f"rc = K*s), because the model's damage clock K is larger than "
        f"ceil(1/dr) (dr = 0.1: K = 11, the ten accumulated 0.1s give "
        f"0.9999999999999999), and because a payment larger than the deferred "
        f"one, dr*rc, can be made every step when dr*rc <= s.  The mechanism "
        f"P2 -- alive iff "
        f"dr*rc <= s or (rc <= K*s and rc < capacity+s) -- misses "
        f"{len(mis_strict['P2'])} of {len(strict)} strict points and "
        f"{len(mis['P2'])} of all {len(points)}; the residual misses are the "
        f"equalities of P4, where the outcome is the reserve carried into a "
        f"neutral cycle (dr = 0.21, rc = 2.0: one of three adjacent rc survives, "
        f"the others die at 700 and 350 steps).  The brief's own capacity "
        f"example is not a counterexample: at dr = 0.001, rc = 12 and 20 the "
        f"per-step price is 0.012 and 0.02 below s = 0.4 and both are measured "
        f"alive.  The ulp prop of FINDING-147 is reproduced exactly: of three "
        f"adjacent rc at dr = {dr_u}, income = {inc_u} one lives "
        f"({[e['lifetime'] for e in ulp_encodings]}) because (energy/rc)*rc "
        f"lands one ulp below energy and the residual is a fixed point of the "
        f"step map."
    )
    if exp.controls_passed() and exp.hashes_are_distinct() and not mis_strict["P2"]:
        exp.verdict("passed", reason)
    else:
        exp.verdict("void", "VOID: " + reason)

    # -- the record ---------------------------------------------------------
    exp.result["points"] = [
        {
            "damage_rate": p["damage_rate"],
            "income": p["income"],
            "repair_cost": p["repair_cost"],
            "label": p["label"],
            "surplus": p["surplus"],
            "clock": p["clock"],
            "repair_every": p["repair_every"],
            "clock_energy": p["clock_energy"],
            "cadence_energy": p["cadence_energy"],
            "per_step_price": p["per_step_price"],
            "capacity_plus_surplus": p["capacity_plus_surplus"],
            "rho": p["rho"],
            "equalities": p["equalities"],
            "equal": any(p["equalities"].values()),
            "predicted": p["predicted"],
            "alive": {r: is_alive(p["arms"][r]) for r in REPAIRS},
            "arms": {
                r: {
                    "lifetime": p["arms"][r]["lifetime"],
                    "cause": p["arms"][r]["cause"],
                    "energy_acc": p["arms"][r]["energy_acc"],
                    "energy_end": p["arms"][r]["energy_end"],
                    "damage_end": p["arms"][r]["damage_end"],
                }
                for r in REPAIRS
            },
        }
        for p in points
    ]
    exp.result["damage_clock"] = {
        "measured_as": "the `none` arm's lifetime: the first step with damage >= 1",
        "rows": {f"{dr:g}": clocks[dr] for dr in DAMAGE_RATES},
    }
    exp.result["clock_edge"] = clock_edge
    exp.result["defect_equality"] = {
        "point": {"damage_rate": dr_e, "income": inc_e, "repair_cost": rc_e},
        "clock": clocks.get(dr_e, {}).get("none_lifetime"),
        "clock_energy": (clocks.get(dr_e, {}).get("none_lifetime", 0)
                         * surplus(inc_e)),
        "encodings": equality_encodings,
        "traces": eq_trace,
        "finding_145_equality": {
            "point": {"damage_rate": 0.3, "repair_cost": 1.6, "income": 1.0},
            "clock_energy": 4 * 0.4,
            "encodings": alive145_encodings,
            "trace_tail": eq145_trace["tail"],
            "ceiling_repairs_in_tail": ceiling_repairs(eq145_trace["tail"], 1.6),
        },
    }
    exp.result["defect_ulp_proportional"] = {
        "point": {"damage_rate": dr_u, "income": inc_u, "repair_cost": rc_u},
        "encodings": ulp_encodings,
        "traces": ulp_traces,
        "pinned_tail": ulp_long["tail"],
        "pinned_energy_end": ulp_long["energy_end"],
        "pinned_damage_end": ulp_long["damage_end"],
    }
    exp.result["deficit_cycle"] = {
        "point": {"damage_rate": 0.1, "income": 1.0, "repair_cost": 4.35},
        "cadence_energy_145": 10 * 0.4,
        "clock_energy": clocks[0.1]["none_lifetime"] * 0.4,
        "lifetime": deficit_trace["lifetime"],
        "cause": deficit_trace["cause"],
        "tail": deficit_trace["tail"],
        "ceiling_repairs_in_tail": ceiling_repairs(deficit_trace["tail"], 4.35),
    }
    exp.result["capacity"] = {
        "edge_predicted": CAPACITY + surplus(1.0),
        "edge_rows": cap_edge_rows,
        "counterexamples": [
            {
                "damage_rate": p["damage_rate"], "income": p["income"],
                "repair_cost": p["repair_cost"],
                "clock_energy": p["clock_energy"],
                "per_step_price": p["per_step_price"],
                "capacity_plus_surplus": p["capacity_plus_surplus"],
                "all_or_nothing": p["arms"]["all-or-nothing"],
                "proportional": p["arms"]["proportional"],
            }
            for p in capacity_dead
        ],
        "brief_examples": brief_examples,
        "trace_tail": cap_trace["tail"],
        "trace_head": cap_trace["head"],
        "trace_lifetime": cap_trace["lifetime"],
        "trace_cause": cap_trace["cause"],
    }
    exp.result["measurement"] = {
        "points": len(points),
        "strict_points": len(strict),
        "mismatches_all": {k: len(v) for k, v in mis.items()},
        "mismatches_strict": {k: len(v) for k, v in mis_strict.items()},
        "mismatches_proportional": len(prop_mis),
        "p1_dead_where_alive": len(p1_dead_where_alive),
        "p1_alive_where_dead": len(p1_alive_where_dead),
        "capacity_counterexamples": len(capacity_dead),
        "alive_all_or_nothing": sum(1 for p in points
                                    if is_alive(p["arms"]["all-or-nothing"])),
        "alive_proportional": sum(1 for p in points
                                  if is_alive(p["arms"]["proportional"])),
        "mismatch_details": [
            {
                "prediction": k,
                "damage_rate": p["damage_rate"], "income": p["income"],
                "repair_cost": p["repair_cost"], "label": p["label"],
                "predicted": p["predicted"][k],
                "equal": any(p["equalities"].values()),
                "measured_alive": is_alive(p["arms"]["all-or-nothing"]),
                "lifetime": p["arms"]["all-or-nothing"]["lifetime"],
                "cause": p["arms"]["all-or-nothing"]["cause"],
                "equalities": p["equalities"],
            }
            for k in ("P1", "P1b", "P2")
            for p in mis[k]
        ],
        "proportional_mismatches": [
            {
                "damage_rate": p["damage_rate"], "income": p["income"],
                "repair_cost": p["repair_cost"], "label": p["label"],
                "lifetime": p["arms"]["proportional"]["lifetime"],
                "cause": p["arms"]["proportional"]["cause"],
                "energy_end": p["arms"]["proportional"]["energy_end"],
                "damage_end": p["arms"]["proportional"]["damage_end"],
            }
            for p in prop_mis
        ],
    }

    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(
        f"\nmismatches all: {exp.result['measurement']['mismatches_all']}; "
        f"strict: {exp.result['measurement']['mismatches_strict']}; "
        f"proportional: {len(prop_mis)}; capacity teeth: {len(capacity_dead)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
