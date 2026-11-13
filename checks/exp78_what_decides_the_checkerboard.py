"""EXP-78: the two numbers that both decide the checkerboard.

EXP-77 asked whether the checkerboard is an attractor by pushing it with a
missing seat and with extra seats. It failed all three controls, and the reason
is worth more than the experiment: **the checkerboard is not a property of the
sighted rule at all. It is a property of three numbers.**

EXP-77 ran `n = 40` with `--layout even` and got `occ = 1 1 1 ... 1` -- ONE
organism per cell, forty alive, nothing moving. EXP-66 ran `n = 80` with the
same field and got `occ = 2 1 2 1 ...`, sixty alive. Same field, same policy,
same 40 cells, and two different frozen arrangements, both stable, neither
moving.

## Why, and this is the arithmetic the experiment is about

`--layout even` puts organism `i` on cell `i`, so `n = 40` starts with one per
cell and `n = 80` starts with two per cell. `Sighted` moves only when a
neighbour is **strictly** richer than the current cell. On a settled
alternating field every poor cell is strictly poorer than both neighbours, so
an organism on a poor cell always leaves, and one that arrives on a rich cell
never leaves. Nothing in that rule says how many may arrive.

What stops the second organism is not the rule, it is the **level**:

    rich cell, k occupants, level = max(M - k*t*(1-r)/r, M*r)
    M = 2.4, t = 1.0, r = 0.8  ->  level(k) = max(2.4 - 0.25k, 1.92)

    k=1: 2.15   k=2: 1.90   k=3: 1.65   k=4: 1.40

and the **take order**: `Field::take` hands out `min(cell, income)` in
population index order (`core/src/field.rs:188`), so with `income = 1.0`:

    k=1: first takes 1.00
    k=2: first 1.00, second 0.90
    k=3: first 1.00, second 0.90, third 0.00 (cell is 1.65 - 2.00 < 0)
    k=4: first 1.00, second 0.90, third 0.00, fourth 0.00

Against `need = maintenance + damage*repair`:

    EXP-66: need = 0.6 + 0.02*0.5 = 0.61   -> 0.90 > 0.61, the second lives
    EXP-77: need = 0.6 + 0.05*1.5 = 0.675  -> 0.90 > 0.675, the second lives

Both say the second lives. So why did EXP-77 get 40?

Because of the **start**, not the level. At `n = 40` every cell holds exactly
one organism, and the field is already alternating. No poor-cell organism can
improve: its rich neighbours are occupied by one each, but `Sighted` compares
LEVELS, not free space -- a rich neighbour is strictly richer whether or not
somebody is on it. So the poor-cell organism should move onto it. It did not.

That is the open question this experiment settles, and there are exactly two
candidate answers:

  H1. `move_cost = 0` makes the move free, so the poor-cell organism moves and
      the rich cell ends with two -- but the second then takes 0.90, lives,
      and the pattern becomes `2 0 2 0 ...` (poor cells empty), which is 40
      alive over 20 cells, crowding 2.00. EXP-77 measured crowding 1.00 over
      40 cells, so H1 is not what happened.

  H2. `move_cost = 0` is not the difference. The difference is `--layout even`
      versus the default spawn: `spawn_even` sets `r.memory.best_level = 0.0`
      and every organism starts at full energy, and the FIRST step decides.
      With `n = 40` and one per cell, at step 1 every cell is at its ceiling,
      so `here == left == right` is FALSE for a poor cell (its neighbours are
      richer) -- it should still move.

Neither hypothesis is confirmed by reading the code, so the experiment
measures instead of arguing. It varies the two numbers that the arithmetic
says matter, one at a time, and reads the resulting arrangement:

  A. n = 40, need = 0.61 (EXP-66's damage)   -- does the second seat open?
  B. n = 40, need = 0.675 (EXP-77's damage)  -- EXP-77 reproduced exactly
  C. n = 80, need = 0.675                    -- does the extra seat still fill?
  D. n = 40, move_cost = 0.05 (EXP-66's)     -- is the free move the cause?

If A gives 60 and B gives 40, the arrangement is decided by `need` alone and
the threshold is `0.90 > need`, i.e. `need < 0.90`. If A and B both give 40,
the cause is the start, not the level, and the checkerboard needs a start with
two on a cell. If D differs from B, movement cost is the gate.

## Controls

  fires:    arm C (n = 80) must give 60 -- the checkerboard exists at all, and
            this reproduces EXP-66 with EXP-77's damage rate. If C is not 60,
            the damage rate alone breaks the arrangement and nothing below
            means anything.
  silent:   arm B must give exactly 40 with crowding 1.00 -- EXP-77's number,
            reproduced. If B is not 40, EXP-77's reading was noise.
  specific: the two arms that differ ONLY in `need` (A and B) must give
            different alive counts, or the two arms that differ ONLY in
            `move_cost` (B and D) must. If neither pair separates, `need` and
            `move_cost` are both irrelevant and the arrangement is decided by
            the start alone -- which is a finding, but a different one, and the
            verdict says so.

## What this does not prove

Four arms cannot separate three factors (start, need, move_cost) that may
interact. If A and D both differ from B, the experiment shows that each factor
matters but not how they combine. The full 2x2x2 is left for the next run.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

CORE = os.path.join(ROOT, "core")
TRACE = os.path.join(CORE, "target", "release", "trace")

CELLS = 40
RICH = 2.4
POOR = 1.6
REGROW = 0.8
INCOME = 1.0
MAINT = 0.6
REPAIR = 1.5
CAP = 10.0
STEPS = 50000
SEED = 1


def level(M, k, t=INCOME, r=REGROW):
    return max(M - k * t * (1 - r) / r, M * r)


def ring_split(field, occ):
    n = len(field)
    on_max = on_min = neither = 0
    for c in range(n):
        if occ[c] == 0:
            continue
        left = field[(c - 1) % n]
        right = field[(c + 1) % n]
        me = field[c]
        if me >= left and me >= right:
            on_max += occ[c]
        elif me <= left and me <= right:
            on_min += occ[c]
        else:
            neither += occ[c]
    return on_max, on_min, neither


def run(n, damage, move_cost, label):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "sighted", "--read-budget", "3",
        "--steps", str(STEPS), "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", str(n), "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(damage),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", str(move_cost),
        "--energy", str(CAP),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(REGROW), "--memory-life", "100000",
    ]
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise RuntimeError("%s: trace failed: %s" % (label, out.stderr[-1200:]))
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    if not after:
        raise RuntimeError("%s: no new trace" % label)
    path = max(after, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    last = data["frames"][-1]
    living = [s for s in last["samples"] if s["alive"]]
    occ = [0] * CELLS
    for s in living:
        occ[s["cell"]] += 1
    field = last["field"]
    on_max, on_min, neither = ring_split(field, occ)
    need = MAINT + damage * REPAIR
    return {
        "hash": digest,
        "label": label,
        "n": n,
        "damage": damage,
        "need": need,
        "move_cost": move_cost,
        "alive": len(living),
        "occupied": sum(1 for c in occ if c),
        "crowding": len(living) / max(1, sum(1 for c in occ if c)),
        "doubled": sum(1 for c in occ if c >= 2),
        "moving": sum(1 for s in living if s.get("direction", 0) != 0),
        "on_max": on_max,
        "on_min": on_min,
        "neither": neither,
        "occ_pattern": occ,
        "field_min": min(field),
        "field_max": max(field),
    }


def main():
    exp = Experiment(
        experiment_id="EXP-78",
        question="Which number decides the checkerboard: the start, `need`, or "
                 "`move_cost`?",
        arithmetic={
            "need_exp66": MAINT + 0.02 * 0.5,
            "need_exp77": MAINT + 0.05 * REPAIR,
            "level": {str(k): level(RICH, k) for k in (1, 2, 3, 4)},
            "takes": {
                "k1": [min(level(RICH, 1), INCOME)],
                "k2": [INCOME, max(level(RICH, 2) - INCOME, 0.0)],
                "k3": [INCOME, max(level(RICH, 2) - INCOME, 0.0),
                       max(level(RICH, 3) - 2 * INCOME, 0.0)],
            },
            "second_seat_lives_if": "0.90 > need, i.e. need < 0.90",
            "both_needs_allow_second": (MAINT + 0.02 * 0.5) < 0.90
                                       and (MAINT + 0.05 * REPAIR) < 0.90,
            "note": "both damage rates allow a second organism on a rich cell, "
                    "so the level arithmetic alone does NOT explain EXP-77's "
                    "40. The start must be doing the work.",
        },
        arms={
            "A": "n=40, need=0.610 (EXP-66 damage)",
            "B": "n=40, need=0.675 (EXP-77 damage)",
            "C": "n=80, need=0.675",
            "D": "n=40, need=0.675, move_cost=0.05",
        },
        seed=SEED,
        command="python3 checks/exp78_what_decides_the_checkerboard.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "income": INCOME, "maintenance": MAINT, "repair_cost": REPAIR,
            "capacity": CAP, "steps": STEPS, "policy": "sighted",
            "read_budget": 3, "layout": "even",
        },
    )

    specs = [
        ("A", 40, 0.02, 0.0),
        ("B", 40, 0.05, 0.0),
        ("C", 80, 0.05, 0.0),
        ("D", 40, 0.05, 0.05),
    ]
    rows = {}
    for key, n, dmg, mc in specs:
        r = run(n, dmg, mc, key)
        rows[key] = r
        print("  %s n=%2d need=%.3f mc=%.2f alive=%2d occ=%2d crowd=%.2f "
              "doubled=%2d moving=%2d max+min=%2d neither=%2d"
              % (key, n, r["need"], mc, r["alive"], r["occupied"],
                 r["crowding"], r["doubled"], r["moving"],
                 r["on_max"] + r["on_min"], r["neither"]))
        print("     occ %s" % " ".join(str(x) for x in r["occ_pattern"]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            "n=%d, need=%.3f, move_cost=%.2f, %d steps, alternating %.1f/%.1f"
            % (r["n"], r["need"], r["move_cost"], STEPS, RICH, POOR),
            {
                "alive": r["alive"],
                "occupied_cells": r["occupied"],
                "crowding": r["crowding"],
                "doubled_cells": r["doubled"],
                "moving_at_end": r["moving"],
                "on_rich_cells": r["on_max"],
                "on_poor_cells": r["on_min"],
                "unclassified": r["neither"],
                "occ_pattern": r["occ_pattern"],
                "field_min": r["field_min"],
                "field_max": r["field_max"],
            },
            trace_hash=r["hash"],
        )

    exp.control(
        "fires",
        rows["C"]["alive"] == 60,
        "arm C (n=80, need=0.675) must reproduce the checkerboard: alive = %d, "
        "doubled cells = %d, crowding = %.2f"
        % (rows["C"]["alive"], rows["C"]["doubled"], rows["C"]["crowding"]),
    )
    exp.control(
        "silent",
        rows["B"]["alive"] == 40 and abs(rows["B"]["crowding"] - 1.0) < 1e-9,
        "arm B (n=40, need=0.675) must reproduce EXP-77's 40 at crowding 1.00: "
        "alive = %d, crowding = %.4f"
        % (rows["B"]["alive"], rows["B"]["crowding"]),
    )
    need_separates = rows["A"]["alive"] != rows["B"]["alive"]
    cost_separates = rows["B"]["alive"] != rows["D"]["alive"]
    exp.control(
        "specific",
        need_separates or cost_separates,
        "A vs B (differ only in need 0.610 vs 0.675): %d vs %d alive -- "
        "separates = %s. B vs D (differ only in move_cost 0.00 vs 0.05): "
        "%d vs %d -- separates = %s."
        % (rows["A"]["alive"], rows["B"]["alive"], need_separates,
           rows["D"]["alive"], rows["B"]["alive"], cost_separates),
    )

    if need_separates and not cost_separates:
        exp.verdict(
            "passed",
            "the checkerboard is decided by `need`, not by the start and not by "
            "`move_cost`. At need = %.3f (arm A) the population reaches %d; at "
            "need = %.3f (arm B) it stays at %d; changing `move_cost` from 0.00 "
            "to 0.05 at the same need changes nothing (arm D = %d). The "
            "threshold is the second organism's take on a rich cell: it gets "
            "%.2f, so it lives while `need < %.2f`. Both damage rates tested "
            "are below that, so the difference between A and B is not the "
            "threshold -- it is the margin."
            % (rows["A"]["need"], rows["A"]["alive"], rows["B"]["need"],
               rows["B"]["alive"], rows["D"]["alive"],
               level(RICH, 2) - INCOME, level(RICH, 2) - INCOME),
        )
    elif cost_separates and not need_separates:
        exp.verdict(
            "passed",
            "the checkerboard is gated by `move_cost`, not by `need`. Arms A "
            "and B, which differ only in `need`, both give %d; arms B and D, "
            "which differ only in `move_cost` (0.00 vs 0.05), give %d and %d. "
            "A free move lets a poor-cell organism walk onto an occupied rich "
            "cell and stay; a priced move does not."
            % (rows["A"]["alive"], rows["B"]["alive"], rows["D"]["alive"]),
        )
    elif need_separates and cost_separates:
        exp.verdict(
            "passed",
            "both `need` and `move_cost` separate the arms: A=%d, B=%d, D=%d. "
            "They interact, and four arms cannot say how. The 2x2x2 over "
            "(n, need, move_cost) is the next run."
            % (rows["A"]["alive"], rows["B"]["alive"], rows["D"]["alive"]),
        )
    else:
        exp.verdict(
            "failed",
            "neither `need` nor `move_cost` separates the arms: A=%d, B=%d, "
            "D=%d, all at n=40. The arrangement is decided by the start alone "
            "-- by how many organisms `--layout even` puts on a cell -- and the "
            "level arithmetic that was supposed to set the count does not "
            "reach it."
            % (rows["A"]["alive"], rows["B"]["alive"], rows["D"]["alive"]),
        )

    exp.limitation(
        "Four arms cannot separate three factors (start, need, move_cost) that "
        "may interact. If both separate, the experiment shows that each matters "
        "but not how they combine."
    )
    exp.limitation(
        "Only one seed and one field amplitude (2.4/1.6). EXP-66 showed the "
        "count varies between 55 and 60 across seeds at n=80; the same spread "
        "at n=40 was not measured."
    )
    exp.limitation(
        "The reading is the final frame only. A transient crowding above 1.00 "
        "that decays would not be seen. EXP-77's n=42 arm already showed that "
        "excess can be absorbed without dying, so transients matter here."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
