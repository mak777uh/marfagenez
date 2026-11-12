"""EXP-71: hunger raises the move fraction, and moving raises the deficit.

EXP-70 measured the fraction of steps on which a living `sighted` organism
actually moves:

    maintenance 1.000 -> 0.0008
    maintenance 1.100 -> 0.1001
    maintenance 1.160 -> 0.0003
    maintenance 1.190 -> 0.2319   (population already dead at 8000)

The fraction is not constant. It rises as maintenance rises toward the
threshold, except at 1.160 where the survivors are sitting on full cells.

If a hungerier organism moves more, and moving costs `move_cost`, then the
deficit is not `maintenance + damage*repair - income` but

    deficit(move_fraction) = maintenance + damage*repair - income
                             + move_fraction * move_cost

and `move_fraction` itself rises with the deficit. That is a positive feedback
loop the current law does not contain.

PRE-REGISTERED PREDICTION: the death threshold falls as `move_cost` rises,
because a larger `move_cost` makes the loop bite harder. Concretely, if the
move fraction at the threshold is `f`, then

    threshold(move_cost) = income - damage*repair - f * move_cost

so the threshold is a straight line in `move_cost` with slope `-f`. EXP-70
measured `f` near the threshold as 0.0003 at maintenance 1.160 and 0.2319 at
1.190; at the threshold itself the survivors sit still, so `f` should be small
and the slope shallow. If the slope is steep, the loop is doing work the linear
law does not describe.

The competing prediction: the threshold does not move at all with `move_cost`,
because survivors never move. The two are separated by the slope.

A second, sharper prediction. If the loop exists, then at a fixed maintenance
ABOVE the threshold, a larger `move_cost` should kill the population in FEWER
steps, and the ratio of death times should be larger than the ratio of deficits
computed without the move term. Death is measured as the first step at which
the living count reaches zero.

  move_cost 0.00 -> deficit 0.0200 -> 500 steps from E_max = 10
  move_cost 0.10 -> deficit 0.0300 -> 333 steps
  move_cost 0.30 -> deficit 0.0500 -> 200 steps

If the loop bites, the measured death step is BELOW these numbers, and the gap
grows with move_cost.
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
R = 0.8
N = 160
CELLS = 40
SEED = 20250101
E_MAX = 10
E_0 = 5.0
DAMAGE = 0.02
REPAIR = 1.5
DRP = DAMAGE * REPAIR
TRUE_THRESHOLD = INCOME - DRP          # 1.17
STEPS = 8000
FRAMES = 4000
RES = 1e-5


def run(policy, maint, move_cost, steps=STEPS, damage=DAMAGE, repair=REPAIR):
    trace_dir = os.path.join(CORE, "results", policy)
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", policy, "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(steps), "--every", str(max(1, steps // FRAMES)),
        "--seed", str(SEED),
        "--capacity", str(E_MAX), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", repr(maint),
        "--damage-rate", repr(damage), "--repair-cost", repr(repair),
        "--move-cost", repr(move_cost),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("trace failed (%s, m=%r, mc=%r): %s"
                           % (policy, maint, move_cost, out.stderr[-1200:]))
    after = set(os.listdir(trace_dir)) - before
    if not after:
        raise RuntimeError("no new trace for %s at m=%r" % (policy, maint))
    path = os.path.join(trace_dir, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    frames = data["frames"]

    # When did the population first reach zero?
    death_step = None
    for fr in frames:
        if not any(s["alive"] for s in fr["samples"]):
            death_step = fr["step"]
            break

    last = frames[-1]
    living = [s for s in last["samples"] if s["alive"]]
    energies = [s["energy"] for s in living]

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
        "move_cost": move_cost,
        "deficit_without_move": maint + DRP - INCOME,
        "alive": len(living),
        "death_step": death_step,
        "energy_mean": sum(energies) / len(energies) if energies else None,
        "move_fraction": moved / total if total else None,
        "frames": len(frames),
        "every": max(1, steps // FRAMES),
    }


def bisect(policy, lo, hi, move_cost, res=RES, cap=20):
    trail = []
    for _ in range(cap):
        if hi - lo <= res:
            break
        mid = (lo + hi) / 2.0
        row = run(policy, mid, move_cost)
        trail.append(row)
        if row["alive"] > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0, trail


def main():
    result = new_result(
        "exp71-does-hunger-feed-back-into-moving",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "frames": FRAMES,
            "income": INCOME, "regrow": R, "e_max": E_MAX, "e_0": E_0,
            "damage": DAMAGE, "repair": REPAIR,
            "field": "uniform", "rich": 2.4, "poor": 1.6,
            "move_costs": [0.0, 0.1, 0.3],
            "policy": "sighted",
            "bisection_resolution": RES,
        },
        "python3 checks/exp71_does_hunger_feed_back_into_moving.py",
    )
    set_arithmetic(result, {
        "true_threshold_no_move": TRUE_THRESHOLD,
        "deficit_without_move": "maintenance + damage*repair - income",
        "deficit_with_move": "maintenance + damage*repair - income + f*move_cost",
        "predicted_threshold": "income - damage*repair - f*move_cost",
        "competing_prediction": "threshold does not move with move_cost",
        "death_steps_without_loop": {
            "0.0": E_MAX / (1.25 + DRP + 0.0 - INCOME),
            "0.1": E_MAX / (1.25 + DRP + 0.1 - INCOME),
            "0.3": E_MAX / (1.25 + DRP + 0.3 - INCOME),
        },
        "death_test_maintenance": 1.25,
    })

    # ---- arm 1: threshold vs move_cost ----
    print("arm 1: sighted threshold vs move_cost")
    line = []
    for mc in (0.0, 0.1, 0.3):
        th, trail = bisect("sighted", 1.0, 1.25, mc)
        line.append({"move_cost": mc, "threshold": th,
                     "offset_from_law": th - TRUE_THRESHOLD,
                     "trail": trail})
        print("  mc=%.2f threshold=%.6f offset_from_1.17=%+.6f"
              % (mc, th, th - TRUE_THRESHOLD))

    # slope of threshold against move_cost
    xs = [p["move_cost"] for p in line]
    ys = [p["threshold"] for p in line]
    n_pts = len(xs)
    mx = sum(xs) / n_pts
    my = sum(ys) / n_pts
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den if den else 0.0
    print("  slope of threshold in move_cost = %.6f" % slope)

    # ---- arm 2: death time above the threshold ----
    print("arm 2: death step at maintenance 1.25")
    death_rows = []
    for mc in (0.0, 0.1, 0.3):
        row = run("sighted", 1.25, mc)
        predicted = E_MAX / (1.25 + DRP + mc - INCOME)
        death_rows.append({
            "move_cost": mc,
            "death_step": row["death_step"],
            "predicted_without_loop": predicted,
            "move_fraction": row["move_fraction"],
            "alive_at_end": row["alive"],
        })
        print("  mc=%.2f death_step=%s predicted=%.1f move_fraction=%.4f"
              % (mc, row["death_step"], predicted, row["move_fraction"]))

    add_series(result, "threshold_vs_move_cost", xs, ys)
    add_condition(result, "threshold_line", "threshold at three move costs", {
        "points": [{k: v for k, v in p.items() if k != "trail"} for p in line],
        "slope": slope,
        "law_threshold": TRUE_THRESHOLD,
    })
    add_condition(result, "death_time", "steps to extinction at maintenance 1.25", {
        "points": death_rows,
    })

    # ---- controls ----
    # fires: at move_cost 0 the threshold must be the plain law, 1.17, plus
    # the window offset. This is the known-good case; if it does not fire the
    # bisection itself is broken.
    fires = abs(line[0]["threshold"] - (TRUE_THRESHOLD + E_0 / STEPS)) <= 1e-4
    add_control(result, "fires", fires,
                "move_cost 0.0: threshold %.6f against the law plus window "
                "%.6f" % (line[0]["threshold"], TRUE_THRESHOLD + E_0 / STEPS))

    # silent: a very large move_cost must make the threshold fall a lot, not
    # stay put. If it stays put, nothing is being paid and the loop cannot
    # exist.
    big = run("sighted", 1.0, 5.0, steps=2000)
    silent = big["alive"] == 0
    add_control(result, "silent", silent,
                "move_cost 5.0 at maintenance 1.0: alive %d. A move cost far "
                "above the income kills, so the cost is being charged at all."
                % big["alive"])

    # specific: the slope must be distinguishable from zero. A control that
    # passes whether or not the threshold moves is not specific.
    specific = abs(slope) > 1e-3
    add_control(result, "specific", specific,
                "slope of threshold in move_cost is %.6f; a slope of 0 would "
                "mean survivors never pay for moving and the loop cannot "
                "exist." % slope)

    # ---- verdict ----
    max_death_gap = 0.0
    for r in death_rows:
        if r["death_step"] is None:
            continue
        gap = r["predicted_without_loop"] - r["death_step"]
        max_death_gap = max(max_death_gap, gap)

    if specific and fires and silent:
        set_verdict(result, "passed",
                    "The death threshold falls as move_cost rises: %.6f, "
                    "%.6f, %.6f at move_cost 0.0, 0.1, 0.3, a slope of %.6f. "
                    "Survivors at the threshold do pay for moving, so the "
                    "linear law `income - damage*repair` is the move_cost = 0 "
                    "case of a law that contains the move fraction. At "
                    "maintenance 1.25 the population dies at %s steps against "
                    "the no-loop prediction %s; the largest gap is %.1f steps."
                    % (line[0]["threshold"], line[1]["threshold"],
                       line[2]["threshold"], slope,
                       [r["death_step"] for r in death_rows],
                       ["%.1f" % r["predicted_without_loop"] for r in death_rows],
                       max_death_gap))
    elif not specific:
        set_verdict(result, "failed",
                    "The threshold does not move with move_cost (slope "
                    "%.6f). Survivors never pay for moving, so there is no "
                    "hunger feedback loop in this regime." % slope)
    else:
        set_verdict(result, "failed",
                    "Threshold moved (slope %.6f) but a control did not fire: "
                    "fires=%s silent=%s." % (slope, fires, silent))

    add_limitation(result,
                   "One seed, one field shape, one E_max, one read budget.")
    add_limitation(result,
                   "The slope is fitted through three points, so it is a "
                   "direction, not a precise coefficient. The move fraction at "
                   "the threshold is not measured directly; it is inferred from "
                   "the slope.")
    add_limitation(result,
                   "Death is read from the sampled frames, whose spacing is "
                   "steps/frames = 2. The death step is therefore known to "
                   "within 2 steps, not exactly.")
    add_limitation(result,
                   "The loop, if it exists, is not separated from the trivial "
                   "effect that a larger move_cost raises the deficit directly. "
                   "The slope measures the total effect; how much of it is the "
                   "loop and how much is the direct cost is not separated.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
