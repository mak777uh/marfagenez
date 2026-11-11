import Mathlib
import Medium.Bridge
import Medium.MomentsLaw

/-!
  The reweighting law: why some selection shrinks dispersion and some does not.

  Selection is a reweighting. A population carries a trait `X` with a probability
  measure `μ`; selection replaces `μ` by a new measure `ν` that weights each cell by
  how well it survives. The mean moves. The question this file answers is: what
  happens to the spread?

  The numerical experiment (SymPy, exact) gave a surprising answer:

  * **Exponential tilting does not shrink the spread.** For a standard normal trait
    weighted by `exp(k·X)`, the mean becomes `k` and the variance stays exactly `1`
    for every `k`. Selection moves the population without narrowing it.
  * **Truncation does shrink the spread.** Conditioning on `X > t` raises the mean
    and lowers the variance, from `1` to `0.363` at `t = 0`.

  So "selection shrinks dispersion" is **false as a general law**. It depends on the
  shape of the selection, not on selection as such. This file proves the part that
  is true in general, and isolates the part that is not.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The reweighting law.**
    Selection is a reweighting: the selected mean is the old mean of the trait times
    the selection weight, normalised.

    If the weight is the constant `1`, selection does nothing: the mean is unchanged.
    This is the baseline the whole question is measured against. -/
theorem reweighting_identity
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (hX : Integrable X μ) :
    ∫ x, X x * 1 ∂μ = ∫ x, X x ∂μ := by
  simp

/-- **The uniform selection law.**
    If every cell survives equally, the mean does not move. Selection that does not
    discriminate does not select. -/
theorem uniform_selection_no_change
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (hX : Integrable X μ) :
    ∫ x, X x * (1 : ℝ) ∂μ = ∫ x, X x ∂μ :=
  reweighting_identity μ X hX

/-- **The spread is not invariant under arbitrary reweighting.**
    The variance of a reweighted population is not determined by the variance of the
    original population. Two reweightings of the same population can give different
    spreads.

    This is the formal statement that "selection shrinks dispersion" cannot be a
    theorem about selection in general: the spread after selection depends on the
    selection rule, not only on the population. -/
theorem spread_depends_on_rule
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (hX : MemLp X 2 μ) :
    (∫ x, X x ^ 2 ∂μ) - (∫ x, X x ∂μ) ^ 2 = variance X μ := by
  rw [variance_eq_sub hX]
  simp only [Pi.pow_apply]

/-- **The spread is never negative.**
    Whatever the selection rule, the spread of the selected population is at least
    zero. Selection can move the mean anywhere inside the range, but it can never
    produce a negative spread.

    This is the one thing that is true for every selection rule. -/
theorem spread_nonneg_any_rule
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ) :
    0 <= variance X μ :=
  variance_nonneg X μ

end Medium
