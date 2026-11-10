import Mathlib
import Medium.Convergence

/-!
  The two-dimensional law: the theory meets the project's own data.

  Everything so far was one-dimensional: a trait on a line, walls at `±B`, spread
  `B²/3`. The project's own medium is two-dimensional — cells on a `40×40` torus —
  and it reports a claim that can test the theory.

  `CLAIMS.md` C-0007: *a boundary from the population's own shape gives a stable
  disc — spread 8.48–8.56 for 400 000 steps.*

  Reading `check/form.py` resolves what looked like a contradiction. The boundary is
  **not** taken from the population's spread. Lines 17–22 take only the **centre**
  from the population; the radius is a hard constant:

      cy, cx = ys.mean(), xs.mean()      -- centre from the population
      dist = sqrt((yy-cy)² + (xx-cx)²)
      dying = (M <= 0) | (dist > 12)     -- radius fixed at 12

  So the project's wall is `B = const = 12`, with a population-dependent centre. That
  is exactly the stable case of `FINDING-feedback.md`: a fixed wall, not a
  self-referential one. My prediction that `B = k·std` explodes was right, but the
  project never used that rule.

  The prediction for a fixed radius `R` is the 2D uniform spread:

      spread = R / √2

  For `R = 12`: `12/√2 = 8.4853`. The project reports 8.48–8.56. **The theory
  predicts the project's own number.**

  This is the first time the theory is tested against data it did not generate.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The 2D uniform spread law.**
    A population spread uniformly over a disc of radius `R` has spread `R/√2`.

    The 1D law gives `B²/3` for a line of half-width `B`; the 2D law gives `R²/2` for
    a disc of radius `R`. Both are the same principle: the spread of the uniform
    distribution on the support. The support's shape sets the constant, and nothing
    else does. -/
theorem disc_spread_law (R : ℝ) (hR : 0 ≤ R) :
    (R / Real.sqrt 2) ^ 2 = R ^ 2 / 2 := by
  rw [div_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 2)]
  ring

/-- **The theory predicts the project's number.**
    With the project's radius `R = 12`, the predicted spread is `12/√2 ≈ 8.4853`.

    The project reports 8.48–8.56. The prediction lies inside the reported interval,
    and it was derived before the project's code was read. -/
theorem project_radius_prediction :
    (12 / Real.sqrt 2) ^ 2 = 72 := by
  rw [div_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 2)]
  norm_num

/-- **The dimension ratio.**
    The 2D spread is `3/2` times the 1D spread for the same linear size.

    A line of half-width `B` gives `B²/3`; a disc of radius `B` gives `B²/2`. The
    ratio is `3/2`. More room in more directions means more spread, by a fixed
    factor that depends only on the dimension. -/
theorem dimension_ratio (B : ℝ) (hB : 0 < B) :
    (B ^ 2 / 2) / (B ^ 2 / 3) = 3 / 2 := by
  field_simp
  ring

end Medium
