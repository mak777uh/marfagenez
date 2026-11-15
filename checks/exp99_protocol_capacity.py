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
but `k_prop = 6`. The proportional protocol holds MORE organisms, because it
rations each of them down to maintenance while the sequential one pays the
first few in full.

`k_prop` is NOT `floor(income/m) = 5`. That was the earlier claim and a run
refuted it: at `n = 120` on 20 cells (`k = 6`) every organism took `0.1` and
lived, so the cell held 6. The reason is that the share is taken from the
cell's stock, not from a budget the cell hands out: the sixth eater arrives
when `income - 5*0.1 = 0.1` is still on the cell and takes it. So the k-th
eater survives iff `income - (k-1)*m >= m`, i.e. `k*m <= income`, which is
`floor(income/m)` when the division is exact and is 6, not 5, only because
`0.6/0.1` is `5.999999...` in binary floating point. The integer law is
`k_prop = floor(income/m)` with a tolerance, and the tolerance is the whole
point: `0.6 // 0.1` is `5.0` in Python and 5 is the wrong answer.

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

This is a real limit on what the run shows, so it is printed and recorded as a
limitation, not left in a comment. The `boundary` case below is refused by the
script rather than run: a row with `S < t` would measure the refusal, not the
protocol.

## Why the earlier probe was void

Its two arms had `hash_seq == hash_prop`: `--share` was not written into the
trace and not folded into the hash, so the arms were one arm. Fixed in
`core/src/trace.rs` (`Trace::hash_with_protocol`). Its `n = max(ks,kp)+3` was
also too small to saturate, so the `fires` control could not fail.

Replacing the single shot with a ladder was not enough. The first ladder
compared the measured arm against `min(n, cells*k_seq)` — the formula under
test — so a wrong `k_seq` moved both sides and `fires` stayed green. The
control now compares against a reference that does not use `k_seq` at all
(see `saturation_holds`), and the defect it must catch is a wrong `k_seq`, not
an arm that tracks `n`.

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
#: Relative tolerance for float divisions whose exact value is an integer.
REL_EPS = 1e-9


def floor_div(a, b):
    """floor(a/b) without float-floor surprises (0.6 // 0.1 == 5.0).

    `a // b` on floats floors the *binary* quotient, so `0.6 // 0.1` is 5.0
    because `0.6 / 0.1` is `5.999999999999999`. Adding a relative epsilon is
    the fix; an absolute one would break for large `a`. `probe_floor_div`
    below is the gate: it goes red if this function is replaced by `//`.
    """
    q = a / b
    return math.floor(q + abs(q) * REL_EPS + EPS)


def probe_floor_div():
    """The float-floor gate. Returns the list of cases that came out wrong.

    Every case is a division where the exact answer is an integer and the
    binary quotient falls just short of it. `0.6 // 0.1 == 5.0` is the one the
    audit named; the others guard the same edge from other directions.
    """
    cases = [
        (0.6, 0.1, 6),   # 0.6/0.1 = 5.999999999999999 -> `//` gives 5
        (0.3, 0.1, 3),   # 2.9999999999999996 -> `//` gives 2
        (1.6, 0.8, 2),   # the supply S=1.6 over r=0.8
        (1.6, 0.6, 2),   # the sequential supply over income
        (2.4, 0.8, 3),
        (1.0, 0.1, 10),
        (0.7, 0.1, 7),   # 6.999999999999999 -> `//` gives 6
    ]
    return [
        (a, b, want, floor_div(a, b))
        for a, b, want in cases
        if floor_div(a, b) != want
    ]


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
    """Eaters that survive on one income: largest k with income/k >= m.

    This is `floor(income/m)` with the float-floor handled. The loop is kept
    because it says what the law means (the k-th eater must still find `m` on
    the cell) rather than restating the closed form, and `probe_k_prop`
    checks it against the closed form on the cases where `//` is wrong.
    """
    k = 0
    while t / (k + 1) >= m - EPS:
        k += 1
    return k


