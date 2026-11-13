# FINDING-084 — `trace` cannot place an organism, so three arms in a row were one arm

**Date:** 2026-11-13
**Experiment:** `checks/exp84_the_trace_cannot_place_an_organism.py`
**Run:** `results/EXP-84/run-2026-11-13T02-09-43.json` (verdict `passed`, three controls passed)

## What was asked

EXP-83 predicted that an organism standing on the **poor** cell 1 of a
four-cell alternating ring would eat it down to `1.6 − 1.0 = 0.6`, which then
regrows to `0.6 + 0.8·1.0 = 1.4`. The measured frame showed the poor cell at
**1.6** — untouched — while the rich cell 0 showed 2.2, eaten and regrown.

## What was actually wrong

The arm, not the model. `--layout even` puts organism `i` on cell
`i % cells` (`core/src/life.rs:178`), and `trace` has **no flag to place an
organism on a chosen cell**. EXP-83's D arm passed `--layout even --n 1`, so it
ran exactly the same run as its A arm. Two identical runs produced two
identical frames, and the prediction about the poor cell was never tested.

This is the third experiment in a row whose arms did not do what their
docstrings said:

| experiment | what the arms were supposed to differ in | what actually differed |
|---|---|---|
| EXP-80 | `--move-cost` 0.00 / 0.05 / 0.30 | nothing — four arms, one run |
| EXP-81 | `--field` alternating vs uniform | the field flag was dropped |
| EXP-83 | which cell the organism stands on | nothing — D was A |

The common cause is the same: **`trace` exposes the field and the spawner but
not the placement.** A question of the form "what happens on this cell" cannot
be asked from the command line at all.

## The measurement

Four cells, `rich 2.4 / poor 1.6`, `regrow 0.8`, `income 1.0`, `maintenance 0.6`,
`damage_rate 0.05`, `repair_cost 1.5`, `capacity 10`, `start 1.0`, `seed 1`.

| arm | spawn | frame 0 | `taken` |
|---|---|---|---|
| A | `n=1` → cell 0 | `[2.2, 1.6, 2.4, 1.6]` | `[1.0]` |
| B | `n=2` → cells 0, 1 | `[2.2, 1.4, 2.4, 1.6]` | `[1.0, 1.0]` |
| C | `n=4` → all cells | `[2.2, 1.4, 2.2, 1.4]` | `[1.0, 1.0, 1.0, 1.0]` |
| D | `n=1`, 2 steps | frame 0 `[2.2, …]`, frame 1 `[2.16, 1.6, 2.4, 1.6]` | `[1.0]` |

A and B agree on cell 0 (2.200000 vs 2.200000) and differ on cell 1
(1.600000 vs 1.400000). The only difference between the arms is one organism.
So the poor cell *can* be eaten — it just needs an organism on it, and the
command line can only put organisms on cells `0..n−1`.

## The second thing this shows

Frame 1 of arm D reads **2.16**, not the built 2.4. The second meal takes the
cell from 2.2 to 1.2, and the regrowth restores `0.8·(2.4 − 1.2) = 0.96`,
giving 2.16. The level at which a fed-on cell settles is therefore

```
L* = (L* − income) + (M − (L* − income))·regrow
   ⇒ L* = M − income·(1 − regrow)/regrow        (for regrow > 0)
```

For `M = 2.4`, `income = 1.0`, `regrow = 0.8`: `L* = 2.4 − 1.0·0.2/0.8 = 2.15`.
The measured 2.16 is one step of a geometric approach to 2.15, and the settled
value 2.15 matches EXP-66's measured 2.15 exactly. The frame is a post-meal
post-regrowth reading, and the "visible drop" of 0.25 on a rich cell is
`income·(1 − regrow) = 0.2`, one fifth of the meal.

**Consequence for every earlier reading of the field:** any statement of the
form "the field looks nearly full, so the organisms are not eating it" is a
statement about `regrow`, not about the eating. Depletion must be read from
`taken`, never from the field level.

## What this does not prove

- It does not say the settled level 2.15 is wrong; it says 2.15 is where the
  meal and the regrowth balance, which is a different quantity from the
  ceiling 2.4.
- It does not test an organism on an arbitrary cell, because the command line
  cannot place one. The unit-test path (`Life::move_to`) can, and EXP-79 used
  it.
- Four cells, one and two steps. It says nothing about a long run.

## What to do about it

Add `--start-cell` (or `--layout explicit:0,2`) to `core/src/bin/trace.rs` so
that a placement question can be asked at all. Until then, every experiment
whose arms claim to differ in placement must be checked for an identical
`cells` list in frame 0 before its verdict is believed.
