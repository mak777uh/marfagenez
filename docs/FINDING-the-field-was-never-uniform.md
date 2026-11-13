# FINDING: the field was never uniform — 0.88 is `M·r`, the starved fixed point

Date: 2026-11-12
Status: measured, arithmetic closed, three numbers exact

## What was believed

`--field uniform` builds `Field::new(cells, (rich + poor) / 2, regrow)`, so
every cell starts at the same level and every ceiling is the same. EXP-31
therefore treated the field as flat and predicted that any movement is pure
cost, so `stay` should be best.

The measurement contradicted that: `sighted` kept 106 organisms where `stay`
kept 72. EXP-31's `silent` control asserted that the two must hash the same,
fired, and the check went `passed -> failed`.

## What is actually there

The field is not flat after one step. A census of the last frame at
`M = 1.1`, `income = 1.0`, `regrow = 0.8`, `damage-rate = 0.2`:

| policy  | field value | cells |
|---------|-------------|-------|
| stay    | 0.88        | 72 (all occupied) |
| stay    | 1.10        | 48 (all empty)    |
| sighted | 0.88        | 92 |
| sighted | 0.8912      | 14 |
| sighted | 1.056       | 14 (all empty)    |

A fine trace (`--every 1`) shows the two-level field is reached at **step 2**
and does not move for the remaining 1198 steps. Deaths happen at step 26
(120 -> 72).

## The arithmetic

One step on a cell held by one organism is: take `min(income, c)`, then
regrow `c + (M - c)·r`. There are two regimes.

**Saturated** (`c >= income`, so the take is the full `income`):

    c' = (c - income) + (M - (c - income))·r
    c* = M + income - income/r

**Starved** (`c < income`, so the take empties the cell and regrow starts from 0):

    c' = 0 + (M - 0)·r
    c* = M·r

With `M = 1.1`, `income = 1.0`, `r = 0.8`:

    saturated:  c* = 1.1 + 1 - 1/0.8 = 0.85
    starved:    c* = 1.1 × 0.8       = 0.88

The measurement is **0.88**, so the field sits in the **starved** regime. The
two regimes coincide exactly when `income = M·r`; here `M·r = 0.88 < income = 1`,
so every occupied cell is emptied every step and only regrowth feeds it.

The other two measured values follow from the same rule:

    0.88  -> one regrow  -> 0.88 + (1.1 - 0.88)·0.8 = 1.056   (a vacated cell)
    1.056 -> take 1      -> 0.056
    0.056 -> one regrow  -> 0.056 + (1.1 - 0.056)·0.8 = 0.8912 (a cell just entered)

Both are exact to the printed digits.

## What this means for EXP-31

The anomaly is not an anomaly. `stay` is not "free" — it is starvation. An
organism that never moves sits on a cell pinned at `M·r = 0.88`, takes 0.88,
and lives on 0.88 per step. A `sighted` organism that moves onto a cell that
has been empty for a step finds 1.056, which is 20% more. That is why it keeps
more organisms, and it is the opposite of the hypothesis the check was written
to test.

The `silent` control was right to fire: in a *truly* flat field `sighted` and
`stay` must hash identically, and they do — verified directly at two levels
(`M = 1.1` and `M = 2.0`), where both arms gave the same hash
(`9b3ef3ce95c7deef` and `a972dee8bb087e7f`). The control failed because the
field is not flat, not because the control is wrong.

## What this does not prove

- It does not prove `0.88` is a *stable* fixed point for any `M`, `income`,
  `r`. It is the fixed point of the one-organism-per-cell map; with `k`
  organisms on a cell the take is `k·income` and the level is lower.
- It does not explain the 14 cells at 0.8912 beyond "entered this step". The
  count 14 equals the number of cells `sighted` vacated, which is consistent
  with a rotation, but a rotation was not measured directly.
- It does not say which regime a *general* parameter set lands in. The
  condition is `income <= M·r` for starved; `M = 1.1, r = 0.8` gives `M·r = 0.88`,
  and `income = 1.0` exceeds it. A run with `income = 0.5` would be saturated
  and would settle at 0.85, not 0.88.
- It does not repair the 27 checks that ran on the default level. Those were
  re-run at their declared level; this finding says the level was only part of
  what was unwritten, because `regrow` and `income` also decide the regime.

## The lesson

**A field is not flat because you built it flat.** `Field::new` sets the level
and the ceiling, but the level after one step is decided by the take and the
regrow, and those depend on `income`, `regrow` and `M` together. The regime
boundary `income = M·r` is a condition nobody wrote on the command line, and it
decided the answer.

`--field uniform` names the *initial* state. It does not name the *steady*
state, and the steady state is what the capacity measurement reads.
