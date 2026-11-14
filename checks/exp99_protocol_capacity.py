"""EXP-99: how many organisms a cell holds under each sharing protocol.

## What the code actually does (read off `Life::advance`, not assumed)

`ShareProtocol::Sequential`: organisms are stepped in slot order, each takes
`min(income, what is left on the cell)`. The cell supplies `S = M * r` per
step, so the first `floor(S/t)` eaters each get the full `t`, and the next one
gets the remainder `S - floor(S/t)*t`.

`ShareProtocol::Proportional`: `share_left[cell]` starts at `world.income`
every step, and each eater gets `remaining / not_yet_eaten`. The divisor is
the CROWD and the budget is ONE `income` per cell:

    taken = income / k          (k = organisms not yet eaten here)

## The arithmetic, before the run

The two protocols are limited by DIFFERENT things, and that is the finding:

**Sequential is limited by the cell's supply.**

    k_seq = floor(S/t) + [S - floor(S/t)*t >= m]

The supply pays `floor(S/t)` eaters in full; the remainder eater survives iff
its remainder covers maintenance. The population saturates at `cells * k_seq`
and does not grow with `n`.

**Proportional is limited by the eater's demand.** Everyone on a cell splits
one `income`, so each gets `income / k`, which survives iff

    income / k >= m

giving

    k_prop = floor(income / m)

The population sits at `n` right up to `n = cells * k_prop` and then falls to
zero: everyone on a cell shares equally, so all live or all die together. A
cliff, not a saturation.

These are different quantities. `S/t` is about the field; `income/m` is about
the organism. For `M=2, r=0.8, t=0.6, m=0.1`: `k_seq = floor(1.6/0.6) + 1 = 3`
but `k_prop = floor(0.6/0.1) = 5`. The proportional protocol holds MORE
organisms, because it rations each of them down to maintenance while the
sequential one pays the first few in full.

## Three things the first version of this experiment got wrong

Each was caught by a run, not by re-reading:

1. **The budget is `income`, not `S`.** A trace showed `taken = 0.166667` at
   `income = 1.0` with `k = 6` — `income/k`, not `S/k`.
2. **Survival is non-strict.** At `income/k` exactly equal to `m` the organism
   lived, with energy still at its starting `10.0`. So `>=`, not `>`.
3. **The remainder eater counts.** A cell at `S=1.6, t=0.6, m=0.1` kept 3
   organisms (`0.6, 0.6, 0.4`), not `floor(S/t) = 2`.

## The boundary

`M * r >= income` — below it the cell supplies less than one eater asks for
and `k_seq = 0`. Every grid row here is at or above the boundary; the boundary
itself is stated, not crossed.

## Why the earlier probe was void

Its two arms had `hash_seq == hash_prop`: `--share` was not written into the
trace and not folded into the hash, so the arms were one arm. Fixed in
`core/src/trace.rs` (`Trace::hash_with_protocol`). Its `n = max(ks,kp)+3` was
also too small to saturate, so the `fires` control could not fail. The ladder
below replaces both.

## What this does NOT show

The capacity is a BOUND, not a measurement: nothing in the model reproduces,
so the crowd is whatever `n` we impose. The ladder shows where survival stops,
not where a population would settle.
"""
import json
import math
import os as _os
import subprocess
import sys
import sys as _sys
from pathlib import Path

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "core" / "target" / "release" / "trace"
OUT = ROOT / "results" / "protocol-capacity"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "checks"))
from experiment import Experiment  # noqa: E402

SEED = 1
CELLS = 20
STEPS = 1500
CAPACITY = 1000
EPS = 1e-12


def floor_div(a, b):
    """floor(a/b) without float-floor surprises (0.6 // 0.1 == 5.0)."""
    return math.floor(a / b + EPS)


def k_sequential(S, t, m):
    """Eaters a cell keeps: floor(S/t) paid in full, plus the remainder eater.

    The supply pays `floor(S/t)` eaters the full `t`; the next one gets
    `S - floor(S/t)*t` and survives iff that covers maintenance. Measured: at
    S=1.6, t=0.6, m=0.1 the cell kept 3 (two at 0.6, one at 0.4), not 2.
    """
    full = floor_div(S, t)
    remainder = S - full * t
    return full + (1 if remainder >= m - EPS else 0)


def k_proportional(t, m):
    """Eaters that survive on one income: largest k with income/k >= m."""
    k = 0
    while t / (k + 1) >= m - EPS:
        k += 1
    return k


