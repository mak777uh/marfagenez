# FINDING: the death threshold is `income − damage·repair`, and it is the mover's

2026-11-12. Follows `docs/FINDING-the-capacity-finding-was-reading-its-own-input.md`,
which established that nothing dies at the settings the capacity work used. This
note finds the settings where something does die, and names the term that sets
the boundary.

## The arithmetic, registered before the run

Two candidate thresholds. A **sitter** eats its own cell down to
`c* = M − income(1−r)/r`; a **mover** always finds a full cell and takes
`income`. Each pays `maintenance` to live and `damage_rate × repair_cost` to
clear one step's damage.

```
sitter threshold  = c* − damage·repair
                  = (2.0 − 1.2·0.8/0.8·... ) − 0.03
                  = 1.7 − 0.03 = 1.67

mover threshold   = income − damage·repair
                  = 1.2 − 0.03 = 1.17
```

The two are 0.5 apart. Which one the field shows is a measurement, not a choice.

## The sweep (EXP-67)

`n = 160`, `cells = 40`, `E_max = 10`, `sighted`, read budget 3, uniform field,
8000 steps, maintenance 0.6 → 2.2 in steps of 0.1.

| maintenance | COST | alive | occupied | energy mean |
|---|---|---|---|---|
| 0.6 | 0.63 | 42 | 40 | 9.3481 |
| 0.7 | 0.73 | 40 | 40 | 9.2700 |
| 0.8 | 0.83 | 40 | 40 | 9.1700 |
| 0.9 | 0.93 | 40 | 40 | 9.0700 |
| 1.0 | 1.03 | 40 | 40 | 8.9700 |
| 1.1 | 1.13 | 38 | 38 | 8.8684 |
| 1.2 | 1.23 | **0** | 0 | — |
| 1.3 … 2.2 | | **0** | 0 | — |

Two things to read, and both are exact:

1. **The collapse is between 1.1 and 1.2**, not between 1.6 and 1.7. The field
   shows the mover's threshold, not the sitter's. These organisms are eating
   fresh cells, not their own steady cell.
2. **The energy is `E_max − COST` to four decimals** at every surviving
   setting: 9.2700 = 10 − 0.73, 9.1700 = 10 − 0.83, 9.0700 = 10 − 0.93,
   8.9700 = 10 − 1.03. Not approximately. Exactly.

## The bisection (EXP-68)

Bisecting `maintenance` in [1.1, 1.2] to 1e-4:

| maintenance | alive | energy mean |
|---|---|---|
| 1.150000 | 40 | 8.820000 |
| 1.175000 | 0 | — |
| 1.162500 | 40 | 8.807500 |
| 1.168750 | 40 | 8.801250 |
| 1.171875 | 0 | — |
| 1.170312 | 0 | — |
| 1.169531 | 40 | 8.355919 |
| 1.169922 | 40 | 5.230919 |
| 1.170117 | 0 | — |
| 1.170020 | 22 | 0.680114 |

**Threshold = 1.170068. Predicted = 1.170000. Distance = 6.8e-5.**

The last two rows are the threshold itself: at 1.170020 twenty-two organisms are
still alive at step 8000, at mean energy 0.68. They are on their way out. The
threshold is not a cliff, it is where the queue finishes.

## Why the energy is exactly `E_max − COST`

At the cap the take is truncated: `energy = min(energy + income, E_max)` gives
nothing. So an organism at the cap loses `maintenance + damage·repair` per step,
and the next take refills it to the cap. The energy it is *seen* at, sampled at
the end of a step, is therefore

```
E_steady = E_max − (maintenance + damage·repair) = E_max − COST
```

This is not a fitted constant. It is what the truncation does.

## Formalised

`laws/Medium/DeathLaw.lean`, 8 theorems, builds with 0 errors:

- `netPerStep income maintenance damageRate repairCost := income − maintenance − damageRate·repairCost`
- `deathThreshold income damageRate repairCost := income − damageRate·repairCost`
- `net_zero_iff_maintenance_eq_threshold` — the threshold is the zero of the net
- `net_pos_of_maintenance_lt_threshold` / `net_neg_of_threshold_lt_maintenance`
- `steadyEnergyAtCap eMax maintenance damageRate repairCost := eMax − (maintenance + damageRate·repairCost)`
- `threshold_iff_steady_energy_eq` — **the two measurements are one statement**:
  `maintenance = income − d·r` iff `steadyEnergyAtCap = E_max − income`
- `stepsToDeath` and `stepsToDeath_pos_iff` — death is certain exactly above the
  threshold, after `E_max / (maintenance + d·r − income)` steps (333.33 at
  maintenance 1.2)
- `mover_threshold_below_sitter_threshold` — the mover's threshold is below the
  sitter's whenever `income < c*`, which is why 1.17 and 1.67 are different
  numbers and only one of them is the field's

## What this does not prove

- **That a mover always finds a full cell.** It does at crowding 4.00 with 40
  cells and read budget 3. At higher crowding the take per step falls below
  `income`, the net shrinks, and the threshold moves down. The law above is the
  threshold in the regime where a mover can always find a full cell.
- **Anything about the sitter regime.** The sitter threshold 1.67 was never
  observed, because no organism in these runs sits. To observe it the organisms
  would have to be denied movement (`--move-cost` high enough, or `--policy
  stay`), and that is a different experiment.
- **Anything about the damage path.** `damage_rate × repair_cost` was assumed to
  be the per-step repair bill. It was never varied independently: only
  `maintenance` was swept. The decomposition `COST = maintenance + damage·repair`
  is consistent with the data but not separated by it.

## The mistake this round, repeated

The first version of EXP-67 reported `alive = 160` at every maintenance,
including 2.2, while the energy mean fell to 0.0000. The tell was in the same
row: an organism with zero energy reported as alive.

The cause was in the check, not the model: `samples()` returns one entry per
**slot**, dead or alive, and the check counted the list length. That is the same
error as reading `--n` back out as the population, one layer down — the slots
are an input, the survivors are the measurement.

`Sample` carries an `alive` field. It was there the whole time. The fix is one
line: `living = [s for s in samples if s["alive"]]`.

**Rule added to `PROTOCOL.md`:** when a count comes from a list, ask what the
list is indexed by before using its length. A list of slots is not a list of
survivors.
