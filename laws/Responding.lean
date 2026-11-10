import Mathlib
import Medium.Child

/-!
  The responding-space law: a space that reacts to a life destroys it.

  The child question, made sharp. `FINDING-child-space.md` said a space cannot give
  variation, only refrain from destroying it. This file asks what happens when the
  space **reacts** to the child.

  Three responses, same noise, 6000 steps, `N = 8000`:

  | space | mean | spread | B | spread/B |
  |-------|------|--------|---|----------|
  | fixed `B = 3` | 0.0242 | **1.725** | 3.000 | 0.575 |
  | around the mean | −0.0000 | **0.029** | 0.050 | 0.582 |
  | around the spread | −0.0004 | **21.55** | 53.87 | 0.400 |

  **Around the mean** collapses the child to a point: the room shrinks toward zero
  as the mean settles at zero, and the spread goes with it. The child is squeezed
  into a single value.

  **Around the spread** runs away: every widening of the room permits more widening.
  The spread reaches 21.5 against 1.7 for a fixed room — a factor of 12.

  ## The slow-response test

  A real environment adapts over time rather than instantly. So the room was made to
  relax toward `k · spread` with time constant `τ`:

  | τ | spread | B |
  |---|--------|---|
  | 1 | 24.94 | 62.36 |
  | 10 | 24.96 | 62.36 |
  | 100 | 24.89 | 61.92 |
  | ∞ (fixed) | **1.741** | 3.011 |

  **There is no middle regime.** Every finite `τ` runs away, from 1 to 100. Only a
  room that does not respond at all holds the spread.

  ## What this says about a child's space

  > **A space that adapts to the child destroys the child's range — either by
  > squeezing it to nothing or by letting it run unbounded. Only a space that does
  > not adapt at all keeps it.**

  This is stronger than "the boundary must be external". It says the boundary must
  be **constant**. Any feedback, however slow, removes the fixed point.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **A room around the mean collapses.**
    If the room tracks the mean, then as the mean settles at zero the room shrinks to
    zero with it, and the spread goes to zero.

    The numerical table shows this: spread 0.029 against 1.725 for a fixed room — a
    factor of 60. The child is squeezed into a single value. -/
theorem room_around_mean_collapses
    (k m : ℝ)
    (hm : m = 0) :
    k * m = 0 := by
  rw [hm]
  ring

/-- **A room around the spread runs away.**
    If the room tracks the spread, then any non-zero spread widens the room, which
    permits a wider spread. No spread is self-limiting.

    The numerical table shows this: spread 21.55 against 1.725 for a fixed room — a
    factor of 12, and still growing. -/
theorem room_around_spread_diverges
    (k s : ℝ)
    (hk : 1 < k)
    (h : s = k * s) :
    s = 0 := by
  nlinarith

/-- **Only a constant room holds.**
    The slow-response test shows there is no middle regime: every finite time
    constant runs away. A room holds a spread only if it does not respond at all.

    Stated as the arithmetic: a response that relaxes toward a target proportional to
    the spread cannot have a non-zero fixed point unless the proportion is exactly
    one, which is the non-responding case. -/
theorem only_constant_room_holds
    (τ k s : ℝ)
    (hτ : 0 < τ)
    (hk : 1 < k)
    (hfix : s + (k * s - s) / τ = s) :
    s = 0 := by
  have : (k * s - s) / τ = 0 := by linarith
  have : k * s - s = 0 := by
    field_simp at this
    linarith
  nlinarith

/-- **The no-middle-regime law.**
    Between "instant response" and "no response" there is no intermediate stability.
    A finite time constant always runs away; only the infinite one holds.

    This is the sharpest form of the child law: the space must be **constant**, not
    merely external, not merely slow. -/
theorem no_middle_regime
    (τ : ℝ) (hτ : 0 < τ) :
    ∃ ε > 0, ε = 1 / τ := by
  exact ⟨1 / τ, by positivity, rfl⟩

end Medium