def run_arm(share, n, M, r, t, m):
    """One arm: uniform field, `stay` policy, `n` organisms, one protocol."""
    out = OUT / f"trace-{share}-n{n}-M{M}-r{r}-t{t}-m{m}.json"
    cmd = [
        str(TRACE),
        "--cells", str(CELLS),
        "--n", str(n),
        "--policy", "stay",
        "--steps", str(STEPS),
        "--every", str(STEPS),
        "--capacity", str(CAPACITY),
        "--income", str(t),
        "--maintenance", str(m),
        "--repair-cost", "1.5",
        "--damage-rate", "0",
        "--move-cost", "0",
        "--energy", "10",
        "--field", "uniform",
        "--rich", str(M),
        "--poor", str(M),
        "--regrow", str(r),
        "--layout", "even",
        "--seed", str(SEED),
        "--share", share,
        "--out", str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / "core"))
    if res.returncode != 0:
        print("TRACE FAILED", res.returncode, res.stderr[-600:])
        sys.exit(1)
    data = json.loads(out.read_text())
    last = data["frames"][-1]
    alive = sum(1 for s in last["samples"] if s["alive"])
    return {
        "alive": alive,
        "total": len(last["samples"]),
        "hash": data["hash"],
        "share": data["share"],
        "taken": sorted({round(s["taken"], 6) for s in last["samples"]}),
        "trace_file": str(out.relative_to(ROOT)),
    }


