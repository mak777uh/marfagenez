"""EXP-151: does the boundary of life survive competition, or was it loneliness?

## The question

`docs/FINDING-149.md` and `docs/FINDING-150.md` close the arithmetic of ONE
organism on a uniform field:

    edge = max( s/dr , min( K*s , capacity + s ) )
    s = taken - maintenance_cost,   taken = min(income, what the cell holds)
    K = min{ k : fl_sum_k(dr) >= 1.0 }   (FINDING-150, measured, not ceil(1/dr))

Every number in 143..150 is from one organism that never had to share a cell.
Competition enters the model in exactly one place -- `taken`: `Life::advance`
hands an organism its share of a cell and `Organism::step` cuts it at `income`.
So the prediction to be written down **before the run** is that the formula of
149 does not change and its INPUT does.

## The arithmetic, before the run (AGENTS.md §1)

Write `S = M*regrow` for the resource one cell supplies per step, `crowd` for
the number of organisms on that cell, `t = income`.

**What the code actually does** (read off `Life::advance_with` and
`Field::regrow_all`, not assumed; the per-step supply `S` is the settled
level's regrowth, `c_next = M*r + (1-r)*(c - eaten)`):

* `Sequential`: organisms are stepped in slot order and each takes
  `min(t, what is left on the cell)`. The cell supplies `S` per step, so in the
  limiting case `S < crowd*t` the shares are a **staircase**

      t_i = clamp(S - (i-1)*t, 0, t)

  and in the rich case `S >= crowd*t` every organism gets the full `t`.
* `Proportional`: one `income` per cell is split among the organisms that have
  not yet eaten there, so each asks `t/crowd`. If the cell can supply a whole
  `t` (`S >= t`) every organism gets `t/crowd`; if not (`S < t`) the first
  `floor(S/(t/crowd))` get `t/crowd` and the rest get nothing.

The mean of the staircase is `S/crowd`, and that is exactly the
`taken_n = min(income, M*regrow/n)` of the brief -- but the mean is not what
any organism eats. The two candidate inputs are therefore

    P_mean (the brief): one taken for everybody,
        taken_n = min(t, S/crowd),
        edge_n  = max( s_n/dr , min(K*s_n, capacity + s_n) ),  s_n = taken_n - m
    P_rank (from the code): one taken per rank,
        edge_i  = max( s_i/dr , min(K*s_i, capacity + s_i) ),   s_i = t_i - m

**The observable that separates them is the survivor fraction.** Under P_mean
every organism of a row has the same input, so all `crowd` organisms must die
at the same `rc`: the fraction goes 1 -> 0 in one step at `edge_n`. Under
P_rank the row has a staircase of inputs, so the fraction is a staircase too:
`(crowd-1)/crowd` just below the top rank's edge, and so on.

**Where competition stops being free.** For `Sequential` the threshold is
exactly `S = crowd*t`: at or above it every organism eats `t`, `s` equals the
lone organism's surplus and the edge does not move at all. For `Proportional`
the threshold is `S = t` for the FIRST eater only, because the protocol splits
one `income` no matter how rich the cell is: everyone gets `t/crowd`, so a rich
field is not free at all. The crowd a cell can hold is then limited by the
organism, not the field: `crowd <= t/m` (EXP-99).

**Horizon.** "Alive" means alive at `T`; above the per-step edge the reserve
pays the deficit for `R/(dr*(rc - s/dr))` steps, so the measured edge carries
an offset `~R/(T*dr)` (FINDING-149 P4). Measured at `T` and `2T`, removed by
`edge(inf) ~ 2*edge(2T) - edge(T)`.

## Grid

`income = 1.0`, `maintenance = 0.2`, `capacity = 10`, `regrow = 0.8`,
`energy0 = 5`, `dr in {0.03, 0.1}` (per-step branch and clock branch), crowd
`n in {1,2,4,8}` on ONE cell, both protocols, two fields:

* rich -- `M = 2.5n`, so `S = 2n >= n*income` (the share does not bind);
* poor -- `M = n`, so `S = 0.8n < n*income` (the share binds) and the mean
  supply per organism is 0.8 > maintenance, so P_mean predicts a real edge
  everywhere instead of a dead row.

Plus a locality control: `cells = 3` with two organisms per cell, compared
against the one-cell/two-organism row (same edges expected) and against the
one-cell/six-organism row (different edges expected).

Run: `python3 checks/exp_competition_edge.py` (a few minutes; not in `run.sh`).
The probe must be built first:

    cd core && cargo build --release --example share_probe
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
PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "share_probe")

SEED = 1
INCOME = 1.0
MAINT = 0.2
CAPACITY = 10.0
ENERGY0 = 5.0
REGROW = 0.8
MOVE_COST = 0.0
T = 10000
T2 = 2 * T
DAMAGE_RATES = (0.03, 0.1)
CROWDS = (1, 2, 4, 8)
#: One step of supply per organism: 0.8 (poor, the share binds) and 2.0 (rich,
#: the share does not bind). `M = supply*n/REGROW`, so `M = n` and `M = 2.5n`.
SUPPLY = {"poor": 0.8, "rich": 2.0}
BISECTION_STEPS = 40
#: The mean edge is probed just below and just above to read the fraction of
#: survivors there; a fraction below the mean edge that is not 1 is the whole
#: refutation of P_mean.
FRACTION_OFFSET = 0.005


def clock_of(dr: float) -> int:
    """`K` measured as the `none` arm's lifetime, as in FINDING-149/150."""
    arm = run_arm("sequential", 1, 1, 2.0, INCOME, 1.5, dr, CAPACITY, T,
                  repair="none")
    org = arm["organisms"][0]
    if org["cause"] != "damage":
        raise SystemExit(f"FATAL: the none arm at dr = {dr} died of "
                         f"{org['cause']}, not damage")
    return int(org["lifetime"])


