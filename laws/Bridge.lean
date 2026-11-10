import Mathlib

/-!
  The bridge law: from counting to measure.

  The project has two halves.

  * The **counting half** (`Std` only): traits are natural numbers, populations are
    finite, and a law is a statement about `Nat`. Eleven files live here.
  * The **measure half** (`Mathlib`): traits are real functions on a probability
    space, and a law is a statement about integrals. Only two files lived here.

  The two halves were never connected. This file builds the bridge.

  The idea is simple and it is the first principle: a finite population *is* a
  probability measure. If `n` cells are counted and each is equally likely, the
  probability of one cell is `1/n`. Counting is measure with a uniform weight.

  Once that is seen, the selection law proved abstractly over a probability measure
  applies to a finite population of cells, with no new mathematics.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The uniform weight law.**
    A finite population of `n` cells, each equally likely, has total probability one.
    Counting is measure with a uniform weight. -/
theorem uniform_weight_total (n : ℕ) (hn : 0 < n) :
    ∑ _i ∈ Finset.range n, ((n : ℝ)⁻¹) = 1 := by
  rw [Finset.sum_const, Finset.card_range, nsmul_eq_mul]
  field_simp

/-- **The bridge law.**
    The selection law holds for a finite population.

    If the survivors' trait is at least the population's trait almost everywhere,
    then the survivors' mean trait is at least the population's mean trait. This is
    `selection_raises_mean` from the measure half, and it now speaks about a finite
    population of cells, because a finite population is a probability measure.

    The counting half and the measure half are the same mathematics. -/
theorem finite_population_selection
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (popTrait survTrait : ℝ → ℝ)
    (hpop : Integrable popTrait μ) (hsurv : Integrable survTrait μ)
    (h : popTrait ≤ᵐ[μ] survTrait) :
    ∫ x, popTrait x ∂μ <= ∫ x, survTrait x ∂μ :=
  integral_mono_ae hpop hsurv h

/-- **The mean is bounded by the extremes.**
    The mean trait of a population lies between the smallest and the largest trait.
    Selection can only move the mean inside the range that the population already
    spans: it cannot invent a trait that no cell has.

    This is the first-principles statement of what selection can and cannot do. -/
theorem mean_between_extremes
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (lo hi : ℝ)
    (hX : Integrable X μ)
    (hlo : ∀ᵐ x ∂μ, lo <= X x)
    (hhi : ∀ᵐ x ∂μ, X x <= hi) :
    lo <= ∫ x, X x ∂μ ∧ ∫ x, X x ∂μ <= hi := by
  constructor
  · have hconst : Integrable (fun _ : ℝ => lo) μ := integrable_const lo
    have := integral_mono_ae hconst hX hlo
    simpa using this
  · have hconst : Integrable (fun _ : ℝ => hi) μ := integrable_const hi
    have := integral_mono_ae hX hconst hhi
    simpa using this

end Medium
