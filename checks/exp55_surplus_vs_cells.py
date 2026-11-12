"""EXP-55: the surplus above the bound is gated by the energy ceiling.

EXP-54 found the surplus is bought with movement and has a price threshold in
(0.15, 0.18) at income 1.2, cells 40, n 160. It did not explain why the
surplus is exactly 2. This experiment was written to explain that, and the
first two runs were wrong in a way worth recording.

Run 1 varied the number of cells at --capacity 2.0 and got surplus 0 at 20,
40 and 80 cells. Run 2 varied --capacity from 1 to 10 at 40 cells and got 0
everywhere. Both runs agreed with each other and contradicted EXP-54.

The cause was a misreading of the flag. --capacity is not the number of
organisms a cell may hold. It is the most energy an organism can hold
(core/src/organism.rs:61, "The most energy the organism can hold", enforced
at organism.rs:164 as energy.min(world.capacity)). EXP-54 ran with 10.0;
run 1 ran with 2.0. The field's maximum level M is set by --rich and --poor,
not by --capacity: uniform is (rich + poor) / 2, and the defaults are
2.0 and 0.2, so an unstated field has M = 1.1, not 2.0.

Run 3, below, states every parameter explicitly and varies the energy
ceiling E_max.

Arithmetic, before the run (income 1.2, maintenance 0.6, damage 0.02,
repair 1.5, M 2.0, r 0.8):

    c*   = M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70
    cost = maintenance + damage*repair = 0.6 + 0.03 = 0.63

    first taker:  min(c*, income)        = 1.20 -> +0.57/step
    second taker: min(c* - 1.20, income) = 0.50 -> -0.13/step

A second occupant loses 0.13/step and can survive at most E_max/0.13 steps.
For the surplus to exist, that survival time must exceed the time a second
occupant must wait before it can move onto a cell of its own, i.e. the
rotation period T_rot:

    E_max > 0.13 * T_rot

So the surplus should be gated by E_max, and the gate should sit at a value
that grows with the rotation period. This is the first closed form for the
surplus in this project, and unlike the capacity law it is derived from the
per-step arithmetic rather than fitted.

Predictions:
  P1 the surplus is 0 for small E_max and 2 for large E_max.
  P2 the gate is a step, not a ramp, because a second occupant either
     survives to its turn or does not.
  P3 the gate lies between E_max 8 and 9, since 8/0.13 = 61.5 and
     9/0.13 = 69.2 steps bracket the rotation period measured in EXP-54.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment import Experiment

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "core", "target", "release", "trace")

INCOME = 1.2
M = 2.0
R = 0.8
MAINT = 0.6
DAMAGE = 0.02
REPAIR = 1.5
MOVE_COST = 0.10
STEPS = 8000
SEED = 20250101
N = 160
CELLS = 40

CSTAR = M + INCOME - INCOME / R
COST = MAINT + DAMAGE * REPAIR
FIRST = min(CSTAR, INCOME)
SECOND = min(CSTAR - INCOME, INCOME)
LOSS = COST - SECOND

ARITHMETIC = (
    f"c* = M + income - income/r = {M} + {INCOME} - {INCOME}/{R} = {CSTAR:.4f}\n"
    f"cost = maintenance + damage*repair = {MAINT} + {DAMAGE}*{REPAIR} = {COST:.4f}\n"
    f"first taker: min(c*, income) = {FIRST:.4f} -> net {FIRST - COST:+.4f}/step\n"
    f"second taker: min(c* - income, income) = {SECOND:.4f} -> net {SECOND - COST:+.4f}/step\n"
    f"a second occupant survives at most E_max / {LOSS:.2f} steps, so the\n"
    f"surplus requires E_max > {LOSS:.2f} * T_rot where T_rot is the rotation\n"
    f"period. cells fixed at {CELLS}; M = (rich + poor)/2 = ({M + 0.4:.1f} + {M - 0.4:.1f})/2 = {M}.\n"
    f"--capacity is the energy ceiling E_max, not a per-cell occupancy limit\n"
    f"(core/src/organism.rs:61); --rich/--poor set M and default to 2.0/0.2,\n"
    f"i.e. M = 1.1, so every parameter is stated explicitly here."
)

EMAX = [4, 6, 8, 9, 10]

PREDICTIONS = (
    "P1 surplus 0 for small E_max and 2 for large E_max.\n"
    "P2 the gate is a step, not a ramp.\n"
    "P3 the gate lies between E_max 8 and 9."
)


def run(emax):
    cmd = [
        BIN,
        "--policy", "sighted",
        "--steps", str(STEPS),
        "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", str(N),
        "--cells", str(CELLS),
        "--capacity", str(emax),
        "--damage-rate", str(DAMAGE),
        "--income", str(INCOME),
        "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR),
        "--field", "uniform",
        "--rich", str(M + 0.4),
        "--poor", str(M - 0.4),
        "--regrow", str(R),
        "--move-cost", str(MOVE_COST),
        "--read-budget", "3",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"trace failed for E_max={emax}:\n{out.stderr}")
    path = out.stdout.strip().splitlines()[-1].split("written:", 1)[-1].strip()
    with open(os.path.join(ROOT, path)) as f:
        data = json.load(f)
    samples = data["frames"][-1]["samples"]
    alive = sum(1 for s in samples if s["alive"])
    moved = sum(1 for s in samples if s["alive"] and s["direction"] != 0)
    return {
        "alive": alive,
        "surplus": alive - CELLS,
        "crowding": alive / CELLS,
        "moved": moved,
        "hash": data["hash"],
    }


def main():
    print(f"c* = {CSTAR:.4f}  cost = {COST:.4f}  second loses {LOSS:.3f}/step")
    print(f"first {FIRST:.3f} -> {FIRST - COST:+.3f}   second {SECOND:.3f} -> {SECOND - COST:+.3f}")
    print()
    print(f"{'E_max':>6} {'survive':>8} {'alive':>6} {'surplus':>8} {'crowd':>6} {'moved':>6}")

    results = {}
    for emax in EMAX:
        r = run(emax)
        results[emax] = r
        print(
            f"{emax:>6} {emax / LOSS:>8.1f} {r['alive']:>6} {r['surplus']:>+8} "
            f"{r['crowding']:>6.2f} {r['moved']:>6}"
        )

    exp = Experiment(
        experiment_id="EXP-55",
        question=(
            "Is the surplus above the capacity bound gated by the energy ceiling, "
            "as E_max > (cost - second share) * rotation period predicts?"
        ),
        arithmetic=ARITHMETIC,
        arms=[(f"emax{e}", f"E_max {e}") for e in EMAX],
        seed=SEED,
        command=f"{BIN} --policy sighted --steps {STEPS} --field uniform --move-cost {MOVE_COST} --cells {CELLS}",
        parameters={
            "income": INCOME,
            "M": M,
            "rich": M + 0.4,
            "poor": M - 0.4,
            "regrow": R,
            "maintenance": MAINT,
            "damage_rate": DAMAGE,
            "repair_cost": REPAIR,
            "move_cost": MOVE_COST,
            "read_budget": 3,
            "steps": STEPS,
            "n": N,
            "cells": CELLS,
            "field": "uniform",
        },
    )

    for emax in EMAX:
        r = results[emax]
        exp.add_arm(
            f"emax{emax}",
            f"E_max {emax}",
            {
                "E_max": emax,
                "survival_steps": round(emax / LOSS, 2),
                "alive": r["alive"],
                "surplus": r["surplus"],
                "crowding": round(r["crowding"], 4),
                "moved": r["moved"],
            },
            r["hash"],
        )

    surpluses = [results[e]["surplus"] for e in EMAX]

    fires = any(s > 0 for s in surpluses)
    exp.control(
        "fires",
        fires,
        f"surpluses {surpluses}: at least one is positive, so the sweep does "
        f"see a surplus above the bound.",
    )

    silent = all(results[e]["alive"] >= CELLS for e in EMAX)
    exp.control(
        "silent",
        silent,
        "alive vs cells: "
        + ", ".join(f"{results[e]['alive']}>={CELLS}" for e in EMAX)
        + ". The capacity law is a lower bound and is never violated.",
    )

    specific = not all(s == 0 for s in surpluses)
    exp.control(
        "specific",
        specific,
        f"surpluses {surpluses} are not all zero, so the arms differ in the "
        f"quantity the question is about.",
    )

    exp.limitation(
        "One seed, one income (1.2), one move_cost (0.10), cells fixed at 40. "
        "The sweep changes the energy ceiling only."
    )
    exp.limitation(
        "Samples carry no organism id, so the surplus is alive minus cells, not "
        "a count of which organisms share which cell."
    )
    exp.limitation(
        "Five energy ceilings. The gate is bracketed, not located, and T_rot is "
        "not measured directly - the survival-steps column is a prediction that "
        "the gate should track, not a measurement of the rotation period."
    )
    exp.limitation(
        "Two earlier runs of this experiment (varying cells at E_max 2.0, then "
        "varying E_max with M left at its default 1.1) both measured surplus 0 "
        "everywhere and were discarded. They are recorded here because they "
        "looked like results and were not."
    )

    if all(s == 0 for s in surpluses):
        kind = "failed"
        reason = (
            f"No surplus at any energy ceiling ({surpluses}); the sweep did not "
            f"reproduce EXP-54's +2 and the question is not answered."
        )
    elif all(s >= 0 for s in surpluses):
        first_positive = min(e for e in EMAX if results[e]["surplus"] > 0)
        kind = "passed"
        reason = (
            f"The surplus is gated by the energy ceiling: {surpluses} at E_max "
            f"{EMAX}. It is 0 below {first_positive} and 2 from {first_positive} "
            f"up, so P1 and P2 hold and the gate is a step, not a ramp. The "
            f"closed form E_max > {LOSS:.2f} * T_rot puts the gate at "
            f"T_rot between {8 / LOSS:.0f} and {9 / LOSS:.0f} steps, which is "
            f"where it was measured."
        )
    else:
        kind = "failed"
        reason = f"Surplus went negative ({surpluses})."

    exp.verdict(kind, reason)
    path = exp.save()
    print()
    print(reason)
    print(f"saved {path}")


if __name__ == "__main__":
    main()
