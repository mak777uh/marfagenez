# FINDING: 80 was real, and the gradient is where sighting loses

Date: 2026-11-12. Experiment: EXP-31 (`checks/exp31_capacity_was_forty.py`).
Result: `results/exp31_capacity_was_forty/run-2026-11-12T21-51-00.json`.

## What I expected

EXP-26 showed that `--policy sighted` with the default `--read-budget 0`
silently becomes `Stay`. Eleven experiments (EXP-09 .. EXP-21) ran sighted
without a budget, so I expected their capacity of 80 to be a capacity of 40 —
the stationary bound, one organism per cell.

## What the measurement said

It is not. With a real budget the sighted population on a uniform field reaches
80, which is the arithmetic bound `k_max * cells = 2 * 40`, and the arm that
cannot see reaches 76:

| field | arm | n=40 | n=80 | n=120 | n=160 |
|---|---|---|---|---|---|
| uniform | stay | 37 | 59 | 72 | 76 |
| uniform | sighted (budget 3) | 40 | 76 | 80 | 80 |
| alternating | stay | 44 | 54 | 54 | 58 |
| alternating | sighted (budget 3) | 40 | 60 | 60 | 60 |
| gradient | stay | 33 | 52 | 64 | 68 |
| gradient | sighted (budget 3) | 34 | 37 | 40 | 40 |

So the old 80 was not an artifact of the missing budget. The budget was a real
defect, and it was hiding a different result, not creating a false one.

## The result that was hiding under it

On a real gradient, sighting **loses**: 40 alive against 68 for the arm that
stands still, at n = 160. On a uniform field sighting wins, 80 against 76.

Both are the same policy. What changes is what there is to see. On a flat field
every neighbour is equally good, so moving costs `move_cost` and buys nothing
except spreading out — and spreading out is what lets a second organism survive
on a cell. On a gradient the rich cells are worth travelling to, and the
sighted population travels to them, eats them down, and then has nowhere left:
the field mean stays at 1.800 while the spread stays at 0.7, so it is holding
the rich cells at a lower level rather than harvesting them.

That is the same shape as the earlier `alternating` finding (oscillation costs
more than travel), but it is not the same mechanism. There the organism moved
between two levels and paid for the trip. Here it moves to the top and stays,
and the top is finite.

## A defect found on the way

`--rich 2 --poor 2` makes `alternating`, `gradient` and `uniform` the same
constant field: `uniform` is built as `(rich + poor) / 2`. All three have the
same dynamics hash. EXP-31's first version used those values, so its gradient
arm measured a flat field. The fix is `rich = 2.4, poor = 1.6`, which keeps the
mean at 2.0 and so leaves the arithmetic unchanged. Any earlier experiment that
passed equal rich and poor and claimed a gradient result has the same problem.

## What this does not prove

- One seed, one parameter set.
- The stationary arm is `--policy stay`, not the refused `sighted
  --read-budget 0`. Their equivalence is argued from the code path and checked
  only indirectly, by showing the two policies do differ on an uneven field.
- It does not say sighting is useless. It says sighting wins on a flat field
  and loses on this gradient at these parameters. Where the boundary lies is
  not measured.
- It does not re-run the eleven affected experiments. It re-measures their
  shared parameter set, so their individual headline numbers are still
  unverified.
