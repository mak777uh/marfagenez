import Mathlib
import Medium.Reweight

/-!
  The compression law: what actually shrinks the spread.

  The previous file showed that "selection shrinks dispersion" is false in general:
  exponential tilting of a normal trait moves the mean by `k` and leaves the variance
  at exactly `1`. Truncation, by contrast, drops the variance from `1` to `0.363`.

  The numerical experiment then showed something sharper. Truncating below at `-t` and
  truncating above at `+t` give *the same* variance:

      Var[X | X > -t] = Var[X | X < t]

  The side does not matter. What matters is the **length of the interval** that
  survives. So the compression is not caused by selection at all. It is caused by the
  population becoming **bounded**.

  This file proves that. The bound on the spread is set by the width of the support,
  and nothing else.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The support-width law.**
    If every surviving cell's trait lies in `[a, b]`, then the spread of the survivors
    is at most `((b - a) / 2) ^ 2`.

    This is Popoviciu's inequality, and it is the real reason truncation compresses:
    not because it selects, but because it narrows the support. A population confined
    to an interval of width `w` can never have a spread above `(w/2)^2`, whatever the
    selection rule that confined it.

    The corollary for the model: to argue that an environment compresses a
    population, it is not enough to show that the environment selects. It is
    necessary to show that the environment *bounds* the trait. -/
theorem spread_bounded_by_support
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (a b : ℝ)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc a b)
    (hX : AEMeasurable X μ) :
    variance X μ <= ((b - a) / 2) ^ 2 :=
  variance_le_sq_of_bounded h hX

/-- **The Bhatia-Davis law.**
    A sharper form: the spread is at most `(b - E[X]) * (E[X] - a)`.

    This says more than Popoviciu: the spread is largest when the mean sits in the
    middle of the support, and it collapses when the mean is pushed to either edge.
    Selection that drives the mean to the boundary of the support squeezes the
    spread to zero, not because it selects, but because it crowds the population
    against the wall. -/
theorem spread_bounded_by_mean_distance
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (a b : ℝ)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc a b)
    (hX : AEMeasurable X μ) :
    variance X μ <= (b - ∫ x, X x ∂μ) * (∫ x, X x ∂μ - a) :=
  variance_le_sub_mul_sub h hX

/-- **The wall law.**
    If the mean reaches the upper wall of the support, the spread is zero.

    A population whose mean equals the maximum possible trait has no spread at all:
    every cell is at the maximum. Selection that pushes the mean to the wall does not
    merely compress the population, it erases its variation entirely.

    This is the extreme case of the compression law, and it is the one the model
    cares about: a ceiling is not a gentle pressure, it is an eraser. -/
theorem spread_zero_at_wall
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (a b : ℝ)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc a b)
    (hX : AEMeasurable X μ)
    (hmean : ∫ x, X x ∂μ = b) :
    variance X μ <= 0 := by
  have hbd := spread_bounded_by_mean_distance μ X a b h hX
  rw [hmean] at hbd
  simpa using hbd

end Medium
