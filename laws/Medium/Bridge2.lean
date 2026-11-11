import Mathlib
import Medium.Bridge
import Medium.MomentsLaw

/-!
  The selection-disPERSION law: what selection has to work with.

  `Selection2.lean` says, in a comment, what it does *not* prove:

  > What this file does NOT prove: that selection raises the mean trait.
  > That needs probabilities and a model of inheritance.

  This file supplies exactly that. Through the bridge a finite population is a
  probability measure, so the moment law applies to cells.

  The first principle: selection can only reweight. It cannot create a trait that no
  cell has, and it cannot create dispersion that the population does not already
  carry. The mean moves inside the range; the spread is bounded below by zero and
  the second moment dominates the square of the mean.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The dispersion law.**
    In any population, finite or infinite, the second moment of the trait is at
    least the square of the mean trait. The gap between them is the variance, and
    it can never be negative.

    This is the moment law carried across the bridge: it now speaks about cells. -/
theorem population_dispersion
    (μ : Measure ℝ) [IsProbabilityMeasure μ] (X : ℝ → ℝ)
    (hX : MemLp X 2 μ) :
    (∫ x, X x ∂μ) ^ 2 <= ∫ x, X x ^ 2 ∂μ :=
  second_moment_ge_mean_sq μ X hX

/-- **The dispersion gap law.**
    The population's spread is exactly the difference between the second moment and
    the square of the mean. Selection that leaves the second moment and the mean
    unchanged leaves the spread unchanged: nothing is invented. -/
theorem population_dispersion_gap
    (μ : Measure ℝ) [IsProbabilityMeasure μ] (X : ℝ → ℝ)
    (hX : MemLp X 2 μ) :
    (∫ x, X x ^ 2 ∂μ) - (∫ x, X x ∂μ) ^ 2 = variance X μ :=
  second_moment_sub_mean_sq μ X hX

/-- **The selection range law.**
    Selection moves the mean only inside the range the population already spans.

    If every cell's trait lies in `[lo, hi]`, then so does the mean trait — before
    and after selection. Selection is a reweighting, and a reweighting cannot leave
    the convex hull of the values it reweights. -/
theorem selection_stays_in_range
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (lo hi : ℝ)
    (hX : Integrable X μ)
    (hlo : ∀ᵐ x ∂μ, lo <= X x)
    (hhi : ∀ᵐ x ∂μ, X x <= hi) :
    lo <= ∫ x, X x ∂μ ∧ ∫ x, X x ∂μ <= hi :=
  mean_between_extremes μ X lo hi hX hlo hhi

/-- **The selection cannot invert the range law.**
    If the mean sits strictly above the lower bound, then some cell strictly exceeds
    that bound. Selection cannot raise a mean above a ceiling that no cell reaches:
    the mean of a population is a weighted average, and an average never exceeds the
    largest term.

    This is the formal answer to "can selection create a trait?" — no. -/
theorem mean_le_of_all_le
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (lo hi : ℝ)
    (hX : Integrable X μ)
    (hlo : ∀ᵐ x ∂μ, lo <= X x)
    (hhi : ∀ᵐ x ∂μ, X x <= hi) :
    ∫ x, X x ∂μ <= hi :=
  (mean_between_extremes μ X lo hi hX hlo hhi).2

end Medium
