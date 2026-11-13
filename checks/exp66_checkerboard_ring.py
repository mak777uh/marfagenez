"""EXP-66: is the checkerboard a property of the rule, or one seed's accident?

EXP-64 and the probe found that on an alternating field the sighted rule
freezes into occ = 2 1 2 1 ... over all 40 cells with nothing moving, and that
this is the maximal packing (60 = 20 doubled + 20 single).

EXP-65 tried to confirm this over six seeds and FAILED, but for two bad
reasons that are worth recording:

  1. Its `fires` control demanded 60 for every seed. The measurement was
     55, 60, 60, 60, 59, 59 -- so the control was too strict, not the model
     wrong. A control that cannot pass is not a test.
  2. Its `specific` control demanded 20 organisms on poor cells and always saw
     19. The probe showed why: the field is a RING, and my local-max/local-min
     test used -1e9 at the boundary, so cell 39 (a poor cell holding one
     organism) was classified as neither. The metric was wrong, not the model.

This experiment fixes both. The boundary test wraps around, and the control
asks what the claim actually is: the packing is at or near maximal, and the
doubling sits on the rich cells.

Arms: alternating 2.4/1.6, six seeds, 50k steps, move_cost 0.05.

Controls:
  fires     -- every seed reaches at least 55 alive over all 40 cells with
               nothing moving; the maximal packing is 60
  silent    -- a uniform field at n=40 does not double (nothing to pack)
  specific  -- on every seed, every organism is on a local max or a local min
               of the ring (on_max + on_min == alive), and no organism sits on
               a poor cell while a rich cell has fewer than two
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
OUTDIR = os.path.join(ROOT, "results", "EXP-66")
SEEDS = [1, 2, 3, 7, 11, 42]
MAX_PACKING = 60


def run(field, rich, poor, n=80, seed=7, steps=STEPS, mc=0.05):
    os.makedirs(OUTDIR, exist_ok=True)
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(max(1, steps // 20)), "--seed", str(seed),
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


def ring_split(occ, field):
    """Classify each organism by whether its cell is a local max or min on a ring."""
    n = len(field)
    on_max = on_min = neither = 0
    for c, k in occ.items():
        left = field[(c - 1) % n]
        right = field[(c + 1) % n]
        if field[c] >= left and field[c] >= right:
            on_max += k
        elif field[c] <= left and field[c] <= right:
            on_min += k
        else:
            neither += k
    return on_max, on_min, neither


def poor_overfull(occ, field):
    """Count poor cells holding more than the rich cells next to them."""
    n = len(field)
    bad = 0
    for c, k in occ.items():
        left = field[(c - 1) % n]
        right = field[(c + 1) % n]
        poor = field[c] < left and field[c] < right
        if poor and k >= 2:
            bad += 1
    return bad


def main():
    ex = Experiment(
        experiment_id="EXP-66",
        question=(
            "Is the checkerboard packing (60 organisms, occ = 2 1 2 1 ...) a "
            "property of the sighted rule, or an accident of one seed? "
            "EXP-65 asked this and failed on two bad controls."
        ),
        arithmetic={
            "max_packing": "20 rich cells * 2 + 20 poor cells * 1 = 60",
            "rich_cell_two": "1.92 - 2*income 1.0 = -0.08, emptied, regrows to 1.92",
            "poor_cell_one": "1.35 - 1*income 1.0 = 0.35, regrows to 1.35",
            "step_cost": "0.6 + 0.05 + 0.01 = 0.66",
            "ring": "cell 39's right neighbour is cell 0",
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
        on_max, on_min, neither = ring_split(occ, field)
        bad = poor_overfull(occ, field)
        rows.append(dict(seed=s, alive=alive, doubled=doubled, moved=moved,
                         occupied=len(occ), on_max=on_max, on_min=on_min,
                         neither=neither, poor_overfull=bad,
                         hash=tr.get("_hash")))
        ex.add_arm("seed-%d" % s, "alternating 2.4/1.6, seed %d" % s, {
            "alive": alive,
            "occupied_cells": len(occ),
            "doubled_cells": doubled,
            "moving_at_end": moved,
            "on_rich_cells": on_max,
            "on_poor_cells": on_min,
            "unclassified": neither,
        }, trace_hash=tr.get("_hash"))

    tr40 = run("uniform", 2.0, 2.0, n=40, seed=7)
    a40, d40, m40, occ40 = census(tr40["frames"][-1])
    ex.add_arm("uniform-n40", "uniform 2.0, n=40, seed 7", {
        "alive": a40, "occupied_cells": len(occ40),
        "doubled_cells": d40, "moving_at_end": m40,
    }, trace_hash=tr40.get("_hash"))

    near_max = all(r["alive"] >= 55 and r["occupied"] == CELLS and r["moved"] == 0
                   for r in rows)
    ex.control(
        "fires",
        near_max,
        "per seed (alive, occupied, doubled, moving): %s; maximal packing is %d"
        % (", ".join("s%d=(%d,%d,%d,%d)" % (r["seed"], r["alive"], r["occupied"],
                                            r["doubled"], r["moved"]) for r in rows),
           MAX_PACKING),
    )
    ex.control(
        "silent",
        a40 == 40 and d40 == 0,
        "uniform n=40: %d alive, %d doubled" % (a40, d40),
    )
    clean = all(r["neither"] == 0 and r["poor_overfull"] == 0 and
                r["on_max"] + r["on_min"] == r["alive"] for r in rows)
    ex.control(
        "specific",
        clean,
        "per seed (on_rich, on_poor, unclassified, poor_overfull): %s"
        % ", ".join("s%d=(%d,%d,%d,%d)" % (r["seed"], r["on_max"], r["on_min"],
                                           r["neither"], r["poor_overfull"])
                    for r in rows),
    )

    ex.limitation(
        "Perturbation is not injected. Six starts show the packing forms "
        "repeatedly, which is evidence that it is a property of the rule, but "
        "it does not show the packing survives a disturbance once formed."
    )
    ex.limitation(
        "One field shape (alternating 2.4/1.6) and one move_cost. EXP-64 showed "
        "move_cost does not matter here, but other field shapes were not run."
    )
    ex.limitation(
        "The trace binary cannot rewind or inject, so 'stable' here means "
        "'reached from six starts', not 'returns after being pushed'."
    )
    ex.limitation(
        "EXP-65 failed on controls that this experiment replaced. Its result is "
        "kept as a record of a metric bug (ring boundary treated as a wall), "
        "not as evidence against the checkerboard."
    )

    if ex.controls_passed():
        ex.verdict(
            "passed",
            "six seeds reach %s alive over all 40 cells with nothing moving, "
            "and every organism sits on a local max or min of the ring"
            % "/".join(str(r["alive"]) for r in rows),
        )
    else:
        failed = [t for t in CONTROL_TESTS
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: %s" % ", ".join(failed))

    path = ex.save()
    print(path)
    for r in rows:
        print("seed %-3d alive=%3d occupied=%2d doubled=%2d moving=%2d "
              "rich=%2d poor=%2d unclass=%d poor_overfull=%d"
              % (r["seed"], r["alive"], r["occupied"], r["doubled"], r["moved"],
                 r["on_max"], r["on_min"], r["neither"], r["poor_overfull"]))
    print("uniform n=40 alive=%d doubled=%d" % (a40, d40))


if __name__ == "__main__":
    main()
