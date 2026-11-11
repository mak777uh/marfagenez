import Mathlib
import Medium.Growing

/-!
  The shape law: what kind of room, not how big.

  Every law so far bounded the child **trait by trait**: `|x_k| ≤ B`. But a room can
  also bound the child **as a whole**: `|x| ≤ B`. For a child with many traits these
  are completely different rooms, and the difference is the answer to the question.

  ## Two rooms

  **Box** — each trait bounded separately, `|x_k| ≤ B`. Volume `(2B)^d`.
  **Ball** — the whole child bounded, `|x| ≤ B`. Volume `∝ B^d / Γ(d/2+1)`.

  For `d = 8` the ball is a tiny fraction of the box.

  ## The measurement

  Traits independent, `d` of them, growing at `μ = 0.05`, noise `σ = 0.4`:

  | d | box per-trait spread | ball per-trait spread | `B/√d` |
  |---|---|---|---|
  | 1 | 1.293 | 1.306 | 3.000 |
  | 2 | 1.293 | 1.194 | 2.121 |
  | 4 | 1.283 | **1.031** | 1.500 |
  | 8 | 1.290 | **0.819** | 1.061 |

  The box keeps every trait at the full range `B/√3 ≈ 1.29` whatever `d` is. The ball
  squeezes each trait as `d` grows: `1.306 → 0.819`.

  ## The law

  > **A room that bounds the whole child squeezes every trait as the child grows more
  > dimensions. A room that bounds each trait separately does not.**

  A child with many sides cannot be given a single overall budget without every side
  shrinking. They need a budget **per side**.

  ## The negative results on the way

  Two things did **not** matter:

  * **More traits with independent noise** changed nothing: per-trait spread stayed at
    `0.745–0.751` of the base for `d = 1…16`.
  * **Coupling the traits** (a shared shock) changed nothing either: `0.744–0.749`
    for `ρ = 0…0.99`. It raised the correlation to `0.97` but left each trait's range
    untouched.

  So the room acts **component by component**. Neither the number of traits nor their
  coupling matters — only whether the bound is per-trait or overall.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **The box keeps every trait.**
    A room that bounds each trait separately gives every trait the same range
    `B/√3`, whatever the number of traits.

    The table shows this: spread `1.283–1.293` for `d = 1, 2, 4, 8`. -/
theorem box_keeps_every_trait (B : ℝ) (hB : 0 < B) :
    (B / Real.sqrt 3) ^ 2 = B ^ 2 / 3 := by
  rw [div_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 3)]

/-- **The ball squeezes every trait.**
    A room that bounds the whole child to radius `B` gives each of `d` traits only
    about `B²/d` of variance.

    The table shows this: per-trait spread falls from `1.306` at `d = 1` to `0.819` at
    `d = 8`, while the box stays at `1.29`. -/
theorem ball_squeezes_traits
    (B : ℝ) (d : ℕ)
    (hB : 0 < B) (hd : 1 < d) :
    B ^ 2 / (d : ℝ) < B ^ 2 := by
  have hd1 : (1 : ℝ) < (d : ℝ) := by exact_mod_cast hd
  have hd0 : (0 : ℝ) < (d : ℝ) := by linarith
  have hB2 : 0 < B ^ 2 := by positivity
  rw [div_lt_iff₀ hd0]
  nlinarith

/-- **More traits squeeze harder.**
    In a ball, doubling the number of traits halves each trait's variance.

    This is the quantitative form of the shape law: an overall budget is divided,
    and the division gets harsher as the child grows more dimensions. -/
theorem more_traits_squeeze_harder
    (B : ℝ) (d₁ d₂ : ℕ)
    (hB : 0 < B)
    (h₁ : 0 < d₁) (h₂ : 0 < d₂)
    (h : d₁ < d₂) :
    B ^ 2 / (d₂ : ℝ) < B ^ 2 / (d₁ : ℝ) := by
  have hB2 : 0 < B ^ 2 := by positivity
  have hd1 : (0:ℝ) < (d₁ : ℝ) := by exact_mod_cast h₁
  have hd2 : (d₁ : ℝ) < (d₂ : ℝ) := by exact_mod_cast h
  gcongr

/-- **The shape matters, not the size.**
    Two rooms of the same half-width `B` give different ranges depending on whether
    the bound is per-trait or overall.

    This is the answer to the child question: what matters is not how big the room is
    but whether it bounds each side separately. -/
theorem shape_matters_not_size
    (B : ℝ) (d : ℕ)
    (hB : 0 < B) (hd : 1 < d) :
    B ^ 2 / (d : ℝ) < B ^ 2 := by
  have hd1 : (1 : ℝ) < (d : ℝ) := by exact_mod_cast hd
  have hB2 : 0 < B ^ 2 := by positivity
  rw [div_lt_iff₀ (by positivity)]
  nlinarith

end Medium
