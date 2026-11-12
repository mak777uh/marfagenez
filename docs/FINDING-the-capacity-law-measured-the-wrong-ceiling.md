# The capacity law was measuring the wrong ceiling

**Date:** 2026-11-12
**Experiment:** `checks/exp52_capacity_vs_income.py`
**Result:** `results/EXP-52/run-2026-11-12T22-03-53.json` — verdict `failed`
**Supersedes:** `docs/FINDING-capacity-is-a-cliff.md`

## What was claimed

EXP-32 swept `maintenance` and found six points matching

```
cost  = maintenance + damage*repair
k_max = 0                                    if income < cost
      = 1 + floor((M*r - cost)/income)        otherwise
capacity = k_max * cells
```

Six points, all six matched, verdict `passed`. The document called it
"capacity is a cliff, not a slope".

## What broke it

EXP-52 swept the other axis — `income`, with `maintenance` fixed at 0.6. The
formula uses `income` twice: as the feasibility gate and as the divisor. The
maintenance sweep only ever exercised the numerator, so it could not tell
whether the divisor was right.

Measured (uniform field, sighted, `cells = 40`, `M = 2.0`, `r = 0.8`,
`maintenance = 0.6`, `damage = 0.02`, `repair = 1.5`, `n = 160`, 2000 steps):

| income | measured alive | EXP-32 formula | |
|-------:|---------------:|---:|---|
| 0.60 | 0 | 0 | ok |
| 0.70 | 79 | 80 | −1 |
| 0.90 | 80 | 80 | ok |
| 0.95 | 80 | 80 | ok |
| 1.00 | **53** | **40** | **+13** |
| 1.20 | 42 | 40 | +2 |
| 1.60 | 40 | 40 | ok |

At `income = 1.00` the formula says `k_max = 1`, so at most one organism per
cell, so at most 40. The measurement has 53 alive. It cannot be a rounding
error: 53 > 40.

## Why 53 is possible

The formula assumed an organism can take at most `income` from a cell, so a
cell's worth is `M*r` and the number of organisms that worth can pay for is
`(M*r - cost)/income`.

But `Field::take` (`core/src/field.rs:188`) is

```rust
let taken = self.cells[cell].min(amount);
```

The cap is `income`, and what is actually there is the cell's stock. And the
cell's stock is not `M*r` — it is the equilibrium of the field law, which
after the 2026-11-12 formula fix is

```
c* = M + income - income/r
```

At `income = 1.0`, `r = 0.8`: `c* = 2.0 + 1.0 - 1.25 = 1.75`. The first
organism takes `min(1.75, 1.0) = 1.0`, leaving 0.75. The second takes
`min(0.75, 1.0) = 0.75`, which is above `cost = 0.63`. **The second organism
lives.** The formula said it could not, because it compared `income` to `cost`
instead of comparing what is left to `cost`.

Measured second-occupant `taken` values: 0.60, 0.72, 0.744, 0.749, 0.75.
The 0.75 ones are exactly `c* - income`. The 0.60 ones are below `cost` and
those organisms are dying (energies 7.45 and 7.85 against a ceiling of 9.37).

## The corrected law

```
c*    = M + income - income/r
k_max = 0                                    if income < cost
      = 1 + floor((c* - cost)/income)        otherwise
```

The first branch is unchanged and still necessary: if `income < cost`, one
organism eating its full cap still starves, so no number of them survives.
That is why the naive `c*`-only version predicts 120 at `income = 0.60` where
the measurement is 0.

Checked on all seven points:

| income | c* | k_max | k_max*cells | measured | |
|-------:|---:|---:|---:|---:|---|
| 0.60 | 1.850 | 0 | 0 | 0 | ok |
| 0.70 | 1.825 | 2 | 80 | 79 | −1 |
| 0.90 | 1.775 | 2 | 80 | 80 | ok |
| 0.95 | 1.763 | 2 | 80 | 80 | ok |
| 1.00 | 1.750 | 2 | 80 | 53 | −27 |
| 1.20 | 1.700 | 1 | 40 | 42 | +2 |
| 1.60 | 1.600 | 1 | 40 | 40 | ok |

