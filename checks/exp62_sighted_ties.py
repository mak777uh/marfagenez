"""EXP-62: is the capacity set by the sighted rule being deterministic?

Hypothesis. `Policy::Sighted` moves only when a neighbour is strictly richer
than the current cell, and a tie means stay (core/src/life.rs:404-441). In a
uniform field every cell is equal, so no sighted organism ever moves. A cell
that happens to hold two organisms therefore stays doubled forever, and its
second seat keeps losing 0.06 per step -- except that EXP-61 measured the seat
ROTATING (45 different organisms over 20 frames). Rotation cannot come from
the sighted rule, which never moves on a tie. It must come from deaths: the
second occupant dies, the seat frees, and a neighbour that was blocked moves in.

If that is the mechanism, the capacity should be set by how many cells can be
kept at one occupant, and it should NOT change when the field is made
non-uniform in a way that gives sighted organisms somewhere to go.

Arms:
  uniform      M=2 everywhere (the EXP-61 field)
  gradient     a slope, so sighted organisms have a reason to move
  alternating  rich/poor, the field where sighted measured 80 in EXP-09

Prediction if the hypothesis holds: uniform gives ~46, and the non-uniform
fields give a different number because movement is possible there.
Prediction if the hypothesis is wrong: all three give the same number.

Controls:
  fires     -- the uniform arm reproduces EXP-61: crowd 2 and cell value 1.6
  silent    -- n=40 on 40 cells gives crowd 1 and 40 alive (no doubling to
               explain, so the mechanism must be absent)
  specific  -- the arms differ from each other; if they all agree the
               experiment cannot see the mechanism at all
"""

import json
import os
import subprocess

from experiment import Experiment
from result import CONTROL_TESTS, VERDICTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

STEPS = 20000
N = 80
CELLS = 40


