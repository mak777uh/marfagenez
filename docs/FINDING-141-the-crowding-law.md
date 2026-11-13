# FINDING-141: the crowding law, and why the old capacity law was half of it

## The law

On a cell that its organisms empty every step, the cell regrows to `M*r`
before the next step. So the per-step supply is

    supply = M * r

The organisms take in index order, each at most `income`. Let

    cost = maintenance + damage_rate * repair_cost

be what one step of staying alive costs. Organism number `j` (1-based) gets
`min(income, supply - (j-1)*income)`. It survives iff that is at least `cost`.
Therefore

    k_max = 0                                        if income < cost or supply < cost
          = floor((supply - cost) / income) + 1       otherwise

    capacity = cells * k_max

## Why the old law was wrong

The old law was `capacity = cells * M*r/income`, which is `floor(supply/income)`
without the `+1` and without the two guards. It counts how many *full portions*
the cell holds. That is a different question from how many organisms can pay
their cost.

The two guards are the part that was missing:

- **`income < cost`** — an organism cannot take more than `income` per step, so
  if one full take does not cover the cost, no crowding at all helps. The cell
  is empty of survivors however rich it is.
- **`supply < cost`** — the cell cannot even feed one organism.

Both cases give `k_max = 0`, and the old law had no way to say 0.

## Verification

`checks/exp98_crowding_law.py`, 15 grid points of `(M, r, income, maintenance, damage)`,
one cell, `k = law + 3` organisms, 1500 steps, `--policy stay`:

    15 of 15 points match the Rust `trace` binary, 0 mismatches.
    verdict: passed

Controls:

- **fires** — the law reproduces all 15 points.
- **silent** — with `income > M` the first organism empties the cell, so
  `k_max = 1` for every `M` in `{1,2,3,4}`. The law says 1 and measurement says 1.
  A law that varied with `M` here would be reading the wrong variable.
- **specific** — the first version of this control raised `r` from 0.8 to 0.9 at
  `M=2, income=0.6` and got 3 -> 3. The `floor` hid `r`: the supply moved from
  1.6 to 1.8 and both land in the same bucket. That is a control that cannot
  fail, so it was replaced with `M=2, income=0.2, r 0.8 -> 0.5`, where the law
  says 8 -> 5, and `cost 0.1 -> 0.5`, where it says 8 -> 2.

## What this does not prove

- Only a single cell, only `stay`, only `maintenance > 0`.
- At `maintenance = 0` the law is out of scope: an organism that takes nothing
  never dies, and 7 survive where the law says 3.
- A field where organisms move is not covered. Movement changes which cell is
  emptied and how often, so `supply = M*r` is not the per-organism supply there.

## The lesson

The control that "passes" is not evidence until you check it *could* have
failed. `r 0.8 -> 0.9` looked like a separation and was not one, because the
law has a floor in it. This is the same failure as `p = 0.2`: a number that
cannot disagree with the measurement is not a test of anything.
