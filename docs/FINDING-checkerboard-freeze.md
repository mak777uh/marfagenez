# Sighted organisms freeze into a checkerboard, and that is why it holds the most

**Date:** 2026-11-13
**Experiments:** EXP-64 (`failed`, honest), probe `checks/probe_alternating.py`
**Answers:** the open question in `docs/FINDING-capacity-is-47.md`

## The measurement

EXP-64 ran `sighted` on a gradient and on an alternating field at three move
costs, 50k steps, seed 7, mean level 2.0.

| field | move_cost 0.00 | 0.05 | 0.20 | moving at end |
|---|---|---|---|---|
| gradient (2.4 → 1.6) | 31 | 33 | 34 | 19 / 21 / 25 |
| alternating (2.4 / 1.6) | **60** | **60** | **60** | **0** |

The alternating field does not care what a step costs, because **nothing ever
steps**. The gradient field moves a lot and holds about half as many.

## Why the alternating field freezes

The probe printed the last frame directly:

```
field: 1.92 1.35 1.92 1.35 1.92 1.35 ...   (40 cells)
occ:      2    1    2    1    2    1 ...   (every cell occupied)
moving: 0
```

Every rich cell holds exactly two organisms, every poor cell exactly one, and
every one of the 40 cells is occupied. Both cell types are at a fixed point:

- rich cell, two occupants: `1.92 - 1.0 - 1.0 = -0.08`, emptied, regrows to
  `M*r`-like value `1.92`. Two organisms each take `income = 1.0`.
- poor cell, one occupant: `1.35 - 1.0 = 0.35`, regrows to `1.35`.

No organism has a reason to move. An organism on a rich cell sees two poor
neighbours (`1.35 < 1.92`) and stays. An organism on a poor cell sees two rich
neighbours, but it is *already* on the cell it needs — and crucially the rich
cells are all full, so moving there would not improve what it can take. The
sighted rule compares **field levels**, not free space, so it sees no
improvement and stays.

This is a checkerboard: the highest possible occupancy of a 40-cell field under
the rule "at most two per cell" is 60 (20 cells doubled, 20 single). The
alternating field reaches exactly that.

## Why the gradient field does worse

```
field: 1.39 1.57 1.60 1.42 1.47 1.49 1.67 1.50 ... 2.12 2.15
occ:     1    .    .    1    1    1    .    1  ...   1    1
```

The gradient is not smooth. Organisms chase their neighbours, and because every
organism moves on the same tick, the field behind them is left drained and the
field ahead is not yet regrown. The result is a sawtooth with 10 empty cells out
of 40, and 25 organisms still moving at the last frame.

Moving is not free: `move_cost = 0.05` per step, and a moving organism also
cannot stay on the cell it just emptied. The gradient field pays this cost
continuously and never settles, so it holds 33 instead of 60.

## The gradient result is backwards, and that is the point

Raising `move_cost` from 0.00 to 0.20 makes the gradient field **better**
(31 → 34), not worse. That is the opposite of "walking is expensive".

The account that fits: at `move_cost = 0.00` organisms move constantly and
never settle, so the field stays churned. At `0.20` many organisms cannot
afford to move and are forced to stay, which lets the field settle. The cost of
moving is not the energy — it is that **moving prevents settling**.

So the sighted rule does not "seek food". It climbs a level gradient and stops
at a local maximum. On a field where local maxima are dense and every cell is
full (alternating), it freezes at the best possible packing. On a field where
there is always a higher neighbour (gradient), it never stops.

## What this does not prove

- It does not prove the checkerboard is stable against perturbation. The probe
  read one frame at 20k steps; EXP-64 saw 60 at 50k for all three move costs,
  which is consistent with stability but not a proof.
- It does not prove the gradient field would stay at 33 forever. EXP-63 showed
  populations can still be falling at 20k.
- It does not separate "moving prevents settling" from "moving costs energy" —
  both point the same way in these arms. An arm with `move_cost = 0` but a rule
  that forbids repeated movement would separate them, and was not run.
- The claim "the sighted rule compares levels, not free space" is read from
  `core/src/life.rs:404-441`, not measured. A probe that records what each
  organism saw would be needed to confirm it.

## The lesson

EXP-62 asked "does a gradient help?" and the answer was no. EXP-64 asked "is it
because the walk is long?" and the answer was also no — the gradient gets
*better* when walking gets more expensive. Both experiments failed to confirm
the intuition, and together they point at something the intuition missed: the
organism is not optimising food, it is climbing a level, and a level-climber
freezes wherever the levels are already highest around it.

A failed experiment that rules out a mechanism is worth more than a passed one
that confirms a number.
