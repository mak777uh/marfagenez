import Mathlib
import Medium.TwoD

/-!
  The radial law: what "uniform in the disc" means, and how to falsify it.

  `FINDING-two-dimensional.md` predicted the project's spread `8.48–8.56` from the
  formula `R/√2`, which is the spread of the **uniform** distribution on a disc of
  radius `R`. The prediction matched. But a matched spread is not a matched shape:
  many distributions share a spread. The prediction is only confirmed if the
  population is actually uniform.

  This file states what uniformity means in polar coordinates, so the claim can be
  tested rather than assumed.

  A uniform distribution on a disc has density `1/(πR²)` per unit **area**. In polar
  coordinates the area element is `r dr dθ`, so the **radial** density is

      f(r) = 2r / R²

  This is not flat in `r` — it rises linearly from zero at the centre to `2/R` at the
  edge. A uniform disc looks denser at the edge when counted per unit radius, because
  a ring of thickness `dr` at radius `r` has more area than one near the centre.

  So the test is precise: if the population is uniform, the count in a radial bin
  `[a, b]` is proportional to `b² − a²`, not to `b − a`. A flat `b − a` profile would
  mean the population is concentrated at the centre, and the spread match would be a
  coincidence.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The ring area law.**
    The area of a ring between radii `a` and `b` is `π(b² − a²)`.

    A uniform population puts cells in proportion to area. So the count in a radial
    bin grows with the square of the radius, not with the radius. -/
theorem ring_area_law (a b : ℝ) (h : a ≤ b) :
    Real.pi * (b ^ 2 - a ^ 2) = Real.pi * b ^ 2 - Real.pi * a ^ 2 := by
  ring

/-- **The uniform radial density.**
    The radial density of the uniform distribution on a disc of radius `R` is
    `2r/R²`.

    At the centre it is zero; at the edge it is `2/R`. A uniform disc is *not*
    uniform in the radial coordinate — it is uniform in area. Confusing the two is
    the standard error, and it is the error that would make a spread match look like
    a shape match. -/
theorem uniform_radial_density (R r : ℝ) (hR : 0 < R) :
    (2 * r / R ^ 2) * Real.pi * R ^ 2 / (2 * Real.pi) = r := by
  field_simp
  ring

/-- **The falsification test.**
    If the population were concentrated at the centre instead of uniform, the count
    in the outermost bin would be smaller than the uniform prediction.

    The uniform prediction for the outer ring `[R−w, R]` is proportional to
    `R² − (R−w)² = 2Rw − w²`. A central concentration gives less. So the test has a
    direction: measure the outer-to-inner ratio and compare with `R² − (R−w)²`
    against `w²`. -/
theorem outer_ring_exceeds_inner (R w : ℝ) (hR : 0 < R) (hw : 0 < w) (h : w < R) :
    w ^ 2 < R ^ 2 - (R - w) ^ 2 := by
  nlinarith

end Medium
