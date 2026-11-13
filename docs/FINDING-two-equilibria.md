# A cell has two equilibria, and the second seat rotates

**Date:** 2026-11-13
**Experiments:** EXP-60 (`failed`), EXP-61 (`passed`)
**Corrects:** EXP-59 (`docs/FINDING-capacity-is-about-48.md`)

## The mistake EXP-59 made

EXP-59 concluded that the second occupant of a cell earns
`c* - income = 1.75 - 1.0 = 0.75`, pays `0.66`, nets `+0.09`, and that the
capacity is therefore "about 48, not 80".

That arithmetic is built on the wrong step order. It assumed the field regrows
after **every organism**. The real order is in `Life::advance`
(`core/src/life.rs:250-465`):

```
for each organism:  move (pay) -> take(cell, income) -> live
then, once:         field.regrow_all()          // line 464
```

`Organism::step` in `core/src/field.rs:316` *does* regrow after each organism,
but `Life::advance` never calls it. Reading that method instead of `advance`
is what produced the wrong number.

## The two equilibria

A cell that keeps a reserve settles at

```
c* = M + income - income/r = 2 + 1 - 1.25 = 1.75
```

One occupant takes `income = 1.0`, the cell falls to `0.75`, one regrow brings
it back to `1.75`.

A cell that is **emptied** every round settles at

```
M*r = 2 * 0.8 = 1.6
```

Two occupants drain it completely: the first takes `1.0`, the second takes
what is left. An empty cell regrows to `M*r` in one step.

Measured (EXP-61, 200k steps, n = 80, 40 cells, `sighted`, uniform field):

| occupancy | cell value | arithmetic |
|---|---|---|
| one organism | 1.72 … 1.75 | `c* = 1.75` |
| two organisms | **1.6000** (all 6) | `M*r = 1.6` |
| n = 40, no doubling | **1.7500** (all 40) | `c* = 1.75` |

So the field value tells you the occupancy. That is why the two equilibria
matter: the field is a readable record of crowding.

## The second seat is a loss, and it rotates

On a doubled cell the second occupant earns `1.6 - 1.0 = 0.60` and pays

```
need + move + damage*repair = 0.6 + 0.05 + 0.02*0.5 = 0.66
```

so it loses **0.06 per step**. From energy 10.0 that is 166 steps, far short of
the 200 000 steps the experiment runs.

Yet crowd 2 persists. The measurement explains why: over the last 20 frames,
**45 different organisms** occupied a second seat, while only 6 cells were
doubled in the final frame. The second seat is not a place an organism holds —
it is a place organisms pass through. No organism stays there long enough to
die of it.

The second seat's take is not always 0.60. It depends on the cell value at the
start of the round, which alternates: a round with one occupant leaves the
cell at 1.75, a round with two leaves it at 1.6. Measured mean take on a
doubled cell: **0.745**, inside the arithmetic range `[0.60, 0.75]`.

## What this does not prove

- It does not give a closed form for the capacity. 46 of 80 alive is measured,
  not derived.
- It does not prove that rotation is what keeps the second seat alive — only
  that crowd 2 persists while a *fixed* second seat would lose 0.06 per step.
- It does not separate `move_cost` from `damage` in the second seat's loss.
- The population may still be drifting: EXP-59 saw 46 fall to 45 at 10M steps.
- EXP-60 tested and **rejected** the read budget as the constraint: budgets
  3, 40 and 80 all gave exactly 46 alive.

## What was tested and failed

**EXP-60, read budget (`failed`).** The hypothesis was that `--read-budget 3`
on a 40-cell field is what caps the population, because an organism that can
only look at 3 cells cannot find an empty one. Predicted 80 at budget 40.
Measured 46 at budgets 3, 40 *and* 80. The read budget is not the constraint.

## Lean

`laws/Medium/Field.lean`:

```lean
theorem empty_cell_regrows_to_M_mul_r (M r : ℝ) :
    cellStep M r 0 0 = M * r

theorem doubled_cell_settles_at_one_point_six :
    cellStep 2 (4 / 5) 0 0 = 8 / 5

theorem two_equilibria_differ :
    cellStep 2 (4 / 5) 1 (7 / 4) ≠ cellStep 2 (4 / 5) 0 0
```

The last one says the two equilibria are distinct, so occupancy is observable
in the field — the measurement above is not an accident of rounding.

## The lesson

EXP-59's error was not a wrong number. It was reading a method that existed,
looked right, and was not the one being called. `Organism::step` and
`Life::advance` both step an organism; only one of them is on the path. Before
trusting a formula about a simulation, find the call site — `grep` the function
name and read the function that actually runs.
