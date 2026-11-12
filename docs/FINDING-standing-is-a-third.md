# FINDING: standing still is 1/3, and EXP-41 was a sample of 24

Date: 2026-11-12. Run: `results/standing-is-a-uniform-third/run-2026-11-12T16-09-20.json`.

## What was asked

EXP-41 measured `p_choose = 0.625` and `0.6923` on a single organism and left it
open whether `Policy::Random` really draws a move with probability 2/3. The code
says it does (`core/src/life.rs`: `u < 1/3 -> -1`, `u < 2/3 -> 0`, else `+1`).

## What was measured

400 organisms, 40 steps, 5 seeds, uniform field, no income, `move-cost 0`:

| seed | choices | moved | p(choose a move) |
|---|---|---|---|
| 1 | 10000 | 6651 | 0.6651 |
| 2 | 10000 | 6625 | 0.6625 |
| 3 | 10000 | 6738 | 0.6738 |
| 4 | 10000 | 6690 | 0.6690 |
| 5 | 10000 | 6671 | 0.6671 |

Total 50000 choices, 33275 moves, `p = 0.6655`, `SE = 0.00211`, `z = -0.55`
against 2/3. The draw is not biased.

## Why EXP-41 was low

EXP-41 had 24 steps on one organism. With `p = 2/3`, `P(X >= 15 | n = 24)` is
about 0.24 — a 0.625 reading is unremarkable. The number was honest, the sample
was small, and the finding drawn from it ("the organism does not move two steps
out of three") was an artefact of the sample size.

## What this changes

- `p(stay) = 1/3` for `random` stands as a property of the policy, not of the
  density (EXP-46) and not of the field.
- EXP-41's `silent` and `specific` controls were `False` because they compared
  `chosen` against `moved`: the difference of exactly one is the last frame,
  where the organism is alive but the run ends before the move is resolved. That
  is a readout boundary, not a mechanism.

## What this does not prove

- Nothing about `remember`, `memory` or `sighted` — their standing fractions are
  structural (EXP-46) and were not re-measured at this sample size.
- Nothing about why the field's own randomness (which neighbour is richer, where
  the organism starts) would or would not correlate with the draw. The 5 seeds
  are 5 draws of the field, not 5 independent policies.
- The organism dies during the run, so later frames contribute fewer choices;
  the count is over living samples only, which is the right denominator for
  "what does the policy choose" but not for "what did the run cost".