def run_arm(share: str, n: int, cells: int, m: float, income: float,
            rc: float, dr: float, cap: float, steps: int,
            repair: str = "all-or-nothing") -> dict:
    cmd = [
        PROBE, "--policy", "stay", "--repair", repair,
        "--cells", str(cells), "--n", str(n),
        "--steps", str(steps), "--seed", str(SEED),
        "--m", repr(m), "--regrow", repr(REGROW),
        "--income", repr(income), "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc), "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST), "--energy", repr(ENERGY0),
        "--capacity", repr(cap), "--read-budget", "0", "--share", share,
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def taken_vector(share: str, crowd: int, supply: float,
                 income: float) -> list[float]:
    """The settled share of every rank, read off `Life::advance_with`."""
    out: list[float] = []
    left = supply
    if share == "sequential":
        full = supply >= crowd * income
        for _ in range(crowd):
            if full:
                out.append(income)
            else:
                got = min(income, max(left, 0.0))
                out.append(got)
                left -= got
        return out
    ask = income / crowd
    full = supply >= income
    for _ in range(crowd):
        if full:
            out.append(ask)
        else:
            got = min(ask, max(left, 0.0))
            out.append(got)
            left -= got
    return out


def predicted_edge(s: float, dr: float, clock: int, cap: float) -> dict:
    """FINDING-149's edge for one organism with surplus `s`."""
    if s < 0.0:
        return {"edge": None, "binding": "starvation",
                "per_step_edge": s / dr, "clock_edge": clock * s,
                "capacity_edge": cap + s}
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
    return {"edge": edge, "binding": binding, "per_step_edge": per_step,
            "clock_edge": clock_edge, "capacity_edge": cap_edge}


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"no probe at {PROBE}; build it:\n"
              "  cd core && cargo build --release --example share_probe")
        return 2

    # -- §1 arithmetic, written before the run ------------------------------
    arithmetic = {
        "step_order": (
            "eat (share of the cell) -> organism step: income, maintenance, "
            "damage += dr (cap 1.0), repair, capacity cap, death test "
            "(core/src/life.rs, core/src/organism.rs)"
        ),
        "field": (
            "one cell regrows toward M: c_next = M*regrow + (1-regrow)*(c - "
            "eaten); the settled per-step supply is S = M*regrow"
        ),
        "taken_sequential": (
            "slot order, each takes min(income, what is left): if "
            "S >= crowd*income every organism gets income, else the shares "
            "are the staircase t_i = clamp(S - (i-1)*income, 0, income)"
        ),
        "taken_proportional": (
            "one income per cell split among the not-yet-eaten: every "
            "organism asks income/crowd. If S >= income every organism gets "
            "income/crowd; if S < income the first floor(S/(income/crowd)) "
            "get that and the rest get nothing"
        ),
        "P_mean_brief": (
            "one input for everybody: taken_n = min(income, M*regrow/crowd), "
            "s_n = taken_n - maintenance, edge_n = max(s_n/dr, "
            "min(K*s_n, capacity + s_n)). Under P_mean the survivor fraction "
            "is a single cliff 1 -> 0 at edge_n"
        ),
        "P_rank_code": (
            "one input per rank: edge_i = max(s_i/dr, min(K*s_i, "
            "capacity + s_i)) with s_i = t_i - maintenance and t_i from the "
            "protocol staircase; the survivor fraction is a staircase in rc"
        ),
        "mean_is_not_a_rank": (
            "the mean of the staircase, S/crowd, is the mean of the rank "
            "inputs and not the input of any rank, so P_mean is P_rank with "
            "the wrong vector, not with a wrong formula"
        ),
        "where_competition_is_free": (
            "sequential: exactly at S = crowd*income -- at or above it every "
            "organism eats income and the edge does not move. proportional: "
            "never, because the protocol splits one income and not the "
            "supply; the first eater's share is cut as soon as S < income, "
            "and the crowd a cell holds is bounded by income/maintenance, "
            "not by the field (EXP-99)"
        ),
        "damage_clock": (
            "K = the none arm's lifetime = min{k : fl_sum_k(dr) >= 1.0}, "
            "measured, not ceil(1/dr) (FINDING-150)"
        ),
        "horizon_offset": (
            "above the per-step edge the reserve R = min(energy0, capacity) "
            "pays the deficit, so the edge measured at horizon T is "
            "s/dr + R/(T*dr); measured at T and 2T and removed by "
            "edge(inf) ~ 2*edge(2T) - edge(T)"
        ),
        "predicted_edges_examples": {
            "note": (
                "edge = max(s/dr, min(K*s, capacity+s)); the binding branch is "
                "the formula's answer, not a choice: at dr = 0.03 the cap "
                "trims the clock for s > 10/33 (K*s = 34s vs 10 + s) and the "
                "per-step price wins above s ~ 0.324 (33.3s vs 10.8); at "
                "dr = 0.1 the clock beats both for every s < 1"
            ),
            "s=0.8": {"dr=0.03": 26.666666666666668, "dr=0.1": 8.8},
            "s=0.4": {"dr=0.03": 13.333333333333334, "dr=0.1": 4.4},
            "s=0.3": {"dr=0.03": 10.2, "dr=0.1": 3.3},
            "s=0.2": {"dr=0.03": 6.8, "dr=0.1": 2.2},
            "s=0.05": {"dr=0.03": 1.7, "dr=0.1": 0.55},
            "s=0.0": {"dr=0.03": 0.0, "dr=0.1": 0.0},
        },
        "grid": (
            "income 1.0, maintenance 0.2, capacity 10, regrow 0.8, energy0 5; "
            "crowd 1,2,4,8 on one cell; protocols sequential and "
            "proportional; rich M = 2.5n (S = 2n) and poor M = n (S = 0.8n); "
            "dr = 0.03 and 0.1; horizons T = 10000 and 2T = 20000"
        ),
    }

    exp = Experiment(
        experiment_id="competition-edge",
        question=(
            "The boundary of life max(s/dr, min(K*s, capacity+s)) was measured "
            "on one organism that never shared a cell. When n organisms divide "
            "one cell, does the boundary survive -- and if it does, is its "
            "input the mean share min(income, M*regrow/n) of the brief, or "
            "each rank's own share, which the share protocol distributes "
            "unequally?"
        ),
        arithmetic=arithmetic,
        arms={
            "sequential": "share=sequential: slot order, each takes min(income, left)",
            "proportional": "share=proportional: one income per cell split by the crowd",
            "solo-reduced-income": (
                "crowd 1 with income cut to M*regrow/crowd: the world P_mean "
                "describes, measured"
            ),
        },
        seed=SEED,
        command="python3 checks/exp_competition_edge.py",
        parameters={
            "damage_rates": list(DAMAGE_RATES),
            "crowds": list(CROWDS),
            "supply_per_organism": {k: v for k, v in SUPPLY.items()},
            "income": INCOME,
            "maintenance_cost": MAINT,
            "capacity": CAPACITY,
            "energy0": ENERGY0,
            "regrow": REGROW,
            "move_cost": MOVE_COST,
            "t_cap": T,
            "t_cap_second_horizon": T2,
            "bisection_steps": BISECTION_STEPS,
            "seed": SEED,
            "probe": "core/examples/share_probe.rs",
        },
    )

    # -- the damage clock, measured by the arm that never repairs -----------
    clocks: dict[float, dict] = {}
    for dr in DAMAGE_RATES:
        k = clock_of(dr)
        clocks[dr] = {"ceil_1_over_dr": int(math.ceil(1.0 / dr - 1e-9)),
                      "none_lifetime": k}
        print(f"clock dr={dr:<6} ceil={clocks[dr]['ceil_1_over_dr']:<4} "
              f"K={k}", flush=True)

    probe_runs = [0]

    def arm(share, n, cells, m, income, rc, dr, cap, steps, repair="all"):
        probe_runs[0] += 1
        return run_arm(share, n, cells, m, income, rc, dr, cap, steps,
                       repair=repair)

    def alive_at(share, n, cells, m, income, rc, dr, rank, steps):
        a = arm(share, n, cells, m, income, rc, dr, CAPACITY, steps)
        return bool(a["organisms"][rank]["alive"])

    def bisect(share, n, cells, m, income, dr, rank, hint, steps):
        """Edge of one RANK, by bisection on rc (never a grid: a grid is rough)."""
        if hint is None:
            hint = 1.0
        hi = 1.2 * max(hint, 1e-6) + 0.1
        lo = 0.0
        zero = arm(share, n, cells, m, income, 0.0, dr, CAPACITY, steps)
        if not zero["organisms"][rank]["alive"]:
            return {"no_edge": True, "dead_at_zero": True,
                    "cause": zero["organisms"][rank]["cause"],
                    "lifetime_at_zero": zero["organisms"][rank]["lifetime"]}
        for _ in range(3):
            if not alive_at(share, n, cells, m, income, hi, dr, rank, steps):
                break
            hi *= 1.5
        else:
            return {"error": f"rc = {hi} is still alive"}
        for _ in range(BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if mid <= lo or mid >= hi:
                break
            if alive_at(share, n, cells, m, income, mid, dr, rank, steps):
                lo = mid
            else:
                hi = mid
        return {"alive_below": lo, "dead_at": hi, "step": hi - lo}

    def edge_two_horizons(share, n, cells, m_field, income, dr, rank, hint):
        """One rank's edge at T and 2T, extrapolated (FINDING-149 P4)."""
        b1 = bisect(share, n, cells, m_field, income, dr, rank, hint, T)
        if "error" in b1 or b1.get("no_edge"):
            return None, b1
        b2 = bisect(share, n, cells, m_field, income, dr, rank, hint, T2)
        if "error" in b2 or b2.get("no_edge"):
            return None, b2
        e1 = 0.5 * (b1["alive_below"] + b1["dead_at"])
        e2 = 0.5 * (b2["alive_below"] + b2["dead_at"])
        return 2.0 * e2 - e1, {"edge_T": e1, "edge_2T": e2,
                               "step_T": b1["step"]}

    # -- the population rows ------------------------------------------------
    rows: list[dict] = []
    groups: list[dict] = []

    for regime, supply_per_org in SUPPLY.items():
        for protocol in ("sequential", "proportional"):
            for n in CROWDS:
                for dr in DAMAGE_RATES:
                    m_field = supply_per_org * n / REGROW
                    supply = m_field * REGROW
                    clock = clocks[dr]["none_lifetime"]
                    tvec = taken_vector(protocol, n, supply, INCOME)
                    taken_mean = min(INCOME, supply / n)
                    mean_pred = predicted_edge(taken_mean - MAINT, dr, clock,
                                               CAPACITY)
                    row = {
                        "regime": regime,
                        "protocol": protocol,
                        "crowd": n,
                        "cells": 1,
                        "m_field": m_field,
                        "supply_per_cell": supply,
                        "supply_per_organism": supply / n,
                        "income": INCOME,
                        "maintenance_cost": MAINT,
                        "damage_rate": dr,
                        "clock": clock,
                        "taken_mean_predicted": taken_mean,
                        "surplus_mean": taken_mean - MAINT,
                        "P_mean_edge": mean_pred["edge"],
                        "P_mean_binding": mean_pred["binding"],
                        "predicted_taken_by_rank": tvec,
                        "ranks": [],
                        "survival_fraction_below_mean": None,
                        "survival_fraction_above_mean": None,
                        "who_died_first": None,
                    }

                    # Bisect per DISTINCT predicted share, then attribute.
                    seen: dict[float, dict] = {}
                    for rank, taken in enumerate(tvec):
                        s = taken - MAINT
                        pred = predicted_edge(s, dr, clock, CAPACITY)
                        key = round(taken, 12)
                        if key not in seen:
                            hint = pred["edge"] if pred["edge"] is not None else None
                            b1 = bisect(protocol, n, 1, m_field, INCOME, dr,
                                        rank, hint, T)
                            if "error" in b1:
                                print(f"FATAL: bisection failed "
                                      f"({regime},{protocol},n={n},dr={dr},"
                                      f"rank={rank}): {b1['error']}")
                                return 2
                            if b1.get("no_edge"):
                                seen[key] = {"no_edge": True,
                                             "lifetime_at_zero":
                                                 b1["lifetime_at_zero"],
                                             "cause_at_zero": b1["cause"]}
                            else:
                                b2 = bisect(protocol, n, 1, m_field, INCOME,
                                            dr, rank, hint, T2)
                                if "error" in b2 or b2.get("no_edge"):
                                    print(f"FATAL: second bisection failed "
                                          f"({regime},{protocol},n={n},"
                                          f"dr={dr},rank={rank})")
                                    return 2
                                e1 = 0.5 * (b1["alive_below"] + b1["dead_at"])
                                e2 = 0.5 * (b2["alive_below"] + b2["dead_at"])
                                seen[key] = {
                                    "no_edge": False,
                                    "edge_T": e1,
                                    "edge_2T": e2,
                                    "edge": 2.0 * e2 - e1,
                                    "step_T": b1["step"],
                                    "offset_2T": e2,
                                }
                        got = seen[key]
                        rec = {
                            "rank": rank,
                            "taken_predicted": taken,
                            "surplus": s,
                            "P_rank_edge": pred["edge"],
                            "P_rank_binding": pred["binding"],
                            "P_rank_per_step_edge": pred["per_step_edge"],
                            "P_rank_clock_edge": pred["clock_edge"],
                            "P_rank_capacity_edge": pred["capacity_edge"],
                        }
                        if got.get("no_edge"):
                            rec["measured_edge"] = None
                            rec["no_edge_measured"] = True
                            rec["lifetime_at_zero"] = got["lifetime_at_zero"]
                            rec["cause_at_zero"] = got["cause_at_zero"]
                            rec["matches"] = pred["edge"] is None
                            rec["tolerance"] = None
                            rec["deviation"] = None
                        else:
                            measured = got["edge"]
                            dev = measured - pred["edge"]
                            tol = max(got["step_T"], 64 * math.ulp(pred["edge"]),
                                      abs(got["offset_2T"] - pred["edge"]))
                            rec.update({
                                "measured_edge_T": got["edge_T"],
                                "measured_edge_2T": got["edge_2T"],
                                "measured_edge": measured,
                                "deviation": dev,
                                "deviation_relative": dev / pred["edge"]
                                if pred["edge"] else None,
                                "tolerance": tol,
                                "tolerance_kind": (
                                    "bisection bracket, 64 ulp or |offset at 2T|"
                                ),
                                "matches": abs(dev) <= tol,
                            })
                        row["ranks"].append(rec)
                        groups.append({"row": row, "rec": rec})

                    # The survivor fraction around the MEAN edge: the number
                    # that separates "one input for everybody" from a staircase.
                    if row["P_mean_edge"] is not None:
                        for side, frac_key in (
                            (1.0 - FRACTION_OFFSET,
                             "survival_fraction_below_mean"),
                            (1.0 + FRACTION_OFFSET,
                             "survival_fraction_above_mean"),
                        ):
                            rc = row["P_mean_edge"] * side
                            a = arm(protocol, n, 1, m_field, INCOME, rc, dr,
                                    CAPACITY, T)
                            row[frac_key] = (a["alive_end"] / a["total"]
                                             if a["total"] else 0.0)

                    # Who died first, and from what: the model's own answer.
                    a = arm(protocol, n, 1, m_field, INCOME,
                            row["P_mean_edge"] if row["P_mean_edge"] else 1.0,
                            dr, CAPACITY, T)
                    dead = [o for o in a["organisms"]
                            if not o["alive"] and o["lifetime"] is not None]
                    if dead:
                        first = min(dead, key=lambda o: o["lifetime"])
                        row["who_died_first"] = {
                            "rank": first["i"],
                            "lifetime": first["lifetime"],
                            "cause": first["cause"],
                            "alive_end": a["alive_end"],
                            "total": a["total"],
                        }
                    row["taken_measured_steady"] = [
                        o["taken_last"] for o in a["organisms"]
                    ]
                    rows.append(row)

                    pmean_matches = all(
                        r["matches"] and r["P_rank_edge"] is not None
                        and row["P_mean_edge"] is not None
                        and abs(r["P_rank_edge"] - row["P_mean_edge"])
                        <= (r["tolerance"] or 0.0)
                        for r in row["ranks"]
                    )
                    row["P_mean_equals_P_rank"] = pmean_matches
                    print(
                        f"{regime:<4} {protocol[:5]:<5} n={n:<2} dr={dr:<5} "
                        f"S={supply:<5.2f} Pmean={row['P_mean_edge'] if row['P_mean_edge'] is None else round(row['P_mean_edge'], 4)} "
                        f"ranks="
                        + ", ".join(
                            "none" if r["measured_edge"] is None
                            else f"{r['measured_edge']:.4f}"
                            for r in row["ranks"])
                        + f" frac_below={row['survival_fraction_below_mean']}",
                        flush=True,
                    )

    # -- the locality control: three cells, two organisms each --------------
    locality: list[dict] = []
    for protocol in ("sequential", "proportional"):
        m_field = SUPPLY["poor"] * 2 / REGROW   # two per cell, poor regime
        supply = m_field * REGROW
        dr = 0.03
        clock = clocks[dr]["none_lifetime"]
        tvec = taken_vector(protocol, 2, supply, INCOME)
        rec = {"protocol": protocol, "cells": 3, "crowd_per_cell": 2,
               "crowd_total": 6, "m_field": m_field,
               "supply_per_cell": supply, "damage_rate": dr,
               "predicted_edges": [
                   predicted_edge(t - MAINT, dr, clock, CAPACITY)["edge"]
                   for t in tvec
               ],
               "measured_edges": [],
               }
        for rank in range(6):
            per_cell_rank = rank // 3
            hint = predicted_edge(tvec[per_cell_rank] - MAINT, dr, clock,
                                  CAPACITY)["edge"]
            edge, info = edge_two_horizons(protocol, 6, 3, m_field, INCOME,
                                          dr, rank, hint)
            if "error" in info:
                print(f"FATAL: locality bisection failed: {info['error']}")
                return 2
            rec["measured_edges"].append(edge)
        # Same cells, one organism each: the crowd is 1, not 2 (specificity of
        # "it is the crowd on the cell", not the population size).
        rec["one_per_cell_predicted_edge"] = predicted_edge(
            INCOME - MAINT, dr, clock, CAPACITY)["edge"]
        rec["one_per_cell_measured_edge"] = None
        edge, info = edge_two_horizons(
            protocol, 3, 3, m_field, INCOME, dr, 0,
            rec["one_per_cell_predicted_edge"])
        if "error" not in info:
            rec["one_per_cell_measured_edge"] = edge
        rec["one_per_cell_matches"] = (
            edge is not None
            and abs(edge - rec["one_per_cell_predicted_edge"]) <= 1e-3
        )
        locality.append(rec)
        print(f"locality {protocol[:5]} cells=3 2/cell: "
              f"measured={[None if e is None else round(e, 4) for e in rec['measured_edges']]} "
              f"one-per-cell={rec['one_per_cell_measured_edge']}", flush=True)

    # -- the specific control: the world P_mean describes, measured ---------
    specific_rows: list[dict] = []
    for regime, supply_per_org in SUPPLY.items():
        for n in (2, 4, 8):
            dr = 0.03
            clock = clocks[dr]["none_lifetime"]
            m_field = supply_per_org * n / REGROW
            supply = m_field * REGROW
            reduced = min(INCOME, supply / n)   # = min(income, S/n)
            pred = predicted_edge(reduced - MAINT, dr, clock, CAPACITY)
            # `income` is cut to the mean share, and the field is rich for it
            # (`supply >= reduced` for every n), so this solo organism eats
            # exactly the mean share: it is P_mean's world.
            b1 = bisect("sequential", 1, 1, m_field, reduced, dr, 0,
                        pred["edge"], T)
            b2 = bisect("sequential", 1, 1, m_field, reduced, dr, 0,
                        pred["edge"], T2)
            if "error" in b1 or "error" in b2 or b1.get("no_edge"):
                print("FATAL: the reduced-income control did not bisect")
                return 2
            e1 = 0.5 * (b1["alive_below"] + b1["dead_at"])
            e2 = 0.5 * (b2["alive_below"] + b2["dead_at"])
            edge = 2.0 * e2 - e1
            specific_rows.append({
                "regime": regime, "crowd": n, "damage_rate": dr,
                "original_income": INCOME,
                "reduced_income": reduced,
                "field_supply": supply,
                "predicted_edge": pred["edge"],
                "measured_edge": edge,
                "deviation": edge - pred["edge"],
                "tolerance": max(b1["step"], 64 * math.ulp(pred["edge"]),
                                 abs(e2 - pred["edge"])),
            })
            print(f"specific {regime} n={n} income'={reduced:g}: "
                  f"pred={pred['edge']:.4f} measured={edge:.4f}",
                  flush=True)

    # -- prediction checks --------------------------------------------------
    mean_misses = []
    rank_misses = []
    noise_rows = []
    for row in rows:
        for r in row["ranks"]:
            if not r["matches"]:
                rank_misses.append((row, r))
            if row["P_mean_edge"] is None:
                continue
            if r["measured_edge"] is None:
                mean_misses.append((row, r))
                continue
            dev = r["measured_edge"] - row["P_mean_edge"]
            if abs(dev) > (r["tolerance"] or 0.0):
                mean_misses.append((row, r))

    # Rows where P_mean and P_rank agree: the test must be silent there.
    for row in rows:
        if row["P_mean_equals_P_rank"]:
            row["silent"] = True
            noise_rows.append(row)

    # The mean prediction has to miss for a reason that is not noise: the
    # survivor fraction below the mean edge must be a staircase, not 1.
    staircase = [
        row for row in rows
        if row["survival_fraction_below_mean"] not in (None, 1.0)
    ]

    silent_bad = [
        row for row in noise_rows
        if any(not r["matches"] for r in row["ranks"])
    ]

    # The shift is a function of the rank's own share, not of the crowd: a
    # row with two distinct shares must show two distinct measured edges, in
    # the predicted order.
    distinct_ok = 0
    distinct_rows = 0
    for row in rows:
        measured = sorted({round(r["measured_edge"], 6)
                           for r in row["ranks"]
                           if r["measured_edge"] is not None})
        predicted = sorted({round(r["P_rank_edge"], 6)
                            for r in row["ranks"]
                            if r["P_rank_edge"] is not None})
        if len(predicted) > 1:
            distinct_rows += 1
            if len(measured) == len(predicted):
                distinct_ok += 1

    # Locality: three cells x two organisms reproduce the one-cell/two ones,
    # and not the one-cell/six-organism row.
    one_cell_two = {}
    one_cell_eight = {}
    for row in rows:
        if row["damage_rate"] == 0.03 and row["regime"] == "poor":
            if row["crowd"] == 2:
                one_cell_two[row["protocol"]] = row
            if row["crowd"] == 8:
                one_cell_eight[row["protocol"]] = row
    locality_bad = []
    for rec in locality:
        ref = one_cell_two.get(rec["protocol"])
        if ref is None:
            continue
        ref_edges = sorted({round(r["measured_edge"], 6)
                            for r in ref["ranks"]
                            if r["measured_edge"] is not None})
        got_edges = sorted({round(e, 6) for e in rec["measured_edges"]
                            if e is not None})
        ok = len(got_edges) == len(ref_edges) and all(
            abs(a - b) <= 1e-3 for a, b in zip(got_edges, ref_edges))
        rec["matches_one_cell_two"] = ok
        rec["one_cell_two_edges"] = ref_edges
        differs = True
        ref8 = one_cell_eight.get(rec["protocol"])
        if ref8 is not None:
            e8 = sorted({round(r["measured_edge"], 6) for r in ref8["ranks"]
                         if r["measured_edge"] is not None})
            differs = not (len(e8) == len(got_edges) and all(
                abs(a - b) <= 1e-3 for a, b in zip(e8, got_edges)))
        rec["differs_from_one_cell_eight"] = differs
        if not ok or not differs or not rec.get("one_per_cell_matches"):
            locality_bad.append(rec)

    specific_bad = [
        s for s in specific_rows
        if abs(s["deviation"]) > s["tolerance"]
    ]
    # ... and the population must not live in that world: no rank may have the
    # mean edge among its own.
    mean_edge_is_a_rank = []
    for s in specific_rows:
        for row in rows:
            if row["P_mean_equals_P_rank"]:
                # there the mean IS the rank's input (rich sequential, crowd
                # 1); a coincidence of the two models is not a coincidence of
                # the mean with a rank's separate input.
                continue
            if (row["regime"] == s["regime"]
                    and row["damage_rate"] == s["damage_rate"]
                    and row["crowd"] == s["crowd"]):
                for r in row["ranks"]:
                    if (r["measured_edge"] is not None
                            and abs(r["measured_edge"] - s["measured_edge"])
                            <= 1e-2):
                        mean_edge_is_a_rank.append((s, row, r))

    exp.control(
        "fires",
        bool(mean_misses) and bool(staircase) and not rank_misses,
        f"the mean share min(income, S/crowd) is the wrong input: P_mean is "
        f"wrong on {len(mean_misses)} rank edges of "
        f"{sum(len(r['ranks']) for r in rows)}, while P_rank (each rank's own "
        f"staircase share through the SAME 149 formula) matches "
        f"{sum(len(r['ranks']) for r in rows) - len(rank_misses)} of "
        f"{sum(len(r['ranks']) for r in rows)}. The fraction of survivors just "
        f"below the mean edge is not 1 on {len(staircase)} rows: "
        + "; ".join(
            f"{r['regime']} {r['protocol']} n={r['crowd']} -> "
            f"{r['survival_fraction_below_mean']:.2f}"
            for r in staircase[:6])
        + f" (P_mean demands 1.00, then 0.00 above). Examples of the miss: "
        + "; ".join(
            f"{row['regime']} {row['protocol']} n={row['crowd']} rank="
            f"{r['rank']}: P_mean={row['P_mean_edge']:.4f} vs measured="
            f"{(r['measured_edge'] if r['measured_edge'] is not None else float('nan')):.4f}"
            for row, r in mean_misses[:4]),
    )

    exp.control(
        "silent",
        not silent_bad,
        f"{len(noise_rows)} of {len(rows)} rows are silent: there P_mean and "
        f"P_rank predict the same edge ({sum(1 for r in noise_rows if r['regime'] == 'rich' and r['protocol'] == 'sequential')} "
        f"rich/sequential rows, where S = 2n >= n*income pays everybody full "
        f"income, and the crowd-1 rows where there is nobody to share with). "
        f"Measurement disagrees with both on {len(silent_bad)} of them, and "
        f"the edge does not move with the crowd on those rows: "
        + "; ".join(
            f"{r['regime']} {r['protocol']} n={r['crowd']} dr={r['damage_rate']} "
            f"edge={[round(x['measured_edge'], 4) for x in r['ranks'] if x['measured_edge'] is not None]}"
            for r in noise_rows if r["regime"] == "rich"
            and r["protocol"] == "sequential" and r["damage_rate"] == 0.03),
    )

    exp.control(
        "specific",
        (not specific_bad and not locality_bad
         and distinct_rows > 0 and distinct_ok == distinct_rows
         and not mean_edge_is_a_rank),
        f"the edge is a function of the organism's OWN share, not of the crowd "
        f"as a number. (a) A solo organism whose income is cut to the mean "
        f"share S/crowd reproduces P_mean's edge: "
        + "; ".join(f"{s['regime']} n={s['crowd']}: predicted "
                    f"{s['predicted_edge']:.4f}, measured "
                    f"{s['measured_edge']:.4f}" for s in specific_rows)
        + f" -- the rc-edge is the same function of `taken` there, so the "
        f"formula did not change. (b) Inside one population the ranks have "
        f"DIFFERENT shares and their measured edges are correspondingly "
        f"distinct: {distinct_ok} of {distinct_rows} rows with two or more "
        f"distinct predicted shares show as many distinct measured edges. "
        f"(c) The competition is the crowd on the CELL, not the population: "
        f"three cells with two organisms each give the same edges as one cell "
        f"with two ({[r.get('matches_one_cell_two') for r in locality]}), "
        f"they differ from the edges of one cell with eight "
        f"({[r.get('differs_from_one_cell_eight') for r in locality]}), and "
        f"one organism per cell keeps the lone edge "
        f"({[r.get('one_per_cell_matches') for r in locality]}). (d) The "
        f"mean edge is a real, "
        f"measurable edge ({len(specific_rows) - len(specific_bad)} of "
        f"{len(specific_rows)} reproduced) that NO rank of the population "
        f"has: {len(mean_edge_is_a_rank)} rank edge(s) of a crowd larger than "
        f"one, on a row where the mean is not a rank's input, coincide with "
        f"it within 1e-2.",
    )

    # -- arms and hashes ----------------------------------------------------
    refs = {}
    for protocol in ("sequential", "proportional"):
        a = arm(protocol, 2, 1, 2.0 * SUPPLY["poor"] / REGROW, INCOME, 5.0,
                0.03, CAPACITY, T)
        refs[protocol] = a
    solo = arm("sequential", 1, 1, 2.0, 0.8, 5.0, 0.03, CAPACITY, T)
    for k, a in refs.items():
        exp.add_arm(
            k, f"share={k}",
            {"crowd": 2, "alive_end": a["alive_end"], "total": a["total"],
             "taken_steady": [o["taken_last"] for o in a["organisms"]],
             "lifetimes": [o["lifetime"] for o in a["organisms"]]},
            trace_hash=a["hash"],
        )
    exp.add_arm(
        "solo-reduced-income",
        "crowd 1 with income cut to M*regrow/crowd",
        {"income": 0.8, "supply": 2.0, "alive_end": solo["alive_end"],
         "total": solo["total"], "lifetime": solo["organisms"][0]["lifetime"]},
        trace_hash=solo["hash"],
    )

    # -- limitations (§6) ---------------------------------------------------
    exp.limitation(
        "the horizon is finite: 'alive' means alive at T = 10000 (and at 2T). "
        "The steady-state edge is recovered by extrapolating from two "
        "horizons, which assumes the offset is c/T; the residual is the "
        "tolerance, not a proof that the extrapolated edge is exact. A rank "
        "whose surplus is just below zero survives the horizon if |s| < "
        "energy0/T, and no rank here is that close."
    )
    exp.limitation(
        "the steady shares are the SETTLED ones. The field starts full, so the "
        "first two or three steps pay everybody more than the settled share; "
        "the two-horizon extrapolation removes that one-off bonus only in its "
        "effect on the edge, not in the recorded taken_mean, which is the mean "
        "over each organism's own life."
    )
    exp.limitation(
        "K is measured as the none arm's lifetime, not derived: FINDING-150 "
        "showed K = ceil(1/dr) except in a few ulp around dr = 1/n, and both "
        "dr here (0.03, 0.1) are measured, not assumed."
    )
    exp.limitation(
        "movement is `stay`, the field is uniform, there is no reproduction, "
        "no memory, no read budget and no interaction between organisms other "
        "than the share of one cell. Whether the staircase survives movement "
        "(where an organism can leave a crowded cell) is not measured."
    )
    exp.limitation(
        "the population is imposed, not settled: nothing reproduces, so the "
        "crowd is whatever `--n` says. This measures which ranks of a given "
        "crowd survive, not where a crowd would settle (EXP-99)."
    )
    exp.limitation(
        "one cell per crowd in the main grid; the locality control uses three "
        "cells with two organisms each and only at dr = 0.03 and the poor "
        "regime. Field geometry beyond that (a gradient, a moving field) is "
        "not measured."
    )
    exp.limitation(
        "the threshold where competition stops being free is derived for "
        "these two protocols only. A third protocol (equal split of the "
        "SUPPLY instead of the income) would have a different threshold and "
        "is not in `core`."
    )

    # -- verdict (§4) -------------------------------------------------------
    total_ranks = sum(len(r["ranks"]) for r in rows)
    reason = (
        f"The boundary of FINDING-149 survives competition, but its input is "
        f"the organism's own share, not the mean the brief proposed. On "
        f"{len(rows)} population rows ({len(CROWDS)} crowds x 2 protocols x 2 "
        f"fields x {len(DAMAGE_RATES)} damage rates, {total_ranks} rank edges "
        f"bisected at two horizons) the same formula "
        f"max(s/dr, min(K*s, capacity+s)) matches "
        f"{total_ranks - len(rank_misses)} of {total_ranks} ranks when s is "
        f"each rank's own surplus, and the single mean share "
        f"min(income, S/crowd) misses {len(mean_misses)} of them. The "
        f"mechanism is the share protocol, and it is a number: under "
        f"Sequential the settled shares are the staircase clamp(S - "
        f"(i-1)*income, 0, income), so in the poor field the first ranks eat "
        f"the full income and keep the lone organism's edge while the tail "
        f"starves; under Proportional one income is split among the crowd, so "
        f"everybody eats income/crowd and the edge shrinks with the crowd even "
        f"in a field rich enough to pay the whole crowd. The survivor fraction "
        f"just below the mean edge is not 1 on {len(staircase)} rows, which is "
        f"the observable the mean model cannot produce. Competition is free "
        f"exactly where it is free for the protocol: Sequential stops binding "
        f"at S = crowd*income (the brief's threshold, measured: the rich "
        f"rows), Proportional never stops binding, because it splits one "
        f"income and not the supply -- its crowd limit is income/maintenance "
        f"(EXP-99), not M*regrow. The reduced-income solo control reproduces "
        f"the mean edge on all {len(specific_rows)} rows, so the formula is "
        f"unchanged: only the vector of inputs was wrong. The locality control "
        f"shows the competition is the crowd on the cell, not the population."
    )
    apparatus_ok = (exp.controls_passed() and exp.hashes_are_distinct()
                    and not silent_bad and not specific_bad
                    and not locality_bad)
    if apparatus_ok and not rank_misses and mean_misses:
        exp.verdict("passed", reason)
    elif apparatus_ok and rank_misses:
        exp.verdict(
            "failed",
            f"the per-rank law does not hold: {len(rank_misses)} rank edges "
            f"miss the 149 formula with the rank's own share. " + reason,
        )
    elif apparatus_ok:
        exp.verdict(
            "failed",
            "the mean share of the brief was not refuted on this grid, so the "
            "claim that the input is the rank's own share is not established. "
            + reason,
        )
    else:
        exp.verdict(
            "void",
            f"VOID: the apparatus is broken: controls passed "
            f"{exp.controls_passed()}, hashes distinct "
            f"{exp.hashes_are_distinct()}, silent rows disagreeing "
            f"{len(silent_bad)}, specific-control misses "
            f"{len(specific_bad)}, locality misses {len(locality_bad)}. "
            + reason,
        )

    # -- the record ---------------------------------------------------------
    exp.result["rows"] = rows
    exp.result["specific_rows"] = specific_rows
    exp.result["locality"] = locality
    exp.result["damage_clock"] = {
        "measured_as": "the none arm's lifetime",
        "rows": {f"{dr:g}": clocks[dr] for dr in DAMAGE_RATES},
    }
    exp.result["measurement"] = {
        "rows": len(rows),
        "rank_edges": total_ranks,
        "rank_edges_matching": total_ranks - len(rank_misses),
        "rank_edge_misses": [
            {"regime": row["regime"], "protocol": row["protocol"],
             "crowd": row["crowd"], "damage_rate": row["damage_rate"],
             "rank": r["rank"], "predicted": r["P_rank_edge"],
             "measured": r["measured_edge"], "deviation": r["deviation"],
             "tolerance": r["tolerance"]}
            for row, r in rank_misses
        ],
        "P_mean_misses": len(mean_misses),
        "P_mean_equals_P_rank_rows": len(noise_rows),
        "rows_with_a_survivor_staircase": len(staircase),
        "rows_with_two_distinct_predicted_edges": distinct_rows,
        "rows_with_as_many_measured_edges": distinct_ok,
        "specific_control_rows": len(specific_rows),
        "specific_control_matches": len(specific_rows) - len(specific_bad),
        "locality_rows": len(locality),
        "locality_mismatches": len(locality_bad),
        "mean_edge_shared_by_a_rank": len(mean_edge_is_a_rank),
        "probe_runs": probe_runs[0],
    }
    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(f"\nrank edges: {total_ranks - len(rank_misses)} of {total_ranks} "
          f"match P_rank; P_mean misses {len(mean_misses)} rank edges; "
          f"staircase rows {len(staircase)} of {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
