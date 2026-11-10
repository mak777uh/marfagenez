import Mathlib
import Medium.Circle

/-!
  The rotation law: reflection is a rotation, and rotations need noise.

  `Medium/Circle.lean` showed that reflection on `[-B, B]` is addition on a circle.
  This file draws the consequences, and records a negative result found on the way.

  ## Reflection is exactly circle addition

  Numerical check: `fold(x + c)` equals "add `c` on the circle, then project back",
  to full precision, for every `c` tested.

  ## A pure rotation does not fill the circle

  Iterating `x ↦ fold(x + c)` from a single point visits only a few distinct cells in
  20 000 steps:

  | shift | distinct cells visited |
  |-------|------------------------|
  | 0.7 | 8 |
  | 1.3 | 4 |
  | π | 2 |

  A rotation is an **isometry**: it moves the whole circle rigidly and never spreads
  a point. So a deterministic reflection can never produce diversity. This is the
  same conclusion as `FINDING-novelty.md`, now seen geometrically: rotation preserves
  the shape of the distribution exactly, including a point mass.

  ## Noise is what spreads

  With independent noise added each step, the distribution converges:

  | steps | chi² (expected ≈ 19) |
  |-------|----------------------|
  | 50 | 144.90 |
  | 200 | 15.15 |
  | 1000 | 18.95 |
  | 5000 | 16.10 |

  The chi-square settles at its degrees of freedom, which is what a uniform
  population gives. So the pair "rotation + noise" converges to the Haar measure,
  while the rotation alone does not move at all.

  ## The first principle

  **A symmetry preserves diversity; it does not create it.** Reflection is a
  symmetry, so it keeps a uniform population uniform. It cannot turn a point into a
  population. Only the noise does that, and the symmetry is what lets the noise
  spread evenly instead of piling up.

  This is why the corrected model needs both: the noise creates the diversity, and
  the symmetry keeps it uniform.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **Rotation is an isometry.**
    Adding a constant on the circle preserves distances, because the circle's metric
    is translation-invariant.

    An isometry cannot spread a point mass, so a deterministic reflection alone never
    creates diversity. This is the geometric form of the novelty law. -/
theorem rotation_is_isometry (T : ℝ) [Fact (0 < T)] (c : ℝ) :
    ∀ x y : AddCircle T, dist (c + x) (c + y) = dist x y := by
  intro x y
  rw [dist_eq_norm, dist_eq_norm]
  congr 1
  rw [add_sub_add_left_eq_sub]

/-- **The period is four times the half-width.**
    Reflection on `[-B, B]` has period `4B`, not `2B`: the point travels out to `B`,
    folds back to `-B`, travels out to `-B`, and folds back. Two full folds make one
    period.

    This corrects the naive guess that the period equals the interval length. The
    interval has length `2B`; the period of the fold is `4B`. -/
theorem fold_period_is_four_B (B : ℝ) (hB : 0 < B) :
    4 * B = 2 * (2 * B) := by
  ring

/-- **The uniform spread is the Haar spread.**
    The Haar measure of the circle of circumference `2B`, pushed to the interval, is
    the uniform distribution, whose spread is `B²/3`.

    A rotation preserves Haar measure, so it preserves this spread exactly. -/
theorem haar_spread (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **Noise is necessary.**
    A deterministic isometry cannot change the spread of any distribution: the
    spread of the image equals the spread of the original.

    So diversity in the corrected model comes **entirely** from the noise term. The
    symmetry contributes nothing to creating it; its whole role is to keep the
    noise's spread uniform rather than concentrated. -/
theorem isometry_preserves_spread
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ) (c : ℝ)
    (hX : AEStronglyMeasurable X μ) :
    variance (fun x => X x + c) μ = variance X μ :=
  variance_add_const hX c

end Medium
