# The latecomer walks a full field

EXP-62 found two late deaths: an organism with 0.0749 energy that arrived on a
shared cell one step before dying, next to a mate with the full 7.37. It could not
say where the dying organism had been, because the trace recorded only the current
cell. The trace now records `prev_cell`, and EXP-63 walks the dying slot backwards
through all 199 steps of its last stretch.

## What the path shows

Slot 54, steps 3379 to 3577, uniform field, 160 organisms on 40 cells:

| quantity | value |
|---|---:|
| steps traced | 199 |
| times it moved | 78 |
| steps it shared its cell | 71 |
| steps it took nothing | 0 |
| energy at the start | 7.3700 |
| energy at the death | 0.0749 |
| change | -7.2951 |

The path is a walk along cells 6 to 25. Every time it moves onto a cell that
already carries a full organism it takes **0.500** and loses **0.130**. Every time
it stands on a cell alone it takes **1.200** and gains. It never once found a cell
that was actually empty.

The arithmetic of the whole stretch:

```
71 shared steps  at 0.500 - 0.63 = -0.130  ->  -9.23
128 private steps at 1.200 - 0.63 = +0.570  ->  +72.96
```

That does not add up to -7.2951, because the private steps cap at 7.37 and the
surplus is thrown away. What matters is that the losses are concentrated in the
shared steps and the gains stop at the ceiling: an organism that spends 36% of its
time sharing a cell cannot recover between the shared stretches, because the
recovery is capped while the loss is not.

## The 0.500 and the 0.400 in the same trace

Lines 3486 and 3487 show `taken 0.400` and `taken 0.480`, and line 3488 shows
`0.499`. These are not noise. The first taker's share is `min(level, 1.2)`, and
the level depends on how long the cell has been regrowing since the last take.
A cell that was taken from one step ago has regrown only partially, so the second
taker gets less than `1.700 - 1.200 = 0.500`. The steady state 0.500 is the value
when the cell has fully regrown; a cell that was just taken from gives less.

This is the same rule as EXP-60, read at the level the taker actually saw rather
than the steady-state level.

## Why it never found an empty cell

The population is 80 survivors on 40 cells. The mean occupancy is 2.0. A random
walk on a field where every cell already carries two organisms has no empty cell
to find. The organism is not unlucky; the field is full.

EXP-61 measured the same thing from the other side: 10834 runs of shared
occupancy, 99.1% of them one step long. Those one-step runs are exactly this
walk -- an organism stepping onto an occupied cell, taking the leftover, and
stepping off again.

## What this does not prove

- **Why slot 54 rather than another slot.** 78 of 80 organisms survive; two do
  not. Nothing here says what distinguishes them. The path shows the mechanism,
  not the selection.
- **That the walk is random.** The policy is `sighted` with read budget 3. It
  compares its own cell with both neighbours and moves to a richer one; a tie
  goes to `0`, so on a field that is uniform at the instant of the decision it
  stays. The trace shows 78 moves out of 199, so the field is not uniform at the
  instant of the decision -- and the reason is the organism itself. It eats
  `1.200` from its own cell, which drops that cell to `0.500` before regrowth,
  while the neighbours have regrown. So the organism makes its own cell the
  poorest one it can see and then moves off it.

  **This paragraph was an inference when written and has since been measured.**
  `docs/FINDING-the-sighted-organism-eats-its-own-cell.md` (EXP-64) splits every
  step by whether a neighbour was richer at the start of the step: 72.9% of moves
  yes, 13.2% of stands-still yes, a gap of 59.7 percentage points. A single
  organism alone on the same field moved 599 of 599 steps and every move had a
  richer neighbour. The 27.1% of moves that show no richer neighbour in the
  recorded frame are the gap between deciding (before acting, in slot order) and
  recording (after every organism has acted), not a second mechanism.
- **That 199 steps is typical.** It is the length of the last unbroken alive
  stretch of one slot. Other slots may have longer or shorter stretches.
- **Anything about the alternating field.** This is the uniform field.
