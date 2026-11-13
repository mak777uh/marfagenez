"""EXP-77: how much slack does the checkerboard have?

EXP-66 showed that six starting seeds all end on a frozen checkerboard: every
organism stands still, every organism sits on a local max or a local min of the
ring, and the rich cells carry two while the poor cells carry one. That is
**reachability**, not **stability**. Six seeds that happen to work do not say
what happens when the arrangement is pushed.

The trace binary cannot inject a state: it spawns organisms and runs. So the
push has to be something the spawner can produce. It can.

## What the push is

`--layout even` puts organism `i` on cell `i`, so with 40 cells and `n = 40`
the field starts with one organism on every cell -- the *opposite* of a
checkerboard, and the maximum-entropy start. That is not a push, it is a
different start.

The push is a **hole**: run `n = 39` instead of 40. Now one cell of the ring
has no organism on it. If the arrangement is a stable attractor, the population
should not be able to use that hole to rearrange -- the field should freeze
into the same checkerboard with one seat empty, and the empty seat should be
wherever the missing organism would have been. If the arrangement is only a
lucky start, the hole will let the population drift into a different pattern.

The second push is **excess**: `n = 42`, two more than the checkerboard holds.
The excess has to die, and where it dies says whether the arrangement is
restored or merely thinned.

## The arithmetic, before the run

Parameters are EXP-66's: 40 cells, `alternating` rich `2.4` / poor `1.6`,
`regrow = 0.8`, `income = 1.0`, `maintenance = 0.6`, `damage_rate = 0.05`,
`repair_cost = 1.5`, `E_max = 10`.

Cost per organism per step:

    need = 0.6 + 0.05 * 1.5 = 0.675

Cell levels, from `cellLevel M r k t = max(M - k*t*(1-r)/r, M*r)`:

    rich, k=1:  M=2.4  ->  2.4 - 1*1*(0.2)/0.8 = 2.15
    rich, k=2:          ->  2.4 - 2*1*(0.2)/0.8 = 1.90
    rich, k=3:          ->  2.4 - 3*1*(0.2)/0.8 = 1.65
    poor, k=1:  M=1.6  ->  1.6 - 1*(0.2)/0.8   = 1.35
    poor, k=2:          ->  1.6 - 2*(0.2)/0.8   = 1.10
    poor, k=3:          ->  1.6 - 3*(0.2)/0.8   = 0.85

Takes, in index order, capped at `income = 1.0`:

    rich, k=2:  first min(1.90, 1.0) = 1.00 ; second min(0.90, 1.0) = 0.90
                both 1.00 and 0.90 exceed need 0.675  -> both live
    rich, k=3:  third takes 1.65 - 2.00 = -0.35 -> clamped at 0.00 < 0.675 -> dies
    poor, k=1:  min(1.35, 1.0) = 1.00 > 0.675 -> lives
    poor, k=2:  first 1.00 ; second 1.10 - 1.00 = 0.10 < 0.675 -> dies
    poor, k=3:  the third sees a cell already below its own floor

So the checkerboard `2 rich + 1 poor` gives `20*2 + 20*1 = 60` and it is the
**unique** arrangement that saturates both cell types: rich cells cannot hold a
third (it takes `-0.35`), poor cells cannot hold a second (`0.10 < 0.675`).

That is the prediction, and it is a prediction about a *count*, which is
weaker than a prediction about a *shape*. The shape prediction is:

    with n = 39, exactly one cell is empty, and it is a rich cell
    (because a rich cell is the only seat whose loss costs the pattern
    nothing -- the remaining rich cell still feeds its two).

No. That is wrong, and writing it down is the point of pre-registration. A
hole at a rich cell leaves that rich cell with one organism at level 2.15,
taking 1.00. A neighbour organism on a poor cell sees a rich neighbour and
`Sighted` walks onto it. So the hole at a rich cell **fills**. A hole at a
poor cell leaves that poor cell empty; a neighbouring rich cell has no
incentive to move down onto it, so the hole at a poor cell **stays**.

Prediction, corrected before the run:

    n = 39: alive 59, one cell empty, and the empty cell is a POOR cell.
    n = 42: alive 60, two die, and the two that die are the ones that could
            not find a seat -- the count returns to 60, not 42.

## Controls

  fires:    n = 42 must give alive 60. Excess above the arrangement's count
            must die rather than crowd. If alive > 60, the arrangement is not
            the ceiling and the arithmetic is wrong.
  silent:   n = 40 must give alive 60 and moving 0 -- EXP-66's condition,
            reproduced under this script.
  specific: at n = 39 the empty cell must be poor, and `on_max + on_min` must
            still equal `alive`. If the hole were at a rich cell, the empty
            cell would be rich and the reading would be the opposite: the
            arrangement would fill holes rather than keep them.

## What this does not prove

The push is one hole and one excess. It does not test a *local* perturbation
that keeps the count fixed -- moving one organism from a rich cell to a poor
cell while leaving every other organism in place. The trace binary cannot
express that start. So "stable" here still means "stable against a missing
seat and against extra seats", not "stable against every rearrangement".
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
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
STEPS = 50000
SEED = 1

NEED = MAINT + DAMAGE * REPAIR


def level(M, k, t=INCOME, r=REGROW):
    """`cellLevel` from laws/Medium/Capacity.lean, both branches."""
    return max(M - k * t * (1 - r) / r, M * r)


def ring_split(field, cells, occ):
    """Local max / min on a RING. EXP-65 used -1e9 as a wall and was wrong."""
    n = len(field)
    on_max = on_min = neither = 0
    for c in range(n):
        if occ[c] == 0:
            continue
        left = field[(c - 1) % n]
        right = field[(c + 1) % n]
        me = field[c]
        if me >= left and me >= right:
            on_max += 1
        elif me <= left and me <= right:
            on_min += 1
        else:
            neither += 1
    return on_max, on_min, neither


def run(n):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "sighted", "--read-budget", "3",
        "--steps", str(STEPS), "--every", str(STEPS),
        "--seed", str(SEED),
        "--n", str(n), "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0",
        "--energy", str(CAP),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", str(REGROW),
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
    occ = [0] * CELLS
    for s in living:
        occ[s["cell"]] += 1
    field = last.get("field")
    if field is None:
        raise RuntimeError("frame has no field")
    on_max, on_min, neither = ring_split(field, CELLS, occ)

    empty = [c for c in range(CELLS) if occ[c] == 0]
    # In EXP-66's field, even cells are rich (0, 2, 4, ...) and odd are poor.
    empty_rich = [c for c in empty if c % 2 == 0]
    empty_poor = [c for c in empty if c % 2 == 1]
    overfull = [c for c in range(CELLS) if occ[c] > (2 if c % 2 == 0 else 1)]
    moving = sum(1 for s in living if s.get("direction", 0) != 0)

    return {
        "hash": digest,
        "n": n,
        "alive": len(living),
        "occupied": sum(1 for c in occ if c),
        "moving": moving,
        "on_max": on_max,
        "on_min": on_min,
        "neither": neither,
        "empty": empty,
        "empty_rich": empty_rich,
        "empty_poor": empty_poor,
        "overfull": overfull,
        "field_min": min(field),
        "field_max": max(field),
    }


def main():
    exp = Experiment(
        experiment_id="EXP-77",
        question="Is the checkerboard an attractor, or only a reachable state?",
        arithmetic={
            "need": NEED,
            "levels": {
                "rich_k1": level(RICH, 1), "rich_k2": level(RICH, 2),
                "rich_k3": level(RICH, 3),
                "poor_k1": level(POOR, 1), "poor_k2": level(POOR, 2),
                "poor_k3": level(POOR, 3),
            },
            "takes": {
                "rich_k2": [min(level(RICH, 2), INCOME),
                            max(level(RICH, 2) - INCOME, 0.0)],
                "rich_k3_third": level(RICH, 3) - 2 * INCOME,
                "poor_k2_second": level(POOR, 2) - INCOME,
            },
            "predicted_count": 20 * 2 + 20 * 1,
            "note": "the checkerboard is the unique arrangement that saturates "
                    "both cell types: rich cannot hold a third, poor cannot "
                    "hold a second",
        },
        arms={
            "n39": "one seat missing (the hole push)",
            "n40": "the checkerboard itself (EXP-66 reproduction)",
            "n42": "two seats too many (the excess push)",
        },
        seed=SEED,
        command="python3 checks/exp77_how_much_slack_does_the_checkerboard_have.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "income": INCOME, "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "steps": STEPS,
            "policy": "sighted", "move_cost": 0, "layout": "even",
        },
    )

    rows = {}
    for n in (39, 40, 42):
        r = run(n)
        rows[n] = r
        print("  n=%2d alive=%2d occ=%2d moving=%2d max+min=%2d neither=%2d "
              "empty=%s overfull=%s"
              % (n, r["alive"], r["occupied"], r["moving"],
                 r["on_max"] + r["on_min"], r["neither"],
                 r["empty"], r["overfull"]))

    for n, r in rows.items():
        exp.add_arm(
            "n%d" % n,
            "%d steps, alternating %.1f/%.1f, layout even, n=%d"
            % (STEPS, RICH, POOR, n),
            {
                "alive": r["alive"],
                "occupied": r["occupied"],
                "moving": r["moving"],
                "on_max": r["on_max"],
                "on_min": r["on_min"],
                "neither": r["neither"],
                "empty_cells": r["empty"],
                "empty_rich": r["empty_rich"],
                "empty_poor": r["empty_poor"],
                "overfull": r["overfull"],
                "field_min": r["field_min"],
                "field_max": r["field_max"],
            },
            trace_hash=r["hash"],
        )

    exp.control(
        "fires",
        rows[42]["alive"] == 60,
        "n=42 (two seats too many) must fall back to 60, not stay above it: "
        "alive = %d, overfull cells = %s"
        % (rows[42]["alive"], rows[42]["overfull"]),
    )
    exp.control(
        "silent",
        rows[40]["alive"] == 60 and rows[40]["moving"] == 0,
        "n=40 must reproduce EXP-66: alive = %d, moving = %d"
        % (rows[40]["alive"], rows[40]["moving"]),
    )
    exp.control(
        "specific",
        len(rows[39]["empty"]) == 1
        and rows[39]["empty_poor"] == rows[39]["empty"]
        and rows[39]["on_max"] + rows[39]["on_min"] == rows[39]["alive"],
        "n=39: empty cells = %s (rich %s, poor %s); on_max+on_min = %d vs "
        "alive = %d. The hole must be POOR: a hole at a rich cell fills, "
        "because a neighbour on a poor cell sees a richer neighbour and walks "
        "onto it."
        % (rows[39]["empty"], rows[39]["empty_rich"], rows[39]["empty_poor"],
           rows[39]["on_max"] + rows[39]["on_min"], rows[39]["alive"]),
    )

    hole_kept = len(rows[39]["empty"]) == 1 and rows[39]["empty_poor"]
    excess_died = rows[42]["alive"] == 60
    if hole_kept and excess_died:
        exp.verdict(
            "passed",
            "the checkerboard survives both pushes. At n=39 the population "
            "freezes with exactly one empty cell and that cell is poor; at "
            "n=42 it falls back to 60. Both are what the level arithmetic "
            "predicts: rich k=3 takes %.2f (negative, so nobody), poor k=2 "
            "gives the second %.2f against a need of %.3f. The arrangement is "
            "the unique saturating one, and the population finds it from "
            "below and from above."
            % (level(RICH, 3) - 2 * INCOME, level(POOR, 2) - INCOME, NEED),
        )
    else:
        exp.verdict(
            "failed",
            "hole kept = %s (empty %s), excess died = %s (alive %d at n=42). "
            "At least one push rearranged the arrangement, so it is a "
            "reachable state and not an attractor."
            % (hole_kept, rows[39]["empty"], excess_died, rows[42]["alive"]),
        )

    exp.limitation(
        "The pushes are a missing seat and extra seats. Neither is a local "
        "rearrangement at fixed count -- moving one organism from a rich cell "
        "to a poor cell while every other organism stays put. The trace binary "
        "cannot express that start, so 'stable' here does not yet mean 'stable "
        "against every rearrangement'."
    )
    exp.limitation(
        "Only one field amplitude is tested (rich 2.4 / poor 1.6). A weaker "
        "contrast may have a different arrangement, and the arithmetic above "
        "says when: the poor cell stops feeding one when "
        "min(M_poor, income) < need, i.e. below M_poor = 0.675."
    )
    exp.limitation(
        "move_cost is 0, so this says nothing about whether moving is "
        "affordable -- only about where the population ends up when it is free."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