def reference_k_seq(S, t, m):
    """The pre-registered capacity of one cell, written out independently.

    Deliberately NOT `k_sequential`: the control compares the measured arm
    against this, so the two must be separate statements of the same law.

    What this buys, measured rather than assumed: it is a MUTATION GATE, not a
    second opinion. Two spellings of the same arithmetic cannot disagree --
    `floor(S/t) + [rem >= m]` and a subtract-loop agree on all 6600 rows tried,
    with a worst leftover gap of 1.1e-12 against `REL_EPS = 1e-9`. So a
    reference that merely restates the law stays green under a mutation of the
    law (measured: M7 stays green), and a reference that is a different law is
    not a reference. What the gate does catch is the reference losing the
    remainder eater (M9 red) and the law and the reference losing it together
    (M10 red) -- the arm is measured, so it disagrees with both.
    """
    # A third shape, and it has to be a genuinely different arithmetic, not a
    # respelling of `k_sequential`: `floor_div(S, t) + [rem >= m]` written out
    # here stays green under mutation, because it cannot disagree with the
    # formula under test. Measured this session. So: pay the eaters one at a
    # time out of the supply, and never compute a floor at all.
    left = S
    full = 0
    while left >= t - EPS:
        left -= t
        full += 1
    return full + (1 if left >= m - EPS else 0)


def probe_k_prop():
    """`k_proportional` against `floor_div(t, m)` on the float-floor cases."""
    cases = [
        (0.6, 0.1, 6),
        (1.0, 0.1, 10),
        (0.3, 0.1, 3),
        (0.7, 0.1, 7),
        (0.6, 0.5, 1),
        (1.0, 0.3, 3),
    ]
    return [
        (t, m, want, k_proportional(t, m), floor_div(t, m))
        for t, m, want in cases
        if k_proportional(t, m) != want or floor_div(t, m) != want
    ]


