"""EXP-82: the field is not the field.

EXP-81 ran four arms on a four-cell ring and got:

    A  n=1  alternating 2.4/1.6   starts [0]        ends [0]        moves 0
    B  n=2  alternating 2.4/1.6   starts [0, 2]     ends [0, 2]     moves 0
    C  n=4  alternating 2.4/1.6   starts [0,2,1,3]  ends [0,2,1,3]  moves 0
    D  n=1  uniform 1.6           starts [0]        ends [3]        moves 9

Two things in that table cannot both be true of the code as read:

  1. **B starts on cells 0 and 2, not 0 and 1.** `spawn_even` is
     `let cell = i % cells;` (`core/src/life.rs:178`), so organism 1 must be on
     cell 1. It is on cell 2. The spawner is not the spawner that was read.
  2. **D moves 9 times on a UNIFORM field.** `Sighted` returns 0 whenever
     `best <= here` (`core/src/life.rs:431-435`), and on a uniform field every
     level is equal, so it must return 0 every step. It walked
     0 1 2 3 2 1 0 1 2 3 -- a back-and-forth with no gradient to follow.

So the field the organism stands on is not the field the run was asked for.
The candidate that explains both: `--layout even` is not being taken, the
random spawner is used, and the `--field` flag is not being taken either, so
the field is whatever the default is. A random spawn on four cells with two
organisms gives distinct cells (0 and 2 here, not 0 and 1), and a field that
is not uniform gives a reason to move.

The trace prints the field; nobody read it. That is the lesson, and it is the
same lesson as `docs/FINDING-the-tool-showed-inconsistent-data.md`: read the
instrument's own report of its inputs before reading its output.

## The arms

  A. `--field alternating --rich 2.4 --poor 1.6 --layout even --n 2`, and the
     run's own echo of field levels and start cells is captured.
  B. `--field uniform --rich 1.6 --poor 1.6 --n 1`, same capture.
  C. `--field alternating` with `--rich` equal to `--poor` (2.4/2.4): if the
     trace refuses this, the flag is being read; if it runs, the refusal is
     not reached.
  D. No `--field` flag at all, everything else as A.

Prediction, if the flags are read: A echoes `[2.4, 1.6, 2.4, 1.6]` and starts
`[0, 1]`; B echoes `[1.6, 1.6, 1.6, 1.6]`; C is refused; D echoes the default.

## Controls

  fires:    A's echoed field must be `[2.4, 1.6, 2.4, 1.6]`. If it is not, the
            `--field` flag is not reaching the field and every arm built on it
            measured the default.
  silent:   B's echoed field must be `[1.6, 1.6, 1.6, 1.6]` and B must not
            move. A uniform field is the case with nothing to see.
  specific: A's start cells must be `[0, 1]`, which is what `spawn_even` says,
            and not `[0, 2]`, which is what EXP-81 measured.
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

CELLS = 4
STEPS = 10
SEED = 1
INCOME = 1.0
MAINT = 0.6
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
START = 1.0
REGROW = 0.8


def run(label, extra, n):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "sighted", "--read-budget", "3",
        "--steps", str(STEPS), "--every", "1",
        "--seed", str(SEED),
        "--n", str(n), "--cells", str(CELLS),
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0.0",
        "--energy", str(START),
        "--regrow", str(REGROW), "--memory-life", "100000",
    ] + extra
    out = subprocess.run(cmd, cwd=CORE, capture_output=True, text=True, timeout=3600)
    digest = None
    for line in out.stdout.splitlines():
        if line.startswith("hash:"):
            digest = line.split(":", 1)[1].strip()
    after = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir)
             if f not in before]
    data = None
    if after:
        path = max(after, key=os.path.getmtime)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    return {
        "hash": digest,
        "label": label,
        "returncode": out.returncode,
        "stdout_tail": out.stdout[-1500:],
        "stderr_tail": out.stderr[-800:],
        "data": data,
    }


def echo(r):
    """What the run itself says its field and starts were."""
    d = r["data"]
    if d is None:
        return None, None, None
    frames = d["frames"]
    first = frames[0]
    levels = first.get("field") or first.get("levels") or first.get("cells")
    starts = [s["cell"] for s in first["samples"]]
    ends = [s["cell"] for s in frames[-1]["samples"]]
    return levels, starts, ends


def main():
    exp = Experiment(
        experiment_id="EXP-82",
        question="EXP-81's runs did not stand on the field they were asked for. "
                 "Are `--field` and `--layout` reaching the field and the "
                 "spawner at all?",
        arithmetic={
            "cells": CELLS,
            "spawn_even_rule": "cell = i % cells -> starts [0, 1] for n=2",
            "exp81_measured_starts_n2": [0, 2],
            "sighted_stay_rule": "returns 0 whenever best <= here",
            "uniform_field_consequence": "best == here everywhere -> 0 moves",
            "exp81_measured_uniform_moves": 9,
            "contradiction": "both of the above cannot hold if the flags reach "
                             "the field; one of the two flags is being dropped",
        },
        arms={
            "A": "alternating 2.4/1.6, layout even, n=2",
            "B": "uniform 1.6, n=1",
            "C": "alternating with rich == poor (2.4/2.4), n=1",
            "D": "no --field flag at all, n=2",
        },
        seed=SEED,
        command="python3 checks/exp82_the_field_is_not_the_field.py",
        parameters={
            "cells": CELLS, "steps": STEPS, "income": INCOME,
            "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "start_energy": START,
            "regrow": REGROW, "read_budget": 3,
        },
    )

    arms = {
        "A": ("alternating", ["--field", "alternating", "--rich", "2.4",
                              "--poor", "1.6", "--layout", "even"], 2),
        "B": ("uniform", ["--field", "uniform", "--rich", "1.6",
                          "--poor", "1.6"], 1),
        "C": ("rich==poor", ["--field", "alternating", "--rich", "2.4",
                             "--poor", "2.4", "--layout", "even"], 1),
        "D": ("no flag", ["--layout", "even"], 2),
    }

    rows = {}
    for key, (label, extra, n) in arms.items():
        r = run(key, extra, n)
        levels, starts, ends = echo(r)
        r["levels"] = levels
        r["starts"] = starts
        r["ends"] = ends
        rows[key] = r
        print("  %s %-12s rc=%d levels=%s starts=%s ends=%s"
              % (key, label, r["returncode"], levels, starts, ends))
        if r["returncode"] != 0:
            print("     stderr: %s" % r["stderr_tail"].strip().replace("\n", " | ")[:300])

    for key, r in rows.items():
        exp.add_arm(
            key,
            "%s" % arms[key][0],
            {
                "returncode": r["returncode"],
                "levels": r["levels"],
                "starts": r["starts"],
                "ends": r["ends"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, [0], [r["returncode"]])

    a_levels = rows["A"]["levels"]
    a_ok = a_levels is not None and [round(x, 6) for x in a_levels] == [2.4, 1.6, 2.4, 1.6]
    b_levels = rows["B"]["levels"]
    b_ok = b_levels is not None and all(abs(x - 1.6) < 1e-9 for x in b_levels)
    b_still = rows["B"]["starts"] == rows["B"]["ends"]
    a_starts_ok = rows["A"]["starts"] == [0, 1]

    exp.control(
        "fires",
        a_ok,
        "A echoed field levels %s; it must be [2.4, 1.6, 2.4, 1.6]. If it is "
        "not, `--field` is not reaching the field." % (a_levels,),
    )
    exp.control(
        "silent",
        b_ok and b_still,
        "B echoed levels %s and moved from %s to %s. On a uniform field there "
        "is nothing to see and nothing to move toward."
        % (b_levels, rows["B"]["starts"], rows["B"]["ends"]),
    )
    exp.control(
        "specific",
        a_starts_ok,
        "A started on %s; `spawn_even` says [0, 1]. EXP-81 measured [0, 2]."
        % (rows["A"]["starts"],),
    )

    if a_ok and b_ok and b_still and a_starts_ok:
        exp.verdict(
            "passed",
            "the flags do reach the field and the spawner, and EXP-81's two "
            "contradictions do not reproduce. A echoed [2.4, 1.6, 2.4, 1.6] and "
            "started on [0, 1]; B echoed a uniform 1.6 and did not move. "
            "EXP-81's runs therefore did not carry the arguments they were "
            "written to carry -- the arms were built by a helper whose "
            "signature dropped the field flags, so the run fell back to the "
            "default field. The output was read; the input was not."
        )
    else:
        bad = []
        if not a_ok:
            bad.append("A's field is %s, not [2.4, 1.6, 2.4, 1.6]" % (a_levels,))
        if not b_ok:
            bad.append("B's field is %s, not uniform 1.6" % (b_levels,))
        if not b_still:
            bad.append("B moved from %s to %s on a uniform field"
                       % (rows["B"]["starts"], rows["B"]["ends"]))
        if not a_starts_ok:
            bad.append("A started on %s, not [0, 1]" % (rows["A"]["starts"],))
        exp.verdict(
            "failed",
            "the run does not stand on the field it was asked for: "
            + "; ".join(bad) + "."
        )

    exp.limitation(
        "Four cells and ten steps. This checks that the arguments reach the "
        "field and the spawner; it does not check that the field evolves as "
        "the model says over a long run."
    )
    exp.limitation(
        "The check reads the trace's own echo of its field. If the trace echoed "
        "the arguments instead of the field, this would pass while the field "
        "was wrong -- the same failure one level down. The echo is the level "
        "that could be checked here."
    )
    exp.limitation(
        "It does not say which of EXP-81's arms were affected. Every arm built "
        "by the same helper is suspect, and EXP-80's four identical arms are "
        "the obvious next suspect."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
