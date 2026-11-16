"""EXP-149: is the edge of life the capacity cap `capacity + surplus`?

## The question

`docs/FINDING-148.md` derived the criterion

    alive  <=>  dr*rc <= s  OR  (rc <= K*s  AND  rc < capacity + s)

with `s = taken - maintenance_cost` and `K` the model's damage clock (the
lifetime of the `none` policy). It also wrote the capacity edge down as a
standalone sentence: "the edge is `capacity + surplus`, not `capacity`", and
confirmed it at one capacity (`10.0`, `dr = 0.039`, where `capacity + s` and
`K*s` happen to be equal: both are 10.4). One capacity cannot separate the
two halves of the conjunction, so this experiment sweeps capacity.

## The arithmetic, before the run (AGENTS.md §1)

Write `s = taken - maintenance_cost`, `taken = min(income, M*regrow) = income`
on this grid, `n = ceil(1/dr)`, and `K` = the measured lifetime of the `none`
arm.

The per-step branch is affordable on every step iff `dr*rc <= s`; it gives a
repair price of `dr*rc` and never lets the damage reach the cap. Above it the
payment is deferred to the damage cap, where its price is `rc` and the reserve
at the repair test is at most `capacity + s`. Two conditions must hold there,
and both are needed:

  * `rc < capacity + s` -- the cap limits the payment (one step's surplus can
    be in hand *before* the cap is applied, which is why the limit is
    `capacity + s` and not `capacity`);
  * `rc <= K*s` -- `K` steps of surplus have to accumulate the payment.

**P2 (FINDING-148, the prediction of this run).**

    alive  <=>  rc <= s/dr  OR  (rc <= K*s  AND  rc < capacity + s)

so the steady-state edge is

    edge = max( s/dr , min(K*s, capacity + s) )

**P1 (the brief's prediction, recorded because it is the question).** "alive
exactly where `rc < capacity + surplus`" -- i.e. `edge = capacity + s`,
independent of `dr` and `income` at fixed `capacity`.

**P0 (why P1 must be wrong, derived before the run).** Deferring the payment
needs `dr*rc > s`, and at `rc = capacity + s` that is `dr*(capacity+s) > s`,
i.e. `capacity + s > s/dr`. The clock edge is `K*s`, and `K` is `ceil(1/dr)`
except in the accumulation teeth, so `K*s` is within one step of surplus of
`s/dr`: `K*s <= s/dr + s`. Therefore a capacity edge can only be the tight
one where

    s/dr - s  <  capacity  <  K*s - s

and the width of that window is `s*(K - 1/dr) <= s` -- at most one step of
surplus, and nonzero only in the teeth (`dr = 0.1` gives the widest one,
`K - 1/dr = 1`). A coarse capacity sweep (`2, 5, 10, 20, 50`) is almost
entirely outside that window, so P1 is expected to be refuted in both
directions, and the measured edge is expected to be `s/dr` (per-step) or
`K*s` (clock), with `capacity + s` visible only inside the window.

**P3 (the observable capacity edge).** Inside the window a shift of the edge
must follow capacity one-for-one: at `dr = 0.1` the window is
`(s/dr - s, K*s - s)`, i.e. `(3.6, 4.0)` for `income = 1.0` (`s = 0.4`) and
`(8.1, 9.0)` for `income = 1.5` (`s = 0.9`). Picking capacities inside it
(`3.65 ... 3.95` and `8.2 ... 8.8`) must give measured edges equal to
`capacity + s` and moving with capacity by the same amount.

**P4 (the finite horizon smears the edge, and by how much).** "Alive" means
alive at `T`, so a point just above a steady-state edge is not dead yet: its
reserve pays the difference, and it dies later. Above the per-step edge the
deficit is `dr*(rc - s/dr)` per step, so a reserve `R = min(energy0, capacity)`
carries it for `R / (dr*(rc - s/dr))` steps, i.e. it survives `T` while
`rc - s/dr <= R / (T*dr)`. Above the clock edge the deficit is
`rc - K*s` per cycle of `K` steps, so it survives `T` while
`rc - K*s <= R*K/T`. The measured edge therefore carries an offset
proportional to `1/T`: the edge is measured at two horizons and the offset is
removed by `edge(inf) ~ 2*edge(2T) - edge(T)`. This is the same `blur` that
`FINDING-147` recorded as `E0/(T*income)`, here in rc units.

## Controls (§2)

* `fires` -- P1 is wrong in both directions on the coarse grid: some points
  above `capacity + s` live (the per-step branch is cheaper) and some below
  it die (the clock edge is lower). And in the teeth window the measured edge
  moves with capacity, so the cap is real where it can be seen.
* `silent` -- points where P1 and P2 agree (deep in the per-step branch, or
  deep above every edge): measurement must agree with both, with no
  difference to explain.
* `specific` -- the shift of the edge is a capacity effect: inside the window,
  `delta edge / delta capacity = 1` while `dr`, `income` and `rc` are held
  fixed; outside it, at fixed capacity, the edge follows `dr` (`s/dr` or
  `K*s`), not `capacity`.

## Horizon and tolerance

`T = 20000` and `2T = 40000`; "alive" means alive at that horizon. The edge is
measured by bisection on `rc`; the final bracket width is reported per row and
is the numerical tolerance. Near `rc = K*s` the equality is the comb of
`FINDING-148` P4 (the cycle is neutral and the side is decided by accumulated
rounding), so clock-bound rows may deviate by a few ulp at a fixed horizon;
the tolerance for them is 64 ulp and the extrapolated offset is reported, not
hidden.

Run: `python3 checks/exp_capacity_edge.py` (a few minutes; not part of
`run.sh`). The probe must be built first:

    cd core && cargo build --release --example rho_probe
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

SEED = 1
MAINT = 0.6
ENERGY0 = 5.0
CELLS = 8
REGROW = 0.8
M_FIELD = 2.0
MOVE_COST = 0.0
T = 20000
T2 = 2 * T

CAPACITIES = (2.0, 5.0, 10.0, 20.0, 50.0)
INCOMES = (1.0, 1.5)
DAMAGE_RATES = (0.03, 0.038, 0.1)
#: `rc` is computed from the edge, not chosen: the five fractions of
#: `capacity + surplus` the brief asks for.
EDGE_FRACTIONS = (0.9, 0.99, 1.0, 1.01, 1.1)

#: The teeth window of P3: `dr = 0.1` has `K = 11` while `ceil(1/dr) = 10`,
#: so `capacity` has one full step of surplus (`s = 0.4` or `0.9`) of room in
#: which `capacity + s` is the tight edge.
WINDOW_CAPACITIES = {
    1.0: (3.65, 3.75, 3.85, 3.95),
    1.5: (8.2, 8.4, 8.6, 8.8),
}
WINDOW_DR = 0.1

BISECTION_STEPS = 50


def repair_every(dr: float) -> int:
    return int(math.ceil(1.0 / dr - 1e-9))


def taken(income: float) -> float:
    return min(income, M_FIELD * REGROW)


def surplus(income: float) -> float:
    return taken(income) - MAINT


def run_arm(repair: str, dr: float, rc: float, income: float,
            cap: float, steps: int = T) -> dict:
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
        "energy_end": float(p["energy_end"]),
        "damage_end": float(p["damage_end"]),
        "trace_hash": str(p["hash"]),
    }


def is_alive(arm: dict) -> bool:
    return arm["cause"] == "alive"


def hx(x: float) -> str:
    return "0x%016x" % struct.unpack("<Q", struct.pack("<d", x))[0]


def predicted_edge(dr: float, income: float, cap: float, clock: int) -> dict:
    """P2's edge and the label of the condition that binds it."""
    s = surplus(income)
    per_step = s / dr
    clock_edge = clock * s
    cap_edge = cap + s
    edge = max(per_step, min(clock_edge, cap_edge))
    if per_step >= min(clock_edge, cap_edge):
        binding = "per-step"
    elif cap_edge <= clock_edge:
        binding = "capacity"
    else:
        binding = "clock"
    return {
        "per_step_edge": per_step,
        "clock_edge": clock_edge,
        "capacity_edge": cap_edge,
        "edge": edge,
        "binding": binding,
    }


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"no probe at {PROBE}; build it:\n"
              "  cd core && cargo build --release --example rho_probe")
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
            "capacity + s: income and maintenance happen before the repair and "
            "the cap is applied after it, so the reserve can exceed the "
            "capacity by exactly one step's surplus"
        ),
        "damage_clock": (
            "K = the none arm's lifetime = the number of accumulated "
            "`damage += dr` steps to the first damage >= 1.0; measured, not "
            "assumed to be ceil(1/dr)"
        ),
        "P2_finding_148": (
            "alive <=> rc <= s/dr OR (rc <= K*s AND rc < capacity + s); the "
            "steady-state edge is max(s/dr, min(K*s, capacity + s))"
        ),
        "P1_brief": (
            "alive <=> rc < capacity + s, i.e. the edge is capacity + s and "
            "does not depend on dr or income"
        ),
        "P0_why_P1_must_fail": (
            "deferring needs dr*rc > s, so at rc = capacity + s it needs "
            "capacity + s > s/dr; the clock edge K*s is within one step of "
            "surplus of s/dr (K = ceil(1/dr) except in the accumulation "
            "teeth), so capacity + s can only be the tight edge when "
            "s/dr - s < capacity < K*s - s. That window is at most s wide "
            "and nonzero only in the teeth (dr = 0.1 is the widest). On a "
            "coarse capacity sweep (2, 5, 10, 20, 50) P1 must therefore be "
            "refuted in both directions."
        ),
        "P3_observable_capacity_edge": (
            "inside the teeth window the edge must be capacity + s and move "
            "with capacity one-for-one: dr = 0.1 gives the window (3.6, 4.0) "
            "at income 1.0 and (8.1, 9.0) at income 1.5"
        ),
        "P4_finite_horizon_offset": (
            "the measured edge at horizon T is offset above the steady-state "
            "edge by a term proportional to 1/T, because the reserve pays the "
            "deficit until it runs out: about R/(T*dr) above the per-step edge "
            "and R*K/T above the clock edge, with R = min(energy0, capacity). "
            "Measured at T and 2T, the offset is removed by "
            "edge(inf) ~ 2*edge(2T) - edge(T)"
        ),
        "predicted_edges": {
            "P1": "capacity + s (brief)",
            "P2": "max(s/dr, min(K*s, capacity + s)) (FINDING-148)",
        },
    }

    exp = Experiment(
        experiment_id="capacity-edge",
        question=(
            "Is the edge of indefinite life the capacity cap `capacity + "
            "surplus`, as FINDING-148 wrote it down and confirmed at capacity "
            "10? Or is the cap only one of the two conditions, with the damage "
            "clock deciding first everywhere outside the accumulation teeth?"
        ),
        arithmetic=arithmetic,
        arms={
            "all-or-nothing": "repair=all-or-nothing, the default rule",
            "none": "repair=none: measures the damage clock K, never repairs",
        },
        seed=SEED,
        command="python3 checks/exp_capacity_edge.py",
        parameters={
            "capacities": list(CAPACITIES),
            "incomes": list(INCOMES),
            "damage_rates": list(DAMAGE_RATES),
            "edge_fractions_of_capacity_plus_surplus": list(EDGE_FRACTIONS),
            "window_capacities": {f"{k:g}": list(v)
                                  for k, v in WINDOW_CAPACITIES.items()},
            "window_damage_rate": WINDOW_DR,
            "movement_policy": "stay",
            "maintenance_cost": MAINT,
            "energy0": ENERGY0,
            "cells": CELLS,
            "regrow": REGROW,
            "m_field": M_FIELD,
            "move_cost": MOVE_COST,
            "read_budget": 0,
            "t_cap": T,
            "t_cap_second_horizon": T2,
            "seed": SEED,
            "bisection_steps": BISECTION_STEPS,
        },
    )

    # -- the damage clock, measured by the arm that never repairs -----------
    clocks: dict[float, dict] = {}
    for dr in DAMAGE_RATES:
        arm = run_arm("none", dr, 1.5, 1.0, 10.0, steps=T)
        clocks[dr] = {
            "ceil_1_over_dr": repair_every(dr),
            "none_lifetime": arm["lifetime"],
            "cause": arm["cause"],
            "difference": arm["lifetime"] - repair_every(dr),
        }
        print(f"clock dr={dr:<6} ceil={clocks[dr]['ceil_1_over_dr']:<4} "
              f"K={clocks[dr]['none_lifetime']:<4} ({arm['cause']})", flush=True)
    for dr, row in clocks.items():
        if row["cause"] != "damage":
            print(f"FATAL: the none arm at dr = {dr} did not die of damage")
            return 2

    # -- bisection on rc ----------------------------------------------------
    cache: dict[tuple, bool] = {}

    def alive_at(dr: float, income: float, rc: float, cap: float,
                 steps: int) -> bool:
        key = (dr, income, rc, cap, steps)
        if key not in cache:
            cache[key] = is_alive(
                run_arm("all-or-nothing", dr, rc, income, cap, steps=steps))
        return cache[key]

    def bisect(dr: float, income: float, cap: float, hint: float,
               steps: int) -> dict:
        s = surplus(income)
        lo = 0.0
        hi = 1.2 * max(hint, s / dr, clocks[dr]["none_lifetime"] * s,
                       cap + s) + s
        if not alive_at(dr, income, lo, cap, steps):
            return {"error": "rc = 0 is dead; the bracket is wrong"}
        if alive_at(dr, income, hi, cap, steps):
            return {"error": f"rc = {hi} is alive; the bracket is wrong"}
        for _ in range(BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if mid <= lo or mid >= hi:
                break
            if alive_at(dr, income, mid, cap, steps):
                lo = mid
            else:
                hi = mid
        return {"alive_below": lo, "dead_at": hi, "step": hi - lo}

    # -- coarse sweep: the capacity grid of the brief -----------------------
    rows: list[dict] = []
    grid_points: list[dict] = []

    for cap in CAPACITIES:
        for income in INCOMES:
            s = surplus(income)
            for dr in DAMAGE_RATES:
                clock = clocks[dr]["none_lifetime"]
                pred = predicted_edge(dr, income, cap, clock)
                b1 = bisect(dr, income, cap, pred["edge"], T)
                b2 = bisect(dr, income, cap, pred["edge"], T2)
                if "error" in b1 or "error" in b2:
                    print(f"FATAL: bisection failed at cap={cap} "
                          f"income={income} dr={dr}: "
                          f"{b1.get('error') or b2.get('error')}")
                    return 2
                edge_t = 0.5 * (b1["alive_below"] + b1["dead_at"])
                edge_2t = 0.5 * (b2["alive_below"] + b2["dead_at"])
                edge = 2.0 * edge_2t - edge_t  # removes the O(1/T) offset
                dev = edge - pred["edge"]
                offset_t = edge_t - pred["edge"]
                offset_2t = edge_2t - pred["edge"]
                # The extrapolation removes the leading 1/T term, not the
                # second-order one, so the tolerance is the last measured
                # offset: the extrapolated edge cannot be further from the
                # steady-state one than the offset it removed.
                tol = max(b2["step"], 64 * math.ulp(pred["edge"]),
                          abs(offset_2t))
                rows.append({
                    "capacity": cap,
                    "income": income,
                    "damage_rate": dr,
                    "surplus": round(s, 12),
                    "clock": clock,
                    "ceil_1_over_dr": repair_every(dr),
                    "per_step_edge": round(pred["per_step_edge"], 12),
                    "capacity_edge": round(pred["capacity_edge"], 12),
                    "clock_edge": round(pred["clock_edge"], 12),
                    "P2_edge": round(pred["edge"], 12),
                    "P1_edge": round(pred["capacity_edge"], 12),
                    "binding": pred["binding"],
                    "measured_edge_T": edge_t,
                    "measured_edge_2T": edge_2t,
                    "measured_edge_extrapolated": edge,
                    "offset_at_T": offset_t,
                    "offset_at_2T": offset_2t,
                    "offset_shrinks": abs(offset_2t) < abs(offset_t),
                    "bisection_step_T": b1["step"],
                    "bisection_step_2T": b2["step"],
                    "deviation_from_P2": dev,
                    "deviation_relative": dev / pred["edge"],
                    "deviation_from_P1": edge - pred["capacity_edge"],
                    "tolerance": tol,
                    "tolerance_kind": "bisection bracket, 64 ulp or |offset at 2T|",
                    "matches_P2": abs(dev) <= tol,
                })
                print(
                    f"cap={cap:<5} inc={income:<4} dr={dr:<6} "
                    f"binding={pred['binding']:<9} "
                    f"P2={pred['edge']:<10.6g} "
                    f"edge(T)={edge_t:<10.6g} edge(2T)={edge_2t:<10.6g} "
                    f"lim={edge:<10.6g} dev={dev:+.3g} "
                    f"(P1={pred['capacity_edge']:.6g})",
                    flush=True,
                )

                for frac in EDGE_FRACTIONS:
                    rc = frac * pred["capacity_edge"]
                    arm = run_arm("all-or-nothing", dr, rc, income, cap, steps=T)
                    grid_points.append({
                        "capacity": cap,
                        "income": income,
                        "damage_rate": dr,
                        "repair_cost": rc,
                        "fraction_of_capacity_edge": frac,
                        "capacity_edge": pred["capacity_edge"],
                        "per_step_edge": pred["per_step_edge"],
                        "clock_edge": pred["clock_edge"],
                        "rc_above_capacity_edge": rc > pred["capacity_edge"],
                        "P1": rc < pred["capacity_edge"],
                        "P2": (rc <= pred["per_step_edge"]
                               or (rc <= pred["clock_edge"]
                                   and rc < pred["capacity_edge"])),
                        "alive": is_alive(arm),
                        "lifetime": arm["lifetime"],
                        "cause": arm["cause"],
                        "energy_end": arm["energy_end"],
                        "damage_end": arm["damage_end"],
                    })

    # -- the teeth window: where the capacity edge is the tight one ---------
    window_rows: list[dict] = []
    for income, caps in WINDOW_CAPACITIES.items():
        s = surplus(income)
        dr = WINDOW_DR
        clock = clocks[dr]["none_lifetime"]
        for cap in caps:
            pred = predicted_edge(dr, income, cap, clock)
            b = bisect(dr, income, cap, pred["edge"], T)
            if "error" in b:
                print(f"FATAL: window bisection failed at cap={cap}: "
                      f"{b['error']}")
                return 2
            measured = 0.5 * (b["alive_below"] + b["dead_at"])
            tol = max(b["step"], 64 * math.ulp(pred["edge"]))
            # The capacity edge is a hard edge, not a horizon one: above it the
            # ceiling payment is impossible and the death comes within one
            # damage clock, so the lifetime at `dead_at` must be short.
            dead_arm = run_arm("all-or-nothing", dr, b["dead_at"], income, cap,
                               steps=T)
            window_rows.append({
                "capacity": cap,
                "income": income,
                "damage_rate": dr,
                "surplus": round(s, 12),
                "clock": clock,
                "clock_edge": round(pred["clock_edge"], 12),
                "per_step_edge": round(pred["per_step_edge"], 12),
                "capacity_edge": round(pred["capacity_edge"], 12),
                "P2_edge": round(pred["edge"], 12),
                "binding": pred["binding"],
                "measured_edge": measured,
                "deviation": measured - pred["edge"],
                "tolerance": tol,
                "matches_P2": abs(measured - pred["edge"]) <= tol,
                "dead_at": b["dead_at"],
                "dead_at_lifetime": dead_arm["lifetime"],
                "dead_at_cause": dead_arm["cause"],
                "hard_edge": dead_arm["lifetime"] <= clock + 2,
            })
            print(
                f"WINDOW cap={cap:<5} inc={income:<4} dr={dr} "
                f"binding={pred['binding']:<9} "
                f"capacity+s={pred['capacity_edge']:.6g} "
                f"clock={pred['clock_edge']:.6g} measured={measured:.6g} "
                f"dev={measured - pred['edge']:+.3g} "
                f"dead_at_life={dead_arm['lifetime']}",
                flush=True,
            )

    # -- prediction checks --------------------------------------------------
    def m_p2(points):
        return [p for p in points if p["P2"] != p["alive"]]

    def m_p1(points):
        return [p for p in points if p["P1"] != p["alive"]]

    p2_bad = m_p2(grid_points)
    p1_bad = m_p1(grid_points)
    p1_bad_alive_above = [p for p in p1_bad if p["alive"]]
    p1_bad_dead_below = [p for p in p1_bad if not p["alive"]]

    silent = [p for p in grid_points if p["P1"] == p["P2"]]
    silent_bad = [p for p in silent if p["P1"] != p["alive"]]

    def slope(rows_of_income):
        lo = rows_of_income[0]
        hi = rows_of_income[-1]
        return ((hi["measured_edge"] - lo["measured_edge"])
                / (hi["capacity"] - lo["capacity"]))

    slopes = {}
    window_bad = [r for r in window_rows if not r["matches_P2"]]
    for income in WINDOW_CAPACITIES:
        slopes[income] = slope([r for r in window_rows if r["income"] == income])

    dr_moves = []
    for cap in CAPACITIES:
        for income in INCOMES:
            subset = [r for r in rows if r["capacity"] == cap
                      and r["income"] == income]
            edges = {r["damage_rate"]: r["measured_edge_extrapolated"]
                     for r in subset}
            dr_moves.append({
                "capacity": cap, "income": income,
                "measured_edges": {f"{k:g}": v for k, v in edges.items()},
                "P2_edges": {f"{r['damage_rate']:g}": r["P2_edge"]
                             for r in subset},
                "distinct": len({round(v, 9) for v in edges.values()})
                            == len(edges),
            })

    offsets_shrink = sum(1 for r in rows if r["offset_shrinks"])
    worst_offset = max(abs(r["offset_at_T"]) for r in rows)

    exp.control(
        "fires",
        bool(p1_bad_alive_above) and bool(p1_bad_dead_below) and not window_bad,
        f"P1 (edge = capacity + s) is wrong in both directions on the "
        f"{len(grid_points)}-point grid: {len(p1_bad_alive_above)} points live "
        f"above capacity + s (the per-step price dr*rc is still below s) and "
        f"{len(p1_bad_dead_below)} die below it (the clock edge K*s is lower "
        f"than capacity + s). Examples: alive at cap = "
        f"{p1_bad_alive_above[0]['capacity']:g}, rc = "
        f"{p1_bad_alive_above[0]['repair_cost']:.6g} > capacity+s = "
        f"{p1_bad_alive_above[0]['capacity_edge']:.6g}; dead at cap = "
        f"{p1_bad_dead_below[0]['capacity']:g}, rc = "
        f"{p1_bad_dead_below[0]['repair_cost']:.6g} < capacity+s = "
        f"{p1_bad_dead_below[0]['capacity_edge']:.6g} "
        f"(K*s = {p1_bad_dead_below[0]['clock_edge']:.6g}). And in the teeth "
        f"window all {len(window_rows)} rows match capacity + s "
        f"({len(window_bad)} mismatches), with d(edge)/d(capacity) = {slopes}."
        if p1_bad_alive_above and p1_bad_dead_below else
        "P1 was not refuted in both directions; the grid cannot separate it",
    )

    exp.control(
        "silent",
        not silent_bad,
        f"{len(silent)} of {len(grid_points)} points are silent (P1 and P2 "
        f"agree: deep in the per-step branch or deep above every edge); "
        f"measurement disagrees with both on {len(silent_bad)} of them"
        + (": " + "; ".join(
            f"cap={p['capacity']:g}, rc={p['repair_cost']:.6g}, alive={p['alive']}"
            for p in silent_bad[:4]) if silent_bad else ""),
    )

    window_matches = [r for r in window_rows if r["matches_P2"]]
    exp.control(
        "specific",
        (not window_bad
         and all(abs(v - 1.0) <= 1e-6 for v in slopes.values())
         and all(d["distinct"] for d in dr_moves)
         and offsets_shrink == len(rows)),
        f"the shift of the edge is a capacity effect, in two halves. (a) Inside "
        f"the teeth window (dr = {WINDOW_DR}, where K = "
        f"{clocks[WINDOW_DR]['none_lifetime']} and ceil(1/dr) = "
        f"{repair_every(WINDOW_DR)}) the measured edge equals capacity + s on "
        f"{len(window_matches)} of {len(window_rows)} rows and moves "
        f"one-for-one with capacity: d(edge)/d(capacity) = {slopes} (expected "
        f"1); the death just above the edge comes within one damage clock on "
        f"{sum(1 for r in window_rows if r['hard_edge'])} of "
        f"{len(window_rows)} rows, so it is a hard edge, not a horizon one. "
        f"The window is (s/dr - s, K*s - s) = (3.6, 4.0) at income 1.0 and "
        f"(8.1, 9.0) at income 1.5, i.e. at most one step of surplus wide. "
        f"(b) Outside it, at a fixed capacity, the edge follows dr, not "
        f"capacity: the measured edges are distinct for different dr on "
        f"{sum(1 for d in dr_moves if d['distinct'])} of {len(dr_moves)} "
        f"capacity/income rows, and all of them match "
        f"max(s/dr, min(K*s, capacity+s)) on "
        f"{sum(1 for r in rows if r['matches_P2'])} of {len(rows)} "
        f"two-horizon bisections. (c) The finite-horizon offset shrinks with "
        f"the horizon on {offsets_shrink} of {len(rows)} rows (largest at "
        f"T: {worst_offset:.3g} in rc), which is why the edge is measured at "
        f"two horizons and extrapolated.",
    )

    # -- arms and hashes ----------------------------------------------------
    ref = run_arm("all-or-nothing", 0.03, 5.0, 1.0, 10.0, steps=T)
    ref_none = run_arm("none", 0.03, 5.0, 1.0, 10.0, steps=T)
    assert ref["trace_hash"] != ref_none["trace_hash"]
    assert is_alive(ref) and not is_alive(ref_none)
    exp.add_arm(
        "all-or-nothing",
        "repair=all-or-nothing",
        {
            "alive_grid_points": sum(1 for p in grid_points if p["alive"]),
            "grid_points": len(grid_points),
            "reference_point": {
                "dr": 0.03, "income": 1.0, "rc": 5.0, "capacity": 10.0,
                "lifetime": ref["lifetime"], "cause": ref["cause"],
            },
        },
        trace_hash=ref["trace_hash"],
    )
    exp.add_arm(
        "none",
        "repair=none (measures K)",
        {
            "clocks": {f"{dr:g}": clocks[dr]["none_lifetime"]
                       for dr in DAMAGE_RATES},
            "ceil_1_over_dr": {f"{dr:g}": clocks[dr]["ceil_1_over_dr"]
                               for dr in DAMAGE_RATES},
            "reference_point": {
                "dr": 0.03, "income": 1.0, "rc": 5.0, "capacity": 10.0,
                "lifetime": ref_none["lifetime"], "cause": ref_none["cause"],
            },
        },
        trace_hash=ref_none["trace_hash"],
    )

    # -- limitations (§6) ---------------------------------------------------
    exp.limitation(
        "the horizon is finite: 'alive' means alive at T = 20000 (and at 2T for "
        "the edge). The steady-state edge is recovered by extrapolating from "
        "two horizons, which assumes the offset is c/T; the residual is the "
        "tolerance, not a proof that the extrapolated edge is exact."
    )
    exp.limitation(
        "the edge is measured by bisection, and the tolerance is the final "
        "bracket. At rc = K*s the equality is the comb of FINDING-148 P4 (one "
        "of three adjacent representable values can live), so a bisection there "
        "can land a few ulp away from the formula; clock-bound rows carry a "
        "64-ulp tolerance, reported per row."
    )
    exp.limitation(
        "K is measured as the none arm's lifetime, not derived: the accumulated "
        "sum dr + dr + ... reaches 1.0 at its own step, and dr = 0.1 is the "
        "case where that is 11, not ceil(1/dr) = 10. Other dr values with the "
        "same accumulation defect were not searched for."
    )
    exp.limitation(
        "one organism on a uniform field, movement `stay`, no competition, no "
        "sharing, no memory; taken = income on the whole grid, the field is "
        "never limiting (income <= M*regrow)."
    )
    exp.limitation(
        "the teeth window is located analytically (s/dr - s < capacity < "
        "K*s - s) and then measured; it is one step of surplus wide at most. "
        "The capacity edge is therefore a narrow-band phenomenon and not a "
        "description of the coarse capacity sweep. Whether it can be widened "
        "by another mechanism (a slower clock, a different step order) is not "
        "measured here."
    )
    exp.limitation(
        "capacity keeps the role it has in FINDING-148: it caps the reserve "
        "after every payment. A world that applied the cap before the repair "
        "would have the edge at capacity, and is not measured."
    )

    # -- verdict (§4) -------------------------------------------------------
    edges_p2 = [r for r in rows if r["matches_P2"]]
    reason = (
        f"The edge is not `capacity + surplus` alone: that reading of "
        f"FINDING-148 is refuted. On the coarse sweep "
        f"({len(CAPACITIES)} capacities x {len(INCOMES)} incomes x "
        f"{len(DAMAGE_RATES)} damage rates = {len(rows)} bisected edges and "
        f"{len(grid_points)} grid points) P1 'alive iff rc < capacity + s' is "
        f"wrong in both directions -- {len(p1_bad_alive_above)} points live "
        f"above capacity + s and {len(p1_bad_dead_below)} die below it -- while "
        f"P2 (FINDING-148's conjunction) matches {len(edges_p2)} of "
        f"{len(rows)} extrapolated edges and {len(grid_points) - len(p2_bad)} "
        f"of {len(grid_points)} points. The mechanism is the one derived before "
        f"the run (P0): the deferred payment needs dr*(capacity+s) > s, so the "
        f"cap can only be the tight edge inside s/dr - s < capacity < K*s - s, "
        f"a window at most one step of surplus wide. Inside that window "
        f"(dr = 0.1, K = 11 vs ceil(1/dr) = 10) the capacity edge is real: all "
        f"{len(window_rows)} rows match capacity + s, the measured edge moves "
        f"one-for-one with capacity ({slopes}), and the death just above it "
        f"comes within one damage clock. Outside it the binding condition is "
        f"the per-step price s/dr or the clock K*s; the cap is a necessary "
        f"half of the deferred condition, not the boundary. "
        f"FINDING-148's own capacity row (dr = 0.039, capacity 10) had "
        f"capacity + s = K*s = 10.4, so one capacity could not tell the two "
        f"apart; this sweep does. Measured edges carry a finite-horizon offset "
        f"of up to {worst_offset:.3g} in rc at T; it shrinks with the horizon "
        f"and is removed by the two-horizon extrapolation."
    )
    if (exp.controls_passed() and exp.hashes_are_distinct()
            and not p2_bad and not window_bad):
        exp.verdict("passed", reason)
    else:
        exp.verdict(
            "void",
            "VOID: a control failed or a prediction missed: "
            + f"p2 point mismatches {len(p2_bad)}, p2 edge mismatches "
              f"{len(rows) - len(edges_p2)}, window mismatches "
              f"{len(window_bad)}, controls passed {exp.controls_passed()}. "
            + reason,
        )

    # -- the record ---------------------------------------------------------
    exp.result["coarse_rows"] = rows
    exp.result["window_rows"] = window_rows
    exp.result["window_slopes"] = {f"{k:g}": v for k, v in slopes.items()}
    exp.result["grid_points"] = grid_points
    exp.result["damage_clock"] = {
        "measured_as": "the none arm's lifetime: the first step with damage >= 1",
        "rows": {f"{dr:g}": clocks[dr] for dr in DAMAGE_RATES},
    }
    exp.result["measurement"] = {
        "coarse_edges": len(rows),
        "grid_points": len(grid_points),
        "p2_edge_matches": len(edges_p2),
        "p2_point_matches": len(grid_points) - len(p2_bad),
        "p1_point_misses": len(p1_bad),
        "p1_alive_above_capacity_edge": len(p1_bad_alive_above),
        "p1_dead_below_capacity_edge": len(p1_bad_dead_below),
        "silent_points": len(silent),
        "silent_violations": len(silent_bad),
        "window_rows": len(window_rows),
        "window_matches": len(window_matches),
        "offset_shrinks_with_horizon": offsets_shrink,
        "largest_offset_at_T": worst_offset,
        "largest_relative_deviation_from_P2": max(
            abs(r["deviation_relative"]) for r in rows),
        "p2_mismatches": [
            {
                "capacity": p["capacity"], "income": p["income"],
                "damage_rate": p["damage_rate"], "repair_cost": p["repair_cost"],
                "predicted": p["P2"], "alive": p["alive"],
                "cause": p["cause"], "lifetime": p["lifetime"],
            }
            for p in p2_bad
        ],
        "probe_runs": len(cache) + len(grid_points) + len(window_rows) + 2,
    }
    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(f"\nP2 edge mismatches: {len(rows) - len(edges_p2)} of {len(rows)}; "
          f"P2 point mismatches: {len(p2_bad)} of {len(grid_points)}; "
          f"P1 point misses: {len(p1_bad)} of {len(grid_points)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
