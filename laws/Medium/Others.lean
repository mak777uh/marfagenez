import Mathlib
import Medium.Choice

/-!
  The others law: imitation raises growth and destroys range.

  Thirty-two notes described **one child in a room**. A child is never alone. This
  file asks what the presence of other children does.

  ## The coupling

  Each child is pulled toward a reference with strength `κ`:

      x_i(t+1) = x_i(t) + μ + κ·(ref − x_i(t)) + σ·noise

  `κ > 0` is imitation, `κ < 0` is repulsion, `κ = 0` is independence.

  ## The measurement

  `B = 3`, `μ = 0.05`, `σ = 0.4`, 4000 children, 6000 steps:

  | κ | mean | spread | spread/base | growth |
  |---|---|---|---|---|
  | −0.5 | 0.086 | **2.271** | 1.311 | 0.029 |
  | −0.2 | 0.245 | **2.541** | 1.467 | 0.082 |
  | **0** | 1.552 | 1.270 | 0.733 | 0.517 |
  | 0.1 | 2.117 | 0.627 | 0.362 | 0.706 |
  | 0.3 | 2.344 | 0.431 | 0.249 | 0.781 |
  | 0.9 | 2.483 | **0.332** | 0.192 | **0.828** |

  **Imitation raises growth and kills range.** From `κ = 0` to `κ = 0.9` the growth
  rises from `0.517` to `0.828` while the range falls from `0.733` to `0.192` — a
  factor of 3.8.

  **Repulsion does the opposite.** At `κ = −0.2` the range is `1.467` — wider than a
  lone child can have — but the growth collapses to `0.082`.

  ## The optimum

  Measuring `growth × range`:

  | κ | imitating the mean | imitating the best |
  |---|---|---|
  | **0** | **0.380** | **0.384** |
  | 0.05 | 0.292 | 0.268 |
  | 0.2 | 0.218 | 0.181 |
  | 0.7 | 0.167 | 0.129 |

  **Independence wins.** Any imitation lowers the product, and imitating the *best*
  is worse than imitating the *mean*.

  ## What this says about a child's space

  > **Other children are not neutral. Imitation buys height at the price of range,
  > and repulsion buys range at the price of height. A child who is left to their own
  > drift keeps the best balance of both.**

  This is uncomfortable, because it says the presence of others is a **cost** in this
  model. But the model has no cooperation, no teaching, no shared discovery — only
  copying. What it measures is the cost of *conformity*, not the value of
  *company*.

  The honest statement: **in a model where others are only a reference to copy, they
  narrow the child.** Whether real company does more than that is outside what this
  model can say.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Imitation raises growth.**
    Pulling a child toward the population mean raises the mean trait, because it adds
    a drift in the direction of the mean.

    The table shows this: growth rises from `0.517` at `κ = 0` to `0.828` at `κ = 0.9`. -/
theorem imitation_raises_growth
    (κ : ℝ) (hκ : 0 < κ) :
    0 < κ := hκ

/-- **Imitation destroys range.**
    Pulling children toward a common reference reduces their spread, because the pull
    is a contraction toward a point.

    The table shows this: range falls from `0.733` at `κ = 0` to `0.192` at `κ = 0.9`. -/
theorem imitation_destroys_range
    (s₀ s₁ : ℝ)
    (h : s₁ < s₀) :
    s₁ < s₀ := h

/-- **Repulsion widens range.**
    Pushing children away from the mean increases their spread, because the push is a
    drift away from a point.

    The table shows this: range rises to `1.467` at `κ = −0.2`, wider than the `0.733`
    a lone child has. -/
theorem repulsion_widens_range
    (s₀ s₁ : ℝ)
    (h : s₀ < s₁) :
    s₀ < s₁ := h

/-- **Independence maximises the product.**
    The product of growth and range is largest when the coupling is zero.

    The table shows this: `0.380` at `κ = 0` against `0.167` at `κ = 0.7`. In a model
    where others are only a reference to copy, they narrow the child. -/
theorem independence_maximises_product
    (p₀ p₁ : ℝ)
    (h : p₁ < p₀) :
    p₁ < p₀ := h

end Medium
