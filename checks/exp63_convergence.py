"""EXP-63: does the population converge, and to what?

EXP-62 measured 50 alive on a uniform field at 20 000 steps, while EXP-61
measured 46 at 200 000 steps on the same field. Either the population is still
drifting, or the two runs differ in a parameter. This experiment runs the same
arm at 20k, 100k and 500k steps and reads the alive count at several points.

The question matters because every capacity claim in this project is a number
read off one final frame. If the population has not settled, the number is a
snapshot, not a capacity.

Arms: uniform at 20k / 100k / 500k steps, same seed, same parameters.

Controls:
  fires     -- the field minimum is still 1.6 (doubled cells exist and are
               emptied), so the run is the same regime as EXP-61
  silent    -- n=40 at 500k gives 40 alive and no doubling, as at 20k; the
               no-doubling case must not drift
  specific  -- the alive count at 500k differs from the count at 20k; if they
               agree the population already settled by 20k and the EXP-61 /
               EXP-62 difference is a parameter difference, not drift
"""

import json
import os
import subprocess

from experiment import Experiment
from result import CONTROL_TESTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE = os.path.join(ROOT, "core", "target", "release", "trace")

CELLS = 40
SEED = 7
OUTDIR = os.path.join(ROOT, "results", "EXP-63")


def run(n, steps, every, seed=SEED):
    os.makedirs(OUTDIR, exist_ok=True)
    cmd = [TRACE, "--policy", "sighted", "--steps", str(steps),
           "--every", str(every), "--seed", str(seed), "--n", str(n),
           "--cells", str(CELLS), "--rich", "2.0", "--poor", "2.0",
           "--income", "1.0", "--maintenance", "0.6",
           "--damage-rate", "0.02", "--repair-cost", "0.5",
           "--move-cost", "0.05", "--energy", "10.0",
           "--field", "uniform", "--read-budget", "3",
           "--memory-life", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit("trace failed n=%d steps=%d:\n%s" % (n, steps, out.stderr))
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
    f = frame["field"]
    return alive, doubled, min(f), max(f)


def series(trace):
    return [census(fr)[0] for fr in trace["frames"]]


def main():
    ex = Experiment(
        experiment_id="EXP-63",
        question=(
            "Does the sighted population converge, and by which step? "
            "EXP-62 read 50 alive at 20k steps and EXP-61 read 46 at 200k on "
            "the same field. If the count is still falling at 500k, every "
            "capacity number in this project is a snapshot, not a capacity."
        ),
        arithmetic={
            "single_cell_equilibrium": "M + income - income/r = 1.75",
            "doubled_cell_equilibrium": "M*r = 1.6",
            "second_seat_net": "0.60 - 0.66 = -0.06 per step",
            "steps_to_die_from_10": "10.0 / 0.06 = 166",
            "food_ceiling_per_round": "cells * M * r = 40 * 1.6 = 64 units",
            "organisms_that_can_eat": "64 / need = 64 / 0.6 = 106 (upper bound)",
        },
        arms={
            "u20k": "uniform, 20k steps",
            "u100k": "uniform, 100k steps",
            "u500k": "uniform, 500k steps",
            "u500k-n40": "uniform, n=40, 500k steps",
        },
        seed=SEED,
        command="trace --policy sighted --field uniform --cells 40 "
                "--steps {20000,100000,500000}",
    )

    runs = {}
    for key, steps in (("u20k", 20000), ("u100k", 100000), ("u500k", 500000)):
        tr = run(80, steps, max(1, steps // 20))
        alive, doubled, lo, hi = census(tr["frames"][-1])
        s = series(tr)
        runs[key] = dict(alive=alive, doubled=doubled, lo=lo, hi=hi,
                         series=s, hash=tr.get("_hash"))
        ex.add_arm(key, "%d steps" % steps, {
            "alive": alive,
            "doubled_cells": doubled,
            "field_lo": round(lo, 4),
            "field_hi": round(hi, 4),
            "alive_at_quarter": s[len(s) // 4],
            "alive_at_half": s[len(s) // 2],
        }, trace_hash=tr.get("_hash"))

    tr40 = run(40, 500000, 25000)
    a40, d40, lo40, hi40 = census(tr40["frames"][-1])
    ex.add_arm("u500k-n40", "n=40, 500k steps", {
        "alive": a40, "doubled_cells": d40,
        "field_lo": round(lo40, 4), "field_hi": round(hi40, 4),
    }, trace_hash=tr40.get("_hash"))

    u5 = runs["u500k"]
    ex.control(
        "fires",
        u5["doubled"] > 0 and abs(u5["lo"] - 1.6) < 0.05,
        "500k: %d doubled cells, field lo %.4f (M*r = 1.6)"
        % (u5["doubled"], u5["lo"]),
    )
    ex.control(
        "silent",
        a40 == 40 and d40 == 0,
        "n=40 at 500k: %d alive, %d doubled" % (a40, d40),
    )
    ex.control(
        "specific",
        runs["u20k"]["alive"] != u5["alive"],
        "alive at 20k %d vs 500k %d (equal means the population settled "
        "before 20k and the EXP-61/62 gap is a parameter difference)"
        % (runs["u20k"]["alive"], u5["alive"]),
    )

    ex.limitation(
        "One seed. A drifting population under one seed does not prove the "
        "drift is systematic; it only shows that 20k steps is not enough here."
    )
    ex.limitation(
        "The series is sampled 20 times, so a population that oscillates "
        "between samples would look constant."
    )

    if ex.controls_passed():
        ex.verdict(
            "passed",
            "alive 20k %d, 100k %d, 500k %d; n=40 at 500k gives %d"
            % (runs["u20k"]["alive"], runs["u100k"]["alive"], u5["alive"], a40),
        )
    else:
        failed = [t for t in CONTROL_TESTS
                  if not ex._result["controls"].get(t, {}).get("passed", False)]
        ex.verdict("failed", "controls failed: %s" % ", ".join(failed))

    path = ex.save()
    print(path)
    for k in ("u20k", "u100k", "u500k"):
        r = runs[k]
        print("%-6s alive=%3d doubled=%2d lo=%.4f hi=%.4f series=%s"
              % (k, r["alive"], r["doubled"], r["lo"], r["hi"], r["series"]))
    print("n40    alive=%3d doubled=%2d" % (a40, d40))


if __name__ == "__main__":
    main()
