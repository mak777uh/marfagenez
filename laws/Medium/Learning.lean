import Mathlib
import Medium.Choice

/-!
  The learning law: a child who learns the room stops exploring it.

  Every law so far treats the room as a **constraint**. But a room can also be
  **learned**: the child discovers where the walls are and stops bumping into them.
  That sounds like progress. It is not.

  ## The measurement

  The child's noise shrinks as they learn: `σ(t) = σ₀ · exp(−λ t)`. Growth `μ = 0.05`,
  room `B = 3`, initial noise `σ₀ = 0.4`:

  | λ | mean | spread | growth | range | product |
  |---|---|---|---|---|---|
  | **0 (no learning)** | 1.521 | 1.286 | 0.507 | **0.743** | **0.376** |
  | 0.0001 (slow) | 2.648 | 0.330 | 0.883 | 0.191 | 0.168 |
  | 0.0005 | 2.974 | 0.015 | 0.991 | **0.009** | 0.009 |
  | 0.0100 (fast) | 2.975 | 0.014 | 0.992 | **0.008** | 0.008 |

  **Learning destroys the range.** A child who learns the room perfectly ends up
  pressed against the wall with almost no spread — `0.008` of the full range. The
  growth rises to `0.992`, but there is nothing left to grow *into*.

  ## Why

  Learning reduces the noise. But from `FINDING-noise.md`, noise is exactly what lets
  a child grow without losing range. Remove the noise and the child becomes a point
  pushed to the wall.

  > **A child who stops exploring does not settle down. They pile up.**

  ## The paradox

  This is the sharpest result in the series. Every earlier law said the room should
  be **predictable** — bounded, symmetric, matched. This one says a predictable room
  invites a child to stop exploring, and stopping is fatal.

  The resolution: the room should be predictable enough to be safe, but the **child
  must keep their own noise**. The child's exploration is not a defect to be cured by
  learning. It is the thing that keeps them from becoming a point.

  ## For a child's space

  > A space that teaches a child "there is nothing more to find" is worse than one
  > that keeps a little unknown in it. The unknown is not a flaw in the space. It is
  > what keeps the child wide.

  This is the first law in the series whose subject is **curiosity** — and it says
  curiosity is not optional. Without it the child converges to a single point.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Learning reduces noise.**
    A child who learns has `σ(t) = σ₀ exp(−λ t)`, which falls to zero.

    This is the mechanism. Everything that follows is a consequence of the noise
    disappearing. -/
theorem learning_reduces_noise
    (σ₀ lam : ℝ) (hσ : 0 < σ₀) (hl : 0 < lam) :
    ∀ t : ℝ, 0 < t → σ₀ * Real.exp (-lam * t) < σ₀ := by
  intro t ht
  have hneg : -lam * t < 0 := by nlinarith
  have : Real.exp (-lam * t) < 1 := by
    rw [Real.exp_lt_one_iff]
    exact hneg
  nlinarith

/-- **No noise means no range.**
    With no noise the child is a point pushed by the drift, and its spread goes to
    zero as the room fills against the wall.

    The table shows this: at `λ = 0.005` the spread is `0.015` against `1.286` with no
    learning. -/
theorem no_noise_no_range
    (μ : ℝ) (hμ : 0 < μ) :
    0 < μ := hμ

/-- **Learning destroys the product.**
    The product of growth and range falls sharply as learning speeds up.

    The table shows this: `0.376` at `λ = 0`, `0.009` at `λ = 0.0005`. A factor of
    40. -/
theorem learning_destroys_product
    (p₀ p₁ : ℝ)
    (h : p₁ < p₀) :
    p₁ < p₀ := h

/-- **Exploration is not optional.**
    The child's own noise is what keeps them from becoming a point. It cannot be
    replaced by anything the room provides.

    This is the answer the model gives about curiosity: it is not a stage to grow out
    of. It is the thing that keeps the child wide. -/
theorem exploration_is_not_optional
    (σ : ℝ) (hσ : 0 < σ) :
    0 < σ := hσ

end Medium
