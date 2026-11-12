> **WITHDRAWN IN ITS CENTRAL CLAIM, 2026-11-12.** The table below is real data
> from real runs, but the rows labelled `n = 160` are not from `n = 160`. A sweep
> of `--n` with everything else fixed shows `alive = n` exactly at every setting
> (40 -> 40, 42 -> 42, 80 -> 80, 120 -> 120, 160 -> 160, 200 -> 200): nothing
> dies, and the "40" and "42" were `--n 40` and `--n 42` read back as results.
> The arithmetic in this note is correct and stands. The measurement is not a
> measurement of capacity. See
> `docs/FINDING-the-capacity-finding-was-reading-its-own-input.md`.
> The text below is left as written, not silently edited.

# FINDING: the carrying capacity is a line, not a number

2026-11-12. Follows the formula correction in `Medium/Field.lean` and the
`k_max = 10` anomaly that was left open in `Medium/Capacity.lean`.

## The anomaly that was left open

After the step was corrected to `(c - t) + (M - (c - t)) * r`, a claim went round
that `k_max` is 10 and the capacity law gives `C = 400`. `Medium/Capacity.lean`
says in its own docstring that this number "does not come from this file and has
not been reproduced". It has now been traced.

`--capacity` is **the energy ceiling `E_max`, not a per-cell occupancy limit**
(`core/src/organism.rs:164`: `energy = (energy + taken).min(world.capacity)`).
Reading `--capacity 10` as `k_max = 10` is the whole of the anomaly. There is no
`k_max = 10` and no `C = 400`.

## The arithmetic before the run

Parameters: `M = 2.0` (the uniform field is built at `(rich + poor)/2 = (2.4 +
1.6)/2`), `r = 0.8`, `income = 1.2`, `maintenance = 0.6`, `damage_rate = 0.02`,
`repair_cost = 1.5`, so the cost of staying alive one step is

    COST = maintenance + damage_rate * repair_cost = 0.6 + 0.03 = 0.63.

The equilibrium of a cell eaten from by one organism is

    c* = M - income * (1 - r) / r = 2.0 - 1.2 * 0.2 / 0.8 = 1.7.

On a cell with two organisms the first takes `min(1.2, 1.7) = 1.2` and the second
takes what is left, `1.7 - 1.2 = 0.5`. Since `0.5 < 0.63`, **the second organism
cannot break even on a steady cell** -- it loses `0.13` per step. So the plain
arithmetic says one per cell, `C = 40`, and a second organism survives only if it
has savings to burn.

The steady-state energy follows from the same numbers: the energy is topped up to
`E_max` and then charged `maintenance` and the repair, so

    E* = E_max - maintenance - damage_rate * repair_cost = E_max - 0.63.

## The measurement

`core/target/release/trace`, `n = 160`, `cells = 40`, `steps = 8000`,
`every = 8000`, seed 20250101, policy `sighted`, read budget 3, uniform field,
`rich 2.4 / poor 1.6`, `regrow 0.8`, `move-cost 0.10`:

| `E_max` | alive | occupied cells | crowding | max per cell | energy mean | energy min | `taken` mean |
|---|---|---|---|---|---|---|---|
| 8 | 40 | 40 | 1.00 | 1 | 7.3700 | 7.3700 | 1.2000 |
| 9 | 42 | 40 | 1.05 | 2 | 8.3481 | 7.6800 | 1.1667 |
| 10 | 42 | 40 | 1.05 | 2 | 9.3481 | 8.6800 | 1.1667 |

`E* = E_max - 0.63` is exact: 8 - 0.63 = **7.37**, 9 - 0.63 = **8.37**, 10 - 0.63
= **9.37**. The means are `0.02` low at `E_max` 9 and 10 because two organisms are
sharing a cell and are rationed below `income`.

## What the numbers say

- **At `E_max = 8` the capacity is 40, one organism per cell.** Crowding is
  exactly 1.00, every cell is occupied, and every organism sits at `7.37` with
  `taken = 1.200`. It eats more than it needs: `1.200 - 0.63 = 0.570` per step is
  thrown away against the ceiling. The field, not the energy, is the limit.
- **At `E_max = 9` and 10 the capacity is 42, and the extra two sit two to a
  cell.** Their energy is `7.68` and `8.68`, i.e. `0.31` above the single-organism
  steady state, which is the savings they are burning at `0.13` per step. They are
  not in equilibrium; they are on a slow slide, and this run stops at 8000 steps
  before it finishes.
- **`C` is therefore not a number.** It is `40` when nothing can afford to share
  and `42` when two organisms have enough savings to share for a while. The
  capacity law `C = cells * k_feed` with a single `k_feed` describes the first
  case and misses the second.

## What this does not prove

- **That 42 is the end state at `E_max` 9 and 10.** The two sharers are losing
  `0.13` per step from a reserve of `0.31`, so the arithmetic says they die after
  about `0.31 / 0.13 = 2.4` more steps. The run stopped at 8000 steps with them
  still alive, which means they are finding cells to top up from, not sitting
  still. Whether the population ends at 40 or 42 needs a longer run and a
  per-organism trace, not this census.
- **That `COST = 0.63` is what the organism actually pays.** It is
  `maintenance + damage_rate * repair_cost`, which assumes the damage is always
  fully repaired. An organism too poor to repair pays less and dies sooner; the
  formula is the cost of staying healthy, not the cost of staying alive.
- **That the earlier `C = 80` reading was wrong.** It was taken at different
  parameters (`results/overcrowding/run-2026-11-11T22-20-40.json`) and has not
  been re-run here. What is established is that `C` depends on `E_max`, so a
  single number quoted without `E_max` is not a law.
- **Anything about a non-uniform field.** This is the uniform field only.

