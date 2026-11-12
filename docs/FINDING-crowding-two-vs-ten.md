# FINDING: crowding is 2, and `k_max = 10` was never a count

Date: 2026-11-12
Status: settled by arithmetic + Lean (`laws/Medium/Capacity.lean`), build green

## The question

After the formula correction (`cellStep M r t c = (c - t) + (M - (c - t)) * r`,
equilibrium `c* = M - t*(1-r)/r`) it looked as if the field should hold
**10 organisms per cell**, so a 40-cell field should hold `C = 400`. The
measurement gives crowding **2.00** and `C = 80`. Which one is wrong?

## Answer: `k_max = 10` is not a count

The number 10 comes from

```
M * r / (t₀ * (1 - r))  =  2 * 0.8 / (0.8 * 0.2)  =  1.6 / 0.16  =  10
```

That expression is the **steady-state stock divided by the share**, scaled by
`1/(1-r)`. It is not the number of organisms that can stand on a cell.

The count is

```
kMaxCount M r t₀ = ⌊M * r / t₀⌋  =  ⌊2 * 0.8 / 0.8⌋  =  ⌊2⌋  =  2
```

The two differ by exactly the factor `1/(1-r) = 5`. At `r = 0.8` that is the
whole discrepancy: `2 * 5 = 10`.

`docs/CLAIMS.md:158` already listed `k_max = M·r/(t₀(1−r))` as **"верное число
по неверной причине"**. That entry was too generous: the number is not even
right. It is right for a *different* question — "how many shares does the
standing stock cover" — and wrong for "how many organisms can stand here".

## Why the count is the floor, not the ratio

The take is **sequential**. The cell does not hand out `M*r` of credit; it hands
out what is physically there, one organism at a time, and the level drops after
each take. `laws/Medium/Capacity.lean` models this exactly:

```
takeOne t₀ c        = min t₀ c
afterTakes t₀ 0 c   = c
afterTakes t₀ (k+1) c = afterTakes t₀ k (c - takeOne t₀ c)
```

and proves (`afterTakes_nonneg`) that the cell never goes below zero however
many organisms take from it. So the `k`-th organism gets
`min(t₀, c* - (k-1)*t₀)`, and it lives iff that is at least `maintenance`.

At `M = 2, r = 0.8, t₀ = 0.8`:

| k | level before take | take | lives? (maint = 0.6) |
|---|---|---|---|
| 1 | 1.800 | 0.800 | yes |
| 2 | 1.000 | 0.800 | yes |
| 3 | 0.200 | 0.200 | **no** |

So `k = 2`. The level with two organisms is `cStar 2 0.8 2 0.8 = 1.6`, which is
the measured `1.600`. Proved as `measured_levels` in `Capacity.lean:388`.

## Why 10 is not merely a stale number

It is a *category error* that a formula can produce without any bug: the
expression `M*r/(t₀*(1-r))` is dimensionally a count (shares), it is
monotone in the right directions, and it gives the right answer for
`r → 0` (large) and `r → 1` (infinite). It only breaks because the take is
discrete and sequential. The `floor` is where the model stops being linear —
`Capacity.lean:219` says this explicitly.

## What this does NOT prove

- That `C = 80` is right for every parameter set. It is right at
  `M = 2, r = 0.8, t₀ = 0.8` and at the two other parameter sets measured in
  `docs/FINDING-capacity-exact.md` (`M = 4.0 → k_max = 4 → C = 126`;
  `M = 2.25 → k_max = 2 → C = 77`), because there the count is limited by
  **seating** (`sum min(occupancy, k_max)`), not by the per-cell count alone.
- That the field never holds more than 80. It holds more organisms than that in
  the transient; 80 is the number that survives.
- Anything about `r ≥ 1` or `r = 0`. `kMaxCount` divides by `t₀`, not by
  `1 - r`, so it is defined there, but the equilibrium `c*` changes sign and the
  survival argument above no longer applies.

## Where the numbers live

| quantity | formula | value at `M=2, r=0.8, t₀=0.8` | Lean |
|---|---|---|---|
| count of organisms | `⌊M*r/t₀⌋` | **2** | `kMaxCount`, `kFeedCount` |
| steady level, k = 1 | `M - t*(1-r)/r` | 1.800 | `cStar_one`, `measured_levels` |
| steady level, k = 2 | `M + 2t - 2t/r` | 1.600 | `measured_levels` |
| continuous capacity | `M*r/t₀` | 2.0 | `capacity` |
| field capacity | `cells * kMaxCount` | **80** | `totalCapacity` (continuous form) |
| the wrong 10 | `M*r/(t₀*(1-r))` | 10 | — (not in Lean) |

## Reproduce

```bash
cd laws && lake build Medium.Capacity     # 0 errors
```

Theorems that decide this: `kMaxCount`, `kFeedCount_iff`, `count_jumps_at_threshold`,
`measured_levels`, `afterTakes_nonneg`, `cStar_draw_le_iff`, `kth_take_full_iff`.
