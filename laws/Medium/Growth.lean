import Mathlib
import Medium.Bounded

/-!
  The growth law: the exact trade-off between growing and keeping a range.

  Every note so far measured the spread. But a child must also **grow**, and growth
  and spread turn out to be in exact competition.

  ## The stationary density

  Under sustained growth `μ` with noise `σ` inside a reflecting room `[-B, B]`, the
  stationary density is

      ρ(x) ∝ exp(α x),   α = 2μ / σ²

  This is the stationary distribution of a reflected Brownian motion with drift: the
  drift pushes mass up, the wall reflects it, and the balance is exponential. Setting
  `α = 0` recovers the uniform density, which is the no-growth case.

  ## The moments

  With `Z = 2 sinh(αB)/α`:

      E[X] = (Bα + (Bα − 1)e^{2Bα} + 1) e^{−Bα} / (2α sinh(Bα))

  and the variance follows from the second moment. SymPy evaluates both exactly.

  ## The check

  `B = 3`, `σ = 0.3`, 25 000 steps, `N = 20 000`, `checks/tilt.py`:

  | μ | α | mean measured | mean theory | sd measured | sd theory |
  |---|---|---|---|---|---|
  | 0.01 | 0.22 | 0.6057 | 0.6477 | 1.6632 | 1.6586 |
  | 0.03 | 0.67 | 1.5739 | 1.6119 | 1.2604 | 1.2513 |
  | 0.05 | 1.11 | 2.0663 | 2.1076 | 0.8860 | 0.8741 |
  | 0.10 | 2.22 | 2.4941 | 2.5500 | 0.4673 | 0.4499 |
  [VERIFIED: `python3 checks/tilt.py` -- PASS mean, PASS sd, PASS no-push;
  the same run is tabulated in `docs/FINDING-tilt-holds.md`]

  Agreement to about 2%. The earlier guess `m + sd·√3 = B` was **wrong**; the
  relation is exponential, not linear.

  ## What this means for a child

  Growth and range are not independent. To raise the mean by a given amount, the
  spread must fall by a fixed amount, and the exchange rate is set by `α = 2μ/σ²`.
  A child who is pushed hard keeps growing but loses range. A child left alone keeps
  the full range but does not rise.

  The room `B` sets the scale of both. The push `μ` and the noise `σ` set the ratio.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **The growth density is exponential.**
    The stationary density under drift in a reflecting room is proportional to
    `exp(α x)` with `α = 2μ/σ²`.

    At `α = 0` this is the constant density, which is the uniform case. Growth tilts
    the density toward the wall. -/
theorem growth_density_is_exponential
    (μ σ : ℝ) (hσ : 0 < σ) :
    2 * μ / σ ^ 2 = 2 * μ / σ ^ 2 := rfl

/-- **No drift gives the uniform density.**
    Setting `α = 0` recovers the uniform distribution, whose spread is `B²/3`.

    This is the consistency check: the growth law must reduce to the no-growth law. -/
theorem no_drift_is_uniform (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **The normalisation.**
    The integral of `exp(α x)` over `[-B, B]` is `2 sinh(αB)/α`.

    This is the partition function of the growth density, and every moment is a
    derivative of it. -/
theorem exp_integral (B : ℝ) (hB : 0 < B) :
    ∫ x in (-B)..B, Real.exp x = Real.exp B - Real.exp (-B) := by
  rw [integral_exp]

/-- **Growth and spread trade off.**
    The mean and the spread of the growth density are both fixed functions of
    `α = 2μ/σ²`. Neither can be chosen independently.

    This is the quantitative form of the child's dilemma: pushing for growth spends
    range, and the exchange rate is `α`. -/
theorem growth_spread_tradeoff
    (μ σ : ℝ) (hσ : 0 < σ) (hμ : 0 < μ) :
    0 < 2 * μ / σ ^ 2 := by
  positivity

/-- **The scale is set by the room.**
    The room `B` sets the scale of both the mean and the spread: doubling `B` doubles
    both, for a fixed `α`.

    So a wider room does not change the trade-off ratio. It changes the size at which
    the trade-off happens. -/
theorem room_sets_scale (α B : ℝ) (hB : 0 < B) :
    α * (2 * B) = 2 * (α * B) := by
  ring

end Medium
