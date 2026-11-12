# FINDING: reading is not eating — `Field::take` glues two operations

Date: 2026-11-12. Status: **hypothesis, not measured yet**. The prediction is
written before the run, as `PROTOCOL.md` §1 requires.

## The claim

`Field::take(cell, income)` does two different things at once:

1. **observe** — the organism learns how much is in the cell;
2. **eat** — the organism removes `income` from the cell.

Because they are one operation, *looking costs the thing looked at*. Every
conclusion that involves perception inherits that cost, and some of them are
about perception only by accident.

## What this explains

| finding | the old reading | the reading after the split |
|---|---|---|
| `docs/FINDING-sighted-depletes.md` | sighted organisms deplete the field | a sighted organism damages the cell **by the act of seeing it**; depletion is a property of `take`, not of sight |
| `docs/FINDING-memory-weak.md` | memory does not pay | remembering a rich cell is pointless if visiting it destroys it; memory cannot pay **structurally** |
| `k_max = M·r/income` | capacity of a cell | capacity of a cell **that is also its own reader** |

The frozen `life.rs` memory (fixed 2026-11-12, commit before this note) is a
**second** defect on top of this one. The two must be separated, not chosen
between.

## The arithmetic that has to be true before the run

Let a cell hold `c`, regrow `r`, per-organism income `i`, and let `k`
organisms stand on it. With the current order (take inside the step, regrow
once per step at the end):

    c_{n+1} = (c_n − k·i) + (M − (c_n − k·i))·r

Fixed point:

    c* = M − k·i·(1−r)/r

The cell supports `k` organisms iff `c* ≥ k·i`:

    k ≤ M·r/i        (the old law; unchanged by the split)

Now split. `observe` reads the level and removes nothing. `eat` removes `i`
only if the organism decides to eat. A cell that is only *read* stays at `M`:

    c*_read = M

So under the split, `k_max` is no longer a property of the cell alone — it
depends on how many organisms **eat** there, and reading is free. The law
becomes:

    k_eat ≤ M·r/i,   k_read unbounded

That is the prediction: **the capacity law changes from a law about cells to a
law about eaters.**

## The experiment (EXP-30)

Split `take` into `observe` (no subtraction) and `eat` (subtraction), and give
each organism a separate **read budget** per step (number of cells it may
observe). Twenty lines of change in `core/src/field.rs` and one field in
`Organism`.

Predictions, written before the run:

1. `sighted` stops depleting its own cell: with read budget ≥ 2 the field
   spread under `sighted` stays at the spread of the field, not below it.
2. `memory` starts to differ from `remember`: an updating memory can hold a
   cell it has only *read*, so it can be right about the field.
3. `k_max` changes: it becomes the number of **eaters**, not the number of
   occupants.

**Control (the one that decides whether the split did anything):** with read
budget = 0 and `eat` = the old `take`, the run must reproduce the current
behaviour **exactly** — same trace hash as the run before the change. If the
hash differs, the split changed something it was not supposed to change and
the experiment is void (`PROTOCOL.md` §5).

## What this does not prove

- That a transformer is a member of the same class. The analogy is an
  anatomical hint, not a measurement. The falsifiable part is narrow: integer
  `k_max`, a strict boundary, dependence on insertion order, floor-type rather
  than ceiling-type. If multi-needle retrieval shows neither an integer jump
  nor order hysteresis, the correspondence is false.
- That splitting reading makes the child grow. It removes one structural
  obstacle; `EXP-28` (birth) is a different obstacle.

## Why this is cheaper and deeper than birth

Birth adds a **source**. Splitting reading adds the **possibility of having
information**. A child that cannot have information cannot use a second
source either.
