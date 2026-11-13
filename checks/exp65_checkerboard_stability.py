"""EXP-65: is the checkerboard a stable structure, or just a lucky reading?

EXP-64 and the probe found that on an alternating field the sighted rule
freezes into occ = 2 1 2 1 ... over all 40 cells with nothing moving, and that
this is the maximal packing (60 = 20 doubled + 20 single).

A frozen frame is not the same as a stable structure. The frame could be
frozen only because nothing disturbed it. The test is perturbation: take the
frozen configuration, move one organism by hand, and see whether the system
returns to the checkerboard or drifts to something else.

The trace binary cannot inject a perturbation, so this experiment perturbs the
FIELD instead: start the run from a field that is already in the checkerboard
shape and see whether the same packing forms from a different starting point.
If the checkerboard is a property of the rule, it should form from many
starting fields. If it is an accident of one run, it should not.

Arms: the same alternating field, six seeds, 50k steps, move_cost 0.05.

Controls:
  fires     -- every seed reaches the full 40 occupied cells and 60 alive
  silent    -- a uniform field at n=40 does not double (nothing to pack)
  specific  -- the doubling is exactly on the rich cells, not scattered:
               all 20 rich cells hold 2 and all 20 poor cells hold 1
"""

import json
import os
import subprocess

from experiment import Experiment
from result import CONTROL_TESTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 40
STEPS = 50000
EVERY = 2500
OUTDIR = os.path.join(ROOT, "results", "EXP-65")
SEEDS = [1, 2, 3, 7, 11, 42]


def run(field, rich, poor, n=80, seed=7, steps=STEPS, mc=0.05):
    os.makedirs(OUTDIR, exist_ok=True)
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(every_default(steps)), "--seed", str(seed),
           "--n", str(n), "--cells", str(CELLS),
           "--rich", str(rich), "--poor", str(poor),
           "--income", "1.0", "--maintenance", "0.6",
           "--damage-rate", "0.02", "--repair-cost", "0.5",
           "--move-cost", str(mc), "--energy", "10.0",
           "--field", field, "--read-budget", "3", "--memory-life", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit("trace failed %s seed=%s:\n%s" % (field, seed, out.stderr))
    written, h = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            h = line.split(":", 1)[1].strip()
    d = json.load(open(os.path.join(ROOT, written)))
    d["_hash"] = h
    return d


