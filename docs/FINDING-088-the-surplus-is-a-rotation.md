# FINDING-088 — the surplus above the bound is a rotation, and it costs nothing to keep

**Date:** 2026-11-13
**Experiment:** `checks/exp88_is_the_surplus_a_rotation.py`
**Run:** `results/EXP-88/run-2026-11-13T02-26-24.json` (verdict `passed`, three controls passed)
**Closes:** the one number `FINDING-the-capacity-law-measured-the-wrong-ceiling.md` recorded and did not explain.

## The number that was left open

At `income = 1.20`, `cost = 0.63`, 40 cells, the capacity bound is 40 and the
measurement was **42**. The finding attributed the surplus to a rotation of
second occupants and said plainly that this was "an inference from `taken`
values, not a controlled result". It was right, and now it is controlled.

## The arithmetic before the run

```
c*           = M + income − income/r = 2.0 + 1.2 − 1.5 = 1.70
first takes  = min(c*, income)      = min(1.70, 1.20) = 1.20
left on cell = c* − income          = 0.50
second takes = min(0.50, income)    = 0.50
second loses = cost − taken         = 0.63 − 0.50 = 0.13 per step
dies in      = 10.0 / 0.13          = 76.9 steps
```

The trace samples every 1000 steps. **A second occupant that never leaves cannot
appear in two consecutive samples** — it dies 13 times over between them. So any
double occupancy seen at a sample is either a fresh arrival or a rotation.

## The four arms

Uniform field, `M = 2.0`, `r = 0.8`, 40 cells, 160 organisms, 8000 steps,
seed 1, `income = 1.20`, `maintenance = 0.60`, `damage = 0.02`, `repair = 1.5`.

| arm | policy | `move_cost` | layout | alive | double cells |
|---|---|---:|---|---:|---:|
| A_free | sighted | 0.00 | random | **41** | 1 (cell 3) |
| B_paid | sighted | 0.20 | random | 40 | 0 |
| C_stay | stay | 0.00 | random | **40** | 0 |
| D_even | sighted | 0.00 | even | 40 | 0 |

A holds 41 at **every** sample (`[41, 41, 41, 41, 41, 41, 41, 41]`), always with
exactly one double-occupied cell, and the cell changes between samples. The
second occupant takes 0.50 against a cost of 0.63 and still never dies: it is
not the same organism twice.

## Why the three controls are the three predictions

| control | prediction if the surplus is a rotation | measured |
|---|---|---|
| `fires` | the free arm reproduces a value above the bound | 41 > 40 |
| `silent` | standing still cannot rotate, so it cannot exceed the bound | 40 = 40 |
| `specific` | if leaving costs 0.20 the surplus shrinks | 40 < 41 |

The `silent` arm is the one that carries the argument. `stay` has no way to
produce a surplus — an organism that cannot leave a crowded cell cannot be
replaced by another one — and it gives exactly the bound. The surplus requires
movement, and movement requires the field to be disturbed.

## The 42 did not reproduce — and the reason matters

The first run of this experiment, with the same parameters, gave **40 in all
three arms**. The surplus had vanished. The cause was not the model: it was
`--layout`. The original 42 was measured before the layout flag existed, when
`trace` placed organisms with `Life::spawn` (random). By the time this
experiment ran, `even` had become the default (FINDING-087), so the same
parameters produced a different initial condition.

Arm D_even is there to make that visible: same parameters as A_free, even
layout, **40 instead of 41**. The surplus is not a property of the field law
alone; it needs an initial placement that leaves a cell doubly occupied for the
rotation to start from.

This is the same lesson as FINDING-087, arriving from the other direction: a
number is only comparable to another number if the condition behind it is the
same. The finding's 42 and this experiment's first 40 were both correct
measurements of different conditions.

## What this does not prove

- **One seed.** The surplus is one or two organisms out of 40. A single seed
  cannot say whether 41 is the typical value or one draw. The original finding
  measured 42, this run 41: the surplus is real but its size is not pinned.
- **One income, one `move_cost` pair.** `0.00` and `0.20` bracket the effect;
  nothing here says where between them the surplus disappears, or whether it
  reappears at a higher `move_cost` through a different mechanism.
- **`read_budget` is 3 in both moving arms.** This experiment varies the price
  of leaving, not the information an organism has. A `sighted` organism with a
  budget of 0 degenerates to `stay`, so the two are not separable here.
- **The sampler cannot see the rotation happen**, only its residue. The claim
  that a specific organism leaves and another arrives is inferred from the
  arithmetic (76.9 steps to die against a 1000-step sampling interval) and from
  the changing double cell, not from watching an individual.
- **Nothing here touches capacity as a prediction.** The bound of 40 is still
  the bound. What the surplus shows is that a moving population can hold a
  position *above* the bound indefinitely, at the price of one organism
  continuously in deficit. That is a statement about the dynamics, not about
  how many the field can feed.

## Consequence for the model

The capacity law `k_max · cells` is an upper bound on **standing** occupancy.
Under movement the population can sit one or two above it, and that excess is
paid for by a continuously rotating deficit position. Any claim of the form
"this field supports N organisms" has to say whether the organisms move and
what a move costs, because the answer differs by at least one in exactly the
regime where the bound is tight.
