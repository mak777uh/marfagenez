# FINDING: a blind `memory` organism never stands still

2026-11-13. This note corrects the note next to it, and then corrects
itself. The first reading was wrong, and the way it was wrong is worth
keeping.

## The wrong reading

`FINDING-memory-sees-for-free.md` said: `memory` moves in a uniform field
because it reads its two neighbours for free, and the neighbour read is
the whole of its movement. The measurement behind that was a run with
`--read-budget 0` where `memory` walked through all 8 cells while `stay`
did not move.

The measurement was right. The explanation was wrong.

## What the code actually does

`core/src/life.rs`, the `Policy::Memory` arm of the `direction` match:

```rust
Policy::Memory => {
    // Same direction rule, but the memory keeps updating, so the
    // organism can leave a cell that was once the best.
    if r.memory.best_level <= 0.0 {
        let u = self.rng.uniform();
        if u < 0.5 { -1 } else { 1 }
    } else {
        r.direction()
    }
}
```

With `--read-budget 0` the organism cannot read its own cell either
(`here` is `0.0`, not the field level), so `best_level` stays `0.0`, so
the `else` branch is never taken. Every step is a coin toss. The
`DBG_MEMORY=1` output shows the decision function returning `0` on every
step while the organism still moves:

```
step 0 org cell 0 here 0.000 mem 0 level 0.000 dir 0
step 1 org cell 1 here 0.000 mem 1 level 0.000 dir 0
step 2 org cell 2 here 0.000 mem 2 level 0.000 dir 0
step 3 org cell 3 here 0.000 mem 3 level 0.000 dir 0
```

`dir` is `r.direction()`, evaluated before the match. It is `0` because
`best_cell == cell`. The movement comes from the coin toss above it.

So the movement of a blind `memory` organism is **random walk**, and it
has nothing to do with memory. The comment in the code says "must look
around" and the coin toss is how it looks around.

## What the fix changed

The patch made the `Memory` policy pay for its neighbour reads from
`read_budget`, exactly as `sighted` does. That patch is correct on its
own terms -- one policy should not get free reads that another pays for
-- but it did not do what the note claimed it would. Before the patch,
`memory` at budget 0 moved by free sight. After the patch, `memory` at
budget 0 moves by coin toss. Both move. The patch changed which mechanism
does it, not whether it happens.

## What this does not prove

1. It does not say the patch was wrong. Paying for a read is right
   regardless of what the payment changes.
2. It does not say `memory` is `random`. With information the two
   policies differ: `random` never uses the field, `memory` walks toward
   the remembered cell. The claim is narrower: **with no information,
   `memory` is indistinguishable from `random` in its movement rule.**
3. It does not measure how often a real run is in the no-information
   state. In the 120-cell run with the default budget the organism read
   every step and `best_level` was never `0.0`, so the coin toss never
   fired there.
4. The `Remember` policy has the same `best_level <= 0.0` coin toss, so
   the same statement holds for it. Not measured here.

## The lesson

The first note took a difference between two runs (`memory` moved,
`stay` did not) and assigned it to the mechanism that was nearest in the
code (the neighbour read). The mechanism that was actually running was
three lines further down and produced the same observable. A control that
only says "it moved" cannot tell the two apart.

The control that would have told them apart: run `memory` at budget 0
with the coin toss removed, or compare the cell sequence against
`--policy random` at the same seed. If the sequences match, the movement
is the coin toss. That comparison was not run before the first note was
written.

## Correction: it is not `random` either

The comparison was run. `--policy random` and `--policy memory` at
`--read-budget 0`, same seed 7, 30 steps, 8 cells:

```
random       : 0 1 1 0 0 1 1 1 0 1 2 3 2 2 1 0 0 0 0 0 0 1 1 2 3 4 5 4 5 6
memory blind : 0 1 2 1 0 1 2 3 2 3 4 5 4 5 4 3 4 3 2 1 0 1 2 3 4 5 6 5 6 7
```

Directions match at 20 of 30 positions, and the disagreements are all the
same kind: `random` sometimes returns `0`, `memory` never does.

The two coin tosses are not the same toss:

```rust
Policy::Random  => { if u < 1.0/3.0 { -1 } else if u < 2.0/3.0 { 0 } else { 1 } }
Policy::Memory  => { if u < 0.5     { -1 } else                          { 1 } }
```

`random` chooses among three moves, one of which is standing still.
`memory` chooses among two, neither of which is standing still. So a
blind `memory` organism is a random walk **that never rests**, which is
strictly more movement than `random`, not the same thing.

The title of this note is therefore too strong. The measured statement
is: **with no information, `memory` moves by a coin toss that has no
"stay" outcome.** Calling it `random` was a guess that the comparison
refuted.

## What to do next

1. Decide whether "no information means random walk" is the intended
   design. If it is, say so in the policy table, because a policy named
   `memory` that never stands still when blind will be misread again.
2. Make the two coin tosses comparable, or say why they differ. A blind
   `memory` that cannot rest will deplete a field faster than a blind
   `random` that can, and nothing in the code says that was chosen.
3. Record `read_budget` in the trace header. It is not there now, and
   every claim in this note depends on it.
4. The same three questions apply to `Remember`, which has the same coin
   toss. Not measured.
