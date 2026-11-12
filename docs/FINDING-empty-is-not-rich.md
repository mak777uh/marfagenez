# FINDING: an empty cell is not a richer cell

**Date:** 2026-11-12
**Experiment:** EXP-27 `empty-cell-refused` — `results/empty-cell-refused/run-2026-11-12T21-42-08.json`
**Verdict:** passed

## The question

EXP-26 measured something odd: at `n = 160` on 40 cells the population settles at
77 alive with 0–3 empty cells, and the number varies with the seed. The 80 who
survive are at capacity; the empty cells stay empty.

EXP-26's explanation was: *in a uniform field an empty cell is not richer than an
occupied one — both are 1.600 — and `sighted` only moves toward a richer
neighbour.*

That is a statement about the decision rule, not about the population. It can be
tested directly, with one organism and three cells.

## The rule

`core/src/life.rs`, `Policy::Sighted`:

```
best = max(here, left, right)
if best > here:  step toward the better neighbour (tie -> left)
else:            stay
```

The prediction follows from the rule alone:

| shape | here | left | right | prediction | measured |
|---|---|---|---|---|---|
| `equal` | 1.6 | 1.6 | 1.6 | 0 (best == here) | **0** |
| `richer` | 2.4 | 1.6 | 3.2 | +1 (3.2 > 2.4) | **+1** |
| `enter-empty` | 1.6 | — | 0.0 | 0 (1.6 == here) | **0** |
| `leave-empty` | 0.0 | 1.6 | 0.0 | −1 (1.6 > 0.0) | **−1** |

`Stay` is 0 in all four. `Random` is −1 in all four, which shows the field is not
what decides: random moves regardless of level.

So the rule is exactly asymmetric about emptiness:

- it will **not** enter an empty cell, because empty is not better;
- it **will** leave an empty cell, because the neighbour is better.

That asymmetry is the mechanism EXP-26 assumed. It is now measured.

## What this does not prove

It does not show that the empty cells at `n = 160` came from this rule. It shows
the rule *cannot fill them*, which is a necessary part of the explanation, not the
whole of it. The population-level consequence — that 77 rather than 80 survive —
still needs its own measurement.

## A trap found on the way: `read_budget` must be 3

Seeing costs three reads: the cell underfoot, the left neighbour, the right
neighbour. With `read_budget = 2` the budget runs out after reading the left
neighbour, the right neighbour is never read, and `Sighted` silently degrades to
"look left only".

Measured before the fix, on the `richer` shape (here = 2.4, left = 1.6,
right = 3.2): the answer was **0**, not +1. After the fix it is +1.

This is not a model defect — the test suite in `core/src/life.rs` already uses
`read_budget: 3` everywhere. It was a defect in the experiment. But it is a real
trap for anyone writing a sighted policy: a budget that is one too small does not
fail loudly, it just makes the organism half-blind, and the result still looks
like a decision.

## Where this leaves the picture

Three things are now measured separately and agree:

1. the field in equilibrium is uniform at 1.600;
2. capacity is 80 on 40 cells, crowding 2.00;
3. a sighted organism will not step into an empty cell, and will step out of one.

Together they say: once the population is at capacity, the empty cells left by
deaths are not refilled by movement, because movement needs a gradient and the
field has none. The refilling, if it happens, has to come from somewhere else —
and that is the next question.
