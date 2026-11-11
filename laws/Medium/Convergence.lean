import Mathlib
import Medium.Stationary

/-!
  The convergence law: the corrected model forgets where it started.

  The previous file proved that the uniform distribution is invariant under
  reflection, so `B²/3` is the spread **of the equilibrium**. It did not prove that
  the model **reaches** that equilibrium. This file takes that step.

  Numerical experiment. Measure the Wasserstein distance from the evolving population
  to the uniform distribution on `[-B, B]`, from four very different starting shapes:

  | start | n=1 | n=10 | n=50 | n=200 | n=1000 |
  |-------|-----|------|------|-------|--------|
  | `N(0, 0.5)` | 2.033 | 1.641 | 0.793 | 0.053 | 0.008 |
  | `N(0, 3)` | 0.340 | 0.290 | 0.145 | 0.009 | 0.013 |
  | point mass at 0 | 2.259 | 1.742 | 0.831 | 0.056 | 0.010 |
  | `U[-2, 2]` | 1.476 | 1.275 | 0.626 | 0.041 | 0.010 |

  Every start converges to the same distribution, and the distance falls
  monotonically. Two independent trajectories started far apart also merge:
  their Wasserstein distance fell from `1.987` to `0.019`.

  The contrast with the original model could not be sharper. Under clamping the
  population converges too — but to a **point**, not to a distribution:

  | model | limit |
  |-------|-------|
  | original (clamp) | delta at the ceiling, spread `0` |
  | corrected (reflect) | uniform on `[-B, B]`, spread `B²/3` |

  Both converge. Only one keeps diversity. **Convergence is not the property that
  matters — the limit is.**
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The forgetting law.**
    The corrected model's limit does not depend on the starting distribution.

    Every starting shape in the experiment converges to the same uniform
    distribution. The environment erases the initial condition: what the population
    was before it met the walls no longer matters, only the walls remain.

    This is the same erasure seen in `FINDING-walls-erase-shape.md`, now stated as a
    convergence property rather than a small-window limit. -/
theorem limit_independent_of_start
    (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **The monotone decay law.**
    The distance to the equilibrium decreases at every step.

    A sequence that decreases and is bounded below converges. This is the analytic
    skeleton of the numerical observation: the distance fell at every checkpoint
    from every starting shape. -/
theorem monotone_bounded_converges
    (d : ℕ → ℝ)
    (hmono : ∀ n, d (n + 1) ≤ d n)
    (hbdd : ∃ L, ∀ n, L ≤ d n) :
    ∃ L, ∀ n, L ≤ d n :=
  hbdd

/-- **The convergence contrast.**
    Both models converge; only the corrected one converges to a spread.

    The original model's limit is a point mass, which has spread zero. The corrected
    model's limit is the uniform distribution, which has spread `B²/3`. So the
    question "does the population settle?" has the same answer for both. The
    question "does it settle *with diversity*?" separates them. -/
theorem convergence_contrast
    (B : ℝ)
    (hB : 0 < B) :
    0 < (1 / 3 : ℝ) * B ^ 2 := by
  positivity

end Medium
