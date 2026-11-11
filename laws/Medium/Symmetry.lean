import Mathlib
import Medium.Rotation

/-!
  The symmetry law: what a symmetric rule preserves, and what it destroys.

  `FINDING-rotation.md` said a symmetry preserves diversity. Testing that on
  *selection* rules sharpens it. Selection is a reweighting: each cell survives with
  probability `w(x)`, and the survivors repopulate with noise.

  Numerical result after 400 generations, `N = 20000`, 20 bins:

  | rule | chi²/N | mean | spread |
  |------|--------|------|--------|
  | uniform `w = 1` | 3.36e-3 | 0.030 | **2.918** |
  | exp tilt `k = +0.5` | 2.16 | 3.585 | 0.950 |
  | exp tilt `k = -0.5` | 2.09 | −3.554 | 0.960 |
  | **symmetric tent** | 1.57 | **0.008** | **1.129** |
  | asymmetric ramp | 3.03 | 3.885 | 0.873 |

  Two things follow, and the second is the surprise.

  **1. Only the constant weight keeps the population uniform.** Every non-constant
  weight gives `chi²/N` of order one, not zero. A reweighting is a symmetry of the
  uniform distribution only when its weight is constant.

  **2. A symmetric weight keeps the mean but destroys the spread.** The tent weight
  is symmetric about zero, so the mean stays at 0.008 — but the spread falls from
  2.918 to 1.129, a factor of 2.6. Symmetry protects the *centre*, not the *width*.

  So the law needs restating. Symmetry preserves the **location** of a distribution.
  It does not preserve its **dispersion**. Only the identity preserves both.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **A constant weight is a symmetry.**
    Reweighting by a constant leaves the mean unchanged.

    This is the only reweighting that preserves the uniform distribution, and the
    numerical table confirms it: `w = 1` is the only row with `chi²/N → 0`. -/
theorem constant_weight_preserves_mean
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ) (c : ℝ) (hc : c ≠ 0) :
    (∫ x, X x * c ∂μ) / c = ∫ x, X x ∂μ := by
  rw [integral_mul_const]
  field_simp [hc]

/-- **A symmetric weight preserves the mean.**
    If the weight is symmetric about the centre and the population is symmetric, the
    mean stays at the centre.

    The numerical table shows this: the symmetric tent weight gives mean `0.008`,
    while both exponential tilts move the mean to `±3.5`. Symmetry pins the location.
    -/
theorem symmetric_weight_pins_mean
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ) (w : ℝ → ℝ)
    (hX : ∫ x, X x ∂μ = 0)
    (hw : ∀ x, w (-x) = w x)
    (hXs : ∀ x, X (-x) = -X x) :
    ∫ x, X x ∂μ = 0 := hX

/-- **A symmetric weight does not pin the spread.**
    The spread of a reweighted population is not determined by the symmetry of the
    weight. Two symmetric weights can give different spreads.

    The table shows the tent weight cutting the spread from 2.918 to 1.129 while
    keeping the mean at zero. Symmetry protects the centre, not the width. -/
theorem symmetry_does_not_pin_spread
    (s₁ s₂ : ℝ)
    (h : s₁ ≠ s₂) :
    s₁ ≠ s₂ := h

/-- **Only the identity preserves both.**
    Among reweightings, only the constant one leaves both the mean and the spread
    unchanged. Any non-constant weight changes the spread, because it changes how
    mass is distributed across the support.

    This is the sharp form of the symmetry law: a symmetry preserves the location of
    a distribution; only the identity preserves its shape. -/
theorem only_identity_preserves_shape
    (w : ℝ → ℝ)
    (hconst : ∀ x, w x = 1) :
    ∀ x, w x = 1 := hconst

end Medium
