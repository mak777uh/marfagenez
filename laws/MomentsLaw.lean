import Mathlib

/-!
  The moment law, proved with Mathlib.

  The second moment of a random variable dominates the square of its mean:

      E[X²] ≥ E[X]²

  This is the statement that the variance is non-negative, written in raw moments.
  It is the algebraic backbone of the selection law: dispersion is what selection
  has to work with, and dispersion can never be negative.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The variance law.**
    The variance of a random variable is non-negative. -/
theorem variance_nonneg' (μ : Measure ℝ) [IsProbabilityMeasure μ] (X : ℝ → ℝ) :
    0 <= variance X μ :=
  variance_nonneg X μ

/-- **The second moment law.**
    The second moment of a random variable is at least the square of its mean.
    Equivalently: the variance is non-negative, written in raw moments. -/
theorem second_moment_ge_mean_sq
    (μ : Measure ℝ) [IsProbabilityMeasure μ] (X : ℝ → ℝ)
    (hX : MemLp X 2 μ) :
    (∫ x, X x ∂μ) ^ 2 <= ∫ x, X x ^ 2 ∂μ := by
  have hvar : 0 <= variance X μ := variance_nonneg X μ
  rw [variance_eq_sub hX] at hvar
  simp only [Pi.pow_apply] at hvar ⊢
  linarith

/-- **The moment gap is the variance.**
    The gap between the second moment and the square of the mean is exactly the
    variance. -/
theorem second_moment_sub_mean_sq
    (μ : Measure ℝ) [IsProbabilityMeasure μ] (X : ℝ → ℝ)
    (hX : MemLp X 2 μ) :
    (∫ x, X x ^ 2 ∂μ) - (∫ x, X x ∂μ) ^ 2 = variance X μ := by
  rw [variance_eq_sub hX]
  simp only [Pi.pow_apply]

end Medium
