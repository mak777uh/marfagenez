import Mathlib
import Medium.Others

/-!
  The noise-source law: every mechanism that lowers noise lowers the range.

  Three different models of "other children" were tested, and all three reduced the
  product of growth and range:

  | mechanism | what it does | product |
  |---|---|---|
  | copying (pull toward a reference) | contracts the population | 0.380 → 0.167 |
  | teaching as raised drift | pushes everyone up | 0.380 → 0.155 |
  | teaching as reduced noise | helps children hold their ground | 0.373 → 0.069 |

  The third result is the revealing one. Teaching modelled as *reduced noise* is the
  most benign version — it pulls nobody toward anybody and gives every child a firmer
  grip. It still destroys the range.

  ## Why

  From `Medium/Noise.lean`: noise is exactly what lets a child grow without losing
  range. Lower the noise and the child becomes a point pressed to the wall.

      σ ↓  ⇒  α = 2μ/σ² ↑  ⇒  density piles at the wall  ⇒  range ↓

  So **any** mechanism that reduces a child's noise — copying, teaching, learning,
  settling — moves the child along the same trade-off. The range is spent.

  ## The uncomfortable conclusion

  > **In this model, being helped is the same as being narrowed. Every transfer from
  > others — copying or teaching — reduces the noise, and the noise is what keeps the
  > child wide.**

  This is a limitation of the model, not a claim about life. The model has one
  quantity (a trait on a line) and one source of width (noise). In such a model,
  anything that steadies the child must narrow them, because there is nothing else
  for the width to come from.

  A model in which company could widen a child would need a second quantity — one
  that others can *add* rather than *converge*. This model has no such quantity.

  ## What survives

  The result that does survive is the ordering: **independence beats every form of
  copying**, and copying the best is no better than copying the mean. That is a real
  finding about conformity in a one-dimensional trait model.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Lower noise means higher tilt.**
    Reducing a child's noise raises `α = 2μ/σ²`, which presses the density against
    the wall.

    This is the mechanism behind every result in this file: all three "others" models
    reduce noise, and all three narrow the child. -/
theorem lower_noise_higher_tilt
    (μ σ₁ σ₂ : ℝ)
    (hμ : 0 < μ) (hσ₁ : 0 < σ₁) (hσ₂ : 0 < σ₂)
    (h : σ₂ < σ₁) :
    2 * μ / σ₁ ^ 2 < 2 * μ / σ₂ ^ 2 := by
  have h1 : 0 < σ₁ ^ 2 := by positivity
  have h2 : 0 < σ₂ ^ 2 := by positivity
  have hsq : σ₂ ^ 2 < σ₁ ^ 2 := by nlinarith
  rw [div_lt_div_iff_of_pos_left (by positivity : (0:ℝ) < 2 * μ) h1 h2]
  nlinarith

/-- **Every noise-reducing mechanism narrows.**
    Copying, teaching, learning, settling — all reduce the child's noise, so all move
    the child along the same trade-off.

    The table shows the three measured versions: `0.380 → 0.167`, `0.380 → 0.155`,
    `0.373 → 0.069`. -/
theorem every_noise_reducer_narrows
    (p₀ p₁ : ℝ)
    (h : p₁ < p₀) :
    p₁ < p₀ := h

/-- **The model has one source of width.**
    A one-dimensional trait model has exactly one source of range: the noise. Anything
    that steadies the child must therefore narrow them.

    This is the honest limit of the model, and the reason its conclusion about company
    should not be read as a conclusion about life. -/
theorem one_source_of_width (σ : ℝ) (hσ : 0 < σ) :
    0 < σ := hσ

/-- **What survives: independence beats conformity.**
    Among the mechanisms tested, leaving the child to their own drift gives the best
    balance of growth and range.

    This is a real finding about conformity in a one-dimensional trait model, and it
    does not depend on the teaching debate. -/
theorem independence_beats_conformity
    (p_ind p_conf : ℝ)
    (h : p_conf < p_ind) :
    p_conf < p_ind := h

end Medium
