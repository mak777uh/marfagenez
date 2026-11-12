# FINDING: the sighted organism moves because it eats its own cell

EXP-64, 2026-11-12. Follows `FINDING-the-latecomer-walks-a-full-field.md`.

## The question

EXP-63 measured a sighted organism on a uniform field moving 78 times in 199
steps. `Policy::Sighted` steps toward a richer neighbour and stays when its own
cell is as rich as both neighbours (`core/src/life.rs:400-434`), so on a uniform
field it should stay. It does not. Why?

The guess was that eating makes the cell poor: the organism takes `1.200` from
its own cell, the cell drops to `0.500`, the neighbours have regrown, so the
organism makes its own cell the poorest thing it can see and leaves.

## The arithmetic before the run

The decision is made **before** the eat, on the field as it stands at the start
of the step (`core/src/life.rs:277-279` reads `here`, then the policy runs, then
`core/src/life.rs:455` eats). So the `taken` recorded on a step cannot be the
cause of that step's move -- it is a consequence. The value the organism saw is
the level of its own cell in the **previous frame**, and the previous frame is
sampled after regrowth (`core/src/life.rs:462-465`), which is exactly the field
the next step starts from.

With `rich = 2.4`, `poor = 1.6`, `regrow = 0.8`, `income = 1.2`:
- the uniform field is built at `(rich + poor) / 2 = 2.0` and every cell's
  ceiling is `2.0`;
- an untouched cell sits at `2.0`;
- a cell eaten from at `2.0` drops to `0.8`, then regrows to `0.8 + 1.2 * 0.8 =
  1.76`;
- a cell eaten from at `1.76` drops to `0.56`, then regrows to `0.56 + 1.44 *
  0.8 = 1.712`, and so on to the fixed point `c* = 2.0 - 1.2 * (1 - 0.8) / 0.8 =
  1.7`.

So an organism that eats sits on `1.7` while an untouched neighbour is at `2.0`.
The gap is `0.3` and it is entirely the organism's own doing.

## The measurement

`checks/exp64_why_it_moves.py`, `n = 160`, `cells = 40`, `steps = 8000`,
`every = 1`, seed 20250101, policy `sighted`, read budget 3, steps after 500:

| | moved | stood still |
|---|---|---|
| steps | 54509 | 254913 |
| a neighbour was richer **at the start of the step** | 39711 (72.9%) | 33642 (13.2%) |
| own cell level, mean | 1.6679 | 1.6983 |
| best neighbour level, mean | 1.7007 | 1.7003 |
| `taken` on that step, mean | 1.1039 | 1.1933 |
| mates on the cell, mean | 0.30 | 0.01 |

The difference is **59.7 percentage points**: a step that starts with a richer
neighbour moves, a step that does not stays.

But 27.1% of the moves (14798) had no richer neighbour in the previous frame.
That residue is not explained by the table above, so it was measured directly.

**Single organism, same field, 600 steps** (`n = 1`, everything else unchanged):
**599 moves, 0 stands still, 0 moves without a richer neighbour.**

One organism alone never has a companion to eat its neighbours, so every move it
makes is visible as "a neighbour is richer". With 160 organisms the neighbours
are eaten too, so on 27.1% of the moves the neighbour that was richer at the
instant of the decision is no longer richer in the frame that records the step.
The frame records the field **after** every organism has acted; the decision is
made **before** the organism acts, in slot order. The residue is that gap, not a
second mechanism.

## What this establishes

- The sighted organism's walk is **self-inflicted**: it eats its own cell down to
  `1.7` while untouched cells sit at `2.0`, and then moves to the richer cell.
- The move is not a random tie-break. On a field that is uniform at the instant
  of the decision it stays, and the single-organism run confirms the decision
  rule fires exactly when a neighbour is richer.
- The `taken` on a step is a **consequence** of the move, not its cause. Reading
  the trace as "it moved because it took little" reverses the arrow.

## What this does not prove

- **That the organism is better off moving.** It spends `0.10` per move and
  arrives at a cell that is `2.0` only until it eats it. Whether the walk pays
  for itself is a separate measurement, and EXP-55's survival numbers are the
  place to look, not this note.
- **That 72.9% is a law.** It is one seed, one density, one field. At a different
  density the neighbours are eaten at a different rate and the fraction changes.
- **That the residue is fully accounted for.** The single-organism run shows the
  decision rule is consistent when there are no companions; it does not measure
  the multi-organism residue directly. The claim that the residue is the
  frame-versus-decision gap is an inference from the two runs, not a separate
  control.
- **Anything about `Memory` or `Remember`.** They use a different branch of the
  same function and were not run here.
