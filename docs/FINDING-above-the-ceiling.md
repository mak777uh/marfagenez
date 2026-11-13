# Above the ceiling: the energy buffer pays for the second organism

**Date:** 2026-11-13
**Status:** measured; one regime; explains the only point in EXP-52 that sits above its ceiling

## The anomaly

`FINDING-static-count-is-a-ceiling.md` records that the count

```
k_max = 0 if income <= need, else 1 + floor((M·r - need)/income)
```

is an upper bound on how many organisms a cell can feed, and that the field
usually sits *below* it. There is one regime where it sits *above*:

| income | ceiling (40 cells) | measured |
|---|---|---|
| 0.70 | 80 | 79 |
| 0.90 | 80 | 80 |
| 0.95 | 80 | 80 |
| 1.00 | 80 | 46–52 |
| **1.20** | **40** | **42–43** |
| 1.60 | 40 | 40 |

At `income = 1.20` the ceiling is `k_max = 1 + floor((1.6 - 0.6)/1.2) = 1`.
Forty cells, forty organisms. The field holds 43.

## What the extra organisms eat

`M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.2`, 40 cells, 80 organisms,
`sighted`, `read_budget = 3`, seed 1, 200 000 steps, 200 frames:

- alive: 45 at the first frame, 43 at the last, never outside `[43, 45]`
- all 40 cells occupied; crowding `{1: 37, 2: 3}` — three cells hold two

The three doubled cells at the last frame:

| cell | first occupant | second occupant |
|---|---|---|
| 3 | `E = 10.000`, `taken = 1.200`, `dmg = 0` | `E = 9.068`, `taken = 0.500`, `dmg = 0` |
| 8 | `E = 10.000`, `taken = 1.200`, `dmg = 0` | `E = 8.811`, `taken = 0.496`, `dmg = 0` |
| 11 | `E = 10.000`, `taken = 1.200`, `dmg = 0` | `E = 9.640`, `taken = 0.500`, `dmg = 0` |

The first organism takes `1.2` — its whole income — and sits at full energy.
The second takes about `0.5`, which is **below `need = 0.6`**. It is losing
`0.1` per step and it is still alive, at `E ≈ 9`.

That is the whole mechanism: **the energy buffer pays for the second
organism.** A cell yields `M·r = 1.6`; the first organism takes `1.2`; `0.4`
remains, which is below `need`. An organism arriving into that remainder
loses `0.2` per step, and with `E = 10` it survives about 50 steps before it
must leave. While it is there, the field holds one more organism than the
ceiling allows.

Over the walk (200 frames, 8 608 transitions):

| | n | mean `taken` | p10 | p50 | p90 | below `need` |
|---|---|---|---|---|---|---|
| stayed | 260 | 1.1540 | 1.200 | 1.200 | 1.200 | 17 (6.5%) |
| moved | 8 348 | 1.1446 | 1.200 | 1.200 | 1.200 | 655 (7.8%) |

The mean is `1.14`, well above `need`, and the median is a full `1.2`. The
distribution is not "everyone scraping by" — it is mostly organisms eating
their fill, with about 8% of steps spent in a remainder that does not cover
`need`. Those are the steps the buffer absorbs.

## Why the ceiling is not violated

The ceiling `k_max` counts organisms that eat on a cell **every step**. The
43rd organism does not: it eats `0.5` for a while, leaves, and another takes
its place later. Over any single step the cell feeds one organism at `1.2`
and one at `0.5` — total `1.7` against a yield of `1.6` — which is possible
only because the second organism's `taken` is capped by what is left, and
because it does not stay.

So the count above the ceiling is not a violation of the arithmetic; it is
the arithmetic of a *different* claim. `k_max` is a bound on **sustained**
occupancy. The field can exceed it in **transient** occupancy, paid for out
of stored energy. The size of the excess is set by how much buffer an
organism carries (`E = 10`) and how fast it loses while in the remainder
(`0.2` per step at `income = 1.2`), not by the field.

## Why it does not happen at income 1.00

At `income = 1.00` the remainder after the first organism takes its fill is
`1.6 - 1.0 = 0.6`, which is exactly `need`. A second organism breaks even, so
`k_max = 2` and the ceiling is 80 — and the field holds 46, far *below* it.
There the buffer buys nothing, because a second organism can already sustain
itself; the field is limited by something else (see the ceiling note).

The buffer only buys an excess when the remainder is **below** `need`, which
is `income > M·r - need = 1.0`. That is why `income = 1.20` is the one point
above and `income = 1.00` is the point furthest below. The two anomalies are
the same threshold seen from both sides.

## Limitations

1. One regime: `M = 2.0`, `r = 0.8`, `need = 0.6`, `damage_rate = 0.02`,
   `E_max = 10`, `sighted` with `read_budget = 3`, seed 1. One seed.
2. 200 000 steps is where I stopped. The count is stable at `43–45` over the
   whole run, but "stable" over 200 frames is not "equilibrium".
3. The excess is small (3 organisms on 40 cells). Whether it grows with
   `E_max`, or with the number of cells, is not measured. A larger buffer
   should allow a larger excess, since the survival time in the remainder is
   `E / (need - taken)`.
4. `taken` is sampled once per 1 000 steps, so the below-`need` fractions are
   lower bounds, and a short excursion into a remainder between samples is
   not counted.
5. The mechanism is inferred from three doubled cells at one frame plus the
   transition table. I did not track individual organisms through a full
   remainder excursion, so the "about 50 steps" is arithmetic
   (`10 / 0.2`), not a measurement.

## What this does not prove

It does not prove that the excess is bounded by `E_max / (need - taken)`.
It does not prove that `income = 1.20` is the only regime with an excess —
only that it is the only one measured. It does not prove that the field
settles at 43; it proves that it sits above 40 and that the excess is paid
for by stored energy, which is a different thing from the field feeding more
organisms per step.

## Reproduction

```bash
./core/target/release/trace --policy sighted --field uniform --cells 40 \
  --n 80 --steps 200000 --every 1000 --seed 1 \
  --maintenance 0.6 --rich 2.0 --poor 2.0 --income 1.2 --read-budget 3
```

Trace hash `de64f4c305fde43b`.

or `python3 checks/exp58_above_the_ceiling.py`, which runs the trace and
records the second-occupant measurement with the three controls
(`results/EXP-58/`).
