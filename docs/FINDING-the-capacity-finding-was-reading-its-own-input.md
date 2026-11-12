# FINDING: the capacity finding was reading its own input

2026-11-12. Supersedes `FINDING-the-capacity-is-a-line-not-a-number.md` in its
central claim. That note's arithmetic is right; its measurement is not a
measurement.

## What went wrong

The previous note reported, at `n = 160`, `cells = 40`, `steps = 8000`:

| `E_max` | alive | crowding |
|---|---|---|
| 8 | 40 | 1.00 |
| 9 | 42 | 1.05 |
| 10 | 42 | 1.05 |

and concluded that the capacity is a line in `E_max`: 40 at `E_max = 8`, 42 at
`E_max >= 9`.

Those rows are real numbers from real runs, but they are not from `n = 160`.
Sweeping `--n` with everything else fixed (`E_max = 8`, `steps = 8000`,
`every = 8000`, seed 20250101, uniform field, `rich 2.4 / poor 1.6`,
`regrow 0.8`, `income 1.2`, `maintenance 0.6`, `damage 0.02`, `repair 1.5`,
`move-cost 0.10`):

| `--n` | alive | occupied | crowding | max per cell |
|---|---|---|---|---|
| 40 | 40 | 40 | 1.00 | 1 |
| 42 | 42 | 40 | 1.05 | 2 |
| 80 | 80 | 40 | 2.00 | 5 |
| 120 | 120 | 40 | 3.00 | 6 |
| 160 | 160 | 40 | 4.00 | 7 |
| 200 | 200 | 40 | 5.00 | 9 |

**`alive` is exactly `n`. Nothing dies at any of these settings.** The "40" was
`--n 40` and the "42" was `--n 42`; they were labelled as readings at `n = 160`.

The tell was there and was not read: `alive = 40` is *exactly* `cells = 40`, and
`alive = 42` is *exactly* two more than `cells`. A measured capacity that equals
the number of cells to the last digit, and then equals the number of cells plus
the number of organisms in the second arm, is the input coming back out.

## Why the arithmetic looked confirmed

`E* = E_max - 0.63` held to four decimals (7.37, 8.37, 9.37). It still does, and
it is still correct -- but it is the steady energy of an organism that is **alone
on its cell**, and at these settings most cells hold one organism, so the
single-occupant formula matches by construction. It confirms the arithmetic; it
says nothing about capacity.

The second-occupant arithmetic is also still correct and still unrefuted:

    COST          = maintenance + damage_rate * repair_cost = 0.63
    c*            = M - income * (1 - r) / r = 1.7
    second share  = c* - income = 0.5 < 0.63

so a second organism on a *steady* cell loses 0.13 per step. But the organisms
here are not on steady cells: with `sighted` and a read budget of 3 they move to
a cell they have not eaten, take a full `income = 1.2` there, and the reserve is
replenished. That is why nothing dies. The deficit arithmetic describes a
sedentary organism; these are not sedentary.

## What the measurement actually shows

At `E_max = 8`, `n = 160`, `cells = 40`, run to 40000 steps with `--every 2000`:

- `alive = 160` at every frame from step 2000 to step 40000. No deaths.
- `occupied = 40` -- every cell is occupied at every frame.
- `crowding = 4.00` -- exactly `n / cells`, constant.
- `max per cell` fluctuates between 7 and 8.
- Alone-on-a-cell energy is `7.3700` at every frame, exactly `E_max - 0.63`.
- Shared-cell energy is `1.8077` and **frozen** from step 28000 onward.

So the field is not limiting the population at all at these settings. What
limits it is the number of organisms put in. The crowding is `n / cells` because
that is what was asked for.

## The one real dynamical fact that came out

At `E_max = 9` the shared-cell energy settles at `2.0530` and is frozen from step
18000; at `E_max = 10` it oscillates in a narrow band around `2.40`
(`2.3928` to `2.4104`). At `E_max = 8` it freezes at `1.8077`. In each case the
shared-cell energy is **not** `E_max - 0.63` and **not** `c* - income`; it is a
separate fixed point of the shared cell. That fixed point is worth deriving, and
it is the first thing in this line of work that is a genuine equilibrium rather
than an input read back.

## What this does not prove

- It does not show that capacity is unbounded. It shows that at these settings
  nothing dies, so these settings cannot measure a capacity. A setting with a
  real limit has to be found before any capacity law can be stated.
- It does not retract the `k_max = 10` resolution. `--capacity` is still the
  energy ceiling `E_max` (`core/src/organism.rs:164`); that part stands.
- One seed, one field shape. The `alive = n` identity was checked at six values
  of `n` and three values of `E_max`, not swept.

## The rule this adds

A measured quantity that equals an input parameter to the last digit is the
input, not a measurement. Before reporting a capacity, a rate, or any "how many
survive" number, check whether it is algebraically equal to something that was
set by hand. `alive = n` and `occupied = cells` were both visible in the first
table and both were read as results.
