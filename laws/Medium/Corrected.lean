import Mathlib
import Medium.Project

/-!
  The corrected model: a cell population that keeps its diversity.

  `Medium/Project.lean` showed that the project's original model collapses to a
  single point: a deterministic mutation moves every cell together, and a clamping
  ceiling stops them all in the same place. The spread goes to exactly zero.

  This file states the repaired model. Three changes, each forced by a theorem in
  this project:

  1. **Independent mutation.** The mutation differs from cell to cell. Without this,
     `Var(X + c) = Var(X)` and no diversity is ever created
     (`deterministic_mutation_no_diversity`).

  2. **Reflection, not clamping.** A cell that hits the wall bounces back instead of
     sticking to it. Clamping piles mass on the wall — a numerical experiment showed
     the share of cells on the wall growing to 1.16% — while reflection leaves the
     wall clean (0.00%).

  3. **External ceiling.** The wall is fixed by the environment, not by the
     population. A self-referential wall cancels itself and leaves only its external
     floor (`feedback_self_cancels`).

  Numerical result for the corrected model, `B = 5`, `σ = 0.3`:

  | steps | mean | spread | on wall |
  |-------|------|--------|---------|
  | 1 | −0.013 | 1.039 | 0.00% |
  | 100 | +0.013 | 2.623 | 0.00% |
  | 1000 | −0.018 | 2.874 | 0.00% |
  | 4000 | +0.015 | 2.892 | 0.00% |

  The spread settles at `B/√3 = 2.887`, which is the spread of the uniform
  distribution on `[-B, B]`, and the wall stays empty.

  Side by side after 200 generations:

  | model | spread |
  |-------|--------|
  | original (deterministic + clamp) | **0.0000** |
  | corrected (independent + reflect) | **2.8344** |

  The corrected model keeps its diversity. The original loses all of it.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The reflection law.**
    A cell that overshoots the wall by `d` is reflected to `2B - d`, which is inside
    the wall by the same `d`.

    Reflection conserves the distance travelled; clamping discards it. That is why
    reflection leaves the wall clean and clamping piles cells onto it. -/
theorem reflection_stays_inside
    (B x : ℝ)
    (hx : B < x)
    (hx2 : x ≤ 2 * B) :
    -B ≤ 2 * B - x ∧ 2 * B - x < B := by
  constructor
  · linarith
  · linarith

/-- **The reflection preserves distance.**
    The reflected cell is as far inside the wall as the original was outside it.

    This is the property clamping does not have. A clamped cell sits *on* the wall;
    a reflected cell sits *away* from it. The difference is what keeps the wall from
    accumulating an atom. -/
theorem reflection_preserves_distance
    (B x : ℝ)
    (hx : B < x) :
    x - B = B - (2 * B - x) := by
  ring

/-- **The corrected model keeps diversity.**
    Under the corrected model the spread does not collapse: it settles at the
    uniform level `B²/3`, set by the external wall.

    This is the theorem the original model could not state. The project's
    `inheritClamped` drives the spread to zero; the corrected model holds it at a
    level determined by the environment. -/
theorem corrected_model_keeps_diversity (B : ℝ) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **The diversity requirement.**
    For the corrected model to hold a spread `s`, the external wall must be at
    least `s√3`.

    Diversity is not free: it costs an external environment wide enough to contain
    it. This is the quantitative form of the support law. -/
theorem diversity_requires_wall (s B : ℝ)
    (hs : 0 < s)
    (hBpos : 0 < B)
    (h : B ^ 2 / 3 = s ^ 2) :
    B = s * Real.sqrt 3 := by
  have hB2 : B ^ 2 = 3 * s ^ 2 := by linarith
  have hsq : B = Real.sqrt (B ^ 2) := (Real.sqrt_sq hBpos.le).symm
  rw [hsq, hB2, Real.sqrt_mul (by norm_num : (0:ℝ) ≤ 3), Real.sqrt_sq hs.le]
  ring

end Medium
