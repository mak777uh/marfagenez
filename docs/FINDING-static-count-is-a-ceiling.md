# The static count is a ceiling, not a forecast

**Date:** 2026-11-13
**Status:** measured; one regime; supersedes the first version of this note

## What I got wrong first

I wrote this note claiming the population *exceeds* the static per-cell count
at `income = 1.00` (52 against 40, later 46 against 40), and that the excess
came from organisms sharing a cell's output in time. Both halves were wrong,
and the control caught it.

`k_max = 1 + floor((M·r - need)/income)` with `M·r = 1.6`, `need = 0.6`,
`income = 1.0` gives `1 + floor(1.0/1.0) = 2`, not 1. So 40 cells allow 80
organisms, and 46 is well *below* the ceiling, not above it. The number 40 I
had been comparing against was `k_max = 1` — the count at `income > M·r - need`,
which is a different regime.

The arithmetic is now in the experiment (`checks/exp57_movers_take_their_fill.py`,
`arithmetic["static_bound"]`), so it is computed rather than remembered.

## The real question

At `income = 1.00` the ceiling is 80 and the field holds 46 after 400 000
steps. **34 places are empty.** That is the thing worth explaining, not an
excess.

`M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.0`, 40 cells, 80 organisms,
`sighted`, `read_budget = 3`, seed 1:

| steps | alive | cells used | crowding |
|---|---|---|---|
| 1 000 | 54 | 40 | — |
| 2 000 | 53 | 40 | 27 single, 13 double |
| 20 000 | 48 | 40 | 32 single, 8 double |
| 100 000 | 47 | 40 | 33 single, 7 double |
| 400 000 | 46 | 40 | 34 single, 6 double |

Every cell is occupied at every step. What falls is the number of organisms
sharing cells: 13 doubled cells at 2 000 steps, 6 at 400 000. The field is
thinning its crowding, not losing cells.

## What the organisms actually eat

Reconstructing every frame-to-frame transition over the 400 000-step run
(400 frames; 18 710 transitions where the organism was alive in both frames):

| | n | mean `taken` | p10 | p50 | p90 | below `need` |
|---|---|---|---|---|---|---|
| stayed on the same cell | 646 | 0.9659 | 0.750 | 1.000 | 1.000 | 0 (0.0%) |
| moved to another cell | 18 064 | 0.9590 | 0.750 | 1.000 | 1.000 | 3 (0.0%) |

Movers take `0.959` on average — they eat their fill, they do not scrape
remainders. My earlier claim that movers average about `0.68` by picking up
spare capacity was an inference from endpoint values and it was wrong; the
measured mean is `0.959`. Only 3 of 18 064 sampled transitions fall below
`need`.

## The arithmetic of the ceiling

A cell yields `M·r = 1.6` per step. An organism takes at most `income = 1.0`.
So in one step a cell can serve one organism at `1.0` and a second at `0.6` —
which is exactly `need`, break-even. That is where `k_max = 2` comes from: the
second organism survives only if it gets the whole remainder, every step.

The field holds 46, not 80, because the second organism on a cell does not
get `0.6` every step. When it moves, it sometimes arrives first and takes
`1.0`, and sometimes arrives second and takes `0.6` or less. Since `0.6` is
break-even, any step below it costs energy, and a second organism that moves
around cannot hold `k_max = 2` on every cell forever.

So the ceiling is achievable only by organisms that sit still and always
arrive second. The sighted policy does not do that — it moves toward richer
cells — and 46 is what its movement costs.

## What this changes

The static count

```
k_max = 0 if income <= need, else 1 + floor((M·r - need)/income)
```

is a **ceiling**: the most organisms a cell can feed if each of them eats
there every step and the second one always gets exactly the remainder. It is
not a forecast, and it is not tight. Measured against it:

| income | ceiling (40 cells) | measured | |
|---|---|---|---|
| 0.70 | 80 | 79 | at the ceiling |
| 0.90 | 80 | 80 | at the ceiling |
| 0.95 | 80 | 80 | at the ceiling |
| 1.00 | 80 | 46–52 | far below |
| 1.20 | 40 | 42 | **above** |
| 1.60 | 40 | 40 | at the ceiling |

`income = 1.20` is the one case above the ceiling, and it deserves its own
note: the ceiling there is `k_max = 1`, so the excess is organisms that walk
between cells and eat their fill on some steps and nothing on others. That is
the temporal-sharing mechanism I originally described — it is real, but it
lives at `income > M·r - need`, not at `income = 1.00`.

This is the same lesson as `FINDING-one-per-cell-was-a-strategy.md`, one
level up. There I found that "one organism per cell" was a strategy the
sighted policy happened to produce, not a law of the field. Here I find that
the *count* the field settles at is also a property of the policy, not only
of the field: the same field holds 80 under one movement rule and 46 under
another.

## Why the thinning is slow

Movers average `0.959` against `need = 0.6`, so a typical step is a large
gain. They die when a *run* of bad steps drains the `E = 10` buffer: at
`taken = 0.6` they break even, below `0.6` they lose `(0.6 - taken)` per step.
Only 3 of 18 064 sampled transitions were below `need`, so a fatal run is
rare — which is why the loss is about one organism per hundred thousand
steps. The rate falls as the field thins because fewer organisms means less
contention for the first-arrival slot, which means fewer bad steps.

## Limitations

1. One regime: `M = 2.0`, `r = 0.8`, `need = 0.6`, `income = 1.0`,
   `damage_rate = 0.02`, `move_cost` at its default, one seed, `sighted` with
   `read_budget = 3`. Nothing here says what happens at other parameters.
2. The 400 000-step run is the longest I ran. 46 is not an equilibrium; it is
   where the field was when I stopped. Whether it reaches 40 at 10⁶ steps, or
   settles above 40, is not known.
3. The `taken` table samples the walk once per thousand steps, so a bad value
   on an unsampled step is not counted and the below-`need` count is a lower
   bound. `moved` is a change of cell between consecutive frames, so an
   organism that leaves and returns between two frames counts as `stayed`.
4. `sighted` is the policy that produced this. A policy that does not read
   neighbours, or one with a different `read_budget`, may settle elsewhere —
   EXP-31 found sighting *loses* on a gradient field.
5. The `income = 1.20` excess is measured but not explained here; it is the
   subject of `FINDING-need-is-maintenance-not-cost.md` and deserves its own
   measurement of the walk.

## What this does not prove

It does not prove that 46 is where the field settles, or that the thinning
stops. It does not prove that a policy exists which reaches the ceiling of 80
— it shows that `sighted` does not. It does not prove that `k_max` is the
true ceiling; it shows it is an upper bound that is achieved at some incomes
(0.90, 0.95, 1.60) and missed at others (1.00), which is consistent with it
being a ceiling and not a law of motion.

## Reproduction

```bash
./core/target/release/trace --policy sighted --field uniform --cells 40 \
  --n 80 --steps 400000 --every 1000 --seed 1 \
  --maintenance 0.6 --rich 2.0 --poor 2.0 --income 1.0 --read-budget 3
```

or `python3 checks/exp57_movers_take_their_fill.py`, which runs the trace and
records the `taken` table with the three controls.
