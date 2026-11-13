# FINDING-085 — a fed-on cell settles at `M − income·(1−r)/r`, not at `M`

**Date:** 2026-11-13
**Experiment:** `checks/exp85_where_a_fed_on_cell_settles.py`
**Run:** `results/EXP-85/run-2026-11-13T02-10-48.json` (verdict `failed`; A, B, C matched, D did not)

## The law

A cell that is eaten every step by an organism that never moves obeys

```
L_{n+1} = (L_n − income) + (M − (L_n − income))·r
```

Setting `L_{n+1} = L_n`:

```
L* = M − income·(1 − r)/r          (0 < r < 1, L* ≥ 0)
```

Three regimes:

| `r` | `L*` | what the cell does |
|---|---|---|
| `0` | — | never comes back; the cell empties and stays empty |
| `0 < r < 1` | `M − income·(1−r)/r` | settles strictly below the ceiling |
| `1` | `M` | restored completely; the meal is invisible |

And the law is only valid while `L* ≥ 0`, i.e. while

```
income ≤ M·r
```

which is the **same threshold** `Capacity.lean` states for `0 ≤ c*`. The two
facts are one fact.

## The measurement

Four cells, `rich 2.4 / poor 1.6`, `maintenance 0.6`, `damage 0.05`,
`repair 1.5`, `capacity 10`, `start 1.0`, `seed 1`, 400 steps,
`--start-cell 0` (the flag added in EXP-84).

| arm | `r` | `income` | predicted `L*` | measured |
|---|---|---|---|---|
| A | 0.8 | 1.0 | 2.4 − 1.0·0.2/0.8 = **2.15** | **2.150000** |
| B | 1.0 | 1.0 | 2.40 | **2.400000** |
| C | 0.0 | 1.0 | cell empties | **0.000000**, organism dead |
| D | 0.8 | 2.0 | −0.1 (impossible) | **1.920000** |

A, B, C match to the last digit with no free parameter. D does not, and the
reason is FINDING-086: a level cannot be negative, and `Field::take` cannot
overdraw a cell.

## Why this matters for every earlier reading of the field

The **visible** drop on a rich cell is

```
M − L* = income·(1 − r)/r
```

At `r = 0.8` and `income = 1.0` that is **0.25**, one quarter of the meal. At
`r = 0.95` it is 0.05, one twentieth. An observer who reads the field level and
concludes "the organisms are barely eating" is reading the regrowth rate, not
the eating. **Depletion must be read from `taken`, never from the field level.**

This also corrects the reading of EXP-66, which measured 2.15 on a full ring
and was treated as an unexplained number. It is this law, exactly.

## What this does not prove

- One organism, one cell. It measures the settled level of a cell, not the
  capacity of a field.
- The organism never moves. A moving organism samples several cells and the
  level it leaves behind depends on its path.
- `income > M·r` empties the cell, but this experiment does not follow the
  organism after that.

## Consequence for the model

`Capacity.lean`'s condition `0 ≤ c*` and this law's condition `L* ≥ 0` are the
same inequality `income ≤ M·r`. The Lean file should state it once, as the
condition under which a fed-on cell has a positive level at all, rather than as
a separate fact about capacity.
