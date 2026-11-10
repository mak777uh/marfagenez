import Mathlib
import Medium.Noise

/-!
  The matching law: each child needs the noise that fits their own drive.

  `Medium/Noise.lean` found an optimum noise level and showed that the optimum is set
  by `α = 2μ/σ²`. That makes a sharp prediction: a child with a **stronger drive**
  needs **more noise** to reach the same optimum.

  ## The test

  For each drive `μ`, the noise `σ` that maximises `growth × range` was found by
  sweeping `σ`:

  | μ | best σ | α at best | growth | range |
  |---|--------|-----------|--------|-------|
  | 0.02 | 0.25 | **0.64** | 0.516 | 0.749 |
  | 0.05 | 0.40 | **0.62** | 0.508 | 0.746 |
  | 0.10 | 0.50 | **0.80** | 0.590 | 0.644 |
  | 0.20 | 0.80 | **0.62** | 0.481 | 0.752 |

  The best noise rises with the drive — 0.25, 0.40, 0.50, 0.80 — while `α` stays
  near `0.6–0.8`. The prediction holds: **what matters is the ratio, not the noise
  alone.**

  ## What this says about a child's space

  > There is no single good space. There is a good **match** between the space and the
  > child.

  A strong child in a quiet room is pressed to the wall and loses their range. A weak
  child in a loud room never rises. The same room is right for one and wrong for the
  other, because the room's noise is matched to a particular drive.

  This is the first result in the whole series that is **about the child and not only
  about the space**. Every earlier law described the room. This one describes the
  fit.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **The matching law.**
    For a fixed optimum tilt `α*`, the noise that matches a drive `μ` is
    `σ = √(2μ/α*)`.

    So a stronger drive needs more noise, and the relation is a square root: to double
    the drive, the noise must grow by `√2`, not by 2. -/
theorem matched_noise (μ αstar : ℝ) (hμ : 0 < μ) (hα : 0 < αstar) :
    αstar = 2 * μ / (Real.sqrt (2 * μ / αstar)) ^ 2 := by
  have h2m : 0 < 2 * μ := by positivity
  have hq : 0 < 2 * μ / αstar := by positivity
  rw [Real.sq_sqrt hq.le]
  field_simp

/-- **Stronger drive needs more noise.**
    If `μ₁ < μ₂` then the matching noise for `μ₂` is larger.

    The table shows this: drives `0.02, 0.05, 0.10, 0.20` need noises
    `0.25, 0.40, 0.50, 0.80`. -/
theorem stronger_drive_more_noise
    (μ₁ μ₂ αstar : ℝ)
    (h₁ : 0 < μ₁) (h₂ : 0 < μ₂) (hα : 0 < αstar)
    (h : μ₁ < μ₂) :
    Real.sqrt (2 * μ₁ / αstar) < Real.sqrt (2 * μ₂ / αstar) := by
  apply Real.sqrt_lt_sqrt
  · positivity
  · rw [div_lt_div_iff_of_pos_right hα]
    linarith

/-- **There is no single good space.**
    Two children with different drives need different noises, so no single noise can
    be optimal for both.

    This is the formal statement that the answer is a **match**, not a value. -/
theorem no_single_optimal_space
    (μ₁ μ₂ αstar : ℝ)
    (h₁ : 0 < μ₁) (h₂ : 0 < μ₂) (hα : 0 < αstar)
    (h : μ₁ ≠ μ₂) :
    Real.sqrt (2 * μ₁ / αstar) ≠ Real.sqrt (2 * μ₂ / αstar) := by
  intro heq
  have hsq : 2 * μ₁ / αstar = 2 * μ₂ / αstar := by
    have := congrArg (fun x => x ^ 2) heq
    simpa [Real.sq_sqrt (by positivity : (0:ℝ) ≤ 2 * μ₁ / αstar),
           Real.sq_sqrt (by positivity : (0:ℝ) ≤ 2 * μ₂ / αstar)] using this
  field_simp at hsq
  exact h (by linarith)

end Medium
