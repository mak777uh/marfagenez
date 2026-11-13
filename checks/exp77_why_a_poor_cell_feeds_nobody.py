"""EXP-77: if a rich cell feeds one organism, why does the capacity not follow?

EXP-75 measured, with the clamp at the end of the step:

    poor = 0.2 (< income): alternating 20, uniform 0
    poor = 0.8 (> income): alternating 20, uniform 40
    poor = 1.2 (= income): alternating 20, uniform 40
    poor = 1.6 (> income): alternating 40, uniform 40

The capacity law says a cell feeds `k_max = 1 + floor((c* - cost)/income)`
organisms, and the equilibrium of the field law after the 2026-11-12 fix is

    c* = M + income - income/r

With M = 2.0, r = 0.8, income = 1.2, cost = 1.0 + 0.02*1.5 = 1.03:

    c* = 1.700,  (c* - cost)/income = 0.558  ->  k_max = 1

So the law says every cell feeds one organism, whatever its level, and the
alternating capacity should be 40 at every poor value. Measured: 20, 20, 20, 40.

The arithmetic above is only about the level a cell REGROWS to. It is not the
level an organism SEES. This experiment measures what is actually taken.

PRE-REGISTERED PREDICTION, written before the run, with the mechanism:

    A cell's ceiling is what its regrowth aims at, so a cell whose ceiling is
    below the equilibrium stays at its ceiling and never climbs:

        level_after_regrow = v + (v - v)*r = v   for v = ceiling

    An organism standing on it takes `min(v, income)`. A cell feeds an organism
    iff `v >= cost = 1.03`, because below that it cannot hand over the cost of
    living. The equilibrium `c* = 1.70` is reached only by a cell whose ceiling
    is at least that high.

    Therefore, with `cost = 1.03` and `income = 1.2`:

        a cell feeds one organism  iff  v >= 1.03
        a cell feeds two          iff  v - income >= cost, i.e. v >= 2.23

    Neither rich (2.0) nor any poor value reaches 2.23, so no cell feeds two.

    The two field shapes are not the same field. `uniform` is ONE level for
    every cell, `(rich + poor)/2` (`core/src/bin/trace.rs:177`), not `poor`.
    So the two shapes are predicted to differ:

        alternating: 20 for poor < 1.03, 40 at or above
        uniform:      0 for (rich+poor)/2 < 1.03, i.e. poor < 0.06
                     40 for poor >= 0.06

    The transition in the uniform field is at poor = 0.06, and the sweep starts
    at 0.20, so the uniform field is predicted to be 40 at every sampled point
    except possibly none. The alternating transition is at poor = 1.03 and the
    sweep brackets it with 1.02 and 1.04.

    A prediction written for this experiment and then falsified by the first
    run: the first version of this file predicted "uniform gives 0 below cost",
    treating the uniform level as `poor`. It gave 40 at poor = 0.60, which is
    `(2.0 + 0.6)/2 = 1.30 >= 1.03`. The prediction was wrong, the model was
    right, and the correction is recorded here rather than in a commit message.

The trap this experiment is built to avoid: EXP-75's `silent` control said
"poor = 1.6: alternating and uniform agree, so the field shape cannot matter".
That control passed, and it is true at 1.6. It is false at 0.2 and 0.8, where
the same experiment recorded 20 against 0 and 20 against 40. A control that
passes at one point is not a law. This experiment checks the whole curve.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from result import (
    add_condition,
    add_control,
    add_limitation,
    add_series,
    new_result,
    save,
    set_arithmetic,
    set_verdict,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")

INCOME = 1.2
R = 0.8
N = 160
CELLS = 40
SEED = 20250103
DAMAGE = 0.02
REPAIR = 1.5
STEPS = 4000
FRAMES = 2000
MAINT = 1.0
COST = MAINT + DAMAGE * REPAIR
RICH = 2.0
POOR_SWEEP = (0.2, 0.6, 0.9, 1.0, 1.02, 1.03, 1.04, 1.1, 1.2, 1.6)


def run(field, rich, poor):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", "sighted", "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(STEPS), "--every", str(max(1, STEPS // FRAMES)),
        "--seed", str(SEED),
        "--capacity", "10.0", "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(MAINT),
        "--damage-rate", repr(DAMAGE), "--repair-cost", repr(REPAIR),
        "--move-cost", "0.0",
        "--field", field, "--rich", repr(rich), "--poor", repr(poor),
        "--layout", "even",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("trace failed: %s" % out.stderr[-1200:])
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    if not after:
        raise RuntimeError("no new trace")
    path = max(after, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    living = [s for s in last["samples"] if s["alive"]]
    cells_used = len({s["cell"] for s in living})
    energies = [s["energy"] for s in living]
    # What the organisms actually took in the last step, by the parity of the
    # cell they stand on. This is the measurement the prediction is about.
    # `uniform` is one level for the whole field, `(rich + poor)/2`; only an
    # alternating field has cells of two parities. Splitting a uniform field by
    # parity would report the same number under two names.
    if field == "alternating":
        rich_taken = [s["taken"] for s in living if s["cell"] % 2 == 0]
        poor_taken = [s["taken"] for s in living if s["cell"] % 2 == 1]
    else:
        rich_taken = []
        poor_taken = [s["taken"] for s in living]
    return {
        "hash": digest,
        "field": field, "poor": poor,
        "alive": len(living),
        "cells_used": cells_used,
        "crowding": len(living) / cells_used if cells_used else None,
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "rich_taken_min": min(rich_taken) if rich_taken else None,
        "poor_taken_min": min(poor_taken) if poor_taken else None,
        "poor_taken_max": max(poor_taken) if poor_taken else None,
    }


def main():
    result = new_result(
        "exp77-why-a-poor-cell-feeds-nobody",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS,
            "income": INCOME, "regrow": R, "maintenance": MAINT,
            "damage": DAMAGE, "repair": REPAIR, "cost": COST,
            "rich": RICH, "poor_sweep": list(POOR_SWEEP),
            "policy": "sighted", "read_budget": 3, "layout": "even",
            "clamp": "end of step",
        },
        "python3 checks/exp77_why_a_poor_cell_feeds_nobody.py",
    )
    set_arithmetic(result, {
        "cost": "maintenance + damage*repair = %.4f" % COST,
        "equilibrium": "c* = M + income - income/r = %.4f" % (RICH + INCOME - INCOME / R),
        "k_max_by_the_law": "1 + floor((c* - cost)/income) = %d"
                            % (1 + int((RICH + INCOME - INCOME / R - COST) // INCOME)),
        "what_a_cell_actually_gives": "min(ceiling, income); regrowth aims at "
                                      "the cell's own ceiling, so a cell below "
                                      "c* stays at its ceiling",
        "alternating_transition": "poor = cost = %.4f" % COST,
        "uniform_level": "(rich + poor)/2, one level for the whole field",
        "uniform_transition": "(rich + poor)/2 = cost -> poor = %.4f"
                              % (2 * COST - RICH),
        "predicted_alternating": "20 below the transition, 40 at or above it",
        "predicted_uniform": "0 only below poor = %.2f, so 40 across the sweep"
                             % (2 * COST - RICH),
    })

    print("sweeping poor on both field shapes")
    rows = []
    for poor in POOR_SWEEP:
        for field in ("alternating", "uniform"):
            row = run(field, RICH, poor)
            rows.append(row)
            print("  poor=%.2f %-12s alive=%2d cells=%2d crowd=%.2f "
                  "rich_taken=%s poor_taken=%s"
                  % (poor, field, row["alive"], row["cells_used"],
                     row["crowding"] or 0.0,
                     row["rich_taken_min"], row["poor_taken_max"]))

    for r_ in rows:
        add_condition(result, "poor%.2f-%s" % (r_["poor"], r_["field"]),
                      "4000 steps, sighted, read_budget 3, layout even",
                      {"alive": r_["alive"], "cells_used": r_["cells_used"],
                       "crowding": r_["crowding"],
                       "energy_mean": r_["energy_mean"],
                       "rich_taken_min": r_["rich_taken_min"],
                       "poor_taken_min": r_["poor_taken_min"],
                       "poor_taken_max": r_["poor_taken_max"]},
                      trace_hash=r_["hash"])

    def get(field, poor):
        return [r for r in rows if r["field"] == field and r["poor"] == poor][0]

    add_series(result, "alternating_alive_by_poor",
               [r["alive"] for r in rows if r["field"] == "alternating"],
               [r["poor"] for r in rows if r["field"] == "alternating"])
    add_series(result, "uniform_alive_by_poor",
               [r["alive"] for r in rows if r["field"] == "uniform"],
               [r["poor"] for r in rows if r["field"] == "uniform"])

    # fires: below the alternating transition the field shape must matter.
    # Alternating keeps only its rich cells; uniform is at (rich+poor)/2, which
    # is above cost for every poor in this sweep, so it keeps all 40. The
    # control fires only if the two shapes disagree, and they must.
    below = [p for p in POOR_SWEEP if p < COST]
    fires_ok = all(get("alternating", p)["alive"] == CELLS // 2
                   and get("uniform", p)["alive"] == CELLS for p in below)
    add_control(result, "fires", fires_ok,
                "poor below the alternating transition %.2f (%s): alternating "
                "must give %d (the rich cells) and uniform %d (its level "
                "(rich+poor)/2 is above cost). Measured %s."
                % (COST, ", ".join("%.2f" % p for p in below), CELLS // 2, CELLS,
                   ", ".join("%.2f: alt %d / uni %d"
                             % (p, get("alternating", p)["alive"],
                                get("uniform", p)["alive"]) for p in below)))

    # silent: at and above the alternating transition every cell feeds, so the
    # field shape must stop mattering. This is EXP-75's control, but applied to
    # the whole upper half of the curve instead of one point.
    above = [p for p in POOR_SWEEP if p >= COST]
    silent_ok = all(get("alternating", p)["alive"] == CELLS
                    and get("uniform", p)["alive"] == CELLS for p in above)
    add_control(result, "silent", silent_ok,
                "poor at or above the alternating transition %.2f (%s): both "
                "shapes must give %d. Measured %s."
                % (COST, ", ".join("%.2f" % p for p in above), CELLS,
                   ", ".join("%.2f: alt %d / uni %d"
                             % (p, get("alternating", p)["alive"],
                                get("uniform", p)["alive"]) for p in above)))

    # specific: the transition is a step at the cost, and it is the CEILING
    # that sets what a cell hands over, not the rich equilibrium. At poor 1.02
    # the poor cells are empty (they cannot pay), at 1.04 they are full and
    # hand over exactly 1.04 -- not min(c*, income) = 1.20.
    just_below = get("alternating", 1.02)
    just_above = get("alternating", 1.04)
    specific_ok = (just_below["alive"] == CELLS // 2
                   and just_above["alive"] == CELLS
                   and abs((just_above["poor_taken_max"] or 0.0) - 1.04) < 1e-6
                   and abs((just_above["rich_taken_min"] or 0.0) - INCOME) < 1e-6)
    add_control(result, "specific", specific_ok,
                "the transition must be a step at cost = %.2f: poor 1.02 gives "
                "%d, poor 1.04 gives %d. At 1.04 a poor cell must hand over "
                "1.04 itself (measured %.4f), not the equilibrium %.4f, and a "
                "rich cell must hand over income %.2f (measured %.4f)."
                % (COST, just_below["alive"], just_above["alive"],
                   just_above["poor_taken_max"] or 0.0,
                   RICH + INCOME - INCOME / R, INCOME,
                   just_above["rich_taken_min"] or 0.0))

    ok = fires_ok and silent_ok and specific_ok
    if ok:
        set_verdict(result, "passed",
                    "A cell feeds an organism iff its CEILING is at least the "
                    "cost, not iff its equilibrium is. Below cost %.2f the "
                    "alternating field keeps only its %d rich cells; at and "
                    "above it, all %d. The transition is a step at the cost and "
                    "what a cell hands over is its ceiling, not the equilibrium "
                    "%.4f. The capacity law's k_max = 1 is right for every cell "
                    "that can feed and silently wrong for every cell that "
                    "cannot: it divides by the equilibrium, which a cell below "
                    "the equilibrium never reaches."
                    % (COST, CELLS // 2, CELLS, RICH + INCOME - INCOME / R))
    else:
        set_verdict(result, "failed",
                    "fires=%s silent=%s specific=%s. See the conditions table."
                    % (fires_ok, silent_ok, specific_ok))

    add_limitation(result,
                   "One seed, one rich level (2.0), one income (1.2). The "
                   "transition is bracketed to 0.02 around cost; it is not "
                   "located to machine precision.")
    add_limitation(result,
                   "The claim 'a cell feeds iff its ceiling >= cost' is read "
                   "from what organisms take in the last step. It is not a "
                   "proof: an organism could in principle survive on a cell "
                   "that gives less than cost by drawing down stored energy. "
                   "4000 steps is long enough that this would show as a slow "
                   "decline rather than survival, but the decline is not "
                   "measured here.")
    add_limitation(result,
                   "This does not touch the rotation surplus of EXP-52 "
                   "(42 against a bound of 40 at income = 1.00). That surplus "
                   "is a dynamical quantity and this experiment uses layout "
                   "even, which starts saturated.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
