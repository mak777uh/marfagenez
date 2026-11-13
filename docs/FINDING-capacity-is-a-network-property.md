# Capacity is a property of the network, not of the cell

**Date:** 2026-11-13
**Status:** measured, mechanism visible in the trace, one regime

## The question

EXP-52 measured 52 survivors at `income = 1.00` where the static law allows
40, and 42 at `income = 1.20` where it allows 40. I first wrote this off as
"a small excess of walkers". Then I asked the obvious follow-up: does the
excess decay to the static bound, or does it stay?

## The answer

It stays. It decays, but it does not reach the bound.

`M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.0`, 40 cells, 80 organisms,
`sighted`, `read_budget = 3`, seed 1:

| steps | alive | cells used | crowding |
|---|---|---|---|
| 1 000 | 54 | 40 | — |
| 2 000 | 53 | 40 | 27 single, 13 double |
| 20 000 | 48 | 40 | 32 single, 8 double |
| 100 000 | 47 | 40 | 33 single, 7 double |
| 400 000 | 46 | 40 | 34 single, 6 double |

The static bound `k_max = 1` gives 40. After four hundred thousand steps the
field still holds 46, and the last two intervals lost one organism each
(48 → 47 → 46). The decay is real and it is slowing, not converging on 40
within any horizon I ran.

## The mechanism, read off the trace

At step 400 000 every shared cell has exactly the same structure: one
resident at full energy (`E = 10.000`) who takes `1.000` every step, and one
rotating organism who takes less.

```
cell 10: E=10.000 taken=1.0000 prev=10 | E=10.000 taken=0.7500 prev=9
cell 11: E=10.000 taken=1.0000 prev=11 | E=10.000 taken=0.7500 prev=12
cell 13: E=10.000 taken=1.0000 prev=14 | E=9.970  taken=0.6000 prev=13
cell 14: E=10.000 taken=1.0000 prev=13 | E=9.970  taken=0.7200 prev=15
cell 23: E=10.000 taken=1.0000 prev=23 | E=10.000 taken=0.7500 prev=24
cell 39: E=10.000 taken=1.0000 prev=39 | E=10.000 taken=0.7500 prev=38
```

Every organism in the field has `damage = 0.0000`, so nobody is paying
repair. Solo organisms all take exactly `1.000` and sit at `E = 10.000`.

The arithmetic that makes this work:

- A cell yields `M·r = 1.6` per step. The resident takes `1.0`.
- What is left is `0.6`. A rotating organism that eats there gets `0.6`.
- `need = 0.6`. So `0.6` is *exactly* break-even.
- But the rotator does not stay on one cell. It moves between cells and on
  some of them finds `0.75` or `0.72` instead of `0.6`, because the resident
  on that cell arrived later in the step and left more.
- Averaged over its walk, the rotator takes roughly `0.68` against a need of
  `0.6`. It gains about `0.08` per step on average, with occasional steps at
  exactly break-even and occasional steps below it.

So the rotator is not living on one cell's spare capacity. It is living on
the *sum of the spare capacities along its route*, and it is choosing the
route. That is why the population can exceed the per-cell count: the count
assumes each organism is pinned to one cell, and they are not.

## What this changes

The static count

```
k_max = 0 if income <= need, else 1 + floor((M·r - need)/income)
```

is a count of organisms a cell can feed **if each of them eats there every
step**. It is not a bound on the population. It is exact when the field is
not oversubscribed (income 0.70–0.95, and 1.60 in EXP-52), and it is
exceeded when organisms can walk between cells and average their intake
(income 1.20: 42 against 40).

This is the same lesson as `FINDING-one-per-cell-was-a-strategy.md`, one
level up. There I found that "one organism per cell" was a strategy the
sighted policy happened to produce, not a law of the field. Here I find that
even the *count* of organisms a field holds is not a per-cell quantity: it
depends on what the organisms do with the cells between them.

## Why the decay is slow

A rotator that averages `0.68` against `need = 0.6` gains `0.08` per step, so
it should never die. It dies when its route temporarily offers less — when a
neighbouring resident's arrival order shifts and the rotator gets `0.6` or
below for long enough to drain its `E = 10` buffer. At `0.6` exactly it
breaks even; below `0.6` it loses `(0.6 - taken)` per step, so a run of a few
hundred such steps is needed to drain 10 units. That is why the loss is
about one organism per hundred thousand steps, and why the rate falls as the
field becomes less crowded: fewer rotators means longer routes with more
choice, which means fewer bad steps.

I have not measured the route length or the distribution of `taken` along a
route. That is the next thing to look at, and until it is measured the
"averages 0.68" number above is an inference from the endpoint values, not a
measurement of the walk.

## Limitations

1. One regime: `M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.0`,
   `damage_rate = 0.02`, `move_cost` at its default, one seed, `sighted` with
   `read_budget = 3`. Nothing here says what happens at other parameters.
2. The 400 000-step run is the longest I ran. 46 is not an equilibrium; it is
   where the field was when I stopped. Whether it reaches 40 at 10⁶ steps, or
   settles at some number above 40, is not known.
3. The route of a rotator is inferred from `prev_cell` in a single frame. I
   did not reconstruct the walk over time, so "averages 0.68" is not a
   measured average.
4. `sighted` is the policy that produced this. A policy that does not read
   neighbours, or one with a different `read_budget`, may not build these
   routes at all — EXP-31 found sighting *loses* on a gradient field.
5. The static count is still the right tool where the field is not
   oversubscribed. This note does not retire it; it bounds where it applies.

## What this does not prove

It does not prove that the population always exceeds the static count when
`income > M·r - need`. It shows one case where it does and gives the
mechanism. It does not prove the excess is bounded, or that it decays
monotonically. It does not say the field is "smarter" than the count — the
rotators are following a local rule and the count is a global summary; they
are answers to different questions.

## Reproduction

```bash
./core/target/release/trace --policy sighted --field uniform --cells 40 \
  --n 80 --steps 400000 --every 1000 --seed 1 \
  --maintenance 0.6 --rich 2.0 --poor 2.0 --income 1.0 --read-budget 3
```

The trace is written to `results/sighted/trace-sighted-*.json`; the `written:`
line on stdout names the file.
