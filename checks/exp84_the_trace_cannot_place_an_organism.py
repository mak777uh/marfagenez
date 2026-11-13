"""EXP-84: the trace cannot place an organism, so the arm was never run.

EXP-83 predicted that a `stay` organism on the POOR cell 1 of a four-cell
alternating ring would leave that cell at `1.6 - 1.0 = 0.6`, which regrows to
`0.6 + 0.8 * 1.0 = 1.4`. The measured frame showed the poor cell at **1.6** --
untouched -- while the rich cell 0 showed 2.2, eaten and regrown.

The reason is in the arm, not in the model: `--layout even` puts organism 0 on
cell 0 (`spawn_even`, `core/src/life.rs:178`), and `trace` has no flag to put
it anywhere else. EXP-83's D arm passed `--layout even` and therefore ran the
same run as A. The two arms produced the same frame because they WERE the same
run. The prediction was right about the model and wrong about the instrument.

This is the third time in three experiments that the arm did not do what its
docstring said: EXP-80's four arms were one arm, EXP-81's arms dropped their
field flags, EXP-83's D arm could not move the organism. The common cause is
that `trace` exposes the field and the spawner but not the placement, so a
question about a particular cell cannot be asked from the command line at all.

## The arms

  A. `--layout even --n 1`: organism 0 on cell 0. Frame 0 must show cell 0
     eaten (2.2 at regrow 0.8) and cell 1 untouched (1.6).
  B. `--layout even --n 2`: organisms on cells 0 and 1. Frame 0 must show BOTH
     cell 0 at 2.2 and cell 1 at 1.4 -- the poor cell eaten and regrown. This is
     the arm EXP-83's D tried to be.
  C. `--layout even --n 4`: all four cells eaten. Frame 0 must show
     `[2.2, 1.4, 2.2, 1.4]`.
  D. `--layout even --n 1` with `--steps 2`: if the frame is post-regrowth, the
     second step eats the same cell again from 2.2, leaving 1.2, regrown to
     `1.2 + 0.8 * 1.2 = 2.16`. Frame 1 must show 2.16, not 2.2 -- the cell
     settles below its ceiling because the meal and the regrowth do not
     balance at `regrow < 1` when the organism eats more than the regrowth
     restores.

The specific test is (A, B): the same field, the same regrow, and the only
difference is one more organism on the poor cell. If B shows the poor cell
eaten and A does not, the placement is the whole difference and EXP-83's D arm
was simply the wrong arm.

## Controls

  fires:    B must show cell 1 at 1.4. If it does not, an organism on a poor
            cell does not eat it, which would contradict `take`.
  silent:   A must show cell 1 at exactly 1.6. An organism on cell 0 must not
            touch cell 1.
  specific: A and B must differ in cell 1 and agree in cell 0. The difference
            is one organism and nothing else.
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
RICH = 2.4
POOR = 1.6
REGROW = 0.8
INCOME = 1.0
MAINT = 0.6
DAMAGE = 0.05
REPAIR = 1.5
CAP = 10.0
START = 1.0
SEED = 1


def run(label, n, steps):
    trace_dir = os.path.join(CORE, "results", "stay")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "stay",
        "--steps", str(steps), "--every", "1",
        "--seed", str(SEED),
        "--n", str(n), "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0.0",
        "--energy", str(START),
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
    frames = data["frames"]
    return {
        "hash": digest,
        "label": label,
        "n": n,
        "steps": steps,
        "cells": [s["cell"] for s in frames[0]["samples"]],
        "frames": [[round(x, 9) for x in fr["field"]] for fr in frames],
        "taken": [[s["taken"] for s in fr["samples"]] for fr in frames],
    }


def main():
    arms = {
        "A": "n=1 even (cell 0), 1 step",
        "B": "n=2 even (cells 0 and 1), 1 step",
        "C": "n=4 even (all cells), 1 step",
        "D": "n=1 even (cell 0), 2 steps",
    }
    exp = Experiment(
        experiment_id="EXP-84",
        question="EXP-83's D arm could not place an organism on the poor cell. "
                 "Can the poor cell be eaten at all from the command line?",
        arithmetic={
            "built": [RICH, POOR, RICH, POOR],
            "income": INCOME,
            "regrow": REGROW,
            "rich_after_meal": RICH - INCOME,
            "rich_frame0": (RICH - INCOME) + (RICH - (RICH - INCOME)) * REGROW,
            "poor_after_meal": POOR - INCOME,
            "poor_frame0": (POOR - INCOME) + (POOR - (POOR - INCOME)) * REGROW,
            "untouched_poor": POOR,
            "step2_from_2.2": "2.2 - 1.0 = 1.2, then 1.2 + 0.8*(2.4-1.2) = 2.16",
            "note": "at regrow 0.8 an organism that eats income 1.0 from a rich "
                    "cell settles at 2.16, not 2.4: the meal removes more than "
                    "the regrowth restores",
        },
        arms=arms,
        seed=SEED,
        command="python3 checks/exp84_the_trace_cannot_place_an_organism.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "income": INCOME, "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "start_energy": START,
        },
    )

    rows = {}
    for key, n, steps in (("A", 1, 1), ("B", 2, 1), ("C", 4, 1), ("D", 1, 2)):
        r = run(key, n, steps)
        rows[key] = r
        print("  %s n=%d steps=%d cells=%s" % (key, n, steps, r["cells"]))
        for i, fr in enumerate(r["frames"]):
            print("     frame %d: %s  taken %s" % (i, fr, r["taken"][i]))

    for key, r in rows.items():
        exp.add_arm(
            key,
            arms[key],
            {
                "n": r["n"],
                "steps": r["steps"],
                "cells": r["cells"],
                "frames": r["frames"],
                "taken": r["taken"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, list(range(len(r["frames"]))),
                       [fr[1] for fr in r["frames"]])

    a = rows["A"]["frames"][0]
    b = rows["B"]["frames"][0]
    c = rows["C"]["frames"][0]
    d1 = rows["D"]["frames"][1]

    exp.control(
        "fires",
        abs(b[1] - 1.4) < 1e-9,
        "B (organisms on cells 0 and 1) shows the poor cell 1 at %.6f; an "
        "organism standing on it must eat it down to 0.6 and regrow it to 1.4."
        % b[1],
    )
    exp.control(
        "silent",
        abs(a[1] - POOR) < 1e-9,
        "A (organism on cell 0 only) shows the poor cell 1 at %.6f, exactly "
        "untouched. Nothing on cell 0 may reach cell 1." % a[1],
    )
    exp.control(
        "specific",
        abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) > 1e-9,
        "A and B agree on cell 0 (%.6f vs %.6f) and differ on cell 1 (%.6f vs "
        "%.6f). The only difference between the arms is one organism on the "
        "poor cell." % (a[0], b[0], a[1], b[1]),
    )

    if abs(b[1] - 1.4) < 1e-9 and abs(a[1] - POOR) < 1e-9 and abs(a[0] - b[0]) < 1e-9:
        exp.verdict(
            "passed",
            "the poor cell can be eaten, but only by an organism standing on it, "
            "and the command line can only put organisms on cells 0..n-1. B shows "
            "cell 1 at %.3f after one step and A shows it at %.3f; the difference "
            "is one organism. EXP-83's D arm passed `--layout even` with `--n 1`, "
            "so it ran the same run as A and its prediction about the poor cell "
            "could not have been tested. The frame is post-regrowth: frame 1 of D "
            "shows cell 0 at %.4f, which is the second meal and the second "
            "regrowth, not the built 2.4." % (b[1], a[1], d1[0]),
        )
    else:
        exp.verdict(
            "failed",
            "the poor cell does not behave as the arithmetic says: with an "
            "organism on it, cell 1 reads %.6f (predicted 1.400); with an "
            "organism only on cell 0 it reads %.6f (predicted %.6f)."
            % (b[1], a[1], POOR),
        )

    exp.limitation(
        "Four cells, one and two steps. It shows the placement and the first "
        "meal; it does not follow the field to its settled level, which EXP-66 "
        "measured at 1.35 / 2.15 for a full ring."
    )
    exp.limitation(
        "`--layout even` is the only placement the command line offers, so a "
        "question about an arbitrary cell cannot be asked from a trace at all. "
        "The unit-test path (`Life::move_to`) can, and EXP-79 used it."
    )
    exp.limitation(
        "This does not say the settled level is wrong. It says the first frame "
        "is a post-meal post-regrowth reading, so the settled level 2.16 is the "
        "level at which the meal and the regrowth balance, not the ceiling."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
