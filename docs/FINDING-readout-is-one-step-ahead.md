# FINDING: the readout is one step ahead of the energy it explains

## What was measured

One organism, no food, uniform field, `damage-rate 0.2`, `maintenance 0.1`,
`repair-cost 0.5`, `energy 5`, `move-cost 0.2`, 40 steps, `--every 1`.
26 usable steps over two field widths (2 and 120 cells).

Per-step energy drop and the decision recorded in the frame:

| direction (frame k) | moved | drop | count |
|---|---|---|---|
| −1 | no  | 0.2 | 4 |
| −1 | no  | 0.4 | 1 |
| −1 | yes | 0.4 | 3 |
| 0  | no  | 0.2 | 4 |
| 0  | no  | **0.4** | 2 |
| 0  | yes | **0.4** | 2 |
| 1  | no  | 0.2 | 2 |
| 1  | no  | 0.4 | 2 |
| 1  | yes | 0.4 | 6 |

Two rows are impossible under any cost model: a step with `direction 0` that
cost 0.4, and a step with `direction 0` on which the cell changed.

## What the cause is

Not the model. The readout.

`Life::advance` (`core/src/life.rs:229`) ends with `self.step += 1`. The frame is
numbered `self.step`, so frame *k* carries the state **after** step *k* and the
decision **of** step *k*. The drop between frame *k* and frame *k+1* is the cost
of step *k+1*. Comparing `direction` of frame *k* with that drop is off by one
step.

With the decision taken from the **later** frame:

```
drop = 0.2 + 0.2 * (direction != 0)
```

holds on **26 of 26** steps. With the earlier frame it fails on 10 of 26.

## What this fixes

The cost of a step is closed:

```
maintenance + damage_rate*repair_cost + move_cost*(direction != 0)
= 0.1 + 0.2*0.5 + 0.2*(direction != 0)
```

Two earlier readings were wrong because of this:

* EXP-42 concluded "a refused move is paid" from a 0.4 drop on a step where the
  cell did not change. The 0.4 belonged to a different step.
* EXP-43 tried to explain the extra 0.2 as repair. `damage` is 0.0 in every
  frame, before and after, so repair pays nothing at these energies. The extra
  0.2 is the move cost, and it does not depend on whether the move succeeded.

## What this does not prove

* That other fields of the sample are aligned the same way. `direction` and
  `taken` are both written during `advance`, so both belong to step *k*; the
  energy is read after. This was checked for `direction` only.
* That the move cost is charged for a move the field refuses. On two cells the
  organism pays 0.2 extra on steps where it does not change cell, which is
  consistent with paying before the bounds check (`core/src/life.rs:423`), but
  the alignment fix alone does not separate "paid and refused" from "chose and
  the field moved it back".
* Anything about a fed field. With `income > 0` the organism can outlive
  25 steps and the drop is no longer the whole story.

## Why this matters for every earlier experiment

Every experiment that compared `direction` or `taken` to a change measured
between frames is off by one step. The population counts do not change (they are
read from the same frame), but any statement of the form "it chose X and then Y
happened" needs re-reading with the shift.
