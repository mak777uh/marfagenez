# FINDING: the surplus above the bound was a field built at the wrong level

**Date:** 2026-11-13
**Status:** resolved. The capacity law holds at every level tested.

## What was reported

`docs/FINDING-the-capacity-law-measured-the-wrong-ceiling.md` recorded a
measurement that did not fit the proved law. With

    income 1.2, regrow 0.8, maintenance 1.0, damage 0.02, repair 1.5
    n = 160, cells = 40, 4000 steps, sighted, read_budget 3, uniform

the law gave `k_max = 1`, so `C = 40`, and the measurement gave **42**. The
note explained the surplus as a rotation: two cells carry a second occupant
that takes 0.50 against a cost of 0.63, loses 0.13 per step, and survives
because it is first on some other step.

That explanation is not wrong about the mechanism, but it was answering the
wrong question. The 42 was not a property of the capacity law. It was a
property of a field that had been built at a level nobody asked for.

## The mistake

`core/src/bin/trace.rs` builds the uniform field as

    "uniform" => Field::new(cells, (rich + poor) / 2.0, regrow)

and the defaults are `rich = 2.0`, `poor = 0.2`. So `--field uniform`
without `--rich` and `--poor` builds a field at

    M = (2.0 + 0.2) / 2 = 1.10

not at `M = 2.0`. The run above passed `--income 1.2` and never passed the
field levels, so it measured a world with `M = 1.1` and `income = 1.2`.

## Why that changes everything

With `M = 1.1`, `r = 0.8`, `income = 1.2`, one occupant cannot get the cell
above 1.1, so it takes whatever is there. The cell is emptied every step and
regrows from zero:

    c -> 0, then 0 + (M - 0) * r = M * r = 1.1 * 0.8 = 0.88

The measured field was exactly **0.8800**, and `taken` was exactly 0.88 for
every organism. That is the saturated branch `M * r` of

    cellLevel(k) = max(M - k*t*(1-r)/r, M*r)

which `Capacity.lean` proves as `cellLevel`. The number was right. The field
was not the field the experiment claimed to use.

## The control that settles it

Same parameters, only `M` changed, 8000 steps, seed 20250102:

| M | rich, poor | alive | occupied cells | occupants/cell | field | `k_max` from the law | `C = k_max * 40` |
|---|---|---|---|---|---|---|---|
| 1.10 | 2.0, 0.2 | 40 | 40 | 1 | 0.8800 | 1 | 40 |
| 1.60 | 2.0, 1.2 | 40 | 40 | 1 | 1.3000 | 1 | 40 |
| 2.00 | 2.4, 1.6 | 40 | 40 | 1 | 1.7000 | 1 | 40 |
| 3.00 | 3.6, 2.4 | 80 | 40 | 2 | 2.4000 | 2 | 80 |

Four for four. The occupancy histogram is not merely the right count, it is
the right *shape*: at `k_max = 1` every cell holds exactly one organism and
no cell is shared; at `k_max = 2` every cell holds exactly two. The surplus
of 2 was an artefact of `M = 1.1`.

The cell level also matches the proved formula at every point:

| M | k | measured | `max(M - k*t*(1-r)/r, M*r)` |
|---|---|---|---|
| 1.10 | 1 | 0.8800 | 0.8800 |
| 1.60 | 1 | 1.3000 | 1.3000 |
| 2.00 | 1 | 1.7000 | 1.7000 |
| 3.00 | 2 | 2.4000 | 2.4000 |

`M = 1.60` is the case that looks like saturation and is not: the measured
1.3000 is above `M*r = 1.2800` by 0.02, so the cell does reach past its
saturation floor. Reading it as `M*r` would have been a rounding mistake.

## What this does not prove

- It does not prove the capacity law for all parameters. It proves it for
  four values of `M` at one `income`, one `regrow`, one `cost`, one
  `cells = 40`. The law is proved in Lean for the arithmetic; these runs
  check that the code implements that arithmetic.
- It does not prove that a surplus above the bound is impossible. The
  rotation mechanism is real: a second occupant at `M = 2.0` takes 0.50
  against 0.63 and loses 0.13 per step, and one step as first occupant
  (+0.57) pays for 4.38 steps as second. A permanent second occupant dies
  in `10.0 / 0.13 = 76.9` steps, so it cannot persist, but a transient one
  can exist. The four runs above did not catch one at 8000 steps.
- It does not say the earlier 42 was a bug. The code did what it was told.
  The experiment did not say what it meant.

## The lesson

`LESSONS.md` already has a rule about stating the condition. This is the
same rule one level down: **a default is an unstated condition.** `--field
uniform` reads like it names a field, but the field it names is
`(rich + poor) / 2`, and both numbers were defaults. Every run that uses
`uniform` must pass `--rich` and `--poor` explicitly, and every result
record must state `M`, not just `--field uniform`.

The guard in `trace.rs` already refuses `--rich == --poor` for `alternating`
and `gradient`, because that makes the uneven arm flat. There is no
corresponding guard for `uniform`, and there should be: a uniform field
built from defaults is a field nobody chose.

## Reproduction

```sh
cd core
cargo build --release --bin trace
./target/release/trace --policy sighted --steps 8000 --every 8000 \
  --seed 20250102 --n 160 --cells 40 --capacity 10 --damage-rate 0.02 \
  --income 1.2 --maintenance 0.6 --repair-cost 1.5 --move-cost 0.1 \
  --energy 5 --regrow 0.8 --read-budget 3 --field uniform \
  --memory-life 100000 --rich 2.4 --poor 1.6
```

Hashes: `M = 1.10` gives `e37041441a854d41`, `M = 2.00` gives
`9e380d1cd8c3ba20`. The first is the hash the earlier 42 run produced.
