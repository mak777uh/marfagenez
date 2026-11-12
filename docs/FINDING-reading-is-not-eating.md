# FINDING — reading is not eating (EXP-30)

**Date:** 2026-11-12
**Status:** measured. The read budget is a real, separate resource, and it is
the first resource in this medium whose scarcity has a *shape*.

## What was split

Before, `Field::take` did two things at once: it read a cell and it subtracted
from it. An organism therefore could not look without consuming, and — the
part that mattered — it could not look at a cell it was not standing on
without also emptying it. `observe` is the read-only half; `eat` is `take`.

`World::read_budget` is how many cells an organism may look at per step. It
counts the organism's own cell: with `read_budget == 0` the organism knows
nothing, not even where it stands (`here = 0.0`, which `best_level <= 0.0`
already treats as "nothing seen").

## Why the budget is not a constant

A policy needs a specific number of reads per step:

| policy | reads per step | why |
|---|---|---|
| `stay` | 0 | never looks |
| `random` | 0 | never looks |
| `remember` | 1 | own cell only |
| `memory` | 1 | own cell only |
| `sighted` | 3 | own cell + two neighbours |

This is not a design choice, it is arithmetic: to compare three cells you must
see three cells. A budget of 2 leaves a sighted organism unable to compare, and
the result is not "a bit worse" — it is *worse than blind*.

## The measurement (uniform field, n = 120, cells = 120, 1200 steps, 10 seeds)

Survivors out of 120, mean of seeds 1..10
(`results/EXP-30/run-2026-11-12T15-49-47.json`, verdict `passed`, three controls):

| budget | sighted, uniform | sighted, gradient |
|---|---|---|
| 1 | 76.3 | 56.9 |
| 2 | 109.2 | 0.0 |
| 3 | 114.6 | 49.4 |
| 4 | 114.6 | — |

Satiation at 3, exactly the arithmetic number: budget 4 is *the same run* as
budget 3 (identical trace hash), which is why it is recorded as a note and not
as an arm. Below 3 the loss is real and monotone on a uniform field. On a
**gradient** field it is not monotone at all: budget 2 gives
**0 survivors** while budget 1 gives 56.9
and budget 3 gives 49.4.

Budget 1 is better than budget 2. That is not noise, it is the shape of the
failure: with one read the organism sees only its own cell, so `Sighted`
degenerates into "no information, stay put" — which is exactly `stay`, and
`stay` is a decent policy on a gradient. With two reads it sees its own cell
and *one* neighbour, compares them, and always walks toward the one neighbour
it can see. It walks in a straight line off the field. Partial sight is a
trap: it produces confident motion in one direction with no way to correct.

## The other policies, same world, budget 0 vs 1 (uniform field, seed 7)

| policy | budget 0 | budget 1 |
|---|---|---|
| `stay` | 79 | 79 |
| `random` | 13 | 13 |
| `remember` | 11 | 84 |
| `memory` | 60 | 117 |
| `sighted` | 79 (blind = stay) | 79 |

The blind `sighted` arm is not merely *similar* to `stay` — it is the same
trace, hash `870435c692217f1f`. That identity is the `specific` control: the
arm that carries the effect is the one that reads, not the one whose label
says `sighted`.

`stay` and `random` are unchanged by construction — they never read, so the
budget cannot matter, and the trace hash is identical at every budget. That is
the control: a resource that nothing uses must not change anything.

`remember` at budget 0 collapses to 11 survivors because it cannot even see
its own cell, so its memory never fills and it falls back to random walking.
At budget 1 it jumps to 84. **One read — the organism's own cell — is worth
73 survivors.** Memory without a read is not memory.

## What this does NOT prove

- That 3 is the right budget for anything but `sighted`. It is the arithmetic
  minimum for comparing three cells; a different policy would need a different
  number.
- That partial sight is always worse than no sight. It was measured on a
  gradient field with one neighbour visible; on a field where the gradient
  direction is not the field direction the result could reverse.
- That reading has a *cost*. Here reading is free but limited; a model where
  reading costs energy is a different medium and has not been measured.
- That the 0 survivors at budget 2 is a law. It is one field shape, one seed
  set. The mechanism (walk one way, never correct) is the claim; the number 0
  is an observation.

## The lesson

A resource that is only ever "enough" teaches nothing. The read budget was
invisible until it was made scarce enough to bite, and then it produced the
first non-monotone result in this project: **2 reads is worse than 1**.
Scarcity is where the interesting behaviour lives — not because scarcity is
good, but because scarcity is the only thing that makes a resource visible.