## The remaining gap is not noise — it is the difference between a ceiling and what is reached

`k_max * cells` is an **upper bound on how many organisms the field can hold**,
not a prediction of how many it will hold.

At `income = 1.00` the bound is 80 and the measurement is 53. The 53 organisms
sit on 39 of the 40 cells: 25 cells with one, 14 cells with two, none with
three. The bound is not reached because

- `sighted` moves only to an adjacent cell, so a free cell next to a
  double-occupied one is not necessarily found, and
- sharing is strictly worse than being alone (`taken` falls from 1.0 to 0.75),
  so there is no reason for an organism to seek a crowded cell, and nothing
  that pushes the second occupant out.

EXP-32's six points matched because in that regime the bound happened to be
reachable. Matching six points along one axis was not evidence that the
formula described the mechanism; it was evidence that six points were
saturated.

At `income = 1.20` the measurement is 42 against a bound of 40 — **above the
bound**. That is the one number in this table that the corrected law does not
explain, and it is recorded rather than smoothed.

It was chased down and it is not a rounding error. Sampling every 1000 steps
for 8000 steps (`core/results/sighted/trace-sighted-1794521085.json`):

| step | alive | double-occupied cells | second occupant energy / taken |
|---:|---:|---:|---|
| 1000 | 42 | 2 | 9.14 / 0.50, 7.99 / 0.50 |
| 2000 | 42 | 2 | 9.24 / 0.50, 8.45 / 0.50 |
| 3000 | 42 | 2 | 9.01 / 0.50, 8.09 / 0.50 |
| 4000 | 42 | 2 | 8.91 / 0.50, 9.24 / 0.50 |
| 5000 | 42 | 2 | 8.91 / 0.50, 9.24 / 0.50 |
| 6000 | 42 | 2 | 7.77 / 0.48, 8.68 / 0.50 |
| 7000 | 42 | 2 | 8.68 / 0.50, 7.30 / 0.50 |
| 8000 | 42 | 2 | 9.14 / 0.50, 8.68 / 0.50 |

The count is exactly 42 at every sample, and exactly 2 cells are double-occupied
at every sample — but **which cells** changes every sample (11, 3, 6, 7, 10, 1,
11, 9). The second occupant takes 0.50 against `cost = 0.63`, a loss of 0.13 per
step, and its energy wanders between 7.3 and 9.24 instead of falling to zero
over 8000 steps.

So the second occupant is not the same organism twice: the pair is **rotating**.
An organism that finds itself second moves away, takes a cell of its own, eats
1.20 and recovers; another one arrives, becomes second, and leaves in turn. The
42 is 40 saturated cells plus 2 positions that are continuously being vacated
and refilled.

That is a dynamical quantity, not a capacity. It depends on how fast an
organism can leave a bad cell compared to how fast it starves there, which
depends on `move_cost`, `read_budget`, the movement rule and the field kind.
The formula has no place to put any of those, which is the real reason it does
not fit this point. **No fourth version of the formula was attempted**: a
formula that needs the movement rule in it is a description of the dynamics,
not a law about the field.

## What this does not prove

- One seed, one field kind (uniform), one policy (sighted), 2000 steps.
- The two thresholds are bracketed only to 0.05 (`0.60/0.70` and `0.95/1.00`).
- `c* = M + income - income/r` is the equilibrium of the **undisturbed** field
  law. Under sighted movement the field is disturbed every step, so using `c*`
  in the formula is an approximation whose error is not measured here.
- The claim that sharing is why the bound is not reached is an inference from
  `taken` values, not a controlled result. No experiment has varied the
  movement rule to see whether the shortfall moves with it.
- Nothing here touches the gradient-field result of EXP-31, where sighting
  loses to standing still.

## What changed in the repo

- EXP-32's document is marked superseded; its verdict stays `passed` because
  its controls passed and its numbers were real — what was wrong was the
  interpretation, not the measurement.
- EXP-52 is `failed`, and stays `failed`. The formula under test did not
  describe the income axis.
- The corrected law is written here, not in Lean. It is not proved.
