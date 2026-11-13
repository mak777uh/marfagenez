# The default level was a condition nobody wrote

**Date:** 2026-11-13
**Status:** guard added, 27 checks repaired, 2 checks were already broken

## What happened

`core/src/bin/trace.rs` built a uniform field as `(rich + poor) / 2` with
`rich = 2.0, poor = 0.2` as defaults. So `--field uniform` without levels
silently built a field at `M = 1.10`, not the `M = 2.0` most checks assumed.

EXP-75 measured 42 survivors where the capacity law predicted 400. The gap was
not a counterexample to the law: the field was at 1.10, `k_max = 1`, and
`C = 1 × 40 = 40`. The four-point M sweep (`M = 1.10, 1.60, 2.00, 3.00`)
matched the law on all four points, and the cell-level formula
`max(M − k·t·(1−r)/r, M·r)` matched on all four (0.8800 / 1.3000 / 1.7000 /
2.4000).

## The guard

`trace.rs` now refuses to run:

```
refusing to run: --field uniform without both --rich and --poor.
             The defaults are rich 2.0, poor 0.2, so this would build a
             field at M = 1.10 -- a level nobody chose. Pass the level you
             mean, e.g. --rich 2.4 --poor 1.6 for M = 2.0.
```

Exit code 2. Six cases verified:

| case | exit | refused |
|---|---|---|
| uniform, no levels | 2 | yes |
| uniform, only `--rich` | 2 | yes |
| uniform, only `--poor` | 2 | yes |
| uniform, both levels | 0 | no |
| alternating, no levels | 0 | no |
| gradient, no levels | 0 | no |

## The debt

The guard turned a silent wrong answer into a loud refusal, and that exposed
**27 checks that had been running at M = 1.10**. All 27 now pass explicit
levels. 20 were patched mechanically, 7 needed the single-quoted form.

Re-run at declared levels, the verdicts did not change:

| experiment | before | after |
|---|---|---|
| exp32 pair-penalty-or-queue | failed | failed |
| exp33 unevenness-or-regrowth | failed | failed |
| exp34 unevenness-or-move-cost | passed | passed |
| exp35 indifference-point | failed | failed |
| exp36 crossing-shape | passed | passed |
| exp37 crossing-is-death | failed | failed |
| exp38 death-budget-exact | failed | failed |
| exp39 damage-never-accumulates | passed | passed |
| exp40 death-budget-closed | failed | failed |
| exp41 nomad-two-thirds | failed | failed |
| exp42 refused-move-is-paid | failed | failed |
| exp43 where-the-extra-cost-comes-from | failed | failed |
| exp44 readout-is-off-by-one-step | passed | passed |
| exp45 off-by-one-does-not-touch-counts | failed | failed |
| exp46 standing-is-the-policys-own-branch | passed | passed |
| exp47 standing-is-a-uniform-third | passed | passed |
| exp48 where-the-sevenfold-gap-goes | passed | passed |
| exp49 income-tracks-stock | passed | passed |
| exp10 capacity | failed | failed |
| exp31 moving-in-uniform-field | passed | **failed** |

**exp31 changed.** It was `passed`, now `failed`. That is the one result the
level actually moved, and it needs a look.

## Two checks were already broken

- `exp50_regrowth_sets_the_income.py` calls `run(['--regrow', '0.2', '--n', '0'])`.
  `Field::new` cannot build a cycle with zero cells (`cannot build the cycle`),
  so this check has never run. Its `passed` verdict in `results/` predates the
  `--n 0` line or was written by a different version.
- `exp31` and `exp10` also needed `--read-budget 3`: `--policy sighted` with
  budget 0 is refused by an earlier guard, because a sighted organism that
  reads nothing is a `stay` organism wearing a different name.

## What this does not prove

- That the 27 results are *correct*. They now run at a declared level; that
  says nothing about whether the measurement answers the question it claims.
- That `M = 1.1` was wrong for every one of them. For the checks that pass
  `--income 0 --regrow 0` the field never moves and M is irrelevant. What the
  guard buys is that the level is now written down in every case.
- That no other default is doing the same thing. `--capacity`, `--energy`,
  `--damage-rate`, `--maintenance` all have defaults too. The uniform-field
  case is the one that got caught because a hash refused to change.

## The lesson

**A default is a condition nobody wrote.** The run looked fine, the hash was
stable, the JSON was well-formed, and the field was at a level no one chose.
The only reason it was found is that four different `move_cost` values gave
the same hash — an invariance that should not have existed.

The general form: when a parameter has a default, a check that does not pass it
is testing the default, not the hypothesis. The fix is not to remember to pass
it; it is to make the tool refuse when the answer depends on a value the caller
did not supply.
