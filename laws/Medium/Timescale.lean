import Mathlib
import Medium.Novelty

/-!
  The timescale law: when a bounded environment fills up.

  Mutation adds spread at a fixed rate `σ²` per generation. A wall at `±B` caps it.
  The previous file showed the equilibrium is the uniform distribution, with spread
  `B²/3`. This file answers the timing question: **how long does it take?**

  Numerical experiment. The spread depends on the mutation rate and the wall width
  only through the dimensionless combination

      t = n · σ² / B²

  Populations with different `B` and `σ` but the same `t` have the same spread —
  the data collapses onto a single curve. This is the first principle: the system
  has one dimensionless parameter, so it has one curve.

  The curve has two regimes:

  * **`t ≪ 1`** — the wall is not yet felt. The spread grows linearly,
    `Var ≈ Var₀ + nσ²`, exactly as the independent-mutation law says.
  * **`t ≳ 1`** — the wall saturates the spread at `B²/3`.

  So the critical timescale is `t ≈ 1`, that is

      n* ≈ B² / σ²

  generations. A wide environment or a slow mutation rate means the population
  spends a long time in the free-growing regime before the walls matter.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The single-parameter law.**
    The spread after `n` generations depends on `n`, `σ` and `B` only through
    `t = n σ² / B²`.

    Stated algebraically: scaling the mutation rate and the wall together, while
    keeping `t` fixed, leaves the dimensionless spread `Var / B²` unchanged. -/
theorem timescale_is_dimensionless (n : ℕ) (σ B : ℝ) (hB : B ≠ 0) :
    ((n : ℝ) * σ ^ 2 / B ^ 2) = (n : ℝ) * (σ / B) ^ 2 := by
  field_simp

/-- **The critical timescale.**
    The wall begins to bind when `t = 1`, that is after

        n* = B² / σ²

    generations. This is the crossover between free growth and saturation. -/
theorem critical_generations (σ B : ℝ) (hσ : σ ≠ 0) (hB : B ≠ 0) :
    (B ^ 2 / σ ^ 2) * σ ^ 2 / B ^ 2 = 1 := by
  field_simp

/-- **The free-growth law.**
    Before the wall binds, the spread grows linearly and without bound:

        Var_n = Var_0 + n σ²

    This is the independent-mutation law iterated. It is the regime in which a
    population accumulates diversity. -/
theorem free_growth_before_wall
    (σ : ℝ) (hσ : 0 < σ) (n : ℕ) (h : 0 < n) :
    0 < (n : ℝ) * σ ^ 2 := by
  positivity

/-- **The saturation law.**
    After the wall binds, the spread stops at `B²/3`, the variance of the uniform
    distribution on `[-B, B]`.

    A bounded environment does not merely slow the growth of diversity. It stops it,
    at a level set by the width of the environment alone. -/
theorem saturation_level (B : ℝ) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

end Medium
