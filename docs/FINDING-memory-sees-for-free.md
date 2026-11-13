# FINDING: `memory` sees its neighbours for free, and that is the whole of its movement

2026-11-13. Two measurements, one reading of the code.

## What was measured

One organism, uniform field of 8 cells, `rich = 2.4`, `poor = 1.6`,
`memory-life = 100000`, `seed = 1`, 20 steps.

| policy | `--read-budget` | cells visited | distinct |
|---|---|---|---|
| `memory` | 0 | 1 0 1 2 3 4 5 6 7 6 5 4 3 2 1 0 1 2 3 4 | 8 |
| `stay` | 0 | 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 | 1 |
| `sighted` | 0 | refused to run | — |

The `sighted` refusal is the program being honest:

```
refusing to run: --policy sighted with --read-budget 0 is not sighted.
             A budget of zero reads neither neighbour, so the policy degenerates to
             stay without any error. Pass --read-budget 3 (underfoot + both
             neighbours) or choose --policy stay if standing still is what you mean.
```

## Why

`core/src/life.rs`, the `Policy::Memory` branch, reads both neighbours with
`self.field.level(...)`:

```rust
let left  = if r.cell > 0 { self.field.level(r.cell - 1) } else { f64::NEG_INFINITY };
let right = if self.field.inside(r.cell + 1) { self.field.level(r.cell + 1) } else { f64::NEG_INFINITY };
let best  = here.max(left).max(right);
```

`Field::level` (`core/src/field.rs:178`) is a plain array read. It does not
touch `read_budget`. The budget is subtracted only in the `Policy::Sighted`
branch, where `reads_left` is decremented around each `observe` call.

So the budget is not a property of the field, it is a property of one
policy. `memory` reads two cells per step and pays nothing.

## What this means for the word "memory"

`memory` is described in the code and in the notes as an organism that
sees only its own cell and remembers where it has been. That description
is wrong for the current code. In a uniform field the memory is
overwritten every step with the level of the cell being stood on
(`life.rs`, `if self.policy == Policy::Memory && r.memory.best_cell == r.cell`),
and the only thing that ever points the memory away from the current cell
is the free neighbour read:

```rust
if best > here && best > r.memory.best_level {
    r.memory.best_cell = target;
    ...
}
```

Remove the neighbour read and the memory is always the current cell, so
`direction()` returns 0 forever and the organism never moves. The comment
in the code says as much:

> The memory must be able to point AWAY from the current cell, or the
> organism never moves. A memory that only records "the richest cell I
> have stood on" is always the current cell the moment the organism
> arrives, so `direction()` returns 0 forever.

So the movement of `memory` is **sight**, not memory. The memory is a
one-step buffer for the neighbour reading.

## What this does not prove

1. It does not say `memory` is useless. It says the name is wrong: what
   the policy does is "step toward the richer neighbour, and keep doing
   it for one step even if the neighbour has since been emptied". That is
   a real behaviour, and it differs from `sighted` (which re-reads every
   step and ties to stay).
2. It does not measure the cost of the free read. No experiment here
   compares `memory` against a `sighted` organism with the same effective
   information, because `sighted` cannot be run at budget 0.
3. It does not say the oscillation in the 8-cell run is the general
   behaviour. In the 120-cell run the organism went round the field in
   one direction for 1200 steps. The difference between the two runs is
   the field size relative to the regrow rate, and that is not analysed
   here.
4. The trace does not record `read_budget` at all (`d.get("read_budget")`
   is `None`), so this run cannot be reproduced from its own file. The
   command line is in this note and nowhere else.

## What to do next

1. Record `read_budget` in the trace header, next to `regrow` and `feed`.
   A parameter that changes a policy's behaviour and is not in the trace
   is a parameter that will be forgotten.
2. Decide whether the budget should be a property of the field or of the
   policy. If it is a property of the field, `memory` should pay for its
   two reads and the `sighted` refusal becomes unnecessary. If it is a
   property of the policy, say so where the policies are defined, because
   right now the only place that says it is a refusal message.
3. Rename `Policy::Memory` to something that says what it does, or make
   it actually blind and see what it does then. The second is the better
   experiment: a blind organism with memory is the thing the notes keep
   talking about, and it has not been run.
