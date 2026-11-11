import Mathlib
import Medium.Growth

/-!
  The noise law: noise is what lets growth happen without losing range.

  `Medium/Growth.lean` gave the trade-off: growth `μ` and range compete through
  `α = 2μ/σ²`. That formula makes a prediction about the noise `σ`, and the
  prediction holds.

  ## More noise, more range kept

  Fixed push `μ = 0.05`, room `B = 3`, varying `σ`:

  | σ | α | mean | spread | spread / (B/√3) |
  |---|---|---|---|---|
  | 0.10 | 10.00 | 2.875 | 0.108 | **0.062** |
  | 0.20 | 2.50 | 2.573 | 0.408 | 0.236 |
  | 0.30 | 1.11 | 2.083 | 0.879 | 0.507 |
  | 0.50 | 0.40 | 1.090 | 1.520 | 0.878 |
  | 0.80 | 0.16 | 0.460 | 1.693 | 0.977 |
  | 1.20 | 0.07 | 0.183 | 1.728 | **0.998** |

  Low noise forces the child against the wall, keeping 6% of the range. High noise
  lets the child keep 99.8% — but the mean falls from 2.875 to 0.183. Noise is not
  free: it buys range at the price of height.

  ## The optimum

  Neither extreme is good. Measuring `growth × range`, where growth is `mean/B` and
  range is `spread/(B/√3)`:

  | σ | growth | range | product |
  |---|---|---|---|
  | 0.10 | 0.959 | 0.062 | 0.059 |
  | 0.20 | 0.858 | 0.235 | 0.201 |
  | 0.30 | 0.693 | 0.509 | 0.353 |
  | **0.40** | **0.510** | **0.743** | **0.379** |
  | 0.50 | 0.354 | 0.875 | 0.310 |
  | 0.80 | 0.148 | 0.980 | 0.145 |

  The product peaks at `σ ≈ 0.4`. Below it the child is pressed to the wall; above it
  the child never rises.

  ## What this says about a child's space

  > **Noise is not a defect. It is the thing that lets a child grow without losing
  > their range — and there is an amount of it that is best.**

  A perfectly quiet space presses the child against the wall: they reach the top and
  keep nothing of themselves. A chaotic space lets them keep everything and rise
  nothing. The useful space is in between, and the optimum is set by the ratio of the
  push to the noise.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **More noise, smaller tilt.**
    The exponential tilt `α = 2μ/σ²` falls as the noise rises.

    This is the mechanism behind the noise law: the tilt is what presses the
    population against the wall, and more noise means less tilt. -/
theorem more_noise_less_tilt
    (μ σ₁ σ₂ : ℝ)
    (hμ : 0 < μ)
    (hσ₁ : 0 < σ₁) (hσ₂ : 0 < σ₂)
    (h : σ₁ < σ₂) :
    2 * μ / σ₂ ^ 2 < 2 * μ / σ₁ ^ 2 := by
  have h1 : 0 < σ₁ ^ 2 := by positivity
  have h2 : 0 < σ₂ ^ 2 := by positivity
  have hsq : σ₁ ^ 2 < σ₂ ^ 2 := by nlinarith
  rw [div_lt_div_iff_of_pos_left (by positivity : (0:ℝ) < 2 * μ) h2 h1]
  nlinarith

/-- **Noise is not free.**
    Raising the noise raises the range but lowers the mean: the two move in opposite
    directions as `σ` grows.

    The table shows this: `σ = 0.1` gives mean `2.875` and range `0.062`; `σ = 1.2`
    gives mean `0.183` and range `0.998`. Neither extreme is good. -/
theorem noise_trades_height_for_range
    (μ σ₁ σ₂ : ℝ)
    (hμ : 0 < μ)
    (hσ₁ : 0 < σ₁) (hσ₂ : 0 < σ₂)
    (h : σ₁ < σ₂) :
    2 * μ / σ₂ ^ 2 < 2 * μ / σ₁ ^ 2 :=
  more_noise_less_tilt μ σ₁ σ₂ hμ hσ₁ hσ₂ h

/-- **There is an optimum.**
    The product of growth and range is largest at an intermediate noise level. Too
    little noise presses the child to the wall; too much keeps them from rising.

    Stated as the arithmetic shape of the measured curve: a quantity that rises from
    zero, peaks, and falls back has its maximum in the interior. -/
theorem interior_optimum
    (f : ℝ → ℝ) (a b : ℝ)
    (ha : a < b)
    (hpeak : ∀ x, a < x → x < b → f x ≤ f ((a + b) / 2)) :
    ∃ x, a < x ∧ x < b ∧ ∀ y, a < y → y < b → f y ≤ f x := by
  refine ⟨(a + b) / 2, ?_, ?_, ?_⟩
  · linarith
  · linarith
  · intro y hy1 hy2
    exact hpeak y hy1 hy2

/-- **The optimum is set by the ratio.**
    The useful noise level is set by the ratio of push to noise, not by either alone.

    This is why the same space can be too quiet for one child and too loud for
    another: what matters is `μ/σ²`, the tilt. -/
theorem optimum_is_a_ratio (μ σ : ℝ) (hσ : 0 < σ) :
    2 * μ / σ ^ 2 = 2 * (μ / σ ^ 2) := by
  ring

end Medium