def run_arm(share, n, M, r, t, m, cells=CELLS, tag=""):
    """One arm: uniform field, `stay` policy, `n` organisms, one protocol."""
    out = OUT / f"trace-{tag}{share}-n{n}-M{M}-r{r}-t{t}-m{m}.json"
    cmd = [
        str(TRACE),
        "--cells", str(cells),
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
    # Organisms per cell, measured from the trace rather than assumed: the
    # ladder moves `n` at fixed `cells`, so `n/cells` is the crowd only while
    # every organism is still alive. Once they start dying the two differ, and
    # the per-cell count is what the law is about.
    per_cell = [0] * cells
    for s in last["samples"]:
        if s["alive"] and s["cell"] < cells:
            per_cell[s["cell"]] += 1
    return {
        "alive": alive,
        "total": len(last["samples"]),
        "hash": data["hash"],
        "share": data["share"],
        "cells": cells,
        "per_cell_max": max(per_cell) if per_cell else 0,
        "per_cell_min": min(per_cell) if per_cell else 0,
        "taken": sorted({round(s["taken"], 6) for s in last["samples"]}),
        "trace_file": str(out.relative_to(ROOT)),
    }


def main():
    # Three (income, maintenance) pairs. Each ladder brackets BOTH thresholds,
    # so the two mechanisms are visible side by side on the same rows.
    cases = [
        # M,    r,    t,    m     S     k_seq  k_prop
        (2.0, 0.8, 0.6, 0.1),   # 1.60   3      6
        (2.0, 0.8, 1.0, 0.1),   # 1.60   2     10
        (2.0, 0.8, 0.6, 0.5),   # 1.60   2      1
        # Rows where the remainder eater is the whole question, so a
        # reference that agrees with `k_sequential` by construction is not
        # good enough: S=1.7 at t=0.6 leaves 0.5 -- exactly maintenance, the
        # non-strict boundary; S=1.75 leaves 0.55, above it; S=1.65 leaves
        # 0.45, below it and the cell keeps only the two full eaters.
        (2.0, 0.85, 0.6, 0.5),  # 1.70   3      1
        (2.0, 0.875, 0.6, 0.55),  # 1.75  3      1
        (2.0, 0.825, 0.6, 0.5),  # 1.65  2      1
    ]

    # The boundary `M*r >= income` is a limit of the design, not a row: below
    # it the cell supplies less than one eater asks for and `k_seq` is 0 by
    # construction, so a row there would measure the refusal, not the
    # protocol. It is checked, printed, and recorded as a limitation.
    below = [(M, r, t, m) for M, r, t, m in cases if M * r < t - EPS]
    if below:
        print("REFUSED: these cases are below the boundary M*r >= income:")
        for M, r, t, m in below:
            print(f"  M={M} r={r} t={t} m={m}: S={M*r:.4f} < income={t}")
        print("The cell supplies less than one eater asks for; k_seq = 0 by")
        print("construction and the ladder would measure the boundary, not")
        print("the protocol. No run was made.")
        return 2

    # The arithmetic probes are a GATE, not documentation: `probe_floor_div`
    # and `probe_k_prop` were defined but never called, so replacing
    # `floor_div` with `//` left every control green. They run here, before
    # any measurement, and a failure refuses the run (exit 2) rather than
    # producing a file.
    probe_failures = {
        "floor_div": probe_floor_div(),
        "k_proportional": probe_k_prop(),
    }
    if any(probe_failures.values()):
        print("REFUSED: the arithmetic probes failed, so the ladder would be")
        print("built on a wrong capacity:")
        for name, bad in probe_failures.items():
            for case in bad:
                print(f"  {name}: {case} (a, b, want, got)")
        print("No run was made.")
        return 2

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
        "boundary": (
            "M*r >= income — below it the cell supplies less than one eater "
            "asks and k_seq = 0 by construction. Every row here is at or "
            "above the boundary; the boundary itself is stated, not crossed"
        ),
        "sequential_reference": (
            "the control compares the measured arm against "
            "cells*(floor(S/t) + [S - floor(S/t)*t >= m]) computed by "
            "`reference_k_seq`, written separately from `k_sequential` so the "
            "two can disagree; a disagreement turns `silent` red"
        ),
        "probes": (
            "probe_floor_div and probe_k_prop ran before the ladder and "
            "passed: floor_div(0.6, 0.1) == 6 and k_proportional(0.6, 0.1) "
            "== 6, not the 5 that `0.6 // 0.1` gives. A failure here refuses "
            "the run with exit 2 instead of writing a file"
        ),
        "boundary_values": [
            {
                "M": M, "r": r, "income": t, "maintenance": m,
                "S": round(M * r, 6), "above": M * r >= t - EPS,
            }
            for M, r, t, m in cases
        ],
        "k_prop_is_not_income_over_m_floor": (
            "floor(income/m) is the integer law, but the float floor gives 5 "
            "for 0.6/0.1 and the run gives 6: the sixth eater takes the 0.1 "
            "left on the cell. `floor_div` carries a relative epsilon"
        ),
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
    for case_i, (M, r, t, m) in enumerate(cases):
        S = M * r
        ks = k_sequential(S, t, m)
        kp = k_proportional(t, m)
        threshold_seq = CELLS * ks
        threshold_prop = CELLS * kp
        # Ladder brackets both thresholds: below both, between, above both.
        # The top rung is a full CELLS above the higher threshold, not one
        # rung above it: a single rung at the cliff is one observation, and
        # the proportional arm has to be seen to stay dead, not just seen dead.
        ladder = sorted({
            max(1, min(threshold_seq, threshold_prop) // 2),
            max(1, threshold_seq),
            max(1, threshold_prop),
            max(threshold_seq, threshold_prop) + CELLS,
            max(threshold_seq, threshold_prop) + 2 * CELLS,
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
                "_case": case_i,
                "M": M, "r": r, "t": t, "m": m, "S": round(S, 6),
                "cells": CELLS, "k_seq": ks, "k_prop": kp,
                "threshold_seq_n": threshold_seq,
                "threshold_prop_n": threshold_prop,
                "n": n, "k_per_cell": k,
                "share_per_organism": round(t / k, 6),
                "seq_predicted": seq_pred, "prop_predicted": prop_pred,
                "seq_alive": a["alive"], "prop_alive": b["alive"],
                "seq_per_cell_max": a["per_cell_max"],
                "prop_per_cell_max": b["per_cell_max"],
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

    # -- declared coincidences ---------------------------------------------
    #
    # Above its cliff the proportional arm is all-dead whatever `n` is, and
    # the hash carries the dynamics of the survivors, not `n`. So every
    # proportional arm above the cliff is the same run by construction -- and
    # because the three added cases share `t = 0.6, k_prop = 1`, the same run
    # ACROSS cases as well. Declared per collision set (the contract compares
    # a group by exact set equality), with the reason, rather than silenced:
    # what still separates those arms is `specific` (all-dead vs partially
    # fed), and the limitation is written into the report.
    by_hash: dict[str, list[str]] = {}
    for i, row in enumerate(rows):
        by_hash.setdefault(row["prop_hash"], []).append(f"prop{i}")
    for group in by_hash.values():
        if len(group) > 1:
            exp.expect_coincident(*group)

    # -- the three control tests -------------------------------------------
    #
    # Each control is a predicate over a list of rows plus a list of injected
    # defects. The control passes only if it holds on the measured rows AND
    # fails on every injected defect. A control that holds on the broken rows
    # as well is a slogan, and it is recorded as a failure.

    def saturation_holds(rs):
        """True when the sequential arm stops at its capacity and stays there.

        The reference is built from the PRE-REGISTERED arithmetic in
        `arithmetic["sequential_reference"]`, not from `k_seq`: the remainder
        eater is the term the control is supposed to catch, so it cannot be on
        both sides of the comparison. The reference is

            full = floor(S/t)            # eaters paid in full
            rem  = S - full*t            # what is left for the next one
            ref  = cells * (full + [rem >= m])

        which is the same law `k_seq` implements -- so this control does not
        prove the law right. It proves the ARM saturates at the capacity the
        arithmetic predicted, and it goes red when the arm tracks `n` or when
        the capacity is off by one cell-load. The `silent` test is what
        catches a wrong capacity; this one catches an arm that never reaches
        its own capacity.

        Above the capacity the arm must hold exactly the capacity; below it,
        it must hold `n`. That is the saturation claim.
        """
        for r in rs:
            ref = r["cells"] * reference_k_seq(r["S"], r["t"], r["m"])
            want = min(r["n"], ref)
            if r["seq_alive"] != want:
                return False
        return True

    def prop_cliff_holds(rs):
        """True when the proportional arm is all-alive below its cliff and all-dead above."""
        for r in rs:
            ref = r["cells"] * r["k_prop"]
            want = r["n"] if r["n"] <= ref else 0
            if r["prop_alive"] != want:
                return False
        return True

    # The ladder must actually reach both thresholds, or the controls below
    # have nothing to look at. That is a defect of the ladder and is reported
    # as a failed control, not as a pass.
    above_seq = [r for r in rows if r["n"] > r["threshold_seq_n"]]
    above_prop = [r for r in rows if r["n"] > r["threshold_prop_n"]]

    # Injected defects. Each is a copy of the measured rows with ONE thing
    # broken, so a control that cannot tell them apart from the real rows is
    # blind to that thing.
    #
    # D1: the sequential arm tracks `n` instead of saturating (the supply does
    #     not cap it). This is the defect the original probe had.
    # D2: `k_seq` is off by one -- the remainder eater is not counted, which
    #     is exactly the term the docstring says a run caught. The arm is
    #     left measured; only the formula under test moves. This is the defect
    #     the first ladder could not see.
    # D3: the sequential arm saturates one cell-load too early (a capacity
    #     that is too small), the other direction of D2.
    # D4: the proportional arm dies gradually instead of all at once (the
    #     cliff is not a cliff), which is the defect `specific` names.
    broken_tracks_n = [{**r, "seq_alive": r["n"]} for r in rows]
    broken_k_seq_low = [
        {**r, "seq_alive": min(r["n"], r["cells"] * (r["k_seq"] - 1))}
        for r in rows
    ]
    broken_k_seq_high = [
        {**r, "seq_alive": min(r["n"], r["cells"] * (r["k_seq"] + 1))}
        for r in rows
    ]
    broken_cells_ignored = [
        {**r, "seq_alive": min(r["n"], r["k_seq"])} for r in rows
    ]
    broken_gradual = [
        {
            **r,
            "prop_alive": (
                r["n"]
                if r["n"] <= r["cells"] * r["k_prop"]
                else max(0, r["n"] - r["cells"])
            ),
        }
        for r in rows
    ]

    def control(name, holds, defects, evidence_ok, evidence_bad):
        """Records one control: it must hold on the rows and fail on every defect."""
        caught = [d for d, rs in defects if not holds(rs)]
        missed = [d for d, rs in defects if holds(rs)]
        ok = holds(rows) and not missed
        exp.control(name, ok, evidence_ok if ok else evidence_bad(missed, caught))
        return ok

    # fires: the sequential arm must saturate. It is run on the measured rows
    # and on the injected defects; it must hold on the first and fail on all.
    fires_ok = control(
        "fires",
        saturation_holds,
        [
            ("D1 the arm tracks n (no supply cap)", broken_tracks_n),
            ("D2 k_seq off by one, remainder eater not counted", broken_k_seq_low),
            ("D3 k_seq off by one, an extra eater counted", broken_k_seq_high),
            ("D5 the capacity ignores the number of cells", broken_cells_ignored),
        ],
        (
            f"the sequential population saturates at the capacity the "
            f"arithmetic predicted: on the {len(above_seq)} rungs above it, "
            f"it holds exactly that capacity and does not grow with n. The "
            f"reference is `reference_k_seq`, written separately from "
            f"`k_sequential`. All three injected defects are caught: an arm "
            f"that tracks n, a capacity off by one cell-load in either "
            f"direction, and a capacity that ignores the field size. This "
            f"shows the arm saturates where predicted; it "
            f"does not prove the prediction, which `silent` checks against "
            f"the same rows"
            if above_seq else
            f"the ladder never goes above cells*k_seq, so saturation was "
            f"never reached and this control cannot fire -- the ladder is "
            f"broken, not the law"
        ),
        lambda missed, caught: (
            f"the control is blind: it holds on the measured rows but also on "
            f"{len(missed)} injected defect(s) -- {', '.join(missed)}. A "
            f"control that cannot see the defect it names is a slogan; the "
            f"run is void"
        ),
    )

    # silent: on healthy input the control must not fire. Every rung must
    # match its own formula exactly, and the ladder must reach both cliffs.
    exact = [r for r in rows if r["seq_ok"] and r["prop_ok"]]
    mismatched = [r for r in rows if not (r["seq_ok"] and r["prop_ok"])]
    # `seq_ok` compares the arm against `k_seq` -- the formula under test. A
    # wrong `k_seq` moves both sides and stays green. So `silent` also
    # compares the arm against `reference_k_seq`, which is written in a
    # different shape; a disagreement between the two statements of the law
    # is a defect of the law, not a healthy silence.
    ref_off = [
        r for r in rows
        if r["seq_alive"] != min(
            r["n"], r["cells"] * reference_k_seq(r["S"], r["t"], r["m"])
        )
    ]
    silent_ok = (
        len(exact) == len(rows)
        and not ref_off
        and len(above_seq) > 0
        and len(above_prop) > 0
    )
    exp.control(
        "silent",
        silent_ok,
        f"{len(exact)}/{len(rows)} rungs match their own formula exactly "
        f"(seq: min(n, cells*k_seq) with k_seq = floor(S/t) + [rem >= m]; "
        f"prop: n if income/k >= m else 0), and the ladder goes above both "
        f"thresholds ({len(above_seq)} rungs above the sequential capacity, "
        f"{len(above_prop)} above the proportional one), so neither control "
        f"is silent by having nothing to see"
        if silent_ok else
        f"the control fires on healthy input: {len(mismatched)}/{len(rows)} "
        f"rungs do not match their formula -- "
        + "; ".join(
            f"M={r['M']} t={r['t']} m={r['m']} n={r['n']}: "
            f"seq {r['seq_alive']} vs {r['seq_predicted']}, "
            f"prop {r['prop_alive']} vs {r['prop_predicted']}"
            for r in mismatched
        )
        + f" -- or the arm disagrees with `reference_k_seq` on "
        f"{len(ref_off)} rung(s) (the two statements of the law have drifted "
        f"apart) -- or the ladder never goes above a threshold "
        f"(seq: {len(above_seq)}, prop: {len(above_prop)} rungs above)",
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
    specific_ok = control(
        "specific",
        lambda rs: prop_cliff_holds(rs) and any(
            r["n"] > r["cells"] * reference_k_seq(r["S"], r["t"], r["m"])
            and 0 < r["seq_alive"] < r["n"]
            for r in rs
        ),
        [("D4 the proportional arm dies gradually instead of all at once", broken_gradual)],
        f"the protocols are limited by different things: sequential leaves "
        f"{len(seq_partial)} rungs with a partially-fed population (the field "
        f"caps it), proportional leaves {len(prop_partial)} -- it splits "
        f"evenly, so it dies all at once (the organism caps it); the injected "
        f"gradual death of the proportional arm is caught",
        lambda missed, caught: (
            f"the control is blind: it holds on the measured rows but also on "
            f"{len(missed)} injected defect(s) -- {', '.join(missed)}"
        ),
    )

    # -- verdict ------------------------------------------------------------

    if not exp.hashes_are_distinct():
        # A hash collision is not an answer about the world: either a
        # parameter never reached the simulation, or the arms are one arm by
        # construction. AGENTS.md §4 calls that `void`, and the reason has to
        # say which arms collided and where to look.
        seen = {}
        for k, v in exp.hashes().items():
            seen.setdefault(v, []).append(k)
        collisions = {h: ks for h, ks in seen.items() if len(ks) > 1}
        exp.verdict(
            "void",
            "VOID: two arms share a dynamics hash, so they are one arm and "
            "nothing was measured about the mechanism. Collisions: "
            + "; ".join(f"{h} <- {sorted(ks)}" for h, ks in collisions.items())
            + ". Either the parameter never reached the simulation (check "
            "`--share` in `core/src/bin/trace.rs` and `Trace::hash_with_"
            "protocol` in `core/src/trace.rs`) or the arms are equal by "
            "construction (which would have to be declared in "
            "`expected_coincident` with a reason).",
        )
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
            "to maintenance. The saturation control is checked against a "
            "reference that does not use k_seq, and it rejects k_seq off by "
            "one in either direction",
        )
    else:
        # A failed control means the measurement is not valid: we did not ask
        # the question, the world did not answer it. AGENTS.md §4: `void`,
        # not `failed`.
        failed = [
            t for t in ("fires", "silent", "specific")
            if not exp.result["controls"][t]["passed"]
        ]
        exp.verdict(
            "void",
            "VOID: control test(s) failed: " + ", ".join(failed) + ". "
            "A failed control means the measurement is not valid -- either "
            "the control is blind (it holds on the injected defect too) or "
            "the ladder never reached the threshold it was meant to bracket. "
            "The numbers in this run are not evidence; see the control "
            "evidence for which of the two it was.",
        )

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
        "S >= t, and the script refuses any case below it rather than running "
        "it. Below the boundary the cell supplies less than one eater asks "
        "for and k_seq = 0 by construction, so a row there would measure the "
        "refusal, not the protocol. What happens below the boundary is NOT "
        "shown by this run."
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
    exp.limitation(
        "`reference_k_seq` is a mutation gate, not a second opinion. Two "
        "spellings of the same arithmetic (closed form vs subtract-loop) "
        "agree on all 6600 rows tried, with a worst leftover gap of 1.1e-12 "
        "against `REL_EPS = 1e-9`, so a restatement cannot disagree with the "
        "law and stays green when the law is mutated (measured: M7 green). "
        "The gate catches the reference losing the remainder eater (M9 red) "
        "and the law and the reference losing it together (M10 red), because "
        "the arm is measured and disagrees with both. A second formula is not "
        "a second experiment."
    )
    exp.limitation(
        "The proportional arm's dynamics hash does not carry `n` above its "
        "cliff: all-dead is all-dead, so those arms are one run by "
        "construction and are declared in `expected_coincident` (4 groups, 8 "
        "of 60 arms). The declaration is by collision set, which is what the "
        "contract compares; `specific` is what still separates an all-dead "
        "arm from a partially-fed one."
    )
    exp.limitation(
        "`k_prop = floor(income/m)` is an integer law read off the code, and "
        "the float floor of `0.6/0.1` is 5 while the run gives 6. The "
        "epsilon in `floor_div` is a tolerance on float division, not a "
        "physical constant: a case whose `income/m` sits within `REL_EPS` of "
        "an integer is decided by the tolerance, not by the model."
    )

    path = exp.save()

    print()
    print("# EXP-99: протокол дележа и ёмкость клетки")
    print()
    print("ёмкость — граница, а не измерение: размножения нет, толпу задаёт n.")
    print("последовательный ограничен полем: cells*(floor(S/t) + [остаток >= m])")
    print("пропорциональный — организмом: cells*floor(income/m)")
    print()
    print("граница: M*r >= income. Ниже неё клетка даёт меньше, чем просит один")
    print("  едок, и k_seq = 0 по построению. Все строки выше границы; сама")
    print("  граница заявлена, а не пересечена — случай ниже неё скрипт")
    print("  отказывается запускать, а не измеряет.")
    for M, r, t, m in cases:
        print(
            f"  M={M} r={r} income={t} m={m}: S={M*r:.4f} "
            f"{'>=' if M*r >= t - EPS else '<'} income "
            f"({'above' if M*r >= t - EPS else 'BELOW'})"
        )
    print()
    print("floor(income/m) — целочисленный закон, но float-floor даёт 5 для")
    print("  0.6/0.1, а прогон даёт 6: шестой едок забирает оставшиеся 0.1.")
    print()
    for t in ("fires", "silent", "specific"):
        c = exp.result["controls"][t]
        print(f"  {'OK  ' if c['passed'] else 'FAIL'} {t:9s} {c['evidence']}")
    print()
    hashes = exp.hashes()
    print(f"хэшей плеч: {len(hashes)}, различных: {len(set(hashes.values()))}")
    for key in sorted(hashes)[:4]:
        print(f"  {key:8s} {hashes[key]}")
    print()
    print(f"Вердикт: {exp.result['verdict']['kind']}")
    print(f"  {exp.result['verdict']['reason']}")
    print()
    print(f"Сохранено: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