def run(field, n=N, cells=CELLS, steps=STEPS, seed=7):
    os.makedirs(os.path.join(ROOT, "results", "EXP-62"), exist_ok=True)
    # A non-uniform field needs two different levels: the trace refuses
    # --field gradient with --rich == --poor, because that is a flat field and
    # the uneven arm would measure nothing. The two levels average to 2.0, the
    # same mean as the uniform arm, so the arms differ in unevenness only.
    rich, poor = ("2.0", "2.0") if field == "uniform" else ("2.4", "1.6")
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(steps // 20), "--seed", str(seed), "--n", str(n),
           "--cells", str(cells), "--rich", rich, "--poor", poor,
           "--income", "1.0", "--maintenance", "0.6",
           "--damage-rate", "0.02", "--repair-cost", "0.5",
           "--move-cost", "0.05", "--energy", "10.0",
           "--field", field, "--read-budget", "3",
           "--memory-life", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit("trace failed for %s:\n%s" % (field, out.stderr))
    written, trace_hash = None, ""
    for line in out.stdout.splitlines():
        if line.startswith("written:"):
            written = line.split(":", 1)[1].strip()
        elif line.startswith("hash:"):
            trace_hash = line.split(":", 1)[1].strip()
    d = json.load(open(os.path.join(ROOT, written)))
    d["_hash"] = trace_hash
    return d, written


def last_frame(trace):
    return trace["frames"][-1]


def crowding(frame):
    occ = {}
    for s in frame["samples"]:
        if s["alive"]:
            occ[s["cell"]] = occ.get(s["cell"], 0) + 1
    doubled = sum(1 for v in occ.values() if v >= 2)
    return doubled, occ


def alive_in(frame):
    return sum(1 for s in frame["samples"] if s["alive"])


def main():
    ex = Experiment(
        experiment_id="EXP-62",
        question=(
            "Is the capacity set by the sighted rule being deterministic? "
            "Sighted moves only toward a strictly richer neighbour, so on a "
            "uniform field nothing moves and a doubled cell never undoubles."
        ),
        arithmetic={
            "second_seat_income": "1.6 - 1.0 = 0.60",
            "second_seat_cost": "0.6 + 0.05 + 0.02*0.5 = 0.66",
            "second_seat_net": "0.60 - 0.66 = -0.06 per step",
            "steps_to_die": "10.0 / 0.06 = 166",
            "single_cell_equilibrium": "M + income - income/r = 2 + 1 - 1.25 = 1.75",
            "doubled_cell_equilibrium": "M*r = 2*0.8 = 1.6",
        },
        arms={
            "uniform": "uniform M=2",
            "gradient": "slope",
            "alternating": "rich/poor",
            "uniform-n40": "uniform, n=40",
        },
        seed=7,
        command="trace --policy sighted --steps 20000 --n 80 --cells 40 "
                "--capacity 2 --field {uniform,gradient,alternating}",
    )

    data = {}
    for field in ("uniform", "gradient", "alternating"):
        trace, path = run(field)
        frame = last_frame(trace)
        alive = alive_in(frame)
        doubled, occ = crowding(frame)
        vals = list(frame["field"])
        data[field] = dict(
            alive=alive, doubled=doubled,
            spread=max(vals) - min(vals),
            lo=min(vals), hi=max(vals),
            trace=path,
        )
        ex.add_arm(
            field,
            "%s field" % field,
            {
                "alive": alive,
                "doubled_cells": doubled,
                "mean_per_cell": round(alive / CELLS, 4),
                "field_lo": round(min(vals), 4),
                "field_hi": round(max(vals), 4),
            },
            trace_hash=trace.get("_hash"),
        )

    # n = 40: no doubling is possible on 40 cells with 40 organisms only if
    # each finds its own cell. This is the silent control.
    trace40, path40 = run("uniform", n=40)
    f40 = last_frame(trace40)
    alive40 = alive_in(f40)
    doubled40, _ = crowding(f40)
    ex.add_arm("uniform-n40", "uniform, n=40", {
        "alive": alive40, "doubled_cells": doubled40,
    }, trace_hash=trace40.get("_hash"))

    # Controls.
    u = data["uniform"]
    # A doubled cell is the POORER one: it is emptied every round and settles
    # at M*r = 1.6, while a single cell keeps a reserve and settles at 1.75.
    # So the doubled-cell equilibrium is the field MINIMUM, not the maximum.
    ex.control(
        "fires",
        u["doubled"] > 0 and abs(u["lo"] - 1.6) < 0.05,
        "uniform: %d doubled cells, field lo %.4f (arithmetic M*r = 1.6), "
        "hi %.4f (single-cell c* = 1.75)" % (u["doubled"], u["lo"], u["hi"]),
    )
    ex.control(
        "silent",
        alive40 == 40 and doubled40 == 0,
        "n=40 on 40 cells: %d alive, %d doubled" % (alive40, doubled40),
    )
    distinct = len({data[f]["alive"] for f in ("uniform", "gradient", "alternating")})
    ex.control(
        "specific",
        distinct > 1,
        "alive counts: uniform %d, gradient %d, alternating %d"
        % (u["alive"], data["gradient"]["alive"], data["alternating"]["alive"]),
    )

    ex.limitation(
        "Rotation of the second seat is inferred, not observed: the trace "
        "records occupancy per frame, and EXP-61 counted 45 different "
        "organisms over the last 20 frames. This experiment does not repeat "
        "that count."
    )
    ex.limitation(
        "The three fields differ in more than uniformity -- gradient and "
        "alternating also change the mean level, so a difference in alive "
        "counts is not attributable to movement alone."
    )

    ok = ex.controls_passed()
    if ok:
        ex.verdict(
            "passed",
            "uniform %d alive with %d doubled cells at 1.6; n=40 gives %d "
            "alive and no doubling; fields differ (%d distinct alive counts)"
            % (u["alive"], u["doubled"], alive40, distinct),
        )
    else:
        failed = [t for t in CONTROL_TESTS
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: %s" % ", ".join(failed))

    path = ex.save()
    print(path)
    for f in ("uniform", "gradient", "alternating"):
        d = data[f]
        print("%-12s alive=%3d doubled=%2d lo=%.4f hi=%.4f spread=%.4f"
              % (f, d["alive"], d["doubled"], d["lo"], d["hi"], d["spread"]))
    print("uniform-n40  alive=%3d doubled=%2d" % (alive40, doubled40))


if __name__ == "__main__":
    main()
