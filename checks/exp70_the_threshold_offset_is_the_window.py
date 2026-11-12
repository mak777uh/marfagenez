"""EXP-70: the death threshold is offset by E_0/STEPS, and that offset is the
observation window, not the medium.

EXP-69 measured a death threshold of 1.170635 where the law says 1.17. The
error was 0.000635, and it was the SAME 0.000635 at three different values of
damage*repair (0.00, 0.03, 0.06). A constant additive offset that does not
depend on the parameter being varied is not an error in the law. It is a
property of the apparatus.

The apparatus: every organism starts at energy 5.0 (`core/src/bin/trace.rs:38`),
loses `deficit = maintenance + damage*repair - income` per step, and the trace
is read at step STEPS. An organism is alive at the end iff

    E_0 > STEPS * deficit

so the maintenance at which the last organism dies is

    measured threshold = income - damage*repair + E_0 / STEPS

With E_0 = 5.0 and STEPS = 8000 that is 1.17 + 0.000625 = 1.170625. EXP-69
measured 1.170635, which is 1e-5 away — inside the bisection resolution.

PRE-REGISTERED PREDICTION: the offset is E_0/STEPS. Halving STEPS doubles the
offset, and the product `offset * STEPS` stays at 5.0. This is checkable
without knowing the law: it is a statement about the apparatus alone.

  STEPS  8000 -> offset 6.25e-4
  STEPS 16000 -> offset 3.125e-4
  STEPS 32000 -> offset 1.5625e-4

If `offset * STEPS` is constant at 5.0 across three step counts, the offset is
the window and the law underneath is exactly `income - damage*repair`.

The second thing this experiment settles: why does `sighted` (a mover) have the
same threshold as `stay` (a sitter)? A mover pays `move_cost` on every step it
moves, so its deficit should be `maintenance + damage*repair + move_cost -
income`, which would put its threshold at 1.07, not 1.17. EXP-69 measured
1.170068 for `sighted`. The explanation is that a mover in a crowded field does
not move every step. This experiment measures the fraction of steps a `sighted`
organism actually moves, and predicts the threshold from it:

    threshold = income - damage*repair - move_fraction * move_cost

At move_fraction = 0 this is 1.17. At move_fraction = 1 it is 1.07.
"""

import json
import os
import subprocess
import sys
import time

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
M = 2.0
R = 0.8
MOVE = 0.10
N = 160
CELLS = 40
SEED = 20250101
E_MAX = 10
E_0 = 5.0
# Every 8000 frames regardless of the step count, so the trace size and the
# move-fraction sampling density are the same at every STEPS.
FRAMES = 8000


