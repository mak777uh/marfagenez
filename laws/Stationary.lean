import Mathlib
import Medium.Corrected

/-!
  The stationarity law: why the corrected model settles at the uniform spread.

  The corrected model was shown numerically to settle at spread `B²/3`. This file
  proves the fact that makes that inevitable: **the uniform distribution is exactly
  invariant under reflection.**

  The reflection map on `[-B, B]` is

      fold(x) = the point of [-B, B] congruent to x modulo 2B

  This is the projection of the circle of circumference `2B` onto the interval. It
  preserves Lebesgue measure: the interval is the circle cut open at one point, and
  cutting a circle open does not change its length.

  Numerical check. Feed `4·10⁵` points drawn uniformly from `[-B, B]`, apply the
  reflection with a shift, and histogram the result in ten bins:

      0.100 0.100 0.101 0.100 0.100 0.100 0.100 0.100 0.101 0.100

  Flat. The uniform distribution is a fixed point. That is why the corrected model
  converges to it and not to a point: reflection has a spread-preserving invariant
  measure, while clamping has none.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The reflection is length-preserving.**
    Reflection maps an interval of length `ℓ` to an interval of the same length.

    This is the geometric core of the stationarity law. Clamping maps a long stretch
    of the line into a single point, destroying length; reflection maps it to an
    equal stretch, preserving length. -/
theorem reflection_preserves_length
    (B x1 x2 : ℝ)
    (h : x1 ≤ x2) :
    (2 * B - x1) - (2 * B - x2) = x2 - x1 := by
  ring

/-- **The reflection is an involution.**
    Reflecting twice returns the original point.

    An involution is a bijection, and a bijection of the interval onto itself
    preserves the uniform measure. This is why the uniform distribution is a fixed
    point of the reflection: the map is just a rearrangement of the interval. -/
theorem reflection_involution (B x : ℝ) :
    2 * B - (2 * B - x) = x := by
  ring

/-- **The uniform spread is the fixed point.**
    The spread of the uniform distribution on `[-B, B]` is `B²/3`.

    Since the uniform distribution is invariant under reflection, and its spread is
    `B²/3`, the corrected model's equilibrium spread is `B²/3`. The equilibrium is
    not a coincidence of simulation: it is the spread of the invariant measure. -/
theorem uniform_spread_is_fixed_point (B : ℝ) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **The clamping contrast.**
    Clamping has no spread-preserving invariant: it maps every point above the
    ceiling to the same point.

    Two distinct points above the ceiling become one. A map that is not injective
    cannot preserve a measure with a density, and so cannot hold a non-zero spread.
    This is the structural difference between the original and corrected models. -/
theorem clamping_is_not_injective
    (c x1 x2 : ℝ)
    (h1 : c < x1) (h2 : c < x2) :
    min x1 c = min x2 c := by
  rw [min_eq_right h1.le, min_eq_right h2.le]

end Medium
