# The nominal levels are ceilings, not the levels organisms meet

**Date:** 2026-11-12
**Experiments:** EXP-59 (`checks/exp59_why_008.py`, diagnostic),
EXP-60 (`checks/exp60_second_share_is_the_leftover.py`)
**Result:** `results/EXP-60/run-*.json` — `passed`

## The anomaly

EXP-58 found a share of **0.080** with 168 samples on the narrow field, where the
arithmetic `min(1.6 − 1.2, 1.2) = 0.4` predicts a share of 0.4. A share of 0.08
means the cell held 0.08 at the moment of the take, not 1.6.

## The answer, in two steps

### 1. The level a taker sees is `nominal × regrow`

EXP-59 printed the cell's level in the same frame as every 0.08 share:

| quantity | value |
|---|---|
| level in frame a | min 1.2800, max 1.9200, mean 1.3333 |
| level in frame b | **1.2800** (all 168) |
| organisms on the cell | 2, 3, 4, 5, 6, 7, 8 |

**1.28 = 1.6 × 0.8** and **1.92 = 2.4 × 0.8**. The field is eaten every step and
regrows by `regrow` of the gap to its own ceiling. So the level a taker meets is
the nominal level times the regrowth fraction.

The nominal values 2.4 and 1.6 are **ceilings**, not the levels organisms meet.

### 2. `take()` is sequential, so the shares are 1.2, then the leftover, then nothing

With the level at 1.28 and income 1.2:

```
first taker:     min(1.28, 1.2) = 1.20    cell left 0.08
second taker:    min(0.08, 1.2) = 0.08    cell left 0.00
third and later:                = 0.00
```

**0.08 is the second taker's share**, and its size is the first taker's leftover.

## The test: move the regrowth fraction

If the second share is `level_seen − income` and `level_seen = nominal × regrow`,
then it must move when `regrow` moves.

| regrow | level seen | predicted first | predicted second | measured shares |
|---:|---:|---:|---:|---|
| 0.8 | 1.28 | 1.20 | 0.08 | 1.200, **0.080**, 0.000 |
| 0.9 | 1.44 | 1.20 | 0.24 | 1.200, **0.240**, 0.000 |
| 0.5 | 0.80 | 0.80 | none (0.80 < income) | **0.800**, no second share |

All three match exactly. At `regrow 0.5` the level seen falls below income, so the
first taker takes only 0.80 and there is no second share at all — the effect is
**absent** where the arithmetic says it must be.

## What this closes

The loss line of EXP-58 now closes on the queue:

| position | share | `share − 0.63` | measured |
|---|---:|---:|---:|
| first taker | 1.20 | +0.57 | +0.0007 (capped by the energy ceiling) |
| second taker | 0.08 | **−0.55** | **−0.5583** |
| third and later | 0.00 | **−0.63** | **−0.6300** |

The 0.13/step in the earlier reconstruction is not any of these. It was one point
on a line, computed from a single death scene, and the line is `share − 0.63`.

## What this does not prove

- **One seed** (20250101) and one field pair per arm. The claim is about which
  shares exist and their size, not about how often each occurs.
- **The queue order is inferred.** `take()` is sequential in the code, but the
  trace records the share, not the position in the queue. That a 0.08 share is
  "the second taker" is an inference from the arithmetic, not an observation.
- **The queue length of 25 is still unexplained.** This note explains the size of
  each share, not how many organisms end up sharing a cell.
- **Why E_max 9 and 10 show no late deaths is still unexplained.**
- **The 0.720 and 0.960 shares are not explained here.** They appear on the rich
  level (1.92 − 1.2 = 0.72) and at regrow 0.9 (1.44 − 0.48 = 0.96), but this note
  did not test them.
- **The finding note `FINDING-the-late-deaths-are-queued-starvation.md` still
  carries the 0.23/step reconstruction.** It is now known to be a point on the
  line `share − 0.63`, not the line. The note has not been rewritten because the
  reconstruction was made before the measurement, and a note that quietly
  rewrites its own predictions hides the mistake worth keeping.

## What follows

The next question is the queue length: why 25 organisms end up sharing one cell.
That needs the arrival rate and the departure rate at a cell, which the trace can
give — every sample has a slot, a cell and a direction, so arrivals and
departures are countable.
