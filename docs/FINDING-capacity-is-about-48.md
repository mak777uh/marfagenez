# The capacity of the field is about 48, not 80

**Date:** 2026-11-13
**Experiment:** `checks/exp59_capacity_sweep.py`
**Result:** `results/EXP-59/run-2026-11-13T01-37-10.json` (verdict `passed`)

## What was wrong before

`FINDING-static-count-is-a-ceiling.md` computed the static bound as
`cells * k_max = 40 * 2 = 80` and then noted, correctly, that the measured
population of 46 was *below* the bound. The note was rewritten to say
"the static count is a ceiling, not the capacity" and stopped there.

It stopped one step too early. **If the bound were 80, starting at 80 would
lose nobody.** The field loses 34. That contradiction was already visible in
the number the note was written about, and the note treated it as a detail.

## The sweep

`n` from 10 to 160, 200 000 steps, `sighted`, `uniform` field at `M = 2.0`,
`r = 0.8`, `need = 0.6`, `income = 1.0`, 40 cells, `move_cost = 0.05`.

| n | alive | cells used | max crowd | survived |
|---:|---:|---:|---:|---:|
| 10 | 10 | 10 | 1 | 100.0% |
| 20 | 20 | 20 | 1 | 100.0% |
| 30 | 30 | 30 | 1 | 100.0% |
| 40 | 40 | 40 | 1 | 100.0% |
| 50 | 47 | 40 | 2 | 94.0% |
| 60 | 48 | 40 | 2 | 80.0% |
| 70 | 47 | 40 | 2 | 67.1% |
| 80 | 46 | 40 | 2 | 57.5% |
| 120 | 46 | 40 | 2 | 38.3% |
| 160 | 42 | 40 | 2 | 26.2% |

Two flat regions:

1. **`n <= 40`: nobody dies.** Every organism gets its own cell and takes the
   full `income = 1.0`.
2. **`n >= 50`: the population saturates at 42–48.** The extra organisms do not
   add capacity; they die.

The capacity is therefore **about 48**, and it is not `cells * k_max`.

## Why the second occupant barely helps

The steady cell value with one occupant is

    c* = M + income - income/r = 2 + 1 - 1.25 = 1.75

measured directly: the field settles at **1.75**, not at 1.6.

A second occupant eats what the first left: `1.75 - 1.0 = 0.75`. Its net per
step is

    0.75 - 0.6 - 0.05 - 0.02*0.5 = +0.09

which is positive but thin. When the cell is still recovering from a previous
double occupancy it is closer to `M*r - income = 0.6`, and the net becomes

    0.6 - 0.6 - 0.05 - 0.01 = -0.06

which is a slow death.

So `k_max = 2` is arithmetically true and practically almost worthless: the
second seat exists, but it pays only if it always lands on a fully recovered
cell. In a field where organisms move, that is rare. Measured: 40 cells hold
45 organisms, so only about 5 of 40 cells carry a second occupant, not 40.

## The correction to the earlier arithmetic

The earlier note used `c = M*r = 1.6` as the cell value under load. That is the
value *after* a full take and one regrow, not the steady state. The steady state
under one occupant is 1.75, and the difference `1.75 - 1.6 = 0.15` is exactly
the margin that decides whether the second seat is viable.

The general law, proved in Lean (`Medium/Field.lean`, `fixed_point`):

    c* = M - t*(1 - r)/r   (equivalently M + t - t/r)

with `t = income` when the cell is not limiting.

## What this does not prove

- It does not say the saturation value is sharp. The 10M-step run showed the
  count still drifting down by one or two (46 → 45), so 48 is an upper estimate.
- It does not separate the move cost from the damage cost as the reason the
  second occupant fails. Both are small and both are subtracted.
- It does not say which cells admit a second occupant.
- `n = 160` giving 42 rather than 46-48 is unexplained; the trend is weakly
  downward with `n`, which suggests the deaths take longer to settle at higher
  initial density rather than that capacity depends on `n`.

## What this changes

- `FINDING-static-count-is-a-ceiling.md` should be read as: the static count is
  a ceiling that is **not reachable**, and the reason it is not reachable is the
  margin `c* - M*r = 0.15`.
- The `k_max` formula is a bound on *sustained* occupancy, and the sustained
  occupancy of a moving population is about `cells * 1.15`, not `cells * k_max`.
