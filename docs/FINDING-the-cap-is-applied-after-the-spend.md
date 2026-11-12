# The cap is applied after the spend, so the spend is free when the organism is rich

**Date:** 2026-11-12
**Question left open by:** `FINDING-the-move-cost-is-charged-but-the-population-has-two-regimes.md`,
section "What this does not prove", and `PROTOCOL.md` 18.4.
**Status:** answered by reading the code and checking the arithmetic against
the measured number. No new run was needed.

## The open question

EXP-72 measured the mean energy of a surviving `sighted` population at
maintenance 1.0, 4000 steps:

| move_cost | mean energy | move fraction |
|---|---|---|
| 0.0 | 8.9700 | 0.0005 |
| 0.2 | 8.9700 | 0.0008 |

The two are identical to four decimals. The arithmetic says the difference
should be visible: `0.0008 × 0.2 × 4000 = 0.64` over the run. It is not.

`PROTOCOL.md` 18.4 recorded this as possibly a readout problem: a quantity that
does not respond to a cost it is supposed to pay.

## The answer: it is the order of operations

`core/src/life.rs` does, every step:

```
441   if direction != 0 && r.organism.spend(self.move_cost) { ... move ... }
453   let taken = self.field.take(r.cell, self.world.income);
457   r.organism.step(&self.world, taken);
```

`core/src/organism.rs:148-158` does, inside `step`:

```
154   let taken = resource.max(0.0).min(world.income);
155   self.energy = (self.energy + taken).min(world.capacity);   // <- the cap
158   self.energy -= world.maintenance_cost;
```

So the order is: **pay the move cost, then add income, then clamp to the
capacity.**

The clamp is a `min`. Anything paid before it is erased as long as the energy
plus the income still exceeds the capacity:

```
energy_after = min(energy_before - move_cost + taken, capacity)
```

If `energy_before - move_cost + taken >= capacity`, the result is `capacity`
regardless of `move_cost`. The move cost has been paid with money that was
about to be destroyed by the cap anyway.

## The arithmetic matches the measurement exactly

The steady state is reached when the energy sits at the cap every step:

```
E* = capacity - maintenance - damage_rate * repair_cost
   = 10      - 1.0       - 0.02 * 1.5
   = 10 - 1.0 - 0.03
   = 8.97
```

Measured: **8.9700**. This is not a fit; it is the same three numbers the
command line was given, and the formula contains no `move_cost`, which is why
the measurement contains none either.

The condition for the cost to be invisible is `E* + taken >= capacity`:
`8.97 + min(1.2, level) >= 10`. It holds whenever the cell level is at least
1.03, which it is at maintenance 1.0.

The condition for the cost to be visible is the opposite. At `move_cost = 1.0`
the measured mean is 1.5396, and `1.54 + 1.2 = 2.74 < 10`: the cap never binds,
so every payment reaches the energy. The two regimes in EXP-72 are not two
kinds of organism. They are **the regime where the cap hides the cost and the
regime where it does not.**

## What this is

This is a defect in the model, not in the readout. The readout was correct:
the mean energy really was 8.9700.

The defect is that the model says two different things about the same energy
depending on whether it is at the cap:

- An organism at the cap can move for free, because the cost is subtracted
  before the income is clamped.
- An organism below the cap pays in full.

A population of rich organisms therefore has a mobility that costs nothing,
while a population of poor organisms has a mobility that costs everything. The
sign flip in the capacity result (40 → 23 as `move_cost` rises) is at least
partly this: raising the price pushes organisms off the cap, which makes the
price real for the first time.

## The fix, applied and measured

The clamp was moved to the **end** of the step, after the income, the
maintenance and the repair (`core/src/organism.rs`, `step`). The 122 tests in
`core` pass unchanged.

Re-running EXP-72's conditions with the clamp at the end (`capacity = 10`,
maintenance 1.0, 4000 steps, `sighted`, uniform field):

| move_cost | alive | mean energy | max | min | move fraction |
|---|---|---|---|---|---|
| 0.0 | 40 | 10.0000 | 10.0000 | 10.0000 | **0.0000** |
| 0.2 | 40 | 10.0000 | 10.0000 | 10.0000 | **0.0000** |
| 1.0 | 25 | 1.4304 | 4.0000 | 1.0000 | 0.7400 |

Four things changed, and the third is the one that matters.

**1. The steady state is now `capacity`, not `capacity - maintenance -
damage*repair`.** With the clamp last, the energy is pushed to the ceiling
every step, so `E* = 10.0000` exactly. This is what the word "capacity" says.

**2. The two cheap move costs still do not separate.** Both give 10.0000 and
both give a move fraction of 0.0000.

**3. The reason is no longer the cap — it is that nobody moves.** In a uniform
field every cell is equally rich, `sighted` breaks ties by staying, and an
organism that does not move does not pay a move cost. The cost is not hidden by
a `min`; it is not incurred at all.

The old capped run reported move fractions of 0.0005 and 0.0008 rather than
0.0000 because the cap was erasing the spend, which left the energy slightly
below the ceiling and made a rare move affordable. With the clamp at the end
the energy sits exactly at the ceiling and the tie-break dominates.

**4. At `move_cost = 1.0` the population is pushed off the ceiling and the cost
becomes real.** 25 survive at a mean energy of 1.4304 with a move fraction of
0.7400. A move costs a tenth of the whole reserve, so an organism that moves
often cannot stay at the ceiling, and once it is below the ceiling every
payment reaches the energy.

So `move_cost` does not change the decision rule — `Sighted` never looks at
energy (`core/src/life.rs:402-433`) — it changes **which regime the organism is
in**. Cheap enough and the organism sits at the ceiling and never moves;
expensive enough and it is off the ceiling and moves constantly. The
intermediate case, where a rich organism moves for a visible price, does not
occur in a uniform field because there is nothing to move towards.

## What this does not prove

- The old formula `E* = capacity - maintenance - damage*repair` described the
  steady state before the clamp, not the observable energy. It must be
  restated or dropped.
- EXP-73's `capacity = 1e9` arm was run with the old order. With the clamp at
  the end it is unchanged in principle (the clamp never binds either way), but
  it has not been re-run.
- The uniform field is the worst place to look for a move cost, because the
  tie-break makes movement rare. The alternating and gradient fields have not
  been re-run with the clamp at the end.
- **Every capacity number recorded before this change is now suspect.** The
  23, the 26 and the 40 were all measured with the clamp in the old place.
- `alive = 40 = cells` appears again. It is the same echo as before
  (p. 16.1): one organism per cell, not a capacity.

## What to do next

1. Re-run the capacity experiments (EXP-72, EXP-73, and the alternating and
   gradient arms) with the clamp at the end.
2. Restate the steady-state law: it is `capacity` when the organism is rich and
   `income - maintenance - damage*repair` when it is poor, with a crossing where
   the clamp stops binding.
3. Consider whether `capacity` should still be split into `energy_cap` and
   `income_cap`. With the clamp at the end the two jobs no longer interfere, so
   the split is now optional rather than necessary.