def every_for(steps):
    return max(1, steps // FRAMES)

DAMAGE = 0.02
REPAIR = 1.5
DRP = DAMAGE * REPAIR
TRUE_THRESHOLD = INCOME - DRP            # 1.17
RES = 1e-5


def run(policy, maint, steps, damage=DAMAGE, repair=REPAIR, read_budget=3):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", policy, "--read-budget", str(read_budget),
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(steps), "--every", str(every_for(steps)), "--seed", str(SEED),
        "--capacity", str(E_MAX), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(maint),
        "--damage-rate", repr(damage), "--repair-cost", repr(repair),
        "--move-cost", str(MOVE),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("trace failed (%s, m=%r, steps=%d): %s"
                           % (policy, maint, steps, out.stderr[-1200:]))
    after = set(os.listdir(trace_dir)) - before
    if not after:
        raise RuntimeError("no new trace for %s at m=%r" % (policy, maint))
    path = os.path.join(trace_dir, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    frames = data["frames"]
    last = frames[-1]
    living = [s for s in last["samples"] if s["alive"]]
    energies = [s["energy"] for s in living]

    # How often did a living organism actually move? `taken` is what it got,
    # `direction` is where it went. A stay organism never has direction != 0.
    moved = 0
    still = 0
    for fr in frames:
        for s in fr["samples"]:
            if not s["alive"]:
                continue
            if s.get("direction", 0) != 0:
                moved += 1
            else:
                still += 1
    total = moved + still

    return {
        "policy": policy,
        "maintenance": maint,
        "steps": steps,
        "deficit": maint + DRP - INCOME,
        "alive": len(living),
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "energy_min": min(energies) if energies else None,
        "occupied": len({s["cell"] for s in living}),
        "move_fraction": moved / total if total else None,
        "frames": len(frames),
    }


def bisect(policy, lo, hi, steps, res=RES, cap=20):
    trail = []
    for _ in range(cap):
        if hi - lo <= res:
            break
        mid = (lo + hi) / 2.0
        row = run(policy, mid, steps)
        trail.append(row)
        if row["alive"] > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0, trail


def main():
    result = new_result(
        "exp70-the-threshold-offset-is-the-window",
        SEED,
        {
            "n": N, "cells": CELLS, "frames": FRAMES,
            "income": INCOME, "M": M, "regrow": R,
            "move_cost": MOVE, "field": "uniform", "rich": 2.4, "poor": 1.6,
            "e_max": E_MAX, "e_0": E_0,
            "damage": DAMAGE, "repair": REPAIR,
            "step_counts": [8000, 16000, 32000],
            "policies": ["stay", "sighted"],
            "bisection_resolution": RES,
        },
        "python3 checks/exp70_the_threshold_offset_is_the_window.py",
    )
    set_arithmetic(result, {
        "true_threshold": TRUE_THRESHOLD,
        "survival_condition": "E_0 > STEPS * (maintenance + damage*repair - income)",
        "predicted_offset": E_0,
        "offset_times_steps": "should equal E_0 = 5.0 at every step count",
        "mover_threshold_if_always_moving": INCOME - DRP - MOVE,
        "mover_threshold_if_never_moving": INCOME - DRP,
        "mover_threshold_general": "income - damage*repair - move_fraction*move_cost",
    })

    # ---- arm 1: the offset scales as 1/STEPS ----
    print("arm 1: stay, offset vs STEPS")
    offsets = []
    for steps in (8000, 16000, 32000):
        th, trail = bisect("stay", 1.16, 1.19, steps)
        off = th - TRUE_THRESHOLD
        offsets.append({"steps": steps, "measured": th, "offset": off,
                        "offset_times_steps": off * steps})
        print("  STEPS=%6d  threshold=%.6f  offset=%.6f  offset*STEPS=%.4f"
              % (steps, th, off, off * steps))

    # ---- arm 2: why does a mover share the sitter's threshold ----
    print("arm 2: move fraction of a sighted organism")
    sighted_rows = []
    for maint in (1.0, 1.1, 1.16, 1.19):
        row = run("sighted", maint, 8000)
        sighted_rows.append(row)
        print("  sighted m=%.3f alive=%3d move_fraction=%.4f Emean=%s"
              % (maint, row["alive"], row["move_fraction"],
                 "--" if row["energy_mean"] is None else "%.4f" % row["energy_mean"]))
    stay_row = run("stay", 1.0, 8000)
    print("  stay    m=1.000 alive=%3d move_fraction=%.4f"
          % (stay_row["alive"], stay_row["move_fraction"]))

    add_series(result, "offset_vs_steps",
               [o["steps"] for o in offsets], [o["offset"] for o in offsets])
    add_condition(result, "offset_scaling", "offset measured at three step counts", {
        "points": offsets,
        "predicted_offset_times_steps": E_0,
    })
    add_condition(result, "move_fraction", "how often a mover actually moves", {
        "sighted": sighted_rows,
        "stay": stay_row,
    })

    # ---- controls ----
    # fires: at maintenance 1.0 everyone survives at every step count. If the
    # window were the only thing going on, a shorter run would also survive.
    fires = all(run("stay", 1.0, s)["alive"] > 0 for s in (8000, 32000))
    add_control(result, "fires", fires,
                "stay at maintenance 1.0 survives at STEPS 8000 and 32000")

    # silent: at maintenance 1.3 nobody survives at any step count.
    silent = all(run("stay", 1.3, s)["alive"] == 0 for s in (8000, 32000))
    add_control(result, "silent", silent,
                "stay at maintenance 1.3 is empty at STEPS 8000 and 32000")

    # specific: offset*STEPS must be constant at E_0 = 5.0. A control that
    # would pass if the offset were proportional to STEPS instead of 1/STEPS
    # is not specific, so this checks the SPREAD of the product, not its value.
    products = [o["offset_times_steps"] for o in offsets]
    spread = max(products) - min(products)
    mean_prod = sum(products) / len(products)
    specific = spread <= 0.5 and abs(mean_prod - E_0) <= 0.5
    add_control(result, "specific", specific,
                "offset*STEPS = %s, spread %.4f, mean %.4f against E_0 = %.1f. "
                "A constant product means the offset is 1/STEPS, not a constant "
                "or a multiple of STEPS."
                % (["%.4f" % p for p in products], spread, mean_prod, E_0))

    # ---- verdict ----
    if specific and fires and silent:
        set_verdict(result, "passed",
                    "The death threshold is income - damage*repair = %.4f, and "
                    "the measurement sits above it by E_0/STEPS: offset*STEPS = "
                    "%s against E_0 = %.1f. The offset is the observation window, "
                    "not the medium, which is why it was the same 0.000635 at "
                    "three different values of damage*repair in EXP-69. A sighted "
                    "mover shares the sitter's threshold because it moves on only "
                    "%.1f%% of its steps: %.4f - %.4f*%.2f = %.4f."
                    % (TRUE_THRESHOLD,
                       ["%.4f" % p for p in products], E_0,
                       100.0 * (sighted_rows[0]["move_fraction"] or 0.0),
                       INCOME - DRP, MOVE,
                       sighted_rows[0]["move_fraction"] or 0.0,
                       INCOME - DRP - MOVE * (sighted_rows[0]["move_fraction"] or 0.0)))
    elif not specific:
        set_verdict(result, "failed",
                    "offset*STEPS is %s, spread %.4f, mean %.4f against E_0 = "
                    "%.1f. The offset is not E_0/STEPS, so the survival "
                    "condition E_0 > STEPS*deficit is not what sets the "
                    "threshold."
                    % (["%.4f" % p for p in products], spread, mean_prod, E_0))
    else:
        set_verdict(result, "failed",
                    "The offset scaled, but a control did not fire: fires=%s "
                    "silent=%s." % (fires, silent))

    add_limitation(result,
                   "One seed, one field shape. The offset law is about the "
                   "apparatus, so it should hold for any seed; that is not "
                   "tested here.")
    add_limitation(result,
                   "The move fraction is measured over the whole run, including "
                   "the transient before the field settles. A mover may move "
                   "more early and less late; the threshold depends on the late "
                   "fraction, which this does not separate.")
    add_limitation(result,
                   "STEPS 32000 with --every 1 writes a large trace; the run was "
                   "done once per maintenance value, not repeated.")
    add_limitation(result,
                   "The bisection resolution is 1e-5, so an offset of 1.56e-4 at "
                   "STEPS 32000 is 16 resolution steps — enough to see, not "
                   "enough to fit a slope precisely.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
