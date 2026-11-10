import Mathlib

/-!
  The selection law, proved with Mathlib.

  A population has a trait distribution. Selection favours a higher trait: the cells with
  a higher trait die less often, so the mean trait of the survivors is at least the mean
  trait of the population.

  What this file proves: the expectation of a trait is monotone in the trait, and the
  expectation of a constant is the constant.
-/

namespace Medium

open MeasureTheory

/-- **The expectation of a constant.**
    The expectation of a constant function is the constant. -/
theorem integral_const (μ : Measure ℝ) [IsProbabilityMeasure μ] (c : ℝ) :
    ∫ _ : ℝ, c ∂μ = c := by
  simp

/-- **The monotone expectation law.**
    If `f ≤ g` almost everywhere, the expectation of `f` is at most the expectation of
    `g`. -/
theorem integral_mono_of_le
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (f g : ℝ → ℝ)
    (hf : Integrable f μ) (hg : Integrable g μ)
    (h : f ≤ᵐ[μ] g) :
    ∫ x, f x ∂μ <= ∫ x, g x ∂μ :=
  integral_mono_ae hf hg h

/-- **The selection law.**
    If the survivors' trait is at least the population's trait almost everywhere, the
    survivors' mean trait is at least the population's mean trait. -/
theorem selection_raises_mean
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (popTrait survTrait : ℝ → ℝ)
    (hpop : Integrable popTrait μ) (hsurv : Integrable survTrait μ)
    (h : popTrait ≤ᵐ[μ] survTrait) :
    ∫ x, popTrait x ∂μ <= ∫ x, survTrait x ∂μ :=
  integral_mono_ae hpop hsurv h

end Medium
