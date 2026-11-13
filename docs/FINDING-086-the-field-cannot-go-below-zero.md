# FINDING-086 — the field cannot go below zero, so a starved cell sits at `M·r`

**Date:** 2026-11-13
**Experiment:** `checks/exp86_the_field_cannot_go_below_zero.py`
**Run:** `results/EXP-86/run-2026-11-13T02-12-27.json` (verdict `passed`, three controls passed)

## The observation

EXP-85's arm D had `M = 2.4`, `r = 0.8`, `income = 2.0 > M·r = 1.92`. The law
of FINDING-085 gives

```
L* = 2.4 − 2.0·0.2/0.8 = 2.4 − 0.5 = −0.1
```

which is not a level. The measured level was **1.920000 = M·r exactly**, and the
organism was alive at full energy.

## Why

Two `min`s, one on each side of the meal:

```rust
// core/src/field.rs:192
let taken = self.cells[cell].min(amount);

// core/src/organism.rs:165
let taken = resource.max(0.0).min(world.income);
```

A cell can only be **emptied**, never overdrawn. So once `income > M·r`, every
step is the same cycle:

```
cell = 0  →  regrow to M·r  →  take min(M·r, income) = M·r  →  cell = 0
```

The frame is taken **after** the regrowth (`core/src/trace.rs:186`), so it
always reads `M·r`. The organism receives `M·r` per step, not `income`.

## The measurement

Same field and world as EXP-85, 400 steps, `--start-cell 0`.

| arm | `income` | `M·r` | predicted | measured level | measured `taken` |
|---|---|---|---|---|---|
| A | 1.0 | 1.92 | 2.15 (unsaturated) | **2.150000** | 1.000000 |
| B | 2.0 | 1.92 | 1.92 (starved) | **1.920000** | 1.920000 |

A third arm at `income = 1.92` was run and returned **the same hash** as
`income = 2.0` (`08428c70a87a5f1b`). The framework refused to pass two arms
sharing a hash, and it was right: they are one run. That agreement is a fact
about `min`, not a second measurement, and the experiment records it as such.

## The two regimes, in one picture

```
L*
M ┤───────────────╲
  │                ╲
  │                 ╲
M·r┤ ─────────────────╲────────  (floor: the frame can never read less)
  │                    ╲
  0┼─────────────────────╲──────
   0            M·r      income →
```

- `income ≤ M·r`: `L* = M − income·(1−r)/r`, falling linearly in `income`.
- `income > M·r`: `L* = M·r`, flat. The appetite no longer matters.

The two branches meet at `income = M·r`, where both give `M·r`
(`M − M·r·(1−r)/r = M − M(1−r) = M·r`). The function is continuous.

## What this does not prove

- The organism is not necessarily fine. It receives `M·r` per step; whether
  that covers maintenance, damage and repair is a different question, and this
  experiment holds those fixed.
- The cell is empty at the moment of the take and at `M·r` at the moment of the
  frame. Both are true; only one is visible. A "the cell is never empty"
  conclusion from a trace is a conclusion about the frame, not about the cell.
- One organism, one cell, one world.

## Consequence for the model

`M·r` is a **hard supply ceiling per cell per step**. No parameter choice can
make a cell deliver more than `M·r` per step, no matter how large `income` is.
That is the quantity that belongs in the capacity arithmetic, not `income`.
