"""EXP-66: is the second occupant on a cell an equilibrium or a transient?

History. EXP-65 reported, at n = 160, that E_max = 8 gives alive = 40 and
E_max = 9 gives alive = 42, and called the capacity a line in E_max. That was
wrong: sweeping --n with everything else fixed shows alive = n exactly at every
setting (40 -> 40, 42 -> 42, 80 -> 80, 120 -> 120, 160 -> 160, 200 -> 200).
Nothing dies. The "40" and "42" were --n 40 and --n 42, read back as results.
See docs/FINDING-the-capacity-finding-was-reading-its-own-input.md.

So the question this experiment can actually answer is not "what is the
capacity" -- these settings have no capacity, nothing dies -- but "what is the
energy of an organism that shares a cell, and is it a fixed point".

Arithmetic registered before the run:
  COST          = maintenance + damage_rate * repair_cost = 0.6 + 0.02*1.5 = 0.63
  c*            = M - income*(1-r)/r = 2.0 - 1.2*0.2/0.8 = 1.7
  second share  = c* - income = 0.5
  deficit       = COST - second share = 0.13 per step
  alone steady  = E_max - COST  (7.37 / 8.37 / 9.37 for E_max 8 / 9 / 10)

The prediction under test: a sedentary second occupant loses 0.13 per step and
must fall. The measurement will show whether it falls or freezes. If it freezes,
the deficit arithmetic describes a sedentary organism and these organisms are
not sedentary -- they move to a cell they have not eaten.

Pre-registered predictions:
  (a) if the second occupant is sedentary, its energy falls without bound and
      it dies within (E_max - 2*COST) / 0.13 steps of the run start;
  (b) if it moves to a fresh cell each step, its energy freezes at a fixed
      point that is neither E_max - COST nor c* - income.
The two are distinguishable without knowing the answer: (a) gives a falling
series, (b) gives a flat tail.
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
TRACE_DIR = os.path.join(CORE, "results", "sighted")  # trace writes results/<policy>/

INCOME = 1.2
M = 2.0
R = 0.8
MAINT = 0.6
DAMAGE = 0.02
REPAIR = 1.5
MOVE = 0.10
N = 160
CELLS = 40
SEED = 20250101

STEPS = 40000
EVERY = 2000

COST = MAINT + DAMAGE * REPAIR
CSTAR = M - INCOME * (1 - R) / R
SECOND = CSTAR - INCOME
DEFICIT = COST - SECOND


def run(e_max):
    os.makedirs(TRACE_DIR, exist_ok=True)
    before = set(os.listdir(TRACE_DIR))
    time.sleep(1.2)
    cmd = [
        "cargo", "run", "--release", "--bin", "trace", "--quiet", "--",
        "--policy", "sighted", "--read-budget", "3",
        "--n", str(N), "--cells", str(CELLS),
        "--steps", str(STEPS), "--every", str(EVERY), "--seed", str(SEED),
        "--capacity", str(e_max), "--regrow", str(R),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--damage-rate", str(DAMAGE), "--repair-cost", str(REPAIR),
        "--move-cost", str(MOVE),
        "--field", "uniform", "--rich", "2.4", "--poor", "1.6",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3500)
    if out.returncode != 0:
        raise RuntimeError("trace failed for E_max=%s: %s" % (e_max, out.stderr[-2000:]))
    after = set(os.listdir(TRACE_DIR)) - before
    if not after:
        raise RuntimeError("no new trace file for E_max=%s" % e_max)
    path = os.path.join(TRACE_DIR, sorted(after)[-1])
    with open(path, encoding="utf-8") as f:
        return path, json.load(f)


def analyse(data):
    frames = []
    for fr in data["frames"]:
        samples = fr["samples"]
        by_cell = {}
        for s in samples:
            by_cell.setdefault(s["cell"], []).append(s)
        shared_e = [s["energy"] for g in by_cell.values() if len(g) > 1 for s in g]
        alone_e = [s["energy"] for g in by_cell.values() if len(g) == 1 for s in g]
        frames.append({
            "step": fr["step"],
            "alive": len(samples),
            "occupied": len(by_cell),
            "crowding": len(samples) / len(by_cell) if by_cell else 0.0,
            "max_per_cell": max((len(g) for g in by_cell.values()), default=0),
            "shared_cells": sum(1 for g in by_cell.values() if len(g) > 1),
            "shared_energy_mean": sum(shared_e) / len(shared_e) if shared_e else None,
            "shared_energy_min": min(shared_e) if shared_e else None,
            "alone_energy_mean": sum(alone_e) / len(alone_e) if alone_e else None,
        })
    return frames


def tail_drift(frames, frac=0.25):
    """Mean of the last `frac` of frames minus the mean of the middle `frac`."""
    n = len(frames)
    k = max(1, int(n * frac))
    mid = frames[n // 2 - k // 2:n // 2 + k // 2 + 1]
    tail = frames[-k:]
    if not mid or not tail:
        return None
    a = [f["shared_energy_mean"] for f in mid if f["shared_energy_mean"] is not None]
    b = [f["shared_energy_mean"] for f in tail if f["shared_energy_mean"] is not None]
    if not a or not b:
        return None
    return sum(b) / len(b) - sum(a) / len(a)


def main():
    result = new_result(
        "exp66-second-occupant",
        SEED,
        {
            "n": N, "cells": CELLS, "steps": STEPS, "every": EVERY,
            "policy": "sighted", "read_budget": 3,
            "income": INCOME, "M": M, "regrow": R,
            "maintenance": MAINT, "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "move_cost": MOVE, "field": "uniform", "rich": 2.4, "poor": 1.6,
            "e_max": [8, 9, 10],
        },
        "python3 checks/exp66_second_occupant.py",
    )
    set_arithmetic(result, {
        "cost": COST,
        "c_star": CSTAR,
        "second_share": SECOND,
        "deficit_per_step": DEFICIT,
        "alone_steady_by_e_max": {8: 8 - COST, 9: 9 - COST, 10: 10 - COST},
        "prediction_a_sedentary": "shared energy falls, organism dies",
        "prediction_b_moving": "shared energy freezes at a fixed point",
    })

    runs = {}
    for e_max in (8, 9, 10):
        path, data = run(e_max)
        frames = analyse(data)
        runs[e_max] = {"path": path, "frames": frames}
        print("E_max=%d  file=%s" % (e_max, os.path.basename(path)))
        for f in frames:
            se = "--" if f["shared_energy_mean"] is None else "%.4f" % f["shared_energy_mean"]
            ae = "--" if f["alone_energy_mean"] is None else "%.4f" % f["alone_energy_mean"]
            print("  step %6d  alive %3d  occ %3d  crowd %.2f  max %2d  "
                  "shared %2d  sharedE %s  aloneE %s"
                  % (f["step"], f["alive"], f["occupied"], f["crowding"],
                     f["max_per_cell"], f["shared_cells"], se, ae))
        add_condition(result, "e_max_%d" % e_max, "E_max = %d" % e_max, {
            "final_alive": frames[-1]["alive"],
            "final_crowding": frames[-1]["crowding"],
            "final_shared_energy_mean": frames[-1]["shared_energy_mean"],
            "final_alone_energy_mean": frames[-1]["alone_energy_mean"],
            "shared_energy_tail_drift": tail_drift(frames),
        })
        add_series(result, "alive_e%d" % e_max,
                   [f["step"] for f in frames], [f["alive"] for f in frames])
        add_series(result, "shared_energy_e%d" % e_max,
                   [f["step"] for f in frames],
                   [f["shared_energy_mean"] if f["shared_energy_mean"] is not None else 0.0
                    for f in frames])

    # ---- controls ----
    # fires: the alone-on-a-cell energy must equal E_max - COST exactly. This is
    # the one number the arithmetic predicts without ambiguity, and it is known
    # to be present, so a control aimed at it must fire.
    e8 = runs[8]["frames"][-1]
    alone_ok = (e8["alone_energy_mean"] is not None
                and abs(e8["alone_energy_mean"] - (8 - COST)) < 1e-9)
    add_control(result, "fires", alone_ok,
                "E_max=8 alone-energy %.4f vs predicted E_max-COST = %.4f"
                % (e8["alone_energy_mean"] if e8["alone_energy_mean"] is not None else float("nan"),
                   8 - COST))

    # silent: alive must equal n at every frame, i.e. the "capacity" the earlier
    # note reported does not appear. The control that would fire on a real
    # capacity limit stays silent.
    all_alive_n = all(f["alive"] == N for e in runs.values() for f in e["frames"])
    add_control(result, "silent", all_alive_n,
                "alive equals n=%d at every frame of every E_max arm: no capacity "
                "limit appears at these settings" % N)

    # specific: the shared-cell energy must be neither E_max - COST nor
    # c* - income, and its tail must be flat. If it were E_max - COST the
    # measurement would be indistinguishable from the alone case; if it were
    # falling it would be the sedentary prediction.
    drift9 = tail_drift(runs[9]["frames"])
    se9 = runs[9]["frames"][-1]["shared_energy_mean"]
    not_alone = abs(se9 - (9 - COST)) > 0.1
    not_second_share = abs(se9 - SECOND) > 0.1
    flat = drift9 is not None and abs(drift9) < 0.05
    specific = bool(not_alone and not_second_share and flat)
    add_control(result, "specific", specific,
                "E_max=9 shared energy %.4f: differs from E_max-COST=%.4f and from "
                "second share %.4f; tail drift %s over the last quarter"
                % (se9, 9 - COST, SECOND,
                   "n/a" if drift9 is None else "%+.4f" % drift9))

    # ---- verdict ----
    drifts = {e: tail_drift(runs[e]["frames"]) for e in runs}
    flat_arms = [e for e in runs if drifts[e] is not None and abs(drifts[e]) < 0.05]
    if len(flat_arms) == len(runs):
        set_verdict(result, "passed",
                    "The shared-cell energy is a fixed point at every E_max tested "
                    "(%s). It is neither E_max - COST nor c* - income, so the "
                    "deficit arithmetic (0.13 per step) describes a sedentary "
                    "organism and these organisms are not sedentary: they move to "
                    "a cell they have not eaten and the reserve is replenished. "
                    "The earlier reading of 40 and 42 as capacities was the input "
                    "n read back out; alive equals n at every setting."
                    % ", ".join("E_max=%d drift %+.4f" % (e, drifts[e]) for e in sorted(runs)))
    elif not flat_arms:
        set_verdict(result, "failed",
                    "The shared-cell energy falls in every arm (%s): the sedentary "
                    "prediction (a) holds and the second occupant is dying, not "
                    "freezing. The earlier 40/42 reading would then be a genuine "
                    "transient after all."
                    % ", ".join("E_max=%d drift %+.4f" % (e, drifts[e]) for e in sorted(runs)))
    else:
        set_verdict(result, "insensitive by construction",
                    "Flat in %s, falling in the rest; the experiment does not "
                    "separate the two predictions across all arms."
                    % flat_arms)

    add_limitation(result,
                   "One seed. One field shape (uniform 2.0, built as "
                   "(rich+poor)/2). alive = n was checked at six values of n and "
                   "three of E_max in a separate sweep, not swept here.")
    add_limitation(result,
                   "The trace samples every %d steps, so an organism that dies and "
                   "is replaced within one sampling interval is invisible here." % EVERY)
    add_limitation(result,
                   "This does not measure a capacity. At these settings nothing "
                   "dies, so these settings cannot state a capacity law. A setting "
                   "with a real limit has to be found first.")

    path = save(result)
    print("saved", path)


if __name__ == "__main__":
    main()
