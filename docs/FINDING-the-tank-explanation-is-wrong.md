# FINDING: the tank explanation is wrong, and the surplus decays

**Status:** EXP-55's mechanism is refuted by measurement. The gate is real;
the reason given for it is not.

## What EXP-55 claimed

The surplus appeared at `E_max = 9` and not at `E_max = 8`. The explanation
offered was a rotation-period inequality:

```
E_max > 0.13 * T_rot
```

with `T_rot` inferred to lie in (61.5, 69.2) from where the gate sat.

Note what that inference is: the gate position was used to compute `T_rot`,
and then `T_rot` was used to explain the gate position. That is circular. It
cannot fail. It was written down as a derivation, but it was a fit.

## What was measured

`checks/measure_rotation.py` runs with `--every 1` (every step is a frame) and
counts, for each cell, how long it stays double. A double stretch starts when a
cell goes from ≤1 to ≥2 alive occupants and ends when it goes back to ≤1.
Right-censored stretches (still double at the end) are not counted.

| E_max | alive | completed stretches | median | mean | max |
|---:|---:|---:|---:|---:|---:|
| 8 | 42 | 6359 | **1** | 1.2 | 25 |
| 9 | 42 | 6359 | **1** | 1.2 | 25 |
| 10 | 42 | 6359 | **1** | 1.2 | 25 |

The rotation period is **one step**, not 62–69. The derived inequality would
give `E_max > 0.13`, a threshold seventy times below the measured gate.

And the three `E_max` values produce **identical** stretch statistics — 6359
stretches, mean 1.2, max 25, in all three runs. So the stretch distribution
does not carry the difference between the arms. Whatever gates the surplus, it
is not the length of a double stretch.

## What the difference actually is

The runs above were 3000 steps. EXP-55 ran 8000. That difference matters:

| E_max | 1000 steps | 3000 | 5000 | 8000 |
|---:|---:|---:|---:|---:|
| 8 | +2 | +2 | +1 | **0** |
| 9 | +2 | +2 | +2 | **+2** |

The surplus at `E_max = 8` is **not absent — it decays**. It is +2 for the first
few thousand steps, then the extra organisms die and it settles at 0. EXP-55
sampled at 8000 steps and saw the settled value, which is why it looked like a
threshold rather than a decay.

The deaths at `E_max = 8` happen at steps **3578** and **6804** — two events,
3226 steps apart, in 8000 steps. At `E_max = 9` and `10` there are no late
deaths at all.

## The one number that does track the gate

The settled energy of every survivor:

| E_max | settled energy | E_max − energy |
|---:|---:|---:|
| 8 | **7.370** (all identical) | 0.630 |
| 9 | 7.680 … **8.370** | 1.320 |
| 10 | 8.680 … **9.370** | 1.630 |

At `E_max = 8` every survivor sits at exactly 7.370 — the cap binds and pins
them all to the same value. At 9 and 10 the survivors spread over a range whose
top is `E_max − 1.63`.

So `E_max − 1.63` is the highest energy an organism can hold after paying its
worst step. At `E_max = 8` that ceiling is 7.37, and the cap at 8 is never
reached. At `E_max = 9` the ceiling is 8.37 and the cap still does not bind for
the top organisms.

What this does **not** explain is why 7.37 kills an organism every ~3000 steps
while 8.37 never does. The loss rate of a second occupant is 0.13/step, so 7.37
buys 56 steps of continuous loss and 8.37 buys 64 — a difference of 8 steps.
An event that needs 56 steps of continuous loss to happen but not 64 is a rare
excursion, and the measured stretch maximum is 25, well under both. The gap
between 25 and 56 is unexplained.

## What this does not prove

- It does not prove the surplus is unrelated to `E_max`. It plainly is: 8 gives
  0, 9 gives +2, reproducibly.
- It does not give the mechanism. The rotation-period story is dead; nothing
  has replaced it.
- It does not establish that the decay at `E_max = 8` is monotone or that 8000
  steps is long enough for `E_max = 9` too. `E_max = 9` was checked to 8000 and
  held; it was not checked beyond.
- The stretch statistics are per cell, not per organism. Samples carry no
  organism id, so a cell going double→single is attributed to a stretch ending,
  but which organism left is not known. A stretch of length 1 may be one
  organism passing through, not a second occupant being displaced.
- Single seed (20250101). The death steps 3578 and 6804 are properties of this
  seed's trajectory, not of the parameters.

## The mistake worth keeping

EXP-55's inequality was not a prediction. `T_rot` was computed backwards from
the gate, so the inequality was guaranteed to hold at the gate and said nothing
elsewhere. It read like a law because it had the shape of one.

The check that would have caught it costs one run: measure `T_rot`. It was
never measured. The number 62–69 looked derived and was fitted.

This is the same failure as `p = 0.2` (LESSONS.md): a parameter computed from
the data it is supposed to explain cannot fail to match the data.

## What to measure next

The decay at `E_max = 8` is the real phenomenon. Two deaths in 8000 steps,
3226 apart. To find what triggers them, record for each organism the step at
which it dies and its energy over the preceding N steps. That needs an organism
id in the sample, which the trace format does not have. Either add the id, or
reconstruct it from `(cell, energy)` continuity — which fails exactly when two
organisms share a cell, i.e. in the case being studied.
