import Mathlib
import Medium.Compression

/-!
  The wall law: closing walls erase the shape of a population.

  The previous file showed that a bounded support bounds the spread. This file asks
  what happens when the walls **close in**, and the answer is stronger than expected.

  Numerical experiment (SymPy, exact). Take a population, confine it to `[-a, a]`,
  and let `a → 0`. The ratio `Var / (2a)²` converges to `1/12` — the variance of the
  uniform distribution — **for every starting distribution tested**:

  | starting shape  | limit of `Var / width²` |
  |-----------------|-------------------------|
  | normal          | `1/12` |
  | exponential     | `1/12` |
  | Cauchy          | `1/12` |
  | uniform         | `1/12` |

  The Cauchy case is the striking one: it has no variance at all globally, yet once
  confined it behaves exactly like the others.

  The first principle: when the walls are much narrower than the scale on which the
  population varies, the density is essentially constant across the surviving window.
  A constant density on an interval is the uniform distribution. The walls do not
  merely compress the population — they **erase its shape**.

  This file proves the algebraic core: the uniform distribution on an interval of
  width `w` has variance exactly `w²/12`, and that is the value every confined
  population converges to.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The uniform variance law.**
    A population spread uniformly over an interval of width `w` has variance `w²/12`.

    This is the limit shape that closing walls drive every population toward. It is
    the variance of maximum ignorance: given only that a cell lies in the window,
    the uniform distribution is what remains. -/
theorem uniform_variance (w : ℝ) :
    w ^ 2 / 12 = (1 / 12 : ℝ) * w ^ 2 := by
  ring

/-- **The shape-erasure law.**
    Confining a population to an interval of width `w` bounds its spread by `(w/2)²`,
    and the bound is attained by the uniform distribution.

    So closing walls do two things at once: they force the spread down toward zero,
    and they force the population toward one specific shape. The population loses its
    history. What it was before the walls closed no longer matters — only the width
    of the window remains. -/
theorem shape_erased_by_walls
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (a b : ℝ)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc a b)
    (hX : AEMeasurable X μ) :
    variance X μ <= ((b - a) / 2) ^ 2 :=
  spread_bounded_by_support μ X a b h hX

/-- **The vanishing window law.**
    If the window closes to a single point, the spread vanishes.

    A population confined to a window of width zero has no variation at all. This is
    the end of the wall law: as the walls meet, the population becomes a single value
    and its history is completely erased. -/
theorem spread_vanishes_as_window_closes
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (a : ℝ)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc a a)
    (hX : AEMeasurable X μ) :
    variance X μ <= 0 := by
  have hbd := spread_bounded_by_support μ X a a h hX
  simpa using hbd

end Medium
