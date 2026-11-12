# The loss is a line in the share taken, not a constant

**Date:** 2026-11-12
**Experiment:** EXP-58 (`checks/exp58_second_share.py`)
**Result:** `results/EXP-58/run-2026-11-12T22-27-30.json` — `passed`

## What was asked

EXP-56 found two late deaths, at steps 3578 and 6804, both with `taken = 0.500`
and `damage = 0.000`. The finding note
`FINDING-the-late-deaths-are-queued-starvation.md` reconstructed a loss of
**0.23/step** from that scene and used it to explain the queue length.

That reconstruction assumed the loss is a **constant**. EXP-58 asks whether it is.

## The answer: it is a line, not a constant

`delta = taken - 0.63`, where `0.63 = 0.6 maintenance + 0.02 * 1.5 damage`.
Slope 1, intercept −0.63.

| field | taken | measured Δ/step | predicted | n |
|---|---:|---:|---:|---:|
| narrow (2.4 / 1.6) | 0.000 | **−0.6300** | −0.63 | 490 |
| narrow | 0.080 | **−0.5583** | −0.55 | 168 |
| narrow | 0.720 | +0.0007 | +0.09, ceiling | 59980 |
| narrow | 1.200 | +0.0007 | +0.57, ceiling | 119960 |
| wide (2.8 / 1.2) | 0.000 | **−0.6300** | −0.63 | 636 |
| wide | 0.960 | +0.0007 | +0.33, ceiling | 59980 |
| wide | 1.040 | +0.0006 | +0.41, ceiling | 59980 |
| wide | 1.200 | +0.0007 | +0.57, ceiling | 59980 |

The gap between the 0.00 and 0.08 shares is **+0.0717** for a gap of 0.08 in the
share. A constant loss would show 0.0000.

So the 0.13/step in the reconstruction is **not the law**. It is one point on a
line, and a point that was computed from a single death scene.

## Three errors on the way here, all worth keeping

### 1. `--field uniform` flattens the levels

The first version ran two arms, `(2.4, 1.6)` and `(2.8, 1.2)`, under
`--field uniform`. Both produced **byte-identical traces**, same hash
`3d3eb99d7136655b`.

Not a bug: `uniform` builds the field as `(rich + poor) / 2`, and both arms summed
to 4.0. Both were the same field at level 2.0. The "level dependence" was being
measured on a field with one level.

This also means EXP-55 and EXP-56, which ran `uniform`, had **one level**. Their
`M = 2.0` is the mean of 2.4 and 1.6, not the rich level. Their measurements are
valid, but "the second taker's loss as a function of the level" could never have
been measured there.

### 2. Dead organisms are still sampled

A dead organism keeps its slot, with `taken = 0` and its energy frozen. They
outnumbered live samples three to one and contributed a flat zero, which reads as
"no loss". `taken 0.000` showed −0.0015/step instead of −0.63.

Fixed by skipping `alive: false`.

### 3. `taken` is stamped at the end of the step

`s["taken"]` is the share taken during the step that **produced** `s["energy"]`.
The change `nxt["energy"] - s["energy"]` belongs to the **next** step, whose share
is `nxt["taken"]`. Grouping by `s["taken"]` matched a share with a step it did not
pay for.

That is how a 0.4 share appeared to lose 0.55. The raw rows showed it directly:
`e = 4.77 → 4.22`, delta −0.55, with `taken = 0.400` on the left-hand sample.

Fixed by grouping on `nxt["taken"]`.

## What this does not prove

- **One seed** (20250101). The line is measured on one trace per field.
- **The queue is still inferred.** The trace records one share per organism per
  step, not its position in a queue. "Second taker" comes from two organisms on
  one cell, which is what EXP-56 did. This experiment does not observe a queue.
- **The 0.08 share is unexplained.** On the narrow field the poor level is 1.6 and
  `min(1.6 - 1.2, 1.2) = 0.4`, so a share of 0.08 should not exist. It does, with
  168 samples. Either the field level at the moment of the sample is below 1.6, or
  the share is not `min(L - income, income)`. **This is open.**
- **The queue length of 25 is still unexplained.**
- **Why E_max 9 and 10 show no late deaths is still unexplained.**
- **The 0.23/step is still in the finding note** as a reconstruction. It is now
  known to be a point on a line, not the line. The note has not been rewritten
  because the reconstruction was made before this measurement, and a note that
  quietly rewrites its own predictions hides the mistake worth keeping.

## What follows

The late deaths are queued starvation, and the loss of a queued organism is
`taken - 0.63`. Whether that is enough to starve depends on the share, which
depends on the field level, which depends on the regrowth. The queue length of 25
is the next thing to measure, and it needs the field level at the moment of
sharing, not the nominal rich/poor values.
