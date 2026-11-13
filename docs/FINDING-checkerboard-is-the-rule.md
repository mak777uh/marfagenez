# The sighted rule freezes into a checkerboard, and that is a property of the rule

Date: 2026-11-13
Experiments: EXP-64, EXP-65 (failed), EXP-66 (passed)
Probe: `checks/probe_alternating.py`, `checks/probe_boundary.py`

## What happens

On an alternating field (rich 2.4, poor 1.6, 40 cells, income 1.0, move_cost 0.05),
sighted organisms stop moving and pack into

    occ = 2 1 2 1 2 1 ...     over all 40 cells
    field = 1.92 1.35 1.92 1.35 ...

Nothing moves. The packing is 20 rich cells with two organisms each and 20 poor
cells with one each, total 60.

## Why it is the maximal packing

A rich cell at 1.92 loses 2 x income = 2.0, so it goes to -0.08 and is emptied;
it regrows to 1.92 by the next frame. A rich cell with three would lose 3.0 and
the third would starve. A poor cell at 1.35 loses 1.0 and stays at 0.35, which
regrows to 1.35; a poor cell with two would lose 2.0 and both would starve.

    20 x 2 + 20 x 1 = 60

So 60 is not a coincidence of the parameters. It is the largest number of
organisms this field can hold when each one takes exactly `income` per step.

## Why nothing moves

The sighted rule (`core/src/life.rs`, `Policy::Sighted`) compares **field values**
of the two neighbours and moves toward the larger one; on a tie it stays. It does
not compare **free space**. On a checkerboard every cell is either a local max or
a local min, so every organism is already standing on a local max or a local min
and the comparison never points anywhere else. The rule has no reason to move.

That is the mechanism: the rule sees the field, not the crowding. A cell with two
organisms looks exactly as attractive as a cell with none.

## What EXP-65 got wrong, and why it matters

EXP-65 tried to confirm this over six seeds and returned `failed`, with both
`fires` and `specific` failing. Both failures were the experiment's fault:

1. `fires` demanded 60 alive for every seed. The measurement was
   60, 55, 60, 60, 59, 59. A control that cannot pass is not a test of the model;
   it is a test that was written before the measurement was known.
2. `specific` demanded 20 organisms on poor cells and always saw 19.

The second one is the interesting one. The probe
(`checks/probe_boundary.py`) printed the boundary and found:

    NEITHER at cell 39: field 1.350 left 1.920 right -1000000000.000 occ 1

The field is a **ring** -- cell 39's right neighbour is cell 0 -- but my
local-max/local-min test used `-1e9` at the boundary, as if the ring had walls.
Cell 39 is a poor cell holding one organism, and it was classified as neither a
max nor a min. `on_max + on_min = 40 + 19 = 59`, one short of 60.

After wrapping the neighbour index, `on_poor = 20` on all six seeds and
`on_max + on_min == alive` everywhere. EXP-66 passes all three controls.

**The lesson is not "the checkerboard is confirmed".** The lesson is that a
failed control has two possible causes -- the model is wrong, or the metric is
wrong -- and I only checked the first one. EXP-65's failure looked like evidence
against the checkerboard. It was evidence that I had written a boundary test for
a space that has no boundary.

## What this does not prove

- **Perturbation is not injected.** Six starts show the packing forms
  repeatedly. They do not show that a formed packing survives being pushed.
  The trace binary cannot rewind or inject, so "stable" here means "reached from
  six starts", not "returns after a disturbance". This is the same gap recorded
  in `FINDING-checkerboard-freeze.md`.
- **One field shape.** Alternating 2.4/1.6 only. EXP-64 showed move_cost does not
  change the outcome here (60 alive at every move_cost from 0.00 to 0.20), but
  other amplitudes and periods were not run.
- **The gradient field does not settle.** On a gradient the same rule leaves a
  sawtooth (`1.39 1.57 1.60 1.42 ... 2.12 2.15`, 30 of 40 cells occupied, 25 of
  30 moving, 10 empty cells). Every organism moves on the same tick, so the cell
  behind is emptied and the cell ahead has not regrown. The checkerboard is the
  case where the rule has nowhere to point; the gradient is the case where it
  always does. Both are consequences of the same blindness to crowding.
- **This is not "the environment is good".** A frozen packing of 60 is a local
  arrangement of one rule on one field. It says nothing about whether the child
  grows.

## Numbers

| seed | alive | occupied | doubled | moving | on rich | on poor |
|---|---|---|---|---|---|---|
| 1 | 60 | 40 | 20 | 0 | 40 | 20 |
| 2 | 55 | 40 | 15 | 0 | 35 | 20 |
| 3 | 60 | 40 | 20 | 0 | 40 | 20 |
| 7 | 60 | 40 | 20 | 0 | 40 | 20 |
| 11 | 59 | 40 | 19 | 0 | 39 | 20 |
| 42 | 59 | 40 | 19 | 0 | 39 | 20 |
| uniform n=40 | 40 | 40 | 0 | 0 | -- | -- |

Six seeds reach 55 to 60, all 40 cells occupied, nothing moving, every organism
on a local max or min of the ring, no poor cell overfull.

Results: `results/EXP-66/run-2026-11-13T01-53-05.json`
