import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# The other order of operations: regrow, then take

`Medium.Field.cellStep` is **take, then regrow** — the default in the model
(`feed = false`). Its equilibrium is `M + t - t/r`.

The model has a second order, `feed = true` (`core/src/life.rs:115-121`):
regrow first, then take. It is a different world, and its equilibrium is
different by exactly `t`:

    c* = M - t/r

This file proves that. The measured values are in
`docs/FINDING-two-orders-two-equilibria.md` (8 of 8 exact).

## Why the difference is `t`

Take-then-regrow: the organism takes from a full cell, then the cell regrows
toward `M` from what is left. The taken amount is partly put back.

Regrow-then-take: the cell is already at `M` when it regrows, so regrowth does
nothing, and then the organism takes. The equilibrium is lower by exactly one
take, because the take is never followed by a regrowth in the same step.

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

/-- **It is the only fixed point.** -/
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
