# The move cost is charged, and the population has two regimes, not one

**Date:** 2026-11-12
**Experiments:** EXP-71 (`exp71-does-hunger-feed-back-into-moving`), EXP-72
(`exp72-is-the-move-cost-charged`)
**Status:** the hypothesis of EXP-71 is refuted; EXP-72 answers the question
EXP-71 raised.

## What EXP-71 predicted and what it got

EXP-70 measured the fraction of steps on which a living `sighted` organism
moves, and found it was not constant: 0.0008 at maintenance 1.000, 0.1001 at
1.100, 0.0003 at 1.160, 0.2319 at 1.190. The natural reading was a feedback
loop — a hungrier organism moves more, moving costs energy, so hunger feeds
hunger.

EXP-71 pre-registered two predictions from that loop:

1. The death threshold falls as `move_cost` rises, with slope `-f` where `f` is
   the move fraction at the threshold.
2. Above the threshold, a larger `move_cost` kills the population in fewer
   steps, and the gap from the no-loop prediction grows with `move_cost`.

Both failed.

| move_cost | threshold | death step at m = 1.25 | no-loop prediction |
|---|---|---|---|
| 0.0 | 1.170628 | 64 | 62.5 |
| 0.1 | 1.170063 | 64 | 27.8 |
| 0.3 | 1.170216 | 64 | 13.2 |

The slope of the threshold in `move_cost` is `-0.001068`, which is the size of
the bisection noise, not a law. The death step is **64 at every move cost**,
while the arithmetic says 62.5, 27.8 and 13.2.

The `silent` control failed too, and it failed informatively: at
`move_cost = 5.0` and maintenance 1.0 — a move cost four times the income —
23 organisms were still alive.

## Why the death step did not move

The death step was measured as the first frame at which nobody is alive. That
is the lifetime of the **hungriest** organism, not of the population. The
hungriest organisms are the ones that never got food, and those are the ones
that never move. `move_cost` changes nothing about them.

So EXP-71 measured the wrong thing twice: the threshold is set by survivors who
sit still, and the death step is set by losers who sit still. Neither arm can
see a move cost.

This is a ninth kind of error, and it is a variant of §16.2: **the number you
read is indexed by the wrong population.** `alive == 0` is the last moment of
the worst organism, not a property of the population.

## What EXP-72 found instead

EXP-72 asks the cheap question first: run **below** the threshold, where nobody
dies, and look at the mean energy. If the move cost is charged, the mean must
fall as the cost rises.

`sighted`, maintenance 1.0 (threshold is 1.17), 4000 steps, `n = 160`,
`cells = 40`:

| move_cost | alive | mean energy | max energy | move fraction |
|---|---|---|---|---|
| 0.0 | 40 | 8.9700 | 8.9700 | 0.0005 |
| 0.2 | 40 | 8.9700 | 8.9700 | 0.0008 |
| 1.0 | 23 | 1.5396 | 6.0000 | 0.6952 |
| 5.0 | 23 | 3.5330 | 5.0000 | 0.8004 |

The cost is charged. But it is not charged linearly, and the population is not
one population.

### The move fraction jumps by three orders of magnitude

Between `move_cost = 0.2` and `move_cost = 1.0` the move fraction goes from
0.0008 to 0.6952 — a factor of 870 — while the mean energy collapses from 8.97
to 1.54.

A larger move cost makes organisms move **more**, which the `Sighted` rule
cannot produce on its own: `move_cost` does not appear in the decision
(`core/src/life.rs:402-433`). The decision is `best > here`, and both sides are
field levels.

What changes is the field. An organism that cannot afford to move stays on a
cell it has emptied; the cell regrows under it; it eats; it never leaves. An
organism that can afford to move leaves, and the cell it left is empty, so its
neighbour now sees a richer cell and moves too. The move cost is not deciding
where anyone goes — it is deciding whether the field ever gets a chance to
recover.

### `alive = 40` at low move cost is the cell count, not a capacity

`cells = 40`, and `alive = 40` at `move_cost` 0.0 and 0.2. That is one organism
per cell, crowding 1, and it is exactly the echo §16.1 warns about. It is not a
capacity: 120 of the 160 organisms are already dead.

At `move_cost ≥ 1.0` the count is 23, which is neither `cells` nor `n`. **23 is
the first number in this line of work that is a capacity and not an input.**

The two regimes differ in more than the count:

| | move_cost ≤ 0.2 | move_cost ≥ 1.0 |
|---|---|---|
| alive | 40 (= cells) | 23 |
| mean energy | 8.97 (full) | 1.54–3.53 (near empty) |
| move fraction | 0.0008 | 0.70–0.80 |
| what limits the count | one per cell | energy |

A population that never moves saturates at one organism per cell and is rich.
A population that moves saturates at 23 and is poor. **Mobility here buys a
lower capacity, not a higher one** — the opposite of the `sighted` result
recorded earlier (40 → 80), which was measured on an alternating field. The
field shape decides the sign.

## What this does not prove

- One seed, one field shape (uniform with `rich = 2.4`, `poor = 1.6`), one read
  budget (3). The 23 is not a constant of the model.
- The mean energy at `move_cost` 0.0 and 0.2 is identical to four decimals
  (8.9700). The arithmetic says the extra cost over 4000 steps should be
  visible: `0.0008 × 0.2 × 4000 = 0.64`. It is not. Either the mean is pinned
  by a steady state rather than accumulated, or the two runs differ by less
  than the print precision. **This is unexplained and is the next question.**
- EXP-72 proves the cost reaches the energy. It does not measure how much of
  the collapse is the cost and how much is the field never recovering.
- The two regimes were found by sweeping `move_cost` at one maintenance. The
  boundary was not located; it lies somewhere between 0.2 and 1.0.

## What to do next

1. Locate the boundary between the two regimes in `move_cost`. If it is a
   threshold, the arithmetic should say where: an organism can afford to move
   while `income − maintenance − damage·repair > move_cost`, which at
   maintenance 1.0 gives `move_cost < 0.17`. The jump happened between 0.2 and
   1.0, so either the boundary is not there or the criterion is not that.
2. Explain the identical 8.9700. Find what pins the mean energy, because a
   quantity that does not respond to a cost it is supposed to pay is a
   readout problem (§16.2), not a law.
3. Redo the `sighted` capacity result on the uniform field. The 40 → 80 figure
   was measured on alternating, and this note shows the sign of the mobility
   effect depends on the field.
