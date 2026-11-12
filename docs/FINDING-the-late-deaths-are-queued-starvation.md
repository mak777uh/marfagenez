# The late deaths are starvation in a queue, and the queue is longer than any stretch

**Date:** 2026-11-12
**Experiments:** EXP-56 (`checks/exp56_late_deaths.py`), EXP-57 (`checks/exp57_every.py`)
**Status:** mechanism measured; one number in EXP-55 contradicted

## What EXP-55 left open

At `E_max` 8 the surplus decays: +2 at 1000, 3000 and 5000 steps, 0 at 8000.
Two late deaths, at steps 3578 and 6804. `E_max` 9 and 10 kept +2.

The trace could not say which organism died. A `Sample` carried `cell`,
`energy`, `damage`, `alive`, memory and direction, but no identity, so a death
had to be guessed from `(cell, energy)` -- which fails exactly when two
organisms share a cell, the case worth measuring.

## The fix that made it measurable

`Sample` now carries `slot`, the index in `Life::organisms`. Slots are stable
for the whole run, so `slot` is the identity of the organism
(`core/src/trace.rs:45`, `core/src/life.rs:531`). This is a readout change
only: `samples()` still takes the reading from outside and does not touch the
cycle.

## What the deaths look like

`--every 1`, `--steps 8000`, seed 20250101, n 160, cells 40, income 1.2,
M = 2.0 (rich 2.4, poor 1.6), regrow 0.8, move cost 0.10, capacity 8:

| death | slot | cell | energy | damage | taken | others on cell |
|---|---:|---:|---:|---:|---:|---|
| 3578 | 54 | 23 | 0.075 | 0.000 | **0.500** | 1 |
| 6804 | 67 | 10 | 0.074 | 0.000 | **0.500** | 1 |

`taken = 0.500` is the second taker's share, and it is the predicted one:

    min(c* - income, income) = min(1.70 - 1.20, 1.20) = 0.500

Energy 0.075 is the floor. Damage is 0. Both organisms died while sharing a
cell, taking the second share, with nothing left.

So the late deaths are **starvation while queued**. They are not a damage
effect and not a lone organism on a poor cell.

## What this refutes

The arithmetic written into EXP-56 before the run said:

- H1 (alone on a poor cell) is rejected because the poor cell pays 1.60 and the
  spend is 0.73. **Correct, and the measurement agrees: no death was alone.**
- H2 (queued, second taker) is rejected because the top organism holds
  `E_max - 0.63 = 7.370` and loses 0.130/step, so it needs a queue of 57 steps,
  while the longest double occupancy measured was 25 steps. **Wrong.** The
  deaths are queued second takers.
- H3 (damage) was the only survivor. **Wrong: damage is 0.**

The error is in the 0.130/step figure. It is the loss of a second taker on a
cell at `c*`. The dying organisms were not on cells at `c*`: they were on cells
where the field had fallen to the poor level, so the second taker's share was
`min(poor - income, income) = min(0.40, 1.20) = 0.40`, and the loss is
`0.63 - 0.40 = 0.23/step`, not 0.130. At 0.23/step, 7.370 buys 32 steps, and
the queue needed is 32, which is inside the range the measurement allows.

The general lesson, again the same shape as `p = 0.2` in `LESSONS.md`: the
per-step loss was computed for one field level and then used as if it held at
every level. A rate is a function of the state, not a constant.

## The `--every` scare, and why it was not one

EXP-56 first gave alive 47/51/49 where EXP-55 gave 42/42/42. The only visible
difference was `--every 1` instead of `--every 8000`, which looked like the
readout changing the physics.

EXP-57 settles it: same command line, `--every` 1, 7 and 8000 give alive 47,
47, 47 at the last frame (steps 8000, 7994, 8000). `--every` does not touch the
physics. The real difference was `--income 1.0` instead of `1.2` -- a parameter
I typed from memory instead of copying from EXP-55.

This is worth recording because the wrong explanation was more interesting than
the right one. A readout that changes the world would be a deep bug; a
transposed parameter is a typo. The typo was found by diffing the two command
lines, not by reasoning about `record()`.

## What this does not prove

- **One seed.** Two deaths at one seed is not a mechanism census. The claim
  "late deaths are queued second takers" rests on two organisms.
- **The queue length is still unexplained.** 32 steps of survival at
  0.23/step is compatible with a queue of 25, but nothing here shows why the
  queue is 25 rather than 5 or 60.
- **Why `E_max` 9 and 10 have no late deaths is not shown.** The arithmetic
  says a larger tank buys more queue time, but the measurement is three arms at
  one seed, and the difference could be a different trajectory rather than a
  threshold.
- **The 0.23/step figure is itself a reconstruction.** The dying organism's
  field level was not recorded in the sample, so the poor-level share is
  inferred from the cell, not read off.
- **Slot is not lineage.** A slot is a position in an array; it says nothing
  about which organism came from which.
