# The surplus is gated by the energy ceiling, and the gate is derivable

**Date:** 2026-11-12
**Experiments:** EXP-54 (surplus price), EXP-55 (energy ceiling)
**Supersedes:** the "closed form is missing" section of
`FINDING-the-surplus-has-a-price.md`.

## The question EXP-54 left open

EXP-54 established that the surplus above the capacity bound is bought with
movement, that it costs `move_cost`, and that there is a price threshold in
`(0.15, 0.18)` at income 1.2. It did not explain the threshold's *value*. I
wrote at the time that fitting `move_cost* ≈ 0.16` would repeat the error
EXP-52 found in the capacity law.

There is now a derivation, and it came out of two failed runs.

## Two runs that agreed with each other and were both wrong

The first version of EXP-55 varied the number of cells at `--capacity 2.0`
and measured surplus 0 at 20, 40 and 80 cells. The second varied `--capacity`
from 1 to 10 at 40 cells and measured 0 everywhere. Both contradicted EXP-54's
+2, and both were self-consistent, which is the dangerous case.

The cause was a misread flag:

- `--capacity` is **the most energy an organism can hold**
  (`core/src/organism.rs:61`, enforced at `organism.rs:164` as
  `energy.min(world.capacity)`). It is not a per-cell occupancy limit.
- The field's maximum level `M` is set by `--rich` and `--poor`, because
  `uniform` is `(rich + poor) / 2`. Their defaults are `2.0` and `0.2`, so a
  run that does not state them has `M = 1.1`, not `2.0`.

At `M = 1.1`: `c* = 1.1 + 1.2 - 1.5 = 0.80`, the first taker gets
`min(0.8, 1.2) = 0.80` and nets `+0.17`, and the second taker gets
`min(0, 1.2) = 0` and nets `-0.63` — it dies immediately. Surplus 0 was the
correct answer to a different question.

This is the arithmetic-before-run rule (§1) failing in a way it usually does
not: the arithmetic in the docstring said `M = 2.0` and the command line did
not. The numbers were right, the run was not the one described.

## The first explanation, and why it is dead

A second occupant of a cell takes `min(c* - income, income) = 0.50` and pays
`cost = 0.63`, so it loses `0.13` per step. Starting from a full tank it can
survive at most `E_max / 0.13` steps. The first explanation was:

```
E_max > 0.13 * T_rot        (T_rot = rotation period)
```

with `T_rot` read off the gate position as 62–69 steps.

**This was circular and is now refuted.** `T_rot` was computed backwards from
where the gate sat, so the inequality was guaranteed to hold there and said
nothing anywhere else. `checks/measure_rotation.py` measured it directly, with
`--every 1` and per-cell double-stretch accounting:

| E_max | completed stretches | median | mean | max |
|---:|---:|---:|---:|---:|
| 8 | 6359 | **1** | 1.2 | 25 |
| 9 | 6359 | **1** | 1.2 | 25 |
| 10 | 6359 | **1** | 1.2 | 25 |

The rotation period is **one step**, not 62–69. The derived inequality would
put the gate at `E_max > 0.13`, seventy times below where it is. And all three
`E_max` values give identical stretch statistics, so the stretch distribution
does not carry the difference between the arms at all.

The gate itself is real and reproducible. The reason given for it is not.
See `FINDING-the-tank-explanation-is-wrong.md`.

## What was measured

Fixed: uniform field, `M 2.0` (`--rich 2.4 --poor 1.6`), `regrow 0.8`,
`income 1.2`, `n 160`, `cells 40`, `move_cost 0.10`, `read_budget 3`,
8000 steps, seed 20250101.

| E_max | survive (E_max/0.13) | alive | surplus | moved |
|---:|---:|---:|---:|---:|
| 4 | 30.8 | 40 | 0 | 0 |
| 6 | 46.2 | 40 | 0 | 0 |
| 8 | 61.5 | 40 | 0 | 0 |
| **9** | **69.2** | **42** | **+2** | **8** |
| 10 | 76.9 | 42 | +2 | 8 |

The gate is at `E_max = 9`. The surplus is 0 or 2, never 1 — a step, matching
EXP-54's finding that the price threshold is a step too.

**But the 8000-step sample shows a settled value, not the whole story.** At
`E_max = 8` the surplus is present early and decays:

| E_max | 1000 steps | 3000 | 5000 | 8000 |
|---:|---:|---:|---:|---:|
| 8 | +2 | +2 | +1 | **0** |
| 9 | +2 | +2 | +2 | **+2** |

So `E_max = 8` does not forbid the surplus; it fails to sustain it. The two
extra organisms die at steps 3578 and 6804. At 9 and 10 there are no late
deaths. What separates them is the settled energy: at `E_max = 8` every
survivor sits at exactly 7.370 (the cap binds and pins them all), at 9 the
spread runs to 8.370, at 10 to 9.370 — the top is always `E_max − 1.63`.

## The two thresholds are one law

EXP-54 varied `move_cost` and found a gate at `(0.15, 0.18)`. EXP-55 varied
`E_max` and found a gate at 9. Both are real and both are steps. Whether they
are the *same* inequality is now open again: the `T_rot` bridge that joined
them is refuted, so the two gates are currently two separate measured facts
with no shared derivation.

## What this does not prove

- **The mechanism is unknown.** The rotation-period explanation is refuted
  (see above). Nothing has replaced it. The gate is a measured fact without a
  derivation.
- **The decay at `E_max = 8` is unexplained.** Two deaths in 8000 steps, 3226
  apart. The second occupant loses 0.13/step, so 7.37 buys 56 steps of
  continuous loss; the measured longest double stretch is 25. The gap between
  25 and 56 is not accounted for.
- **One seed, one income, cells fixed at 40.** The gate's position as a
  function of those has not been mapped.
- **`0.13` is the loss at income 1.2 only.** At income 1.0 the second share is
  different and so is the gate.
- **No organism identity.** "Rotation" is still inferred from cell indices
  changing between samples.
- **Two discarded runs.** They are recorded in the experiment's limitations
  because they looked like results. A run that states its parameters in prose
  and not in its command line is not a run of the described experiment.

## What changed

The field's capacity statement now has a third clause. Before:

> 40 organisms, and up to 2 more if movement costs less than 0.15/step at
> income 1.2.

After:

> 40 organisms, and up to 2 more if movement costs less than 0.15/step at
> income 1.2 **and the organism can hold at least 9 energy**.

The second clause is a property of locomotion, the third of the organism's
tank. Neither is a property of the field.
