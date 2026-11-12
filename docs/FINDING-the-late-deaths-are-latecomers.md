# The late deaths are latecomers, not a queue

EXP-56 found two late deaths, at steps 3578 and 6804, and the finding note left
open why the queue would be 25 rather than 5 or 60. EXP-61 and EXP-62 answer it:
**there is no queue of 25.** The 25 was the longest run of shared occupancy, and
99.4% of the organisms present at the start of such a run are still there at the
end. It is not a line of organisms dying one after another. It is a pair that
stays put.

## What EXP-61 measured

`checks/exp61_occupancy_runs.py`, uniform field, `rich=2.4 poor=1.6`, regrow 0.8,
8000 steps, frame every step, seed 20250101:

| quantity | value |
|---|---:|
| runs of shared occupancy | 10834 |
| run length, mean | 1.09 |
| run length, max | 25 |
| runs of length 1 | 10734 (99.1%) |
| runs of length 11-25 | 40 |
| peak organisms on one cell | 7 |
| organisms present at the start of a run that are still there at the end | 21611 / 21748 = 99.4% |

The 40 runs of length 11-25 are exactly one per cell: every cell has one long
shared stretch and then thousands of one-step encounters. A queue that starved
its way along would show organisms leaving at the front; 99.4% stay.

The survival bound from the loss line is 13.4 steps for a second taker at the top
energy of 7.37. A 25-step run is beyond it, so the run cannot be one organism
sitting on a shared cell and starving. It is two organisms that both survive,
which is what 99.4% says.

## What EXP-62 measured

`checks/exp62_death_scene.py`, same parameters, frame every step. Both late deaths
look identical:

| | step 3578 | step 6804 |
|---|---|---|
| dying slot | 54 | 67 |
| cell | 23 | 10 |
| energy | 0.0749 | 0.0742 |
| damage | 0.0000 | 0.0000 |
| taken | 0.5000 | 0.5000 |
| mate slot | 15 | 11 |
| mate energy | 7.3700 | 7.3700 |
| mate taken | 1.2000 | 1.2000 |
| cell level, frame before | 1.600 | 1.600 |
| cell level, death frame | 1.600 | 1.600 |
| organisms on cell 2 steps earlier | 1 | 1 |
| organisms on cell 1 step earlier | 2 | 2 |

The dying organism has **0.0749 energy and no damage**. It arrived on the cell
one step before it died, with almost nothing left. Its mate has the full 7.37.
This is not starvation in a queue; it is a latecomer that had already spent its
energy looking for a place and found none.

## The 0.500, which I first read wrong

`0.500` is not `1.600 - 1.200 = 0.400`. The field value in the frame is the level
**after** the take; `taken` is what was removed **before** it. The steady state of
a fed cell in this field is:

```
after take:  x
regrow:      x + (2.0 - x) * 0.8
```

Setting the regrown level to 1.700 gives `x + (2.0 - x) * 0.8 = 1.7`, so
`x = 0.5`. Then the first taker takes `min(1.7, 1.2) = 1.2`, leaving `0.5`, and
regrow returns it to `0.5 + 1.5 * 0.8 = 1.7`. The cycle closes exactly.

So the second taker's share is `1.700 - 1.200 = 0.500`, and EXP-60's rule
`second share = level_seen - income` holds with `level_seen = 1.700`, the level
**before** the take. My first reading used 1.600, the level after, and got 0.400.

The most common cell level after step 500 is 1.700 (260335 of 280000 cell-frames).
1.600 (9916) and 1.680 (9784) are the frames just after a take and just after a
regrow.

## The loss of the latecomer

```
share 0.500, cost 0.63  ->  delta = 0.500 - 0.63 = -0.130 per step
energy 0.0749           ->  0.0749 / 0.130 = 0.58 steps to death
```

It dies on the next step, which is what the trace shows. The loss line from
EXP-58 holds: `delta = taken - 0.63`.

## What this does not prove

- **Why the latecomer had 0.0749 and not more.** The trace does not record where
  it was before the step it arrived. To answer that, the trace needs the previous
  cell of every organism, not only the current one.
- **Why there are only two such deaths in 8000 steps.** 160 organisms start, 80
  survive, and the 80 that die do so at step 10. Two latecomers in 8000 steps is
  a rate, not a mechanism; nothing here says the rate is stable across seeds.
- **That 25 is a typical run length.** The mean is 1.09. 25 is the tail of 10834
  runs on 40 cells.
- **Anything about the alternating field.** Both experiments use the uniform
  field, where every cell has the same ceiling. On an alternating field the poor
  cells carry less and the shares differ (EXP-60).
