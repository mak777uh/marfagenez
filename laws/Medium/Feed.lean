import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# The other order of operations: regrow, then take

`Medium.Field.cellStep` is **take, then regrow** — the default in the model
(`feed = false`). Its equilibrium is `M + t - t/r`.

The model has a second order, `feed = true` (`core/src/life.rs:115-121`):
regrow first, then take. It is a different world, and its equilibrium is
lower by exactly `t`:

    c* = M - t/r

So `M + t - t/r` (take-then-regrow) and `M - t/r` (regrow-then-take) are two
different worlds, and the gap between them is exactly one take.

This file proves the regrow-then-take equilibrium. The measured values are in
`docs/FINDING-two-orders-two-equilibria.md` (8 of 8 exact).

## Why the difference is `t`

Take-then-regrow: the organism takes from a full cell, then the cell regrows
toward `M` from what is left. The taken amount is partly put back, so the
equilibrium sits one take higher.

Regrow-then-take: the cell regrows toward `M` first, and then the organism
takes. The take is never followed by a regrowth in the same step, so the
equilibrium is lower by exactly one take.

Note: `M + t - t/r` and `M - t*(1-r)/r` are NOT equal — they differ by `t`.
Only `M - t/r` is a fixed point of `feedStep`. Verified numerically before
patching; assuming otherwise costs a long detour.

## What is proved

* `feedStep` — the step function for regrow-then-take
* `feed_fixed_point` — `M - t/r` is a fixed point
* `feed_fixed_point_unique` — and it is the only one, when `r ≠ 0`
* `feed_equilibrium_nonneg_iff` — `0 ≤ c*` exactly when `t ≤ M*r`
* `equilibrium_minus_feed` — the two equilibria differ by exactly `t`

## What is NOT proved

That the population reaches it. That is the same gap as for `cellStep`: it
needs a model of who stands where.
-/

namespace Medium

/-- **Regrow, then take.** One organism taking `t` from a cell of level `c`. -/
noncomputable def feedStep (M r t c : ℝ) : ℝ :=
  let c₁ := c + (M - c) * r
  c₁ - t

/-- **The equilibrium of regrow-then-take is `M - t/r`.** -/
theorem feed_fixed_point {M r t : ℝ} (hr : r ≠ 0) :
    feedStep M r t (M - t / r) = M - t / r := by
  simp only [feedStep]
  field_simp
  ring

theorem feed_fixed_point_unique {M r t c : ℝ} (hr : r ≠ 0)
    (h : feedStep M r t c = c) : c = M - t / r := by
  simp only [feedStep] at h
  have h2 : (M - c) * r = t := by linarith
  have h3 : M - c = t / r := by
    rw [eq_div_iff hr]
    linarith
  linarith

/-- **The cell stays non-negative exactly when the take fits in the regrowth.**

`c* = M - t/r ≥ 0` iff `t ≤ M*r`. Below that the organism eats the cell to
nothing every step — measured at `M = 2, r = 0.5, t = 1`, where the field sits
at exactly `0.0` (`docs/FINDING-two-orders-two-equilibria.md`). -/
theorem feed_equilibrium_nonneg_iff {M r t : ℝ} (hr : 0 < r) :
    0 ≤ M - t / r ↔ t ≤ M * r := by
  constructor
  · intro h
    have h1 : t / r ≤ M := by linarith
    rwa [div_le_iff₀ hr] at h1
  · intro h
    have h1 : t / r ≤ M := by
      rw [div_le_iff₀ hr]
      linarith
    linarith

/-- **Regrow, then take, with `k` organisms on the cell.**

`k` organisms each take `t` after the cell has regrown. The equilibrium is
`M - k*t/r`: the take is multiplied by `k` because they all take before the
next regrowth. -/
noncomputable def feedStepK (M r t : ℝ) (k : ℕ) (c : ℝ) : ℝ :=
  let c₁ := c + (M - c) * r
  c₁ - k * t

/-- **The equilibrium of regrow-then-take with `k` organisms is `M - k*t/r`.**

Measured exactly at `n = 8, cells = 8, r = 0.5, t = 1.0, M = 2.0` and
`M = 4.0` (`docs/FINDING-field-segregates.md`): a cell with `k = 1` sits at
`M - t/r`, a cell with `k = 2` sits at `max(M - 2t/r, 0)`. -/
theorem feed_fixed_point_k {M r t : ℝ} (k : ℕ) (hr : r ≠ 0) :
    feedStepK M r t k (M - k * t / r) = M - k * t / r := by
  simp only [feedStepK]
  field_simp
  ring

/-- **It is the only fixed point, for `k` organisms.** -/
theorem feed_fixed_point_k_unique {M r t c : ℝ} (k : ℕ) (hr : r ≠ 0)
    (h : feedStepK M r t k c = c) : c = M - k * t / r := by
  simp only [feedStepK] at h
  have h2 : (M - c) * r = k * t := by linarith
  have h3 : M - c = k * t / r := by
    rw [eq_div_iff hr]
    linarith
  linarith

/-- **`k` organisms empty the cell exactly when `k*t ≥ M*r`.**

`M - k*t/r ≤ 0` iff `M*r ≤ k*t`. This is the per-cell condition behind the
segregation: at `r = 0.5, t = 1.0, M = 2.0` the threshold is `k ≥ 1`, and the
measurement shows a `k = 2` cell at exactly `0.0` while a `k = 1` cell sits at
`0.0` as well — both emptied, but for the same reason. At `M = 4.0` the
threshold is `k ≥ 2`, and the `k = 1` cells stay at `2.0`. -/
theorem feed_k_empties_iff {M r t : ℝ} (k : ℕ) (hr : 0 < r) :
    M - k * t / r ≤ 0 ↔ M * r ≤ k * t := by
  constructor
  · intro h
    have h1 : M ≤ k * t / r := by linarith
    rwa [le_div_iff₀ hr] at h1
  · intro h
    have h1 : M ≤ k * t / r := by
      rw [le_div_iff₀ hr]
      linarith
    linarith

/-- **The two orders of operations differ by exactly one take.**

`equilibrium M r t - (M - t/r) = t`. This is the whole content of
"the flag `feed` changes the world": not a small correction, one full portion. -/
theorem equilibrium_minus_feed {M r t : ℝ} :
    equilibrium M r t - (M - t / r) = t := by
  unfold equilibrium
  ring

/-- **Regrow-then-take converges geometrically with the same factor.**

The gap to the feed equilibrium is multiplied by `(1 - r)` every step, exactly
as in the take-then-regrow case. Only the limit differs. -/
theorem feed_approaches {M r t c : ℝ} (hr : r ≠ 0) :
    feedStep M r t c - (M - t / r) = (c - (M - t / r)) * (1 - r) := by
  simp only [feedStep]
  field_simp
  ring

end Medium
