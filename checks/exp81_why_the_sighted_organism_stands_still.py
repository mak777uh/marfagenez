"""EXP-81: why does a sighted organism on a poor cell stand still?

EXP-80 ran four arms on a four-cell alternating ring with one organism and got
**the same ten energies in every arm**:

    1.3250 1.6500 1.9750 ... 4.2500

and `moves = 0` in all four, including the two arms with `move_cost` 0.00 and
0.05 where the move is free or nearly free. The arithmetic says the organism
SHOULD move:

    cell 0 = rich 2.4, cell 1 = poor 1.6, cell 2 = rich 2.4, cell 3 = poor 1.6

An organism on a poor cell sees `here = 1.6`, `left = 2.4`, `right = 2.4`, and
`best = 2.4 > here`, so `direction` must be -1 or +1. It moved nowhere.

EXP-79 said the same from a unit test and blamed the cap. EXP-80 removed the
cap from the picture -- the arm never reaches 10.0 -- and the move is still
absent. So the cap was not the cause. The question stands.

## What the code says, and what it does not

`Life::advance` (`core/src/life.rs:441`) reads:

    if direction != 0 && r.organism.spend(r.move_cost) { ... r.cell = nc }

`Organism::spend` (`core/src/organism.rs:136-145`) is:

    if !amount.is_finite() || amount < 0.0 { return false }
    if self.energy < amount { return false }
    self.energy -= amount;
    true

With `move_cost = 0.0` and energy 1.325, `spend(0.0)` must return true. So if
`direction` were nonzero the cell would change. `moves = 0` therefore means
`direction == 0` -- the organism decided to stay.

The only way `Sighted` returns 0 is `best <= here`. With `here = 1.6` and both
neighbours at 2.4 that cannot happen -- **unless `here` is not 1.6**.

## The candidate that fits every reading

`--layout even` places organism `i` at cell `i % cells`. With `--n 1` that is
cell 0 -- a **rich** cell (2.4). On a rich cell: `here = 2.4`, `left` is
outside the field (`NEG_INFINITY`), `right = 1.6`, so `best = 2.4 = here` and
`Sighted` correctly returns 0. The organism is standing on the best cell of
the ring and has no reason to move. Nothing is broken; the arm was aimed at
the wrong cell.

EXP-79 was aimed at a poor cell by hand (`move_to`) and its C arm passed the
assertion that the cell changed -- so the move DOES happen from a poor cell.
The two readings disagree only because they start on different cells, and the
trace arm never said which cell it started on.

## The arms

  A. `--n 1 --layout even` (cell 0, rich) on a 4-cell alternating ring:
     starting cell and `moves` over 10 steps. Prediction: cell 0, moves 0.
  B. `--n 2 --layout even` (cells 0 and 1: one rich, one poor): the poor
     organism at cell 1 must move to a rich cell. Prediction: cell 1 -> 0 or 2,
     `moves > 0`.
  C. `--n 4 --layout even` (all four cells occupied): nobody has anywhere
     better to go -- every cell is occupied by someone, but `Sighted` does not
     see organisms, only levels, so the two poor organisms must still move.
     Prediction: `moves > 0`.
  D. `--n 1 --layout even` with `--field uniform` (all cells 1.6): `best ==
     here` everywhere, so the organism must never move. Prediction: moves 0.

The specific test is the pair (A, B): same field, same policy, same cost, and
the only difference is which cell the organism starts on. If A stays and B
moves, the starting cell decides, and every arm in this project that used
`--layout even` with one organism was standing on a rich cell and could not
have measured movement.

## Controls

  fires:    B must move at least once. If it does not, `Sighted` cannot move
            at all and the disagreement is real.
  silent:   D must never move. A uniform field gives no reason to move; if it
            does, `Sighted` is moving for a reason other than the level.
  specific: A must stay and B must move -- the difference is the starting cell
            and nothing else.
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
STEPS = 10
SEED = 1


def run(label, n, field, rich, poor, move_cost=0.0):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "sighted", "--read-budget", "3",
        "--steps", str(STEPS), "--every", "1",
        "--seed", str(SEED),
        "--n", str(n), "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", str(move_cost),
        "--energy", str(START),
        "--field", field, "--rich", str(rich), "--poor", str(poor),
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
    first = frames[0]["samples"]
    starts = [s["cell"] for s in first]
    ends = [s["cell"] for s in frames[-1]["samples"]]
    paths = [[s["cell"] for s in fr["samples"]] for fr in frames]
    moves = 0
    for a, b in zip(paths, paths[1:]):
        moves += sum(1 for x, y in zip(a, b) if x != y)
    return {
        "hash": digest,
        "label": label,
        "n": n,
        "field": field,
        "starts": starts,
        "ends": ends,
        "paths": paths,
        "moves": moves,
        "moves_series": [moves],
        "energies_end": [s["energy"] for s in frames[-1]["samples"]],
    }


def main():
    exp = Experiment(
        experiment_id="EXP-81",
        question="A sighted organism on a poor cell must move, and in EXP-80 it "
                 "did not. Is the starting cell the whole story?",
        arithmetic={
            "cells": CELLS,
            "rich": RICH,
            "poor": POOR,
            "levels": [RICH, POOR, RICH, POOR],
            "even_layout_placement": "organism i -> cell i % cells",
            "n1_start": 0,
            "n1_start_level": RICH,
            "n1_left": "outside the field -> NEG_INFINITY",
            "n1_right": POOR,
            "n1_best": RICH,
            "n1_decision": "best == here -> 0 (stay)",
            "n2_starts": [0, 1],
            "n2_poor_start": 1,
            "n2_poor_here": POOR,
            "n2_poor_neighbours": [RICH, RICH],
            "n2_poor_decision": "best 2.4 > here 1.6 -> +-1 (move)",
            "uniform_decision": "best == here everywhere -> 0 (stay)",
        },
        arms={
            "A": "n=1 even (cell 0, rich), alternating 2.4/1.6",
            "B": "n=2 even (cells 0 rich, 1 poor), alternating 2.4/1.6",
            "C": "n=4 even (all cells), alternating 2.4/1.6",
            "D": "n=1 even (cell 0), uniform 1.6",
        },
        seed=SEED,
        command="python3 checks/exp81_why_the_sighted_organism_stands_still.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "regrow": REGROW,
            "income": INCOME, "maintenance": MAINT, "damage_rate": DAMAGE,
            "repair_cost": REPAIR, "capacity": CAP, "start_energy": START,
            "steps": STEPS, "move_cost": 0.0, "read_budget": 3,
        },
    )

    rows = {}
    for key, n, field, rich, poor in (
        ("A", 1, "alternating", RICH, POOR),
        ("B", 2, "alternating", RICH, POOR),
        ("C", 4, "alternating", RICH, POOR),
        ("D", 1, "uniform", POOR, POOR),
    ):
        r = run(key, n, field, rich, poor)
        rows[key] = r
        print("  %s n=%d field=%-11s starts=%s ends=%s moves=%d"
              % (key, n, field, r["starts"], r["ends"], r["moves"]))
        for i, p in enumerate(r["paths"]):
            print("     org %d: %s" % (i, " ".join(str(c) for c in p)))

    for key, r in rows.items():
        exp.add_arm(
            key,
            "%s, n=%d, %s" % (r["label"], r["n"], r["field"]),
            {
                "n": r["n"],
                "field": r["field"],
                "starts": r["starts"],
                "ends": r["ends"],
                "moves": r["moves"],
                "energies_end": r["energies_end"],
            },
            trace_hash=r["hash"],
        )
        exp.add_series(key, list(range(STEPS + 1)), r["moves_series"]
                       if "moves_series" in r else [r["moves"]])

    a_still = rows["A"]["moves"] == 0
    b_moved = rows["B"]["moves"] > 0
    d_still = rows["D"]["moves"] == 0

    exp.control(
        "fires",
        b_moved,
        "B (n=2, one organism on the poor cell 1) moved %d times. It must move: "
        "its neighbours are both rich." % rows["B"]["moves"],
    )
    exp.control(
        "silent",
        d_still,
        "D (uniform 1.6) moved %d times. A uniform field gives no reason to "
        "move, so this must be zero." % rows["D"]["moves"],
    )
    exp.control(
        "specific",
        a_still and b_moved,
        "A (n=1, cell 0, rich) moved %d times and B (n=2, cell 1, poor) moved "
        "%d times, on the same field with the same policy and the same cost. "
        "The only difference is the starting cell."
        % (rows["A"]["moves"], rows["B"]["moves"]),
    )

    if a_still and b_moved and d_still:
        exp.verdict(
            "passed",
            "the starting cell is the whole story. `--layout even` puts "
            "organism 0 on cell 0, which is RICH on an alternating ring, so a "
            "one-organism arm starts on the best cell and `Sighted` correctly "
            "stays. With two organisms the one on the poor cell 1 moves %d "
            "times while the one on cell 0 stays. EXP-80's four identical arms "
            "were not a bug and not the cap: they were four arms standing on "
            "the richest cell of the ring." % rows["B"]["moves"],
        )
    elif not b_moved:
        exp.verdict(
            "failed",
            "B did not move either, so `Sighted` does not move even from a poor "
            "cell with two rich neighbours. The disagreement with EXP-79's "
            "passing C arm is then real and unresolved."
        )
    else:
        exp.verdict(
            "failed",
            "A moved %d times and B moved %d times. The starting cell does not "
            "separate the arms, so something else decides."
            % (rows["A"]["moves"], rows["B"]["moves"]),
        )

    exp.limitation(
        "Ten steps on a four-cell ring with one to four organisms. The field "
        "regrows toward its own ceiling every step, so a rich cell refills and "
        "the geometry does not change; a longer run would let the poor cells "
        "drift and the paths would not be comparable."
    )
    exp.limitation(
        "This says where the organism starts and whether it moves. It does not "
        "say the move is optimal: `Sighted` sees one cell each way and cannot "
        "know that the cell behind it is also rich."
    )
    exp.limitation(
        "`--layout even` is the only placement used here. The random spawner "
        "would spread the starts and the pair (A, B) would not be a controlled "
        "comparison."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
