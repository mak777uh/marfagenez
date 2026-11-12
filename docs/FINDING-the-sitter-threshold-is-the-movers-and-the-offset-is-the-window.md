# FINDING: the sitter's threshold is the mover's, and the offset is the window

Date: 2026-11-12
Experiments: `checks/exp69_a_sitter_dies_at_the_same_maintenance.py`,
`checks/exp70_the_threshold_offset_is_the_window.py`
Laws: `laws/Medium/DeathLaw.lean`

## Two things I had wrong, and one I had right for the wrong reason

The previous round registered two death thresholds:

```
mover:  income - damage*repair          = 1.2 - 0.03 = 1.17
sitter: c* - damage*repair = 1.7 - 0.03 = 1.67
```

and measured the collapse at 1.170068, calling it the mover's. That reading of
the sitter is wrong, and it is wrong in a way worth naming: **it subtracts a
cost from a level.**

`c* = 1.7` is the cell *level* a sedentary organism drives its own cell down
to. It is not the amount the organism *takes*. The take is `min(income, level)`,
and at the fixed point that is `min(1.2, 1.7) = 1.2` — exactly a mover's take.
Subtracting `damage*repair` from 1.7 compares litres with litres per step.

The corrected sitter threshold is 1.17, the same as the mover's. The two
separate only when the cell cannot supply a full income at its own fixed point,
`c* < income`, which at M = 2.0, r = 0.8, income = 1.2 means `t > 3.2`.

## What was measured

EXP-69 bisected the collapse maintenance for both policies at the same settings
(n = 160, cells = 40, E_max = 10, uniform field, seed 20250101):

| policy | threshold | distance to 1.17 | distance to 1.67 |
|---|---|---|---|
| `stay` (never moves) | 1.170635 | 0.000635 | 0.499365 |
| `sighted` (moves) | 1.170068 | 0.000068 | 0.499932 |

Both land on 1.17. Neither is anywhere near 1.67. The sitter threshold is the
mover threshold.

The same experiment varied `damage*repair` independently, which the previous
round listed as never having been done:

| damage | repair | damage*repair | predicted | measured | distance |
|---|---|---|---|---|---|
| 0.02 | 1.5 | 0.030 | 1.170000 | 1.170635 | 0.000635 |
| 0.04 | 1.5 | 0.060 | 1.140000 | 1.140635 | 0.000635 |
| 0.00 | 1.5 | 0.000 | 1.200000 | 1.200635 | 0.000635 |

The slope is exactly −1 in `damage*repair`. And the error is **the same
0.000635 at all three points** — which is the second finding.

## The offset is the observation window, not the medium

An error that does not depend on the parameter being varied is not an error in
the law. It is a property of the apparatus.

The apparatus: every organism starts at energy `E_0 = 5.0`
(`core/src/bin/trace.rs:38`), loses `deficit = maintenance + damage*repair -
income` per step, and the trace is read at step `STEPS`. An organism is alive at
the end exactly when

```
E_0 > STEPS * deficit
```

so the maintenance at which the last organism is seen alive is

```
measured threshold = income - damage*repair + E_0 / STEPS
```

With `E_0 = 5.0` and `STEPS = 8000` that is `1.17 + 0.000625 = 1.170625`. EXP-69
measured 1.170635, which is 1e-5 away — inside the bisection resolution.

EXP-70 tested the offset directly, without reference to the law, by changing the
step count:

| STEPS | measured threshold | offset | offset × STEPS |
|---|---|---|---|
| 8000 | 1.170624 | 0.000624 | 4.9902 |
| 16000 | 1.170316 | 0.000316 | 5.0586 |
| 32000 | 1.170155 | 0.000155 | 4.9609 |

The offset halves when the run doubles, and `offset × STEPS` stays at 5.0 (mean
5.0033, spread 0.0977). The offset is `E_0/STEPS`; it vanishes as the run grows.

This is a general trap, not a one-off. **Any threshold measured by "is anything
alive at step N" carries an offset of one starting energy divided by N.** It
looks like a small systematic error in the law and it is not in the law at all.

## Why a mover shares the sitter's threshold

A mover pays `move_cost = 0.10` on every step it moves, so its deficit should be
`maintenance + damage*repair + move_cost - income`, putting its threshold at
1.07, not 1.17. EXP-69 measured 1.170068 for `sighted`.

EXP-70 measured how often a `sighted` organism actually moves:

| maintenance | alive | move fraction | energy mean |
|---|---|---|---|
| 1.000 | 40 | 0.0008 | 8.9700 |
| 1.100 | 38 | 0.1001 | 8.8684 |
| 1.160 | 40 | 0.0003 | 8.8100 |
| 1.190 | 0 | 0.2319 | — |

At the threshold the surviving organisms move on 0.03% of their steps. They are
sitting on full cells and there is nothing to gain by moving, so they do not pay
`move_cost`, and their threshold is the sitter's. The mover's 1.07 is the
threshold of a mover that always moves, which in a crowded field nobody is.

## A new question, not yet answered

The move fraction is not a constant. It is 0.0008 at maintenance 1.0, 0.1001 at
1.1, 0.0003 at 1.16, and 0.2319 at 1.19 — where the population is already dead.
The organisms that move most are the ones that are dying. They are looking for
food, and looking costs energy.

That suggests a testable prediction: **a larger `move_cost` should make a hungry
population die faster than the deficit alone says**, because hunger raises the
move fraction and moving raises the deficit. This is a feedback loop the current
law does not contain. It is not tested here.

## What this does not prove

- One seed, one field shape, one `E_max`. The thresholds are properties of these
  settings.
- The trace samples the last step, so the bisection locates where the population
  is *empty at step 8000*, not where it *dies*. The window offset is exactly the
  difference between those two questions.
- The move fraction is averaged over the whole run, including the transient
  before the field settles. The threshold depends on the late fraction, which is
  not separated here.
- `damage*repair` was varied only through `damage`, with `repair` fixed at 1.5.
  The law says only the product matters; this does not separate the factors.
- The regime where `c* < income` (`t > 3.2` at these settings), where the sitter
  and mover thresholds genuinely differ, is not tested.

## The laws, as they now stand

In `laws/Medium/DeathLaw.lean`, 22 theorems, `lake build` clean:

- `net_zero_iff_maintenance_eq_threshold` — the threshold is the zero of the net.
- `net_pos_of_maintenance_lt_threshold`, `net_neg_of_threshold_lt_maintenance` —
  the sign either side.
- `steadyEnergyAtCap_eq`, `threshold_iff_steady_energy_eq` — the energy the field
  settles at and the maintenance at which the population collapses are the same
  statement.
- `stepsToDeath_pos_iff` — how long a doomed organism lasts.
- `sitterTake`, `sitter_take_eq_income_of_income_le_cStar`,
  `sitter_threshold_eq_mover_threshold`,
  `sitter_threshold_lt_mover_threshold_of_cStar_lt_income` — the units fix, as
  theorems. The old 1.67 is the second of these, and it applies only when
  `c* < income`.
- `windowOffset`, `windowOffset_halves`, `windowOffset_mul_steps`,
  `measuredThreshold`, `measuredThreshold_tends_to_threshold` — the offset is the
  window, and it vanishes as the run grows.
