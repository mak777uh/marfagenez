# FINDING-087 — crowding 2 is `kSatCount`, and the default layout is random

**Date:** 2026-11-13
**Experiment:** `checks/exp87_which_count_does_the_field_realise.py`
**Run:** `results/EXP-87/run-2026-11-13T02-16-45.json` (verdict `passed`, three controls passed)

## The anomaly this closes

After the formula fix of 2026-11-12, `Capacity.lean` said

```
k_max = ⌊M·r / t⌋
```

which at `M = 2, r = 0.8, t = 0.8` is `⌊1.6/0.8⌋ = 2`, and at `t = 0.9` is `1`.
But the field measurements kept giving **crowding 2** while `C = 400` was
predicted from `k_max = 10` in another regime. Two different counts were being
called "the capacity".

## The two counts

```
kMaxCount = ⌊M·r / t⌋                  -- every organism on the cell eats a full portion
kSatCount = ⌊(M·r − need) / t⌋ + 1     -- the last one only clears `need`
```

`kMaxCount` is the count at which **nobody is rationed**. `kSatCount` is the
count at which **everybody survives**. They differ by at most one, and they
differ only when the fractional part of `M·r/t` is small enough that the
remainder after `kMaxCount` full portions still covers `need`.

At `M = 2, r = 0.8, need = 0.6`:

| `t` | `M·r/t` | `kMaxCount` | `kSatCount` | separates? |
|---|---|---|---|---|
| 0.9 | 1.778 | 1 | 2 | **yes** |
| 0.8 | 2.000 | 2 | 2 | no |
| 0.6 | 2.667 | 2 | 2 | no |

So `t = 0.9` is the only arm in this set that can tell the two apart. The other
two are the silent control.

## The measurement

8 organisms, 4 cells, `--layout even`, uniform field at `M = 2.0`, `r = 0.8`,
`need = 0.6`, `damage 0`, 400 steps, `stay` policy.

| arm | `income` | `kMaxCount` | `kSatCount` | alive | crowding | per cell |
|---|---|---|---|---|---|---|
| A | 0.9 | 1 | 2 | 8 | **2.000** | `{0:2, 1:2, 2:2, 3:2}` |
| B | 0.8 | 2 | 2 | 8 | 2.000 | `{0:2, 1:2, 2:2, 3:2}` |
| C | 0.6 | 2 | 2 | 8 | 2.000 | `{0:2, 1:2, 2:2, 3:2}` |

At `t = 0.9` the field holds **2** per cell, not 1. The second organism is
rationed — it takes `0.7` where the first takes `0.9` — but `0.7 > need = 0.6`,
so it lives. **The field realises `kSatCount`, not `kMaxCount`.**

## The three instrument defects found on the way

This experiment was run four times before it measured anything. Each attempt
failed for a different reason, and all three are the same class of failure as
EXP-80/81/83/84: **the arm did not execute what the docstring said.**

1. **12 organisms on 4 cells measures the spawner.** The first version used
   `--n 12 --cells 4`. All three arms gave `alive 7`, crowding `1.750`,
   independent of `income`. Three organisms per cell means the third starves
   whatever the income is. The run was correct and the question was wrong.

2. **`--layout even` is not the default.** The second version used
   `--n 8 --cells 4` and got `alive 6`, per-cell `{0:1, 1:1, 2:2, 3:2}` at
   every `income`. Frame 0 showed cells `[3, 0, 1, 3, 3, 2, 2, 3]` — **four
   organisms on cell 3, one each on cells 0 and 1**. The default in
   `core/src/bin/trace.rs:51` is `let mut even = false`, so the trace called
   `Life::spawn`, which places each organism at `(rng.uniform() * cells) as
   usize` (`core/src/life.rs:236`). A random layout was read as an even one.

3. **`trace` writes JSON to a file, not to stdout.** `run_trace` first did
   `json.loads(out.stdout)` and got `Expecting value: line 1 column 1`. The
   summary it prints ends with `written:  <path>`; the frames are in that file.

The general lesson, already in `PROTOCOL.md` as "check the simple before the
complex", has a sharper form here: **before believing any verdict, read frame 0
and check that the `cells` list is the one the docstring says.** A placement
claim that does not survive that check is not a claim.

## What this does not prove

- One `M`, one `r`, one `need`, one point of disagreement. The two counts
  coincide at almost every parameter, so this is a single discriminating point,
  not a law about all parameters.
- The organisms do not move. A `sighted` organism that leaves a cell frees it,
  and the count a field realises under movement is a different question.
- `kSatCount` is the count that **survives**, not the count that is
  comfortable. The second organism takes `0.7` against a maintenance of `0.6`:
  a margin of `0.1`, and nothing in this experiment varies that margin.

## Consequence for the model

`Capacity.lean` carries both definitions. The one that belongs in the capacity
arithmetic is `kSatCount` (`⌊(M·r − need)/t⌋ + 1`), because it is the one a
field realises. `kMaxCount` is the count at which nobody is rationed — a
different and stricter notion, useful as a bound but not as the capacity.

The earlier `C = 400` prediction came from `k_max = 10` measured in a regime
with a different `t`; it was not wrong arithmetic, it was the wrong count.
