# The capacity is 47, and food is not what limits it

**Date:** 2026-11-13
**Experiments:** EXP-62 (`passed`), EXP-63 (`passed`)
**Supersedes:** the "about 48" of `docs/FINDING-capacity-is-about-48.md`

## What was measured

The same arm — `sighted`, 40 cells, uniform `M = 2`, `r = 0.8`,
`income = 1.0`, `need = 0.6`, seed 7 — run at three lengths:

| steps | alive | doubled cells | series |
|---|---|---|---|
| 20 000 | 50 | 10 | 58 57 56 55 54 51 51 51 51 50 50 50 50 50 50 50 50 50 50 50 |
| 100 000 | 47 | 7 | 54 50 50 50 50 50 50 50 50 50 47 47 47 47 47 47 47 47 47 47 |
| 500 000 | 47 | 7 | 50 47 47 47 47 47 47 47 47 47 47 47 47 47 47 47 47 47 47 47 |

The population does not drift smoothly. It falls in **steps** — 50 to 47 in one
frame — and then holds. At 500k the last 18 of 20 samples are exactly 47, so
47 is a steady state, not a snapshot on the way down.

The 46 of EXP-61 is the same steady state under a different seed (1 instead of
7) at 200k steps. The spread across seeds is 46–47.

## Food is not the constraint

```
supply  = cells * M * r = 40 * 1.6 = 64 units per round
demand  = alive * need  = 47 * 0.6  = 28.2 units per round
```

Supply is 2.3 times demand. An organism is not limited by how much food the
field produces. It is limited by **where it can stand**: 33 single cells plus
7 doubled cells is exactly 40 occupied cells out of 40.

This also rules out the earlier guess that capacity is a feeding limit. The
feeding ceiling would be `64 / 0.6 = 106` organisms, more than twice the 47
observed. The field is full long before it is hungry.

## Why 47 and not 40

40 would be one organism per cell. The extra 7 come from doubling: a doubled
cell holds two organisms, so 40 cells hold 47. The question is therefore not
"how many organisms can the field feed" but "how many cells tolerate a second
occupant, and for how long".

EXP-61 measured that the second seat loses `0.60 - 0.66 = -0.06` per step and
that 45 different organisms passed through a second seat in 20 frames. The
second seat is a place organisms pass through. A doubled cell is a *transit*
state, and the population settles where the flow through transit states
balances the deaths.

## The field minimum identifies the doubled cells

In every arm the field reads `lo = 1.6000`, `hi = 1.7500`:

- a single cell keeps a reserve and settles at `c* = M + income - income/r = 1.75`
- a doubled cell is emptied every round and settles at `M*r = 1.6`

So the field is a readable record of crowding: the minimum tells you doubled
cells exist, and the maximum tells you single cells exist. `two_equilibria_differ`
in `laws/Medium/Field.lean` proves the two values cannot coincide.

## Uneven fields: the gradient is worst

EXP-62 compared three fields at 20k steps, all with mean level 2.0:

| field | alive | doubled | field lo | field hi |
|---|---|---|---|---|
| uniform | 50 | 10 | 1.6000 | 1.7500 |
| gradient (2.4 → 1.6) | **33** | 3 | 1.3903 | 2.1483 |
| alternating (2.4 / 1.6) | **60** | 20 | 1.3500 | 1.9200 |

The gradient is the **worst** field, not the best. That is the opposite of what
"sighted organisms walk toward food" predicts. The alternating field, where rich
and poor cells are adjacent, is the best.

This is not yet explained. Two candidate accounts, neither tested:

1. In a gradient an organism that climbs to the rich end finds it crowded and
   must walk back down, paying `move_cost` both ways. In an alternating field a
   rich cell is always one step away, so the walk is short.
2. The gradient's poor end (`1.6`) is below `income + need = 1.6`, so a cell
   there gives exactly what is needed and nothing more. The alternating field's
   poor cells may be visited and left before they are drained.

## What this does not prove

- It does not give a closed form for 47. It is measured, at one seed and one
  set of parameters.
- It does not prove 47 is the limit for all seeds: EXP-61 saw 46 at seed 1.
- The 20k arm had not converged (50, still falling). Any earlier capacity
  number read at 20k steps is a snapshot — this includes the 80 of EXP-09.
- The gradient result contradicts the "walk toward food" intuition and is
  unexplained. Do not cite "a gradient helps" — the measurement says it hurts.
- The food-supply argument shows food is not *binding*; it does not show food
  plays no role in the deaths that step the population down.

## The lesson

Three experiments in a row read a different "capacity": 80 (EXP-09), 46
(EXP-61), 50 (EXP-62), 47 (EXP-63). Only the last two are the same quantity
measured at different lengths. Before quoting a population number, the series
has to be flat — not the final frame. A single frame cannot tell a steady state
from a slow decline.