def every_default(steps):
    return max(1, steps // 20)


def census(frame):
    occ = {}
    for s in frame["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    alive = sum(occ.values())
    doubled = sum(1 for v in occ.values() if v >= 2)
    moved = sum(1 for s in frame["samples"]
                if s["alive"] and s.get("direction", 0) != 0)
    return alive, doubled, moved, occ


def checkerboard_split(occ, field):
    """Count organisms on cells that are local maxima vs local minima."""
    on_max = on_min = 0
    for c, k in occ.items():
        left = field[c - 1] if c > 0 else -1e9
        right = field[c + 1] if c + 1 < len(field) else -1e9
        if field[c] >= left and field[c] >= right:
            on_max += k
        elif field[c] <= left and field[c] <= right:
            on_min += k
    return on_max, on_min


def main():
    ex = Experiment(
        experiment_id="EXP-65",
        question=(
            "Is the checkerboard packing (60 organisms, occ = 2 1 2 1 ...) a "
            "property of the sighted rule, or an accident of one seed?"
        ),
        arithmetic={
            "max_packing": "20 rich cells * 2 + 20 poor cells * 1 = 60",
            "rich_cell_two": "1.92 - 2*income 1.0 = -0.08, emptied, regrows to 1.92",
            "poor_cell_one": "1.35 - 1*income 1.0 = 0.35, regrows to 1.35",
            "step_cost": "0.6 + 0.05 + 0.01 = 0.66",
            "cells": "40 (20 rich, 20 poor)",
        },
        arms={"seed-%d" % s: "alternating 2.4/1.6, seed %d" % s for s in SEEDS}
             | {"uniform-n40": "uniform 2.0, n=40, seed 7"},
        seed=7,
        command="trace --policy sighted --cells 40 --steps 50000 "
                "--field alternating --rich 2.4 --poor 1.6 --seed {1,2,3,7,11,42}",
    )

    rows = []
    for s in SEEDS:
        tr = run("alternating", 2.4, 1.6, seed=s)
        alive, doubled, moved, occ = census(tr["frames"][-1])
        field = tr["frames"][-1]["field"]
        on_max, on_min = checkerboard_split(occ, field)
        rows.append(dict(seed=s, alive=alive, doubled=doubled, moved=moved,
                         occupied=len(occ), on_max=on_max, on_min=on_min,
                         hash=tr.get("_hash")))
        ex.add_arm("seed-%d" % s, "alternating 2.4/1.6, seed %d" % s, {
            "alive": alive,
            "occupied_cells": len(occ),
            "doubled_cells": doubled,
            "moving_at_end": moved,
            "on_rich_cells": on_max,
            "on_poor_cells": on_min,
        }, trace_hash=tr.get("_hash"))

    tr40 = run("uniform", 2.0, 2.0, n=40, seed=7)
    a40, d40, m40, occ40 = census(tr40["frames"][-1])
    ex.add_arm("uniform-n40", "uniform 2.0, n=40, seed 7", {
        "alive": a40, "occupied_cells": len(occ40),
        "doubled_cells": d40, "moving_at_end": m40,
    }, trace_hash=tr40.get("_hash"))

    all_full = all(r["alive"] == 60 and r["occupied"] == 40 for r in rows)
    ex.control(
        "fires",
        all_full,
        "per seed (alive, occupied, doubled, moving): %s"
        % ", ".join("s%d=(%d,%d,%d,%d)" % (r["seed"], r["alive"], r["occupied"],
                                           r["doubled"], r["moved"]) for r in rows),
    )
    ex.control(
        "silent",
        a40 == 40 and d40 == 0,
        "uniform n=40: %d alive, %d doubled" % (a40, d40),
    )
    clean = all(r["doubled"] == 20 and r["on_max"] == 40 and r["on_min"] == 20
                for r in rows)
    ex.control(
        "specific",
        clean,
        "per seed (doubled, on_rich, on_poor): %s"
        % ", ".join("s%d=(%d,%d,%d)" % (r["seed"], r["doubled"], r["on_max"],
                                        r["on_min"]) for r in rows),
    )

    ex.limitation(
        "Perturbation is not injected. The experiment shows the packing forms "
        "from six different random starts, which is evidence that it is a "
        "property of the rule, but it does not show the packing survives a "
        "disturbance once formed."
    )
    ex.limitation(
        "All arms use one field shape (alternating 2.4/1.6) and one move_cost. "
        "EXP-64 showed move_cost does not matter here, but other field shapes "
        "were not run."
    )
    ex.limitation(
        "The trace binary cannot rewind or inject, so 'stable' here means "
        "'reached from six starts', not 'returns after being pushed'."
    )

    if ex.controls_passed():
        ex.verdict(
            "passed",
            "all six seeds reach 60 alive over 40 occupied cells with 20 "
            "doubled cells, all doubling on rich cells (40 on rich, 20 on poor)"
        )
    else:
        failed = [t for t in CONTROL_TESTS
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: %s" % ", ".join(failed))

    path = ex.save()
    print(path)
    for r in rows:
        print("seed %-3d alive=%3d occupied=%2d doubled=%2d moving=%2d "
              "rich=%2d poor=%2d" % (r["seed"], r["alive"], r["occupied"],
                                     r["doubled"], r["moved"], r["on_max"],
                                     r["on_min"]))
    print("uniform n=40 alive=%d doubled=%d" % (a40, d40))


if __name__ == "__main__":
    main()
