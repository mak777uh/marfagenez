# FINDING: the corrected equilibrium predicts the measured capacity exactly

**Date:** 2026-11-13
**Status:** confirms a formula correction made on 2026-11-12/13
**Verdict:** the corrected law `c* = M + t - t/r` reproduces the measured
capacity `C = 80` with no free parameter. The old law `c* = M - t/r` predicts
`C = 40`, which the measurement rules out.

---

## What was in doubt

On 2026-11-12 the order of the step in `core/src/organism.rs` turned out to be
wrong: the model regrows *after* the take, not before.

```
wrong:  c_next = c + (M - c) * r - t
right:  c_next = (c - t) + (M - (c - t)) * r
```

The equilibrium moved with it:

```
wrong:  c* = M - t/r
right:  c* = M + t - t/r
```

This was fixed in `laws/Medium/Field.lean` and `laws/Medium/Convergence.lean`
and verified by sympy (`c_next(c*) - c* = 0`). But a formula that satisfies
its own algebra is not yet a formula that describes the world. The question
left open was: **does the corrected law still predict the numbers that were
measured before the correction?**

If it did not, either the correction was wrong or the measurement was.

---

## The arithmetic

Parameters of the capacity experiments (`checks/exp*.py`):

```
cells = 40,  M = 2.0,  r = 0.8,  income = 1.2,  maintenance = 0.2
```

The equilibrium level of a cell with `k` organisms drawing `t` each:

```
c*(k) = M + k*t - k*t/r
```

The number of organisms a cell can hold is the largest `k` whose level still
covers the maintenance cost:

```
k_max = 1 + floor((c*(1) - maintenance) / income)
```

With the two candidate laws:

| law | `c*(1)` | `k_max` | `C = 40 * k_max` | measured |
|---|---|---|---|---|
| old `M - t/r` | 0.5000 | 1 | **40** | 80 |
| new `M + t - t/r` | 1.7000 | 2 | **80** | **80** |

The corrected law gives 80. The measurement is 80. The old law gives 40.

Reproduce: `python3 checks/capacity_check.py`.

---

## Why this matters more than a fit

`k_max` is a **floor**, so it is a discontinuous function of the parameters.
Matching a discontinuous prediction is much harder to do by accident than
matching a continuous one: the old law does not miss by a little, it misses by
a whole seat per cell (40 vs 80, a factor of two).

The correction was made for an independent reason — the order of the step was
read out of the code, not fitted to this number. The capacity measurement was
taken earlier, for a different purpose. So this is a **prediction that was
already in the data**, made before the formula changed, and it came out right.

That is the strongest kind of confirmation this project can produce without a
new experiment: not "the formula was fitted and matches", but "the formula was
fixed elsewhere and an old number moved onto it".

---

## What this does not prove

1. **It does not prove the law is true.** One parameter set matching one
   integer is a consistency check, not a law. `k_max` is a floor, so it is
   insensitive to `c*` within a band: any `c*(1)` in `[1.4, 2.6)` gives
   `k_max = 2` and therefore `C = 80`. The measurement cannot distinguish
   `c* = 1.7` from `c* = 1.5` or `c* = 2.5`. The law is confirmed only to
   within the width of that band.

2. **It does not explain the second seat.** The level permits about 5
   occupants (`k* = (c*(1) - maintenance) * r / (income * (1 - r)) = 5.0`),
   while `k_max` says 2. The two are different questions: `k_max` asks whether
   the cell still holds an income after `k` take, and the level asks whether
   the level is still above maintenance. The measurement agrees with `k_max`,
   not with the level, and **why** is not settled here. A candidate is that
   the second occupant cannot out-earn the first and so does not stay, but
   that has not been measured.

3. **It does not touch the crowding-2 question.** Crowding 2.00 is what `C = 80`
   on 40 cells means arithmetically. It is not a separate finding.

---

## What to do next

- Find a second parameter set where the old and new laws predict **different**
  `k_max`, and run it. One match is a consistency check; two matches at
  different floors would be much harder to get by accident.
- Measure `c*` directly in a trace rather than inferring it from `k_max`.
  The band `[1.4, 2.6)` is wide; a direct read of the settled level would
  narrow it to the trace's precision.
- The `k* = 5` vs `k_max = 2` gap is the next real question. It is the same
  question as "why does the second seat go unfilled", asked with numbers.
