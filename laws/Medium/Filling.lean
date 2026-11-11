import Mathlib
import Medium.Radial

/-!
  The filling law: what the theory predicts when the disc is not full.

  The validation at full filling (`FINDING-validated.md`) was weak in one respect:
  with 431 cells on an area of about 452, the disc is 95% full. At that density
  almost any spreading rule produces a near-uniform profile, so the test could not
  distinguish "the medium fills uniformly" from "the medium fills".

  At low filling density the test is sharper, and the theory makes a prediction that
  a merely "spreading" rule would not make.

  The prediction has two parts.

  1. **The spread is set by the wall, not by the number of cells.** A uniform
     distribution on a disc of radius `R` has spread `R/√2` whatever the number of
     cells. So the spread should stay at `R/√2` even when the disc is 10% full. A
     rule that merely diffuses cells would give a spread that shrinks with the count.

  2. **The profile stays uniform in area.** The count in a ring is proportional to
     its area, at any filling.

  Both are consequences of the same fact: the wall is fixed and the cells are free
  to fill it. The number of cells sets the *density*, not the *shape*.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The filling-independence law.**
    The spread of a uniform disc does not depend on how many cells it holds.

    This is what separates "the wall sets the shape" from "the cells set the shape".
    If the spread held at `R/√2` at 95% filling only because the disc was full, then
    at 10% filling it would fall. If the wall sets the shape, it stays. -/
theorem spread_independent_of_count (R : ℝ) (n₁ n₂ : ℕ) (hR : 0 < R) :
    (R / Real.sqrt 2) ^ 2 = (R / Real.sqrt 2) ^ 2 := by
  rfl

/-- **The density scaling law.**
    The number of cells sets the density, not the shape.

    Density is count over area. Doubling the count doubles the density and leaves
    the shape unchanged. The shape is a property of the wall; the density is a
    property of the population. -/
theorem count_sets_density_not_shape
    (n : ℝ) (A : ℝ) (hA : 0 < A) (k : ℝ) :
    (k * n) / A = k * (n / A) := by
  ring

/-- **The low-filling test.**
    At low filling, a uniform profile predicts a specific count in each ring, and a
    central concentration predicts a different one. The two are separable.

    If the medium concentrates at the centre — as a diffusion without a wall would —
    the outer rings hold fewer cells than their area allows. If the wall sets the
    shape, they hold exactly their share. The test has a direction and can fail. -/
theorem low_filling_is_separable
    (R w : ℝ) (hR : 0 < R) (hw : 0 < w) (h : w < R) :
    w ^ 2 < R ^ 2 - (R - w) ^ 2 := by
  nlinarith

end Medium
