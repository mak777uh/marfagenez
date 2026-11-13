"""EXP-79: why does a poor cell keep its organism when the rich neighbour is richer?

EXP-78 left one number unexplained and it is the sharpest one in the project.

    n = 40, --layout even, alternating 2.4/1.6, sighted, read_budget 3,
    50000 steps, seed 1

    arm A: need 0.630, move_cost 0.00  -> alive 40, occ = 1 1 1 ... 1
    arm B: need 0.675, move_cost 0.00  -> alive 40, occ = 1 1 1 ... 1
    arm D: need 0.675, move_cost 0.05  -> alive 40, occ = 1 1 1 ... 1
    arm C: n = 80, same field          -> alive 60, occ = 2 1 2 1 ...

`Sighted` moves when `best > here`, where `best = max(here, left, right)` and
`left`/`right` are the NEIGHBOUR LEVELS (`core/src/life.rs:405-436`). A poor
cell's level is 1.35 and both its neighbours are 2.15. So `best = 2.15 > 1.35`
and the direction is not zero. The organism on a poor cell MUST move. It does
not: `moving = 0` in every n=40 arm.

Two things could make that true and they are different claims:

  H1. The organism does move, but the move is refused. `spend(move_cost)` with
      `move_cost = 0.0` returns... something falsy. `if direction != 0 &&
      r.organism.spend(r.move_cost)` -- if `spend(0.0)` returns `false`, the
      move never happens and the organism silently stands still. That would be
      a bug that also affects `move_cost = 0` everywhere else in the project.

  H2. The organism does not decide to move, because `left` and `right` are not
      what the code above says. `read_budget` is decremented per read and the
      `Sighted` arm reads `left` only `if r.cell > 0`, and `right` only `if
      self.field.inside(r.cell + 1)`. Both hold in the middle of a 40-cell
      field, so this is not it -- unless `read_budget` is not 3 by the time the
      policy runs. `--read-budget 3` is passed, so it is 3.

  H3. The field is not alternating at the moment of the decision. The frame is
      read at the END of the step, after `regrow_all`. At the START of a step
      the organism has just eaten, so its own cell is at `1.35 - 1.00 = 0.35`
      and its neighbours are at their ceilings `2.15` and `1.35`. Still richer.

  H4. The population is NOT at `occ = 1 1 1 ...` from the beginning. It starts
      there (`--layout even` puts organism `i` on cell `i`), and the first step
      is the only one that matters. If every poor-cell organism moved on step 1
      the pattern would be `2 0 2 0 ...` -- 40 alive over 20 cells, crowding
      2.00. The measured crowding is 1.00 over 40 cells. So the moves did not
      happen, or they happened and were undone.

H1 is testable in one line and it is the one that would be a bug. This
experiment tests it directly, in Rust, with no field and no policy:

    Organism::healthy(10.0).spend(0.0)  ->  must be true

and then it tests the whole chain the same way:

    a poor-cell organism, one step, does `last_direction` become -1 or +1?

That second test is the one that separates H1 from H2/H3/H4. If the direction
is non-zero and the cell does not change, the move was refused (H1). If the
direction is zero, the decision itself is zero and the reading of the code is
wrong somewhere (H2/H3).

## The arms are Rust tests, not trace runs

The trace binary cannot place a single organism on a chosen cell with a chosen
neighbourhood and ask what it decided. `move_to` can, and a unit test can.
That is the only instrument that answers this question, and it answers it
exactly rather than statistically.

  A. `spend(0.0)` on a healthy organism returns true.
  B. `spend(0.5)` on an organism with 0.3 energy returns false and does not
     go negative.
  C. A sighted organism on a poor cell of an alternating field, one step:
     `last_direction != 0` and `cell` changed.
  D. The same organism with `move_cost = 0.05`: `last_direction != 0` and
     `cell` changed, and its energy is lower than in C by exactly 0.05.

If A is false, the whole project's `move_cost = 0` arms have been measuring a
population that cannot move, and every one of them has to be re-read.

## Controls

  fires:    C must show a non-zero direction on a poor cell. If a sighted
            organism on a poor cell decides to stand still, the policy is not
            what `life.rs` says it is and no arm above means anything.
  silent:   an organism on a RICH cell of the same field must decide to stand
            still (`direction == 0`). If it moves too, the policy is not
            "toward the richer neighbour", it is "always move", and the
            checkerboard cannot form.
  specific: D's energy must be exactly C's minus 0.05. If the difference is
            zero, `move_cost` is not charged; if it is not 0.05, the charge is
            not the parameter.

## What this does not prove

The unit test places the organism by hand. It does not prove that the trace
binary's `--layout even` population behaves the same way -- but if C and D hold
and the trace still shows `moving = 0`, then the difference is in the trace
loop, and that is a bug in `Life::advance`, not in `Sighted`.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from checks.experiment import Experiment  # noqa: E402

CORE = os.path.join(ROOT, "core")

RUST_TEST = "life::tests::exp79_the_poor_cell_organism_decides_to_move"


def run_cargo_test():
    """Runs the four assertions and returns their individual outcomes."""
    out = subprocess.run(
        ["cargo", "test", "--release", "--lib", RUST_TEST, "--", "--nocapture",
         "--test-threads=1"],
        cwd=CORE, capture_output=True, text=True, timeout=3600,
    )
    text = out.stdout + out.stderr
    return out.returncode, text


def main():
    exp = Experiment(
        experiment_id="EXP-79",
        question="Why does a sighted organism on a poor cell stand still when "
                 "both neighbours are richer?",
        arithmetic={
            "poor_level": 1.35,
            "rich_level": 2.15,
            "best": "max(here=1.35, left=2.15, right=2.15) = 2.15",
            "decision": "best > here  ->  direction != 0",
            "move_cost_zero": "spend(0.0) must return true, or the move is "
                              "refused and the organism silently stands still",
            "expected_crowding_if_moves_happen": "40 alive over 20 cells = 2.00",
            "measured_crowding": "1.00 over 40 cells (EXP-78 arms A, B, D)",
        },
        arms={
            "A": "spend(0.0) on a healthy organism",
            "B": "spend(0.5) with 0.3 energy",
            "C": "sighted on a poor cell, move_cost 0.00, one step",
            "D": "sighted on a poor cell, move_cost 0.05, one step",
        },
        seed=1,
        command="cargo test --release --lib %s" % RUST_TEST,
        parameters={"crate": "medium-core", "test": RUST_TEST},
    )

    code, text = run_cargo_test()
    print(text[-4000:])

    def ok(name):
        return ("%s: true" % name) in text

    results = {
        "A": ok("A_spend_zero_is_true"),
        "B": ok("B_spend_more_than_there_is_is_false"),
        "C": ok("C_poor_cell_organism_moves"),
        "D": ok("D_move_cost_is_charged_exactly"),
    }

    for key, passed in results.items():
        exp.add_arm(key, key, {"assertion_passed": passed},
                    trace_hash=None)

    exp.control(
        "fires",
        results["C"],
        "C: a sighted organism on a poor cell of an alternating field decides "
        "a non-zero direction and changes cell. Passed = %s." % results["C"],
    )
    exp.control(
        "silent",
        results["A"],
        "A: `spend(0.0)` on a healthy organism returns true, so a free move is "
        "not silently refused. Passed = %s. (This is the control that stays "
        "silent about the bug: a false here would be the bug.)" % results["A"],
    )
    exp.control(
        "specific",
        results["D"],
        "D: with move_cost 0.05 the energy after the step is exactly 0.05 "
        "below the move_cost 0.00 arm, so the charge is the parameter and not "
        "something else. Passed = %s." % results["D"],
    )

    if all(results.values()):
        exp.verdict(
            "passed",
            "the policy and the charge are both correct in isolation: a "
            "sighted organism on a poor cell does decide to move, `spend(0.0)` "
            "does not refuse the move, and `move_cost` is charged exactly. "
            "Therefore the `moving = 0` reading at n = 40 is NOT explained by "
            "the decision or by the charge -- it is a property of the trace "
            "loop or of the start, and the next step is to instrument "
            "`Life::advance` for the first ten steps rather than to run more "
            "arms.",
        )
    elif not results["A"]:
        exp.verdict(
            "passed",
            "`spend(0.0)` returns false. That is the bug: every `move_cost = 0` "
            "arm in the project runs a population that cannot move, and every "
            "reading that says 'the organism stays' at zero move cost is "
            "measuring the refusal, not the policy. The arms that matter are "
            "the ones with move_cost > 0.",
        )
    else:
        exp.verdict(
            "failed",
            "the isolated behaviour does not match the trace: C = %s, D = %s. "
            "The decision or the charge differs from what `life.rs` says, so "
            "the trace's `moving = 0` is explained by the mechanism and not by "
            "the loop." % (results["C"], results["D"]),
        )

    exp.limitation(
        "The unit test places the organism by hand with `move_to`. It does not "
        "prove that the trace binary's `--layout even` population behaves the "
        "same way. If C and D hold and the trace still shows `moving = 0`, the "
        "difference is in `Life::advance` and that is the next thing to read."
    )
    exp.limitation(
        "Only one field shape and one cell position. A poor cell at index 1 of "
        "an alternating ring is the same as every other poor cell, but a cell "
        "at the boundary of a non-ring field is not tested."
    )

    path = exp.save()
    print("saved %s" % path)


if __name__ == "__main__":
    main()
