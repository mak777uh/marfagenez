# The surplus above the bound is bought with movement, and it has a price

**Date:** 2026-11-12
**Experiments:** EXP-53 (rotation needs movement), EXP-54 (surplus price)
**Supersedes:** nothing. This extends `FINDING-the-capacity-law-measured-the-wrong-ceiling.md`.

## The thing that needed explaining

EXP-52 found 42 organisms alive on a 40-cell field at income 1.20, where the
corrected capacity law allows 40. EXP-53 removed movement and got exactly 40.
That established the surplus *needs* movement. It did not establish what
movement *costs* — and a surplus that survives 8000 steps while the arithmetic
says a second occupant dies in 72 is a surplus someone is paying for.

## The arithmetic, before any run

```
c*      = M + income - income/r = 2.0 + 1.2 - 1.5 = 1.70
cost    = maintenance + damage*repair = 0.6 + 0.02*1.5 = 0.63
net     = income - cost = 1.2 - 0.63 = 0.57 per step, alone on a cell

first taker:  min(c*, income)          = 1.20  -> +0.57 per step
second taker: min(c* - 1.20, income)   = 0.50  -> -0.13 per step
```

A second occupant that stays dies in `9.37 / 0.13 = 72` steps. EXP-53 ran 8000
steps — 111 such lifetimes — and still had two second occupants. They do not
stay. They rotate.

A rotation costs `move_cost` per move, so the surplus should have a price.

## What was measured

Fixed: uniform field, `income 1.2`, `n 160`, `cells 40`, 8000 steps, seed
20250101, `read_budget 3`, `sighted`.

| move_cost | alive | doubles | moved | surplus |
|---:|---:|---:|---:|---:|
| 0.10 | 42 | 2 | 8 | **+2** |
| 0.15 | 42 | 2 | 6 | **+2** |
| 0.18 | 40 | 0 | 0 | 0 |
| 0.20 | 40 | 0 | 0 | 0 |
| 0.30 | 40 | 0 | 0 | 0 |
| 0.60 | 40 | 0 | 0 | 0 |

The threshold is in `(0.15, 0.18)`.

## It is a step, not a slope

The surplus is 2 or 0. Never 1. That matters: a population equilibrium that
happened to land near the bound would show 3, 2, 1, 0 as the price rose. This
shows the surplus is a yes/no fact about whether rotation pays, not a
continuous quantity that shrinks.

## The control that makes it falsifiable

A sighted organism that cannot see its neighbours cannot choose a direction.
`read_budget 1` reads only the cell underfoot, so `best > here` is never true
and the policy degenerates to `stay`.

| read_budget | alive | doubles | moved | surplus |
|---:|---:|---:|---:|---:|
| 1 (no neighbours visible) | 40 | 0 | 0 | **0** |
| 3 (neighbours visible) | 42 | 2 | 8 | **+2** |

Same price (0.10), same field, same seed. Only sight differs. Remove sight and
the surplus goes with it. This is what makes "movement causes the surplus"
falsifiable rather than a story: had the blind arm held 42, the whole account
would be wrong.

The blind arm also holds exactly 40, not fewer. Blindness costs no lives — so
the drop is about movement, not about perception.

## What the sweep does not collapse

`move_cost` 0.18 through 0.60 all give 40 alive, 0 doubles, 0 moved — the same
macroscopic state — but **all six trajectories hash differently**. The system
is not frozen; it is in the same visible configuration with different energies.
Reporting them as one arm would have been wrong, and the hash check (§5) is
what caught it.

## Why the threshold is where it is

Not `income - cost = 0.57`, which is what "can one step of income pay for one
move" predicts. The measured threshold is three times lower.

The reason is that a rotating second occupant is not paying `move_cost` every
step. At `move_cost 0.10` only 8 of 42 organisms move in a given step — about
19%. It spends most steps alone on a cell earning +0.57 and few steps sharing
and losing 0.13. Its average is positive as long as the rotation is rare
enough, and the rotation gets rarer as it gets more expensive. The threshold is
where the average crosses zero, and it depends on how often rotation is
*needed*, not on the price of a single move.

That is why the number is not derivable from `income - cost`: it is a
dynamical quantity, as EXP-53 already said, and this experiment locates it
without explaining its value in closed form.

## What this does not prove

- **No organism identity.** Samples carry no id, so "the two second occupants
  rotate" is inferred from cell indices changing between samples, not from
  following individuals.
- **One seed.** The surplus is not shown stable across seeds.
- **This income only.** EXP-52 found a different surplus (53 vs 40) at income
  1.0. The threshold belongs to income 1.2 and is not a field constant.
- **Blindness and immobility are not separated.** `read_budget 1` removes both
  the neighbour view and the underfoot view. A cleaner control would remove
  only the neighbour view, which the binary does not offer.
- **The threshold is bracketed, not located.** Six prices; the claim that the
  fall is a step rests on no arm landing between 2 and 0.
- **The closed form is missing.** The threshold's *value* is measured, not
  derived. Writing `move_cost* ≈ 0.16` into a law would repeat exactly the
  error EXP-52 found in the capacity law.

## What changed in what we believe

Before EXP-53, "capacity 40" was a law about the field. After EXP-53, the field
holds 40 and movement can add 2. After EXP-54, the 2 is not free: it is bought
at a price, and above that price the field's own number is all you get.

The honest statement of the field's capacity is now: **40 organisms, and up to
2 more if movement is cheaper than 0.15 per step at income 1.2.** The second
clause is a property of the organism's locomotion, not of the field.
