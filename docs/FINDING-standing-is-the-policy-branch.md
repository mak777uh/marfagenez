# FINDING: standing still is the policy's own branch, not the density

## What was claimed before

An earlier FINDING said movement depends on density:

```
at n = 80: 84.6% stand still
at n =  8:  0.0% stand still
```

That pair came from `--policy remember` on an alternating field.

## What was measured now

Uniform field, 120 cells, 400 steps, `--every 10`, second half of the run,
`move-cost 0.05`, `income 1`:

| policy | n | stand still |
|---|---|---|
| random | 8 | 0.3688 |
| random | 80 | 0.3194 |
| remember | 8 | 0.0000 |
| remember | 80 | 0.0000 |

Under `random` standing is about 1/3 at both densities, and 1/3 is exactly the
`direction == 0` branch of `Policy::Random` (`core/src/life.rs:344`):

```
u < 1/3 -> -1
u < 2/3 ->  0
else    -> +1
```

Under `remember` standing is 0.0 at both densities, because a remembering
organism with an empty memory always draws `-1` or `+1` and never 0.

So the old 84.6% / 0.0% pair was not a density effect at all. It was two
different policies, or two different phases of one run, being read as one curve.

## What replaces it

Standing is decided before the field is consulted. The policy is:

* `stay` - always 0;
* `random` - 1/3 of the time;
* `remember` / `memory` - never, while the memory is empty; afterwards it is
  whatever `direction()` says, which is 0 only when the remembered cell is the
  current cell;
* `sighted` - 0 whenever no neighbour is richer, which on a uniform field is
  always.

Density enters only through the second group: a cell can hold several organisms,
and `direction()` does not know about crowding, so density cannot change the
decision - only its consequences.

## What this does not prove

* That `remember` never stands still in a non-uniform field. In an alternating
  field it arrives at a rich cell and then `direction()` returns 0.
* That the 84.6% figure was wrong in its own configuration. It was not re-run;
  what is shown is that it is not a density curve, because the same policy at two
  densities gives the same number.

## Why it matters

Any statement of the form "crowding makes organisms settle" has to be checked
against the policy first. At `random` the settle rate is 1/3 and crowding does
not move it; at `remember` it is 0 and crowding does not move it either.