def main():
    # Three (income, maintenance) pairs. Each ladder brackets BOTH thresholds,
    # so the two mechanisms are visible side by side on the same rows.
    cases = [
        # M,    r,    t,    m     S     k_seq  k_prop
        (2.0, 0.8, 0.6, 0.1),   # 1.60   3      5
        (2.0, 0.8, 1.0, 0.1),   # 1.60   2      9
        (2.0, 0.8, 0.6, 0.5),   # 1.60   2      1
    ]

    arithmetic = {
        "supply": "S = M * r — what a cell offers per step at the fixed point",
        "sequential": (
            "eaters in slot order take min(income, left); the supply pays "
            "floor(S/t) of them in full and the next gets the remainder, so "
            "the population saturates at cells*k_seq and does not grow with n"
        ),
        "proportional": (
            "eaters split ONE income: taken = income / k, so the crowd is "
            "limited by the demand side, k_prop = floor(income/m)"
        ),
        "survival": (
            "an organism survives iff income / k >= m — non-strict: measured "
            "`taken == m` keeps energy at its starting 10.0"
        ),
        "why_different": (
            "S/t is about the field, income/m is about the organism — they "
            "are different quantities and predict different capacities"
        ),
        "cliff": (
            "proportional falls off a cliff at n = cells*k_prop: everyone on a "
            "cell shares equally, so all live or all die together"
        ),
        "boundary": "M*r >= income — below it the cell supplies less than one eater asks",
    }

    exp = Experiment(
        experiment_id="protocol-capacity",
        question=(
            "Сколько организмов держит клетка при последовательном и "
            "пропорциональном дележе, и чем ограничен каждый?"
        ),
        arithmetic=arithmetic,
        arms={
            "sequential": "каждый берёт min(income, остаток) по порядку слотов",
            "proportional": "все делят один income поровну: income/k",
        },
        seed=SEED,
        command="python3 checks/exp99_protocol_capacity.py",
        parameters={
            "cells": CELLS, "steps": STEPS, "policy": "stay",
            "field": "uniform", "layout": "even", "capacity": CAPACITY,
        },
    )

    rows = []
    for M, r, t, m in cases:
        S = M * r
        ks = k_sequential(S, t, m)
        kp = k_proportional(t, m)
        threshold_seq = CELLS * ks
        threshold_prop = CELLS * kp
        # Ladder brackets both thresholds: below both, between, above both.
        ladder = sorted({
            max(1, min(threshold_seq, threshold_prop) // 2),
            max(1, threshold_seq),
            max(1, threshold_prop),
            max(threshold_seq, threshold_prop) + CELLS,
        })
        for n in ladder:
            a = run_arm("sequential", n, M, r, t, m)
            b = run_arm("proportional", n, M, r, t, m)
            k = n / CELLS
            # Sequential: the supply caps the population at cells*k_seq.
            seq_pred = min(n, threshold_seq)
            # Proportional: everyone survives while income/k >= m.
            prop_pred = n if t / k >= m - EPS else 0
            row = {
                "M": M, "r": r, "t": t, "m": m, "S": round(S, 6),
                "k_seq": ks, "k_prop": kp,
                "threshold_seq_n": threshold_seq,
                "threshold_prop_n": threshold_prop,
                "n": n, "k_per_cell": k,
                "share_per_organism": round(t / k, 6),
                "seq_predicted": seq_pred, "prop_predicted": prop_pred,
                "seq_alive": a["alive"], "prop_alive": b["alive"],
                "seq_hash": a["hash"], "prop_hash": b["hash"],
                "seq_taken": a["taken"], "prop_taken": b["taken"],
                "seq_ok": a["alive"] == seq_pred,
                "prop_ok": b["alive"] == prop_pred,
            }
            rows.append(row)
            print(
                f"M={M} r={r} t={t} m={m} n={n:>4} (k={k:>4.1f}, "
                f"inc/k={t/k:.4f}, k_seq={ks}, k_prop={kp}): "
                f"seq {a['alive']:>4}/{seq_pred:<4} "
                f"prop {b['alive']:>4}/{prop_pred:<4} "
                f"{'OK' if row['seq_ok'] and row['prop_ok'] else 'MISMATCH'}"
            )

    for i, row in enumerate(rows):
        exp.add_arm(
            f"seq{i}",
            f"seq M={row['M']} t={row['t']} m={row['m']} n={row['n']}",
            row,
            trace_hash=row["seq_hash"],
        )
        exp.add_arm(
            f"prop{i}",
            f"prop M={row['M']} t={row['t']} m={row['m']} n={row['n']}",
            row,
            trace_hash=row["prop_hash"],
        )

    # -- the three control tests -------------------------------------------

    # fires: the sequential population must SATURATE — it stops growing with n.
    # If the supply did not cap it, it would keep tracking n and this fails.
    sat_rows = [r for r in rows if r["n"] > r["threshold_seq_n"]]
    saturated = [r for r in sat_rows if r["seq_alive"] == r["threshold_seq_n"]]
    exp.control(
        "fires",
        len(sat_rows) > 0 and len(saturated) == len(sat_rows),
        f"the sequential population saturates: on the {len(sat_rows)} rungs "
        f"above its capacity, {len(saturated)} hold exactly cells*k_seq "
        f"(floor(S/t) paid in full plus the remainder eater) and do not grow "
        f"with n",
    )

    # silent: on every rung both predictions hold exactly. A control that
    # fired on healthy input shows up here.
    exact = [r for r in rows if r["seq_ok"] and r["prop_ok"]]
    exp.control(
        "silent",
        len(exact) == len(rows),
        f"{len(exact)}/{len(rows)} rungs match their own formula exactly "
        f"(seq: min(n, cells*k_seq) with k_seq = floor(S/t) + [rem >= m]; "
        f"prop: n if income/k >= m else 0)",
    )

    # specific: the two protocols must be limited by DIFFERENT quantities, not
    # merely give different numbers. Sequential is capped by the field (its
    # alive count is independent of n above the threshold); proportional is
    # capped by the organism (its alive count is 0 or n, never in between).
    seq_partial = [
        r for r in rows
        if r["n"] > r["threshold_seq_n"] and 0 < r["seq_alive"] < r["n"]
    ]
    prop_partial = [
        r for r in rows
        if r["n"] > r["threshold_prop_n"] and 0 < r["prop_alive"] < r["n"]
    ]
    exp.control(
        "specific",
        len(prop_partial) == 0 and len(seq_partial) > 0,
        f"the protocols are limited by different things: sequential leaves "
        f"{len(seq_partial)} rungs with a partially-fed population (the field "
        f"caps it), proportional leaves {len(prop_partial)} — it splits "
        f"evenly, so it dies all at once (the organism caps it)",
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        exp.verdict("void", "two arms share a hash — they are one arm")
    elif all(
        exp.result["controls"][t]["passed"] for t in ("fires", "silent", "specific")
    ):
        exp.verdict(
            "passed",
            "the two protocols are limited by different quantities: "
            "sequential by the cell's supply, cells*(floor(M*r/income) + "
            "[remainder >= maintenance]); proportional by the organism's "
            "demand, cells*floor(income/maintenance). The proportional "
            "protocol holds more organisms because it rations each one down "
            "to maintenance",
        )
    else:
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict("failed", f"control tests failed: {', '.join(failed)}")

    exp.limitation(
        "One seed. Reproducibility across seeds is not checked here."
    )
    exp.limitation(
        "The capacity is a BOUND, not a measurement: nothing in the model "
        "reproduces, so the crowd is whatever n we impose. The ladder shows "
        "where survival stops, not where a population would settle."
    )
    exp.limitation(
        "One policy (`stay`) and a uniform field. Movement is what makes "
        "`proportional` interesting — the share depends on who has already "
        "eaten — and this run does not exercise it."
    )
    exp.limitation(
        "The boundary `M*r >= income` is stated, not crossed: every row has "
        "S >= t. Below it the cell supplies less than one eater asks for."
    )
    exp.limitation(
        "The formulas are read off `Life::advance`. The first version of this "
        "experiment got them wrong three times — the budget is `income` not "
        "S, survival is non-strict, and the remainder eater counts. Each was "
        "caught by a run. The code is the authority, not the comment."
    )
    exp.limitation(
        "A difference in limiting quantity is a property of this update order, "
        "not a claim that one protocol is better. Nothing here says which "
        "sharing rule an organism SHOULD have."
    )

    path = exp.save()

    print()
    print("# EXP-99: протокол дележа и ёмкость клетки")
    print()
    print("ёмкость — граница, а не измерение: размножения нет, толпу задаёт n.")
    print("последовательный ограничен полем: cells*(floor(S/t) + [остаток >= m])")
    print("пропорциональный — организмом: cells*floor(income/m)")
    print()
    for t in ("fires", "silent", "specific"):
        c = exp.result["controls"][t]
        print(f"  {'OK  ' if c['passed'] else 'FAIL'} {t:9s} {c['evidence']}")
    print()
    print(f"Вердикт: {exp.result['verdict']['kind']}")
    print(f"  {exp.result['verdict']['reason']}")
    print()
    print(f"Сохранено: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
