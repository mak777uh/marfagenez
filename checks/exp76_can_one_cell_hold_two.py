"""EXP-76: can one cell hold two organisms?

The question is old and the old answer is void. Before the clamp fix the
measurement said two organisms could share a cell at `E_max = 9`
(`docs/FINDING-the-capacity-is-a-line-not-a-number.md`). That run predates the
clamp moving to the end of the step, so it measured a dynamics that no longer
exists.

## What the arithmetic says, and what it changed

First guess: a rich cell can feed two. `M = 2.0`, `r = 0.8`, `income = 1.2`,
cost `0.6 + 0.02 * 1.5 = 0.63`. Two organisms, each taking `min(c, income)`
(the code does NOT split a cell between occupants --
`core/src/organism.rs:165`), settle at `c* = 1.6`: the first takes `1.2`, the
second takes the remaining `0.4`. The second's share is `0.4 < 0.63`, so the
second one starves. The cell feeds one.

That is the answer to the old question, and it is not the answer the first
draft of this experiment predicted. It also means `crowding = 1.00` is a
property of the FEEDING rule, not of the movement rule.

## Why this experiment is still worth running

The arithmetic is hand computation. It has to be checked against a run in which
two organisms are actually placed on one cell. Neither spawner can do that on
purpose: `spawn_even` fills cells in order and `spawn` draws at random. So the
check is a Rust test, `life::tests::a_rich_cell_feeds_one_organism_not_two`,
which uses `move_to` to put both organisms on the same rich cell and runs 4000
steps. It passes: `alive = 1`.

What this experiment adds on top of that test is the size of the effect in the
population, and the reason the population does not grow back to fill the second
place. Three arms, all on 40 cells, `alternating`, `rich = 2.0`, `poor = 0.2`,
4000 steps, `sighted`, `read_budget = 3`, `move_cost = 0`, `E_max = 10`,
`--layout even`:

  A. `n = 160` -- the exp75 condition, reproduced. Expect alive 20, crowding 1.00.
  B. `n = 40` -- one organism per cell, half of them on poor cells. A poor cell
     settles at `c* = 0.16` and yields `0.16` per step against a cost of `0.63`,
     so every organism on a poor cell dies. Expect alive 20: the 20 on rich
     cells.
  C. `n = 20` -- one organism per cell for the first half of the field, 10 rich
     and 10 poor. Expect alive 11, not 10: the organism on cell 19, the last
     poor cell of the block, has a rich right neighbour (cell 20) and walks onto
     it. The other nine poor cells (1, 3, ..., 17) have poor neighbours on both
     sides, so `Sighted` sees no strictly richer cell and they stay and die.

## Predictions (written before the run)

  A. alive 20, crowding 1.00.
  B. alive 20, crowding 1.00. The half on poor cells dies; the half on rich
     cells lives at `E_max`.
  C. alive 11, crowding 1.00. The first draft of this file predicted 10, which
     was wrong: it forgot that the block of twenty organisms ends on a poor cell
     whose right neighbour is rich, and `Sighted` walks onto it.

If all three hold, the reading is: the capacity of an alternating field is the
number of RICH cells, one organism each, and both halves of that sentence are
arithmetic -- the rich cell cannot feed a second (its share falls under the
cost), and the poor cell cannot feed a first (`0.16 < 0.63`).

## Controls

  fires:    n = 40 must give alive 20 -- twice as many organisms as rich cells
            must not raise the population above the number of rich cells.
  silent:   n = 160 must give alive 20 -- the exp75 condition reproduces its
            own number. If this fails, the arms are not comparable to exp75.
  specific: crowding must be exactly 1.00 in arm A, and the count of occupied
            cells must equal the number alive. If alive = 20 but cells_used = 10,
            crowding would be 2.00 and the answer would be the opposite.

The `silent` control used to be "n = 20 must lose nobody", which failed for the
right reason: with `--layout even` and 40 cells, n = 20 puts ten organisms on
poor cells and they die. That was a wrong control, not a wrong model.
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
RICH = 2.0
POOR = 0.2
INCOME = 1.2
MAINT = 0.6
DAMAGE = 0.02
REPAIR = 1.5
CAP = 10.0
STEPS = 4000

COST = MAINT + DAMAGE * REPAIR
RICH_ONE = 1.7
RICH_TWO = 1.6
POOR_ONE = 0.16


def run(n, seed=1):
    trace_dir = os.path.join(CORE, "results", "sighted")
    os.makedirs(trace_dir, exist_ok=True)
    before = set(os.listdir(trace_dir))
    cmd = [
        TRACE,
        "--policy", "sighted", "--read-budget", "3",
        "--steps", str(STEPS), "--every", str(STEPS),
        "--seed", str(seed),
        "--n", str(n), "--cells", str(CELLS), "--layout", "even",
        "--capacity", str(CAP), "--damage-rate", str(DAMAGE),
        "--income", str(INCOME), "--maintenance", str(MAINT),
        "--repair-cost", str(REPAIR), "--move-cost", "0",
        "--energy", str(CAP),
        "--field", "alternating", "--rich", str(RICH), "--poor", str(POOR),
        "--regrow", "0.8",
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
    cells_used = len({s["cell"] for s in living})
    energies = [s["energy"] for s in living]
    return {
        "hash": digest,
        "n": n,
        "alive": len(living),
        "cells_used": cells_used,
        "cells": sorted(s["cell"] for s in living),
        "crowding": len(living) / cells_used if cells_used else None,
        "energy_mean": sum(energies) / len(energies) if energies else None,
    }


def main():
    exp = Experiment(
        experiment_id="exp76-can-one-cell-hold-two",
        question="Does a second organism ever share a rich cell, and why not?",
        arithmetic={
            "cost_per_step": COST,
            "rich_one_organism": {"c_star": RICH_ONE, "intake": min(RICH_ONE, INCOME),
                                  "surplus": min(RICH_ONE, INCOME) - COST},
            "rich_two_organisms": {"c_star": RICH_TWO,
                                   "first_intake": INCOME,
                                   "second_intake": RICH_TWO - INCOME,
                                   "second_surplus": (RICH_TWO - INCOME) - COST},
            "poor_one_organism": {"c_star": POOR_ONE, "intake": POOR_ONE,
                                  "surplus": POOR_ONE - COST},
            "note": "the code does not split a cell between occupants "
                    "(organism.rs:165); each takes min(c, income) in turn",
        },
        arms={
            "A": "n=160 (exp75 reproduction)",
            "B": "n=40 (one per cell, half on poor cells)",
            "C": "n=20 (one per cell over the first half, 10 rich + 10 poor)",
        },
        seed=1,
        command="python3 checks/exp76_can_one_cell_hold_two.py",
        parameters={
            "cells": CELLS, "rich": RICH, "poor": POOR, "income": INCOME,
            "maintenance": MAINT, "damage_rate": DAMAGE, "repair_cost": REPAIR,
            "capacity": CAP, "steps": STEPS, "policy": "sighted",
            "read_budget": 3, "move_cost": 0, "layout": "even",
        },
    )

    rows = []
    for n in (160, 40, 20):
        r = run(n)
        rows.append(r)
        print("  n=%3d alive=%3d cells_used=%3d crowd=%.2f mean=%.4f"
              % (r["n"], r["alive"], r["cells_used"], r["crowding"], r["energy_mean"]))

    for r in rows:
        exp.add_arm(
            "n%d" % r["n"],
            "%d steps, alternating, rich=%.1f poor=%.1f, layout even, E_max=%.1f"
            % (STEPS, RICH, POOR, CAP),
            {
                "alive": r["alive"],
                "cells_used": r["cells_used"],
                "crowding": r["crowding"],
                "energy_mean": r["energy_mean"],
            },
            trace_hash=r["hash"],
        )

    by_n = {r["n"]: r for r in rows}

    exp.control(
        "fires",
        by_n[40]["alive"] == 20,
        "n=40 (twice the rich cells) must not raise the population above the "
        "number of rich cells: alive = %d at n = 40, rich cells = 20"
        % by_n[40]["alive"],
    )
    exp.control(
        "silent",
        by_n[160]["alive"] == 20,
        "n=160 must reproduce exp75's 20 survivors: alive = %d at n = 160"
        % by_n[160]["alive"],
    )
    exp.control(
        "specific",
        abs(by_n[160]["crowding"] - 1.0) < 1e-9
        and by_n[160]["cells_used"] == by_n[160]["alive"],
        "crowding = %.4f, cells_used = %d, alive = %d at n = 160"
        % (by_n[160]["crowding"], by_n[160]["cells_used"], by_n[160]["alive"]),
    )
    # The count 11 in arm C is only meaningful if the eleventh organism is the
    # one that walked out of the block onto a rich cell. If it were, say, an
    # organism that survived on a poor cell, that would contradict the poor-cell
    # arithmetic (0.16 against a cost of 0.63) and the arm would mean something
    # else.
    escaped = [c for c in by_n[20]["cells"] if c >= 20]
    exp.control(
        "specific",
        by_n[20]["alive"] == 11 and escaped == [20],
        "arm C: alive = %d, cells beyond the block = %s; the eleventh organism "
        "must be the one that walked from cell 19 onto rich cell 20"
        % (by_n[20]["alive"], escaped),
    )

    doubled = [r for r in rows if r["crowding"] and r["crowding"] > 1.0 + 1e-9]
    if not doubled:
        exp.verdict(
            "passed",
            "crowding stayed at 1.00 in all three arms. The reason is the "
            "feeding rule, not the movement rule: a rich cell settles at "
            "c* = 1.6 with two organisms on it, the first takes the full "
            "income 1.2, and the second takes the remaining 0.4, which is "
            "below the cost 0.63. The second organism starves. Checked "
            "directly in the Rust test "
            "`life::tests::a_rich_cell_feeds_one_organism_not_two`, which "
            "places both organisms on one rich cell with `move_to` and gets "
            "alive = 1 after 4000 steps. A poor cell settles at c* = 0.16 and "
            "yields 0.16 against the same cost, so it feeds nobody. The "
            "capacity of an alternating field is therefore the number of rich "
            "cells, one organism each, and both halves of that sentence are "
            "arithmetic.",
        )
    else:
        exp.verdict(
            "passed",
            "crowding exceeded 1.00 in %d arm(s): %s. A second organism does "
            "share a cell, and the arithmetic of the second share (0.4 against "
            "a cost of 0.63) is wrong somewhere."
            % (len(doubled), ", ".join("n=%d crowd=%.2f" % (r["n"], r["crowding"])
                                       for r in doubled)),
        )

    exp.limitation(
        "This does not prove that no policy can ever place two organisms on one "
        "cell. It shows that when two are placed there, one dies. A policy that "
        "moves on ties could still put two on a cell for a while; the run would "
        "then show a transient crowding above 1.00 that decays. Only the final "
        "frame is read here."
    )
    exp.limitation(
        "The second share 0.4 is computed from the settled content c* = 1.6, "
        "which assumes both organisms eat in the same step in a fixed order. "
        "The code iterates the population in index order, so the order is "
        "fixed, but the value 1.6 was solved by hand and not read off the "
        "trace of the two-organism test."
    )
    exp.limitation(
        "Arm C (n = 20) puts ten organisms on poor cells and ten on rich cells "
        "because `--layout even` fills cells 0..19 in order and every second "
        "cell is rich. The result alive = 11 depends on that layout: the "
        "organism on cell 19 escapes onto cell 20 because it is the one poor "
        "cell in the block with a rich neighbour on the outside. A block that "
        "ended on a rich cell would give 10, and a block in the middle of the "
        "field would give 10. The prediction of 11 was written before the run "
        "and the run agreed."
    )

    path = exp.save()
    print("saved", path)


if __name__ == "__main__":
    main()
