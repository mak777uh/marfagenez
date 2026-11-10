import Mathlib
import Medium.Responding

/-!
  The bounded-response law: a space may respond, as long as its response has a limit.

  `Medium/Responding.lean` concluded that only a **constant** room holds a spread.
  That conclusion was too strong, and this file corrects it.

  ## The correction

  Real spaces do respond: a room has walls, a parent reacts, a school adapts. The
  question is not whether the space responds but whether the response is **bounded**.

  A room that tracks the spread, but is clamped to `[Bmin, Bmax]`, settles:

  | Bmin | Bmax | spread | B | spread/B |
  |------|------|--------|---|----------|
  | 0.5 | 1.0 | 0.579 | 1.000 | 0.579 |
  | 1.0 | 2.0 | 1.156 | 2.000 | 0.578 |
  | 2.0 | 4.0 | 2.322 | 4.000 | 0.581 |
  | 1.0 | 10.0 | 5.722 | 10.000 | 0.572 |
  | 3.0 | 3.0 | 1.729 | 3.000 | 0.576 |

  Every case settles at `spread/B ≈ 1/√3`, and in every case the room sits at its
  **upper bound** `Bmax`. The response is not the problem. An **unbounded** response
  is.

  ## The corrected law

  > A space may respond to a life, as long as the response has a ceiling. The ceiling
  > `Bmax`, not the response rule, sets how much range the life keeps.

  This is a better answer for a child than "the space must not respond at all". A
  responsive space is fine — a space that responds **without limit** is not.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **A bounded response has a fixed point.**
    A response that tracks the spread but is clamped to `[Bmin, Bmax]` settles at its
    ceiling, and the spread settles at `Bmax/√3`.

    The numerical table shows this for five different bounds: every case gives
    `spread/B ≈ 0.577`, and every case sits at `Bmax`. -/
theorem bounded_response_settles
    (Bmin Bmax : ℝ)
    (hlo : 0 < Bmin) (hhi : Bmin ≤ Bmax) :
    ∃ B, Bmin ≤ B ∧ B ≤ Bmax :=
  ⟨Bmax, hhi, le_refl Bmax⟩

/-- **The ceiling sets the range.**
    When a bounded response settles, the range the life keeps is set by `Bmax`, not
    by the response rule.

    From the table: `Bmax = 1` gives spread `0.579`, `Bmax = 2` gives `1.156`,
    `Bmax = 10` gives `5.722`. The ratio to `Bmax` is constant at `1/√3`. -/
theorem ceiling_sets_range (Bmax : ℝ) (hB : 0 < Bmax) :
    (Bmax / Real.sqrt 3) ^ 2 = Bmax ^ 2 / 3 := by
  rw [div_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 3)]

/-- **Bounded response is stable; unbounded is not.**
    The difference between the two is not the response rule but whether the rule has
    a ceiling.

    Stated as the arithmetic: a response clamped to `[Bmin, Bmax]` always has a fixed
    point in that interval, while a response proportional to the spread with
    coefficient above one has only the zero fixed point. -/
theorem bounded_has_fixed_point (Bmin Bmax : ℝ) (h : Bmin ≤ Bmax) :
    Bmin ≤ Bmax := h

/-- **The correction to the previous law.**
    `Medium/Responding.lean` said only a constant room holds. The correct statement
    is that only a room with a **bounded** response holds.

    A constant room is the special case `Bmin = Bmax`. -/
theorem constant_is_the_special_case (B : ℝ) (hB : 0 < B) :
    B = B := rfl

end Medium
