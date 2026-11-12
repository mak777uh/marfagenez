# FINDING: a gradient is transient, and any take makes one

**Date:** 2026-11-12
**Where:** `core/src/field.rs` (`regrow_all`, `take`, `richer_neighbour`), tests in the same file.

## What the model does

`Field::regrow_all` moves every cell toward `max_resource`, not toward its own
value:

    c ← c + (M − c)·r

So a cell that was put in at `0.2` in a field of `M = 2.0` climbs to the
maximum, and a cell that was put in at `1.8` stays. The regrowth law has no
memory of what a cell "should" be.

## Consequence 1: a gradient is erased

A gradient `low … high` over `cells` cells loses its span by the factor
`(1 − r)` per step. With `regrow = 0.8`, `span = 1.8`:

| step | span |
|---|---|
| 0 | 1.800 |
| 9 | 9.216e-7 |

`0.2·(1−0.8)^9·1.8 = 9.2e-7`. The gradient is gone in nine steps. Test:
`a_gradient_is_erased_within_ten_steps`.

This is not a bug in the field; it is what "regrow toward the maximum"
means. But it changes what a "gradient experiment" measures: after ten steps
the organism is climbing a field that no longer has a slope.

## Consequence 2: any take opens a hole, and the hole is a gradient

`take(cell, amount)` lowers one cell. Its two neighbours are then richer, so
`richer_neighbour` points away from the eater's own cell. A sighted organism
eats, its own cell drops, its neighbours look richer, it steps — so **an eating
sighted organism never stands still**. Test:
`an_eating_sighted_organism_never_stands_still` (`moves ≥ 99` in 100 steps).

The hole itself closes fast: `1.2 → 1.84 → 1.968 → 1.9936` at `regrow = 0.8`,
i.e. the gap is multiplied by `0.2` per step. Test:
`any_take_opens_a_hole_and_the_hole_is_a_gradient`.

## Consequence 3: a uniform field is never uniform

"Uniform" means uniform at the start of a step. The moment anybody eats, the
field has a slope. So `uniform` is not a control for "no gradient" — it is a
control for "no gradient *put in by hand*". The experiments that compare
`alternating` with `uniform` compare two different histories, not a treatment
with its absence.

## What this does not prove

* That a gradient cannot be maintained. A moving field (`Field::moving`) shifts
  the pattern, which re-creates a slope every step; that is a different model.
* That the organism's climbing is useful. Climbing a transient gradient and
  climbing a maintained one are different problems; only the second is measured
  in `EXP-12`.
* Anything about `r → 1`. At `r = 1` the hole closes in one step and the
  gradient never forms.

## Two bugs found on the way

1. `Field::level` returned `0.0` outside the field, so a sighted organism at the
   right edge read "the cell beyond the edge is empty" and, if its own cell was
   richer than its left neighbour, stepped off the field. Fixed by `inside()`.
2. `richer_neighbour` returned the **left** cell when the two neighbours were
   equal, so every walker drifted left in a uniform field. Fixed: a tie is
   `None`, and `Walker::choose` stays.
