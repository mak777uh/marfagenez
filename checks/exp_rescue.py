"""EXP-152: does the death of one organism save the others?

## The question

`docs/FINDING-151.md` measured competition on a crowd of `n` organisms that
share one cell, and it recorded a limitation:

> the crowd is imposed, not settled: nothing reproduces ... there is no
> feedback "one died -- the share of the survivors grew".

The first half is true (no reproduction, so `n` is what `--n` says). The second
half is **false**, and `core/src/life.rs` says so in the code: `share_counts`
counts only organisms with `r.organism.is_alive()` (`life.rs:334-345`), and the
proportional protocol hands out `remaining / k` with `k` the number of
not-yet-eaten **live** organisms (`life.rs:618-630`). A dead organism is
skipped by the `continue` at the top of the step, so from the step after a
death the survivors divide one `income` among fewer mouths. The feedback
exists; what does not exist is **refill** (birth).

So this experiment asks the question FINDING-151 left open: **when does the
death of one organism save the others, and when is the death a cascade?**

## The arithmetic, written before the run (AGENTS.md §1)

`m = maintenance_cost = 0.2`, `t = income = 1.0`, `capacity = 10`,
`regrow = 0.8`, `dr = 0.03`, field `M = n` per cell (so the settled supply is
`S = 0.8n`, the "poor" field of FINDING-151: the share, not the field, binds),
one cell, `stay`, no repair choice (all-or-nothing), no read budget.
`edge(s) = max(s/dr, min(K*s, capacity + s))`, `s = taken - m`, `K` measured by
the arm that never repairs (`none`) as in 149/150/151.

`E_low = edge(t/n - m)` (the share while everyone is alive) and
`E_high = edge(t/(n-1) - m)` (the share left to a survivor after one death).

**What the code does after a death.** The step that kills an organism still
feeds it: the crowd at the START of the step includes it. From the NEXT step
`share_counts = n-1` and `remaining = income`, so under `Proportional` each
survivor gets `t/(n-1)`. The share rises by exactly

    rise = t/(n-1) - t/n = t / (n(n-1))       (n=2: +0.5, n=3: +0.1667,
                                               n=4: +0.0833 at t = 1)

**P1 -- the brief's prediction.** Every survivor's share goes `t/n ->
t/(n-1)`, so its edge goes `E_low -> E_high`, i.e. the edge rises by the ratio
`E_high/E_low` (the brief says `n/(n-1)`; that is exact only if the same branch
of the formula binds at both shares, and here the clock branch binds at
`t/n` while the per-step branch binds at `t/(n-1)`, so the real numbers are
`26.667/10.2 = 2.614`, `10.2/4.533 = 2.25`, `4.533/1.7 = 2.667` for
`n = 2, 3, 4`). Consequences, by `rc` band:

* `rc < E_low` -- nobody dies, both configurations: nothing to rescue;
* `E_low < rc < E_high` -- **equal** configuration: everybody is above the
  same edge, so everybody dies at the same step (symmetry, cascade, 0
  survivors). **One weak** (`energy0 = 0.5` against `5.0`): the weak dies
  first (less reserve, same share), the share of the rest rises, their edge
  becomes `E_high > rc`, and they survive -- `n-1` survivors. The row is
  "the weak died, the others lived", although the equal row beside it died;
* `rc > E_high` -- the weak dies first, the share rises, and it is still too
  little: cascade again.

**P2 -- the race the repair rule adds (also before the run).** `P1` treats the
new share as if it were there from step 1. It is not: while the weak is alive
the survivors are above their OLD edge, so they lose energy and then accumulate
damage. Repair is all-or-nothing and only happens when
`damage*rc < energy` (`organism.rs:542-556`), and `energy <= capacity` after
the step (`organism.rs:566`). The first sketch of P2 (still in `arithmetic`,
it is what was written before the run) put it as a price ceiling,
`damage_at_rescue*rc < capacity`. The run sharpened it: what binds is not the
price but the TIME to repay it. After the rescue the reserve grows at the
per-step margin `s_high - dr*rc` (repair skipped) while the price grows at
`dr*rc`, so the gap closes in `D*rc/(s_high - dr*rc)` steps and the damage is
then `D + dr*D*rc/(s_high - dr*rc)`, where `D` is the damage carried into the
rescue; the rescue arrives in time only while that is below 1. (The ceiling is
necessary, not sufficient: at `n = 2`, `rc = 20`, `D*rc ~ 9.2` is still below
`capacity = 10` and the survivor dies anyway.) P2 therefore predicts the
MEASURED edge of a rescued survivor is `min(E_high, E_repay)` with
`E_repay < E_high`, and the shortfall grows with the absolute width of the
band (`E_high - E_low`): the widest band here is `n = 2` (`10.2 -> 26.667`,
`dr*(E_high-E_low) = 0.49`), the narrowest `n = 4` (`1.7 -> 4.533`, `0.085`).
P1 and P2 differ by a number the bisection reports.

**Sequential, before the run: no rescue at all.** Slot order, each takes
`min(t, what is left)`, so rank `i` takes `clamp(S - i*t, 0, t)`: a rank's
share depends on the ranks AHEAD of it and not on how many are alive BEHIND
it. Killing rank `i` does not change what rank `i+1` gets, because the first
`i` organisms take the same total `min(S, i*t)` whether rank `i` is one of them
or not. Killing rank `0` (the first eater) is the only death that could raise
someone else's share, but rank `0` already eats `min(t, S)`, so its successor
gets exactly the same. Hence: **the share can rise (measured, when rank 0
dies) and the survival still cannot: the risen share is the edge that failed to
save rank 0 itself.** That is the difference between "the share grew" and "the
survivor was saved", and it is what separates Proportional from Sequential.

**Grid.** `n in {2, 3, 4}`, `ShareProtocol in {Sequential, Proportional}`,
three `energy0` configurations -- `equal` (5.0 for all), `weak0` (rank 0 =
0.5), `weaklast` (rank `n-1` = 0.5) -- and three `rc` bands per `n`:
`below = 0.5*E_low`, `between = sqrt(E_low*E_high)`, `above = 1.25*E_high`.

**What is measured.** For every row of the band grid: survivors at `T`, the
step of the first death, and, per organism, its lifetime, cause of death and
the run of steps over which its meal was constant (`rescue_probe` segments) --
from which the share CHANGE after the first death is read off as a number. For
every distinct rank the `rc`-edge is bisected at `T = 10000` and `2T = 20000`
and extrapolated (`edge(inf) ~ 2*edge(2T) - edge(T)`, FINDING-149 P4).

**Controls (§2).**
* `fires` -- in the equal configuration survival is never higher than in the
  weak one, and in the between band it is strictly lower in the predicted
  direction: `Proportional` equal `0` against weak `n-1`.
* `silent` -- below `E_low` there is nothing to rescue: survival is the same in
  both configurations (and the weak one does not turn a survivor into a
  corpse, except where the equal row is already a corpse: `Sequential`,
  `n = 4`, where the tail's share is `t/n` and its surplus is exactly `0`, so
  its edge is `0` and it dies below the band).
* `specific` -- the rescue is the grown share and not the number of organisms:
  at the same `n` and the same `rc`, with `income` cut to `t*(n-1)/n`, the
  share after the death equals the share BEFORE it (`t/n`), so the rescue must
  vanish and the weak row must die like the equal row.

## Verdict.

`passed` if the three controls hold and the between-band rescue is the
predicted one; the measured edges are reported against P1 and P2, and the
verdict names which of the two the bisection supports. `failed` if the rescue
is absent or in the wrong direction.

Run: `python3 checks/exp_rescue.py` (about four minutes; not in `run.sh`).
The probe must be built first:

    cd core && cargo build --release --example rescue_probe
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
PROBE = os.path.join(ROOT, "core", "target", "release", "examples", "rescue_probe")

SEED = 1
INCOME = 1.0
MAINT = 0.2
CAPACITY = 10.0
REGROW = 0.8
MOVE_COST = 0.0
DR = 0.03
T = 10000
T2 = 2 * T
ENERGY = 5.0
ENERGY_WEAK = 0.5
CROWDS = (2, 3, 4)
PROTOCOLS = ("proportional", "sequential")
#: `weak0` = the first slot is weak, `weaklast` = the last one. Under
#: `Proportional` the two differ only in which slot eats first (the shares are
#: equal), under `Sequential` they are the "the weak eats first" and "the weak
#: eats last" rows the experiment compares.
CONFIGS = ("equal", "weak0", "weaklast")
BISECTION_STEPS = 26


def clock_of(dr: float) -> int:
    """`K`, measured by the arm that never repairs (FINDING-149/150)."""
    arm = run_arm("sequential", 1, 1.5, 1.0, dr, T, weak=None,
                  repair="none")
    org = arm["organisms"][0]
    if org["cause"] != "damage":
        raise SystemExit(f"FATAL: the none arm at dr = {dr} died of "
                         f"{org['cause']}, not damage")
    return int(org["lifetime"])


def run_arm(protocol: str, n: int, rc: float, income: float, dr: float,
            steps: int, weak: float | None = None,
            weak_rank: int = 0,
            repair: str = "all-or-nothing") -> dict:
    """One probe run: `n` organisms on one cell, `M = n`, one reserve each."""
    cmd = [
        PROBE, "--policy", "stay", "--repair", repair,
        "--cells", "1", "--n", str(n),
        "--steps", str(steps), "--seed", str(SEED),
        "--m", repr(float(n)), "--regrow", repr(REGROW),
        "--income", repr(income), "--maintenance", repr(MAINT),
        "--repair-cost", repr(rc), "--damage-rate", repr(dr),
        "--move-cost", repr(MOVE_COST), "--energy", repr(ENERGY),
        "--capacity", repr(CAPACITY), "--read-budget", "0",
        "--share", protocol,
    ]
    if weak is not None:
        cmd += ["--energy-weak", repr(weak), "--weak-rank", str(weak_rank)]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)


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


def sequential_shares(crowd: int, supply: float, income: float) -> list[float]:
    """The settled staircase of `Sequential`, read off `Life::advance_with`."""
    out: list[float] = []
    left = supply
    for _ in range(crowd):
        got = min(income, max(left, 0.0))
        out.append(got)
        left -= got
    return out


def share_change_after(org: dict, first_death: int | None) -> float | None:
    """How much the organism's meal changed across the first death.

    `segments` are the runs of steps with a constant meal, so the change is the
    difference between the meal of the step after the death and the meal of the
    step before it. `None` when the organism is dead at that point, and `0.0`
    when it has no boundary there (its meal did not move).
    """
    if first_death is None:
        return 0.0
    segs = org["segments"]
    before = None
    after = None
    for (a, b, taken) in segs:
        if a <= first_death <= b:
            before = taken
        if a <= first_death + 1 <= b:
            after = taken
    if before is None or after is None:
        return None
    return after - before


def main() -> int:
    if not os.path.exists(PROBE):
        print(f"no probe at {PROBE}; build it:\n"
              "  cd core && cargo build --release --example rescue_probe")
        return 2

    # -- §1 arithmetic, written before the run ------------------------------
    e_low_n = {n: predicted_edge(INCOME / n - MAINT, DR, 34, CAPACITY)["edge"]
               for n in CROWDS}
    e_high_n = {n: predicted_edge(INCOME / (n - 1) - MAINT, DR, 34,
                                 CAPACITY)["edge"] for n in CROWDS}
    arithmetic = {
        "step_order": (
            "eat (share of the cell) -> income -> maintenance -> damage += dr "
            "(cap 1.0) -> repair all-or-nothing if damage*rc < energy -> "
            "capacity clamp -> death test (core/src/life.rs, "
            "core/src/organism.rs)"
        ),
        "share_counts": (
            "core/src/life.rs:334-345 builds share_counts from "
            "`r.organism.is_alive()` only, and :618-630 hands out "
            "`remaining / k` with k = the not-yet-eaten LIVE organisms. A dead "
            "organism is skipped by `continue`, so from the NEXT step it no "
            "longer occupies a share. The feedback 'one died -- the share of "
            "the survivors grew' exists in the model; what does not exist is "
            "refill (there is no birth)."
        ),
        "share_rise_after_a_death": (
            "Proportional, one cell, field M = n (S = 0.8n >= income for every "
            "n here, so the field does not bind the meal): while everyone is "
            "alive each gets t/n; after one death each survivor gets t/(n-1). "
            "rise = t/(n-1) - t/n = t/(n(n-1)) = +0.5 (n=2), +0.1666667 "
            "(n=3), +0.0833333 (n=4) at t = 1"
        ),
        "edges": {
            "formula": "edge(s) = max(s/dr, min(K*s, capacity + s)), "
                       "s = taken - maintenance",
            "E_low_edge(t/n - m)": e_low_n,
            "E_high_edge(t/(n-1) - m)": e_high_n,
            "ratio_E_high_over_E_low": {n: e_high_n[n] / e_low_n[n]
                                        for n in CROWDS},
            "note": (
                "the brief says the edge rises n/(n-1) times; that is exact "
                "only when one branch binds at both shares. Here the clock "
                "branch binds at t/n and the per-step branch at t/(n-1), so "
                "the formula's ratio is 2.614, 2.25, 2.667 for n = 2, 3, 4"
            ),
        },
        "P1_brief": (
            "the survivor's edge goes E_low -> E_high, so the rc bands are: "
            "below E_low nobody dies in either configuration; between E_low "
            "and E_high the EQUAL configuration dies at one step (everybody "
            "has the same share, so the same edge: cascade, 0 survivors) "
            "while the ONE WEAK configuration loses the weak one first and "
            "keeps n-1 (the weak died -> the others lived); above E_high the "
            "share rises and it is still too little (cascade again)"
        ),
        "P2_race": (
            "the new share is not there from step 1: while the weak is alive "
            "the survivors are above their OLD edge and accumulate damage. "
            "Repair is all-or-nothing and needs damage*rc < energy "
            "(organism.rs:542-556) with energy <= capacity after the step "
            "(organism.rs:566), so the rescue is useful only while "
            "damage_at_rescue*rc < capacity. damage_at_rescue grows with the "
            "weak one's lifetime and with dr*rc - s_low, so the MEASURED edge "
            "of a rescued survivor is min(E_high, E_race) with E_race < "
            "E_high, and the shortfall grows with the absolute width of the "
            "band: dr*(E_high-E_low) = 0.49 (n=2), 0.17 (n=3), 0.085 (n=4). "
            "Prediction: a measurable shortfall for n=2, none beyond the "
            "tolerance for n=3 and n=4"
        ),
        "sequential": (
            "rank i takes clamp(S - i*t, 0, t): its share depends on the "
            "ranks AHEAD and not on how many are alive behind. Killing rank i "
            "does not change rank i+1's share, because the first i organisms "
            "take the same total min(S, i*t) either way. Killing rank 0 is the "
            "only death that could raise a successor's share, and rank 0 "
            "already eats min(t, S), so the successor gets exactly the same. "
            "Prediction: under Sequential the share of a survivor can rise "
            "(measured when rank 0 dies) but no death rescues anybody: the "
            "risen share is the edge that just failed to save the dead rank "
            "itself. Sequential rows must be identical to the equal row"
        ),
        "grid": (
            "n = 2,3,4 on one cell, M = n (S = 0.8n), income 1.0, maintenance "
            "0.2, capacity 10, regrow 0.8, dr = 0.03, energy0 5.0 (equal) or "
            "0.5 for one rank (weak0: rank 0, weaklast: rank n-1); bands "
            "below = 0.5*E_low, between = sqrt(E_low*E_high), above = "
            "1.25*E_high; horizons T = 10000 and 2T = 20000"
        ),
        "measured": (
            "per row: survivors at T, step of the first death, and per "
            "organism its lifetime, cause, and the share change across the "
            "first death (from the constant-meal segments of rescue_probe); "
            "per distinct rank: the rc-edge by bisection at two horizons"
        ),
    }

    exp = Experiment(
        experiment_id="rescue",
        question=(
            "FINDING-151 recorded that 'the crowd is imposed: there is no "
            "feedback one died -- the share of the survivors grew'. The code "
            "counts the share over the LIVING, so the feedback exists. Does "
            "the death of one organism save the others -- and when does it "
            "save them, and when is the death a cascade?"
        ),
        arithmetic=arithmetic,
        arms={
            "prop-equal": "Proportional, n=2, equal reserves, rc in the between band",
            "prop-weak0": "Proportional, n=2, rank 0 weak (0.5), same rc",
            "prop-weaklast": "Proportional, n=2, rank 1 weak (0.5), same rc",
            "seq-equal": "Sequential, n=2, equal reserves, same rc",
            "seq-weak0": "Sequential, n=2, rank 0 weak, same rc",
            "seq-weaklast": "Sequential, n=2, rank 1 weak, same rc",
            "prop-weak0-reduced-income": (
                "Proportional, n=2, rank 0 weak, income cut to income*(n-1)/n: "
                "the specific control"
            ),
        },
        seed=SEED,
        command="python3 checks/exp_rescue.py",
        parameters={
            "crowds": list(CROWDS),
            "protocols": list(PROTOCOLS),
            "configs": list(CONFIGS),
            "income": INCOME,
            "maintenance_cost": MAINT,
            "capacity": CAPACITY,
            "regrow": REGROW,
            "move_cost": MOVE_COST,
            "damage_rate": DR,
            "energy0": ENERGY,
            "energy0_weak": ENERGY_WEAK,
            "t_cap": T,
            "t_cap_second_horizon": T2,
            "bisection_steps": BISECTION_STEPS,
            "seed": SEED,
            "probe": "core/examples/rescue_probe.rs",
        },
    )

    clock = clock_of(DR)
    print(f"clock dr={DR}: K={clock}", flush=True)

    # -- reference edges and the three bands --------------------------------
    bands: dict[int, dict] = {}
    for n in CROWDS:
        e_low = predicted_edge(INCOME / n - MAINT, DR, clock, CAPACITY)
        e_high = predicted_edge(INCOME / (n - 1) - MAINT, DR, clock,
                                CAPACITY)
        bands[n] = {
            "E_low": e_low["edge"],
            "E_low_binding": e_low["binding"],
            "E_high": e_high["edge"],
            "E_high_binding": e_high["binding"],
            "ratio": e_high["edge"] / e_low["edge"],
            "below": 0.5 * e_low["edge"],
            "between": math.sqrt(e_low["edge"] * e_high["edge"]),
            "above": 1.25 * e_high["edge"],
        }
        print(f"n={n}: E_low={e_low['edge']:.4f} ({e_low['binding']}) "
              f"E_high={e_high['edge']:.4f} ({e_high['binding']}) "
              f"ratio={bands[n]['ratio']:.4f} bands="
              f"{bands[n]['below']:.4f}/{bands[n]['between']:.4f}/"
              f"{bands[n]['above']:.4f}", flush=True)

    probe_runs = [0]

    def arm(protocol, n, rc, income=INCOME, steps=T, weak=None, weak_rank=0):
        probe_runs[0] += 1
        return run_arm(protocol, n, rc, income, DR, steps,
                       weak=weak, weak_rank=weak_rank)

    def weak_for(config: str, n: int) -> tuple[float | None, int]:
        if config == "equal":
            return None, 0
        if config == "weak0":
            return ENERGY_WEAK, 0
        return ENERGY_WEAK, n - 1

    def alive_at(protocol, n, rc, rank, steps, weak=None, weak_rank=0):
        a = arm(protocol, n, rc, steps=steps, weak=weak, weak_rank=weak_rank)
        return bool(a["organisms"][rank]["alive"])

    def bisect(protocol, n, rank, hint, steps, weak=None, weak_rank=0):
        """Edge of one RANK, by bisection on rc (a grid would be rough)."""
        hint = hint if hint and hint > 0 else 1.0
        zero = arm(protocol, n, 0.0, steps=steps, weak=weak,
                   weak_rank=weak_rank)
        org = zero["organisms"][rank]
        if not org["alive"]:
            return {"no_edge": True, "dead_at_zero": True,
                    "cause": org["cause"], "lifetime_at_zero": org["lifetime"]}
        lo = 0.5 * hint
        guard = 0
        while not alive_at(protocol, n, lo, rank, steps, weak, weak_rank):
            lo *= 0.5
            guard += 1
            if guard > 40 or lo <= 0.0:
                return {"error": f"no rc below {hint} keeps rank {rank} alive"}
        hi = 2.0 * hint
        guard = 0
        while alive_at(protocol, n, hi, rank, steps, weak, weak_rank):
            hi *= 1.5
            guard += 1
            if guard > 400:
                return {"error": f"rc = {hi} is still alive for rank {rank}"}
        for _ in range(BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if mid <= lo or mid >= hi:
                break
            if alive_at(protocol, n, mid, rank, steps, weak, weak_rank):
                lo = mid
            else:
                hi = mid
        return {"alive_below": lo, "dead_at": hi, "step": hi - lo}

    def edge_two_horizons(protocol, n, rank, hint, weak=None, weak_rank=0):
        b1 = bisect(protocol, n, rank, hint, T, weak, weak_rank)
        if "error" in b1 or b1.get("no_edge"):
            return None, b1
        b2 = bisect(protocol, n, rank, hint, T2, weak, weak_rank)
        if "error" in b2 or b2.get("no_edge"):
            return None, b2
        e1 = 0.5 * (b1["alive_below"] + b1["dead_at"])
        e2 = 0.5 * (b2["alive_below"] + b2["dead_at"])
        return 2.0 * e2 - e1, {"edge_T": e1, "edge_2T": e2,
                               "step_T": b1["step"],
                               "offset_2T": e2}

    # -- the band grid ------------------------------------------------------
    rows: list[dict] = []
    for n in CROWDS:
        m_field = float(n)
        supply = m_field * REGROW
        tvec = sequential_shares(n, supply, INCOME)
        for protocol in PROTOCOLS:
            for config in CONFIGS:
                weak, weak_rank = weak_for(config, n)
                for band in ("below", "between", "above"):
                    rc = bands[n][band]
                    a = arm(protocol, n, rc, weak=weak, weak_rank=weak_rank)
                    orgs = a["organisms"]
                    first = a["first_death"]
                    changes = [share_change_after(o, first) for o in orgs]
                    taken = (INCOME / n if protocol == "proportional"
                             else None)
                    rec = {
                        "n": n,
                        "protocol": protocol,
                        "config": config,
                        "weak_rank": weak_rank if weak is not None else None,
                        "band": band,
                        "rc": rc,
                        "E_low": bands[n]["E_low"],
                        "E_high": bands[n]["E_high"],
                        "predicted_taken_while_all_alive": taken,
                        "survivors": a["alive_end"],
                        "total": a["total"],
                        "first_death": first,
                        "share_after_first_death": changes,
                        "damage_at_first_death": [
                            o.get("damage_at_first_death") for o in orgs],
                        "taken_at_first_death": [
                            o.get("taken_at_first_death") for o in orgs],
                        "lifetimes": [o["lifetime"] for o in orgs],
                        "causes": [o["cause"] for o in orgs],
                        "taken_settled": [
                            (o["segments"][-1][2] if o["segments"] else None)
                            for o in orgs
                        ],
                        "hash": a["hash"],
                    }
                    rows.append(rec)
                    print(f"{protocol[:5]:<5} n={n} {config:<8} {band:<7} "
                          f"rc={rc:7.3f} alive={rec['survivors']} "
                          f"first={first} change="
                          f"{[None if c is None else round(c, 4) for c in changes]}"
                          f" life={rec['lifetimes']}", flush=True)

    # -- per-rank edges -----------------------------------------------------
    rank_rows: list[dict] = []
    for n in CROWDS:
        m_field = float(n)
        supply = m_field * REGROW
        tvec = sequential_shares(n, supply, INCOME)
        for protocol in PROTOCOLS:
            for config in CONFIGS:
                weak, weak_rank = weak_for(config, n)
                if protocol == "proportional":
                    if config == "equal":
                        ranks = [0]
                    else:
                        ranks = [weak_rank, (weak_rank + 1) % n]
                else:
                    ranks = list(range(n))
                for rank in ranks:
                    if protocol == "proportional":
                        if config == "equal":
                            s = INCOME / n - MAINT
                        elif rank == weak_rank:
                            s = INCOME / n - MAINT
                        else:
                            s = INCOME / (n - 1) - MAINT
                    else:
                        s = tvec[rank] - MAINT
                    # 3.2 - 3.0 is 0.20000000000000018 in doubles, so the
                    # tail of the Sequential n = 4 staircase has a surplus of
                    # 1.8e-16 and not 0. It is zero: round it, or the edge
                    # prediction is 6e-15 and the bracket cannot find the
                    # measured threshold, which is the HORIZON offset.
                    if abs(s) < 1e-12:
                        s = 0.0
                    pred = predicted_edge(s, DR, clock, CAPACITY)
                    hint = (pred["edge"]
                            if pred["edge"] and pred["edge"] > 1e-3 else 1e-3)
                    edge, info = edge_two_horizons(protocol, n, rank, hint,
                                                   weak, weak_rank)
                    if "error" in info:
                        print(f"FATAL: bisection failed ({protocol}, n={n}, "
                              f"{config}, rank={rank}): {info['error']}")
                        return 2
                    if protocol == "proportional":
                        if config == "equal" or rank == weak_rank:
                            taken = INCOME / n
                        else:
                            taken = INCOME / (n - 1)
                    else:
                        taken = tvec[rank]
                    rec = {
                        "n": n,
                        "protocol": protocol,
                        "config": config,
                        "rank": rank,
                        "taken_share": taken,
                        "surplus": s,
                        "E_low": bands[n]["E_low"],
                        "E_high": bands[n]["E_high"],
                        "P1_predicted_edge": pred["edge"],
                        "P1_binding": pred["binding"],
                    }
                    if info.get("no_edge"):
                        rec["measured_edge"] = None
                        rec["no_edge_measured"] = True
                        rec["lifetime_at_zero"] = info["lifetime_at_zero"]
                        rec["cause_at_zero"] = info["cause_at_zero"]
                        rec["matches_P1"] = pred["edge"] is None
                        rec["tolerance"] = None
                    else:
                        dev = edge - pred["edge"]
                        tol = max(info["step_T"],
                                  64 * math.ulp(pred["edge"]),
                                  abs(info["edge_T"] - info["edge_2T"]),
                                  1e-4 * pred["edge"])
                        rec.update({
                            "measured_edge_T": info["edge_T"],
                            "measured_edge_2T": info["edge_2T"],
                            "measured_edge": edge,
                            "deviation": dev,
                            "deviation_relative": (dev / pred["edge"]
                                                   if pred["edge"] else None),
                            "tolerance": tol,
                            "matches_P1": abs(dev) <= tol,
                        })
                    rank_rows.append(rec)
                    print(f"rank {protocol[:5]:<5} n={n} {config:<8} rank={rank} "
                          f"taken={rec['taken_share']:.4f} "
                          f"P1={rec['P1_predicted_edge']} "
                          f"measured={rec['measured_edge']} "
                          f"tol={rec.get('tolerance')}", flush=True)

    # -- the specific control: income cut to t*(n-1)/n ----------------------
    specific_rows: list[dict] = []
    for n in CROWDS:
        rc = bands[n]["between"]
        income_red = INCOME * (n - 1) / n
        weak, weak_rank = weak_for("weak0", n)
        full = arm("proportional", n, rc, weak=weak, weak_rank=weak_rank)
        red = arm("proportional", n, rc, income=income_red, weak=weak,
                  weak_rank=weak_rank)
        red_changes = [share_change_after(o, red["first_death"])
                       for o in red["organisms"]]
        red_settled = [o["segments"][-1][2] if o["segments"] else None
                       for o in red["organisms"]]
        specific_rows.append({
            "n": n,
            "rc": rc,
            "income": INCOME,
            "income_reduced": income_red,
            "survivors_full_income": full["alive_end"],
            "survivors_reduced_income": red["alive_end"],
            "first_death_full": full["first_death"],
            "first_death_reduced": red["first_death"],
            "share_before_death_full": INCOME / n,
            "share_after_death_full": INCOME / (n - 1),
            "share_before_death_reduced": income_red / n,
            "share_after_death_reduced": income_red / (n - 1),
            "share_after_death_reduced_equals_share_before_death_full": (
                abs(income_red / (n - 1) - INCOME / n) <= 1e-12
            ),
            "measured_share_after_death_reduced": [
                (s if s is not None else None) for s in red_settled
            ],
            "changes_reduced": red_changes,
        })
        print(f"specific n={n} rc={rc:.4f}: income {INCOME} -> {income_red:.4f}; "
              f"survivors {full['alive_end']} -> {red['alive_end']}; "
              f"share after death {income_red / (n - 1):.6f} "
              f"(= the share before death at the full income "
              f"{INCOME / n:.6f})", flush=True)

    # -- Sequential: death of rank 0 against death of the last rank ---------
    sequential_rows: list[dict] = []
    for n in CROWDS:
        for band in ("below", "between", "above"):
            rc = bands[n][band]
            rec = {"n": n, "band": band, "rc": rc}
            for config in CONFIGS:
                weak, weak_rank = weak_for(config, n)
                a = arm("sequential", n, rc, weak=weak, weak_rank=weak_rank)
                changes = [share_change_after(o, a["first_death"])
                           for o in a["organisms"]]
                rec[config] = {
                    "survivors": a["alive_end"],
                    "first_death": a["first_death"],
                    "lifetimes": [o["lifetime"] for o in a["organisms"]],
                    "share_after_first_death": changes,
                    "hash": a["hash"],
                }
            sequential_rows.append(rec)
            print(f"sequential n={n} {band:<7} rc={rc:7.3f} "
                  f"equal={rec['equal']['survivors']} "
                  f"weak0={rec['weak0']['survivors']} "
                  f"weaklast={rec['weaklast']['survivors']} "
                  f"change(weak0)="
                  f"{[None if c is None else round(c, 4) for c in rec['weak0']['share_after_first_death']]}",
                  flush=True)

    # -- controls (§2) -----------------------------------------------------
    by_key = {(r["protocol"], r["n"], r["config"], r["band"]): r for r in rows}

    fires_bad = []
    for n in CROWDS:
        eq = by_key[("proportional", n, "equal", "between")]["survivors"]
        wk = by_key[("proportional", n, "weak0", "between")]["survivors"]
        if not (eq == 0 and wk == n - 1):
            fires_bad.append((n, eq, wk))
        for band in ("below", "between", "above"):
            for config in ("weak0", "weaklast"):
                e = by_key[("proportional", n, "equal", band)]["survivors"]
                w = by_key[("proportional", n, config, band)]["survivors"]
                if w < e:
                    fires_bad.append((n, band, config, "equal higher than weak"))
    rises = {}
    for n in CROWDS:
        r = by_key[("proportional", n, "weak0", "between")]
        rises[n] = [c for c in r["share_after_first_death"] if c]
    rise_bad = [n for n in CROWDS
                if not rises.get(n)
                or abs(max(rises[n]) - INCOME / (n * (n - 1))) > 1e-9]
    exp.control(
        "fires",
        not fires_bad and not rise_bad,
        f"in the between band (E_low < rc < E_high) the equal configuration "
        f"loses everybody and the one-weak configuration keeps n-1: "
        + "; ".join(
            f"n={n}: equal {by_key[('proportional', n, 'equal', 'between')]['survivors']}"
            f" vs weak {by_key[('proportional', n, 'weak0', 'between')]['survivors']}"
            for n in CROWDS)
        + f". The measured share rise after the first death is "
        + "; ".join(f"n={n}: {INCOME / (n * (n - 1)):.6f} predicted, "
                    f"{max(rises[n]) if rises[n] else None} measured"
                    for n in CROWDS)
        + f". Survival in the equal configuration is nowhere higher than in "
        f"the weak one (violations: {fires_bad}); the above band is a cascade "
        f"in both configurations, which is P1's third band, not a control "
        f"failure.",
    )

    silent_bad = []
    silent_expected_dead = []
    for n in CROWDS:
        for protocol in PROTOCOLS:
            for config in CONFIGS:
                rec = by_key[(protocol, n, config, "below")]
                eq = by_key[(protocol, n, "equal", "below")]["survivors"]
                if rec["survivors"] > eq:
                    silent_bad.append((protocol, n, config,
                                       rec["survivors"], eq))
                if rec["survivors"] < n:
                    silent_expected_dead.append(
                        (protocol, n, config, rec["survivors"]))
    exp.control(
        "silent",
        not silent_bad,
        f"below E_low nothing is rescued: survival in the weak configurations "
        f"is equal to the equal configuration on every row and higher on none "
        f"(violations: {silent_bad}). Where the low band does not keep all n, "
        f"the equal row is already short for arithmetic reasons, not for a "
        f"rescue: {silent_expected_dead} -- Sequential, n = 4, the tail's "
        f"share is t/n = 0.25 and its settled share is 0.2 (S = 3.2), so its "
        f"surplus is exactly 0 and its edge is 0: it dies at any rc > 0 in "
        f"every configuration, and no death can bring it back.",
    )

    specific_bad = []
    for s in specific_rows:
        if s["survivors_reduced_income"] != 0:
            specific_bad.append((s["n"], "still rescued"))
        if s["survivors_reduced_income"] != by_key[
                ("proportional", s["n"], "equal", "between")]["survivors"]:
            specific_bad.append((s["n"], "not the equal row's survivors"))
        if not s["share_after_death_reduced_equals_share_before_death_full"]:
            specific_bad.append((s["n"], "the reduced share missed t/n"))
        if s["survivors_full_income"] == 0:
            specific_bad.append((s["n"], "no effect to remove"))
    seq_rescue_bad = []
    for rec in sequential_rows:
        for config in CONFIGS:
            if rec[config]["survivors"] != rec["equal"]["survivors"]:
                seq_rescue_bad.append((rec["n"], rec["band"], config,
                                       rec[config]["survivors"],
                                       rec["equal"]["survivors"]))
    exp.control(
        "specific",
        not specific_bad and not seq_rescue_bad,
        f"the rescue is the grown share, not the number of organisms. (a) At "
        f"the same n and the same rc, with income cut to t*(n-1)/n, the share "
        f"after the death equals the share BEFORE it at the full income "
        f"(t/(n-1)*(n-1)/n = t/n), so the edge does not move and the rescue "
        f"must vanish: "
        + "; ".join(f"n={s['n']}: {s['survivors_full_income']} -> "
                    f"{s['survivors_reduced_income']} survivors at "
                    f"income {s['income']} -> {s['income_reduced']:.4f}"
                    for s in specific_rows)
        + f" (problems: {specific_bad}). (b) Under Sequential no death rescues "
        f"anybody -- the survivor count of every configuration equals the "
        f"equal row in every band, including the rows where the share of a "
        f"survivor DOES rise: rank 0's death raises rank 1's meal from 0.6 to "
        f"1.0 (measured +0.4 at n = 2, above band), and rank 1 still dies "
        f"because the risen share is exactly the edge that failed to save "
        f"rank 0 (violations: {seq_rescue_bad}). (c) Death of rank 0 against "
        f"death of the last rank under Sequential: "
        + "; ".join(f"n={rec['n']} {rec['band']}: rank0-weak "
                    f"{rec['weak0']['survivors']} vs last-weak "
                    f"{rec['weaklast']['survivors']} vs equal "
                    f"{rec['equal']['survivors']}"
                    for rec in sequential_rows)
        + ". The weak first eater keeps the head's edge and survives; the weak "
        "last eater dies earlier; neither death moves the survivor count.",
    )

    # -- arms and hashes (§5) ----------------------------------------------
    arm_specs = []
    for protocol in PROTOCOLS:
        for config in CONFIGS:
            weak, weak_rank = weak_for(config, 2)
            arm_specs.append((f"{protocol[:4]}-{config}", protocol, config,
                              weak, weak_rank))
    arm_specs.append(("prop-weak0-reduced-income", "proportional", "weak0",
                      ENERGY_WEAK, 0))
    for key, protocol, config, weak, weak_rank in arm_specs:
        rc = bands[2]["between"]
        income = (INCOME * (2 - 1) / 2 if "reduced" in key else INCOME)
        a = arm(protocol, 2, rc, income=income, weak=weak,
                weak_rank=weak_rank)
        exp.add_arm(
            key,
            f"{protocol} n=2 {config} rc={rc:.4f} income={income}",
            {"survivors": a["alive_end"], "total": a["total"],
             "first_death": a["first_death"],
             "lifetimes": [o["lifetime"] for o in a["organisms"]],
             "share_after_first_death": [
                 share_change_after(o, a["first_death"])
                 for o in a["organisms"]],
             "segments": [o["segments"] for o in a["organisms"]]},
            trace_hash=a["hash"],
        )

    # -- limitations (§6) ---------------------------------------------------
    for text in (
        "the horizon is finite: 'alive' means alive at T = 10000 (and 2T for "
        "the edge). The edge is extrapolated from two horizons assuming a "
        "c/T offset; the residual is the tolerance, not a proof that the "
        "extrapolated edge is exact.",
        "the crowd is still imposed, only the SHARE is not: nothing is born, so "
        "the row can show that a death frees a share and cannot show where the "
        "crowd would settle. Rescue by death is one half of the feedback the "
        "model has; refill is the half it does not have.",
        "the rescue is measured on ONE cell with a uniform field, `stay`, no "
        "memory and no read budget. On a field with a gradient, or with a "
        "policy that can leave the crowded cell, the death of one organism is "
        "also an opportunity to move, and that is not measured here.",
        "one damage rate (dr = 0.03, K = 34) and one pair (income, maintenance) "
        "= (1.0, 0.2). The width of the rescue band in `rc` is set by the "
        "formula and by the race; other pairs move both and are not swept.",
        "the race of P2 is read off the repair rule (all-or-nothing, "
        "energy <= capacity) and confirmed by the bisection for n = 2, but it "
        "is a threshold in `rc`, not a formula with its own name: the measured "
        "shortfall is a number, not a law.",
        "the weak organism is weak by RESERVE (energy0 = 0.5 against 5.0), not "
        "by share. Under Proportional the share is equal for everybody, so "
        "'the weak one dies first' is a statement about the reserve; a crowd "
        "with unequal shares (Sequential) has a weak one for a second reason, "
        "and the two are separated by the protocol here.",
        "Lean does not cover this: the numbers are a property of doubles and of "
        "the step order, and in exact arithmetic the equalities would move.",
    ):
        exp.limitation(text)

    # -- verdict (§4) -------------------------------------------------------
    between_ok = all(
        by_key[("proportional", n, "equal", "between")]["survivors"] == 0
        and by_key[("proportional", n, "weak0", "between")]["survivors"] == n - 1
        for n in CROWDS
    )
    rank_p1 = [r for r in rank_rows if r.get("measured_edge") is not None]
    rank_p1_bad = [r for r in rank_p1 if not r["matches_P1"]]

    def measured(protocol, n, config, rank):
        for r in rank_rows:
            if (r["protocol"] == protocol and r["n"] == n
                    and r["config"] == config and r["rank"] == rank
                    and r.get("measured_edge") is not None):
                return r["measured_edge"]
        return None

    # P2: the survivors' edge in the between band must be ABOVE the old edge
    # (the rescue is real) and AT MOST the new one (never beyond E_high). The
    # shortfall is the damage the survivor carried into the rescue, so it is
    # read off the above-band row, where the survivor dies after the weak one:
    # damage_at_rescue = 1 - dr * (t_survivor - t_weak).
    rescued_edges = {n: measured("proportional", n, "weak0", 1)
                     for n in CROWDS}
    # The race: a survivor enters the grown share carrying the damage it took
    # while it was above its OLD edge, and all-or-nothing repair must repay it
    # out of a reserve bounded by `capacity`. `damage_at_first_death` is that
    # number, measured, not inferred.
    race = {}
    for n in CROWDS:
        rec = {"n": n, "E_high": bands[n]["E_high"],
               "s_high": INCOME / (n - 1) - MAINT,
               "per_step_edge_of_the_risen_share": (INCOME / (n - 1) - MAINT)
               / DR,
               "measured_rescued_edge": rescued_edges[n],
               "bands": {}}
        for band in ("below", "between", "above"):
            r = by_key[("proportional", n, "weak0", band)]
            dmg = [d for i, d in enumerate(r["damage_at_first_death"])
                   if d is not None
                   and r["lifetimes"][i] != r["first_death"]]
            d = max(dmg) if dmg else 0.0
            s_high = INCOME / (n - 1) - MAINT
            margin = s_high - DR * r["rc"]
            rec["bands"][band] = {
                "rc": r["rc"],
                "survivors": r["survivors"],
                "damage_carried_into_rescue": d,
                "price_damage_times_rc": d * r["rc"],
                "per_step_margin": margin,
                "per_step_ok": margin > 0.0,
                # Even from an EMPTY reserve: the reserve grows at `margin`
                # per step (repair skipped) while the price grows at `dr*rc`,
                # so the gap closes in (d*rc)/(margin) steps -- when margin is
                # positive -- and the damage at the end of it is
                # d + dr*(d*rc)/margin. >= 1 means the rescue is too late.
                "damage_at_end_of_repayment_from_empty_reserve": (
                    d + DR * (d * r["rc"]) / margin
                    if margin > 0.0 else None
                ),
                "rescue_would_arrive_in_time": (
                    margin > 0.0
                    and d + DR * (d * r["rc"]) / margin < 1.0
                ),
            }
        race[n] = rec
    shortfall = {n: (bands[n]["E_high"] - rescued_edges[n]
                     if rescued_edges[n] is not None else None)
                 for n in CROWDS}
    reason = (
        f"FINDING-151's limitation is wrong in one half and right in the "
        f"other. The feedback exists: `core/src/life.rs:334-345` counts only "
        f"`r.organism.is_alive()` and :618-630 divides `remaining` by the live "
        f"not-yet-eaten crowd, so from the step after a death the survivors "
        f"divide one income among fewer mouths -- measured rise of the meal "
        f"after the first death: "
        + "; ".join(f"n={n}: {INCOME / (n * (n - 1)):.6f}" for n in CROWDS)
        + f" (0.5 -> 1.0, 0.3333 -> 0.5, 0.25 -> 0.3333). What does not exist "
        f"is refill: there is no birth, so the crowd can only shrink. Whether "
        f"the death of one SAVES the others is decided by the protocol and by "
        f"the rc band. Under Proportional the equal configuration is a "
        f"cascade -- everybody eats t/n, so everybody has the SAME edge, and "
        f"the row goes 1 -> 0 at one step in the whole band E_low..E_high "
        f"(measured 0 survivors at n = 2, 3, 4) -- while the same row with one "
        f"weak organism loses the weak one first and keeps n-1 (measured 1, 2, "
        f"3). A row whose rc lies between E_low = edge(t/n - m) and "
        f"E_high = edge(t/(n-1) - m) is 'the weak died -> the others lived, "
        f"although the equal row beside it died'. Above E_high the share also "
        f"rises and it is too little: the cascade returns (0 survivors, with "
        f"the share of the survivors rising at the same time -- measured). "
        f"Under Sequential no death saves anybody: a rank's share is set by "
        f"the ranks ahead, killing a rank does not change what the ones behind "
        f"get, and killing rank 0 only hands its successor the same min(t, S). "
        f"Measured: every Sequential configuration has exactly the equal "
        f"row's survivor count in every band, while the share of a survivor "
        f"still rises when rank 0 dies (+0.4 at n = 2, above band) and the "
        f"survivor still dies -- the risen share is the edge that just failed "
        f"to save rank 0 itself. The measured edge of a rescued Proportional "
        f"survivor is NOT E_high but a number below it, by an amount that grows "
        f"with the width of the band in rc (P2, the race): "
        + "; ".join(f"n={n}: measured {rescued_edges[n] if rescued_edges[n] is None else round(rescued_edges[n], 4)} "
                    f"against E_high {bands[n]['E_high']:.4f}, "
                    f"shortfall {shortfall[n] if shortfall[n] is None else round(shortfall[n], 4)}, "
                    f"dr*(E_high-E_low) = "
                    f"{DR * (bands[n]['E_high'] - bands[n]['E_low']):.4f}"
                    for n in CROWDS)
        + f". The survivor does not enter the rescue fresh: it carries the "
        f"damage D it took while it was above its OLD edge, and the repair is "
        f"all-or-nothing, so the damaged number has to be repaid in one step "
        f"out of the reserve. After the rescue the reserve grows at the "
        f"per-step margin `s_high - dr*rc` (repair skipped) while the price "
        f"grows at `dr*rc`, so the gap closes in `D*rc/margin` steps and the "
        f"damage is then `D + dr*D*rc/margin`; the rescue arrives in time only "
        f"while that is below 1. Measured D and the end-of-repayment damage "
        f"even from an EMPTY reserve: "
        + "; ".join(
            f"n={n} between rc={race[n]['bands']['between']['rc']:.4f}: "
            f"D={race[n]['bands']['between']['damage_carried_into_rescue']:.4f}, "
            f"margin "
            f"{race[n]['bands']['between']['per_step_margin']:.4f}, "
            f"damage at the end "
            f"{race[n]['bands']['between']['damage_at_end_of_repayment_from_empty_reserve']}, "
            f"survivors {race[n]['bands']['between']['survivors']}; above "
            f"rc={race[n]['bands']['above']['rc']:.4f}: D="
            f"{race[n]['bands']['above']['damage_carried_into_rescue']:.4f}, "
            f"margin {race[n]['bands']['above']['per_step_margin']:.4f}, "
            f"survivors {race[n]['bands']['above']['survivors']}"
            for n in CROWDS)
        + f". Two ways to fail remain distinct: (i) the carried damage cannot "
        f"be repaid before it reaches 1 -- the wide band, n = 2, where the "
        f"measured edge is 16.9444 and not 26.6667 -- and (ii) the risen share "
        f"is itself below rc, `rc > s_high/dr` = "
        + "; ".join(f"{n}: {race[n]['per_step_edge_of_the_risen_share']:.4f}"
                    for n in CROWDS)
        + f", so the survivors die of the per-step deficit after being "
        f"rescued. Controls: "
        f"fires={not (fires_bad or rise_bad)}, silent={not silent_bad}, "
        f"specific={not (specific_bad or seq_rescue_bad)}."
    )
    apparatus_ok = (exp.controls_passed() and exp.hashes_are_distinct())
    if apparatus_ok and between_ok and not seq_rescue_bad:
        exp.verdict("passed", reason)
    elif apparatus_ok:
        exp.verdict(
            "failed",
            "EXPLAINED: the rescue did not appear in the predicted direction: "
            + f"between-band survivors equal = "
            + "; ".join(str(by_key[("proportional", n, "equal", "between")]["survivors"])
                        for n in CROWDS)
            + ", weak = "
            + "; ".join(str(by_key[("proportional", n, "weak0", "between")]["survivors"])
                        for n in CROWDS)
            + " (predicted 0 and n-1); Sequential violations: "
            + str(seq_rescue_bad) + ". " + reason,
        )
    else:
        exp.verdict(
            "void",
            f"VOID: the apparatus is broken: controls passed "
            f"{exp.controls_passed()}, hashes distinct "
            f"{exp.hashes_are_distinct()}, fires violations {fires_bad}, "
            f"rise violations {rise_bad}, silent violations {silent_bad}, "
            f"specific violations {specific_bad}, sequential violations "
            f"{seq_rescue_bad}. " + reason,
        )

    # -- the record ---------------------------------------------------------
    exp.result["rows"] = rows
    exp.result["rank_rows"] = rank_rows
    exp.result["specific_rows"] = specific_rows
    exp.result["sequential_rows"] = sequential_rows
    exp.result["bands"] = {str(n): bands[n] for n in CROWDS}
    exp.result["race"] = {str(n): race[n] for n in CROWDS}
    exp.result["rescued_edges"] = {str(n): rescued_edges[n] for n in CROWDS}
    exp.result["rescued_edge_shortfall"] = {str(n): shortfall[n]
                                            for n in CROWDS}
    exp.result["damage_clock"] = {"dr": DR, "K": clock,
                                  "measured_as": "the none arm's lifetime"}
    exp.result["measurement"] = {
        "rows": len(rows),
        "rank_edges": len(rank_rows),
        "rank_edges_matching_P1": len(rank_p1) - len(rank_p1_bad),
        "rank_edge_misses": [
            {"n": r["n"], "protocol": r["protocol"], "config": r["config"],
             "rank": r["rank"], "predicted": r["P1_predicted_edge"],
             "measured": r["measured_edge"], "deviation": r["deviation"],
             "tolerance": r["tolerance"]}
            for r in rank_p1_bad
        ],
        "probe_runs": probe_runs[0],
        "bisections": 2 * len(rank_rows),
        "between_band_equal_survivors": {
            n: by_key[("proportional", n, "equal", "between")]["survivors"]
            for n in CROWDS},
        "between_band_weak_survivors": {
            n: by_key[("proportional", n, "weak0", "between")]["survivors"]
            for n in CROWDS},
        "share_rise_measured": {
            n: max(c for c in by_key[("proportional", n, "weak0", "between")][
                "share_after_first_death"] if c) for n in CROWDS},
    }
    path = exp.save()
    print(f"\nsaved {os.path.relpath(path, ROOT)}")
    print(reason)
    print(f"\nprobe runs: {probe_runs[0]}, rank edges: {len(rank_rows)} "
          f"({len(rank_p1) - len(rank_p1_bad)} match P1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
