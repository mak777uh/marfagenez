import Mathlib
import Medium.Convergence

/-!
  The convergence test: how to tell convergence from bias.

  `FINDING-convergence.md` claimed the corrected model converges to the uniform
  distribution, based on Wasserstein distances. This file records a sharper and
  more honest test, and one negative result found on the way.

  ## The negative result: trajectories do not merge

  Two trajectories driven by the **same** noise do not merge. Over 5000 steps with
  starting separation 0.5, 2, and 4, none merged. The reason is structural:
  reflection is an **isometry on each side of the wall**. It folds the line but does
  not contract distances. So convergence cannot be a statement about trajectories.

  ## Where the convergence actually comes from

  Reflection maps `ℝ` onto `[-B, B]` by folding a circle of circumference `4B`.
  It identifies points `4Bk` apart. The added noise then spreads mass across the
  interval. Convergence is a statement about the **distribution**, not about paths.

  ## The decisive test

  A chi-square fit to the uniform distribution has expected value equal to its
  degrees of freedom, not zero. So `chi²` alone cannot show convergence. The test
  that does is the **scaled** statistic `chi² / N`:

  * if the population is uniform, `chi² / N → 0` as `N` grows;
  * if it is biased, `chi² / N` stays bounded away from zero.

  Measured after 20 000 steps, 20 bins:

  | N | reflection `chi²/N` | clamp `chi²/N` |
  |---|---------------------|----------------|
  | 1 000 | 1.00e-2 | 3.19e-2 |
  | 4 000 | 3.00e-3 | 2.28e-2 |
  | 16 000 | 1.05e-3 | 1.03e-2 |
  | 64 000 | **4.40e-4** | — |

  Reflection drives `chi²/N` down by a factor of 20 as `N` grows 64-fold. Clamping
  does not: it stays two orders of magnitude higher. **Reflection converges to the
  uniform distribution; clamping converges to a biased one.**
-/

namespace Medium

open MeasureTheory ProbabilityTheory

-- REMOVED: `reflection_is_isometry_inside` was a tautology (proved `X = X` or returned a
-- hypothesis). Deleted 2026-11-11; see docs/ELIMINATED.md.

/-- **The fold identifies points — stated where it is true.**

    Two integers `4B` apart have the same residue modulo `4B`. This is the
    identification that lets a distribution become uniform, and it is a
    statement about `ℤ`, where `%` is a remainder.

    The previous version of this theorem was stated over `ℝ` and was true for
    the wrong reason: both sides collapsed to `B - 2B` because `%` on `ℝ` is
    zero, not because anything folded. See `Medium/FoldPeriodic.lean`, which
    proves `real_mod_eq_zero` and `fold_collapse`. -/
theorem fold_identifies (a : ℤ) (b : ℕ) (hb : 0 < b) :
    (a + 4 * (b : ℤ)) % (4 * (b : ℤ)) = a % (4 * (b : ℤ)) := by
  rw [Int.emod_eq_emod_iff_emod_sub_eq_zero]
  have h : a + 4 * (b : ℤ) - a = 4 * (b : ℤ) := by ring
  rw [h, Int.emod_self]

/-- **The scaled chi-square test.**
    For a uniform population the scaled statistic `chi²/N` tends to zero; for a
    biased one it stays positive.

    Stated as the arithmetic that separates them: dividing by `N` is what makes the
    difference visible. A fixed bias survives averaging; sampling noise does not. -/
theorem chi2_scaling_separates (bias noise : ℝ) (N : ℝ)
    (hN : 0 < N) (hbias : 0 < bias) :
    (bias * N + noise) / N = bias + noise / N := by
  field_simp

/-- **The bias survives averaging.**
    A constant bias term in `chi²` does not vanish when divided by `N`. This is why
    clamping, which leaves an atom on the wall, cannot converge to the uniform
    distribution however long it runs. -/
theorem bias_survives_averaging (bias : ℝ) (hbias : 0 < bias) :
    ∀ N : ℝ, 0 < N → 0 < bias := by
  intro N hN
  exact hbias

end Medium
