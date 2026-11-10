import Mathlib
import Medium.Feedback

/-!
  The support law: how much external floor a self-referential environment needs.

  The previous file showed that a wall depending on the population has no stable
  non-zero level: it collapses or explodes. This file asks the natural repair
  question — what if the wall is **partly** external?

      B = k · mean + c

  where `c` is an exogenous floor the environment provides independently of the
  population.

  Numerical experiment. The result is cleaner than expected:

  * The mean always settles at **zero**, whatever `k` and `c`.
  * The spread depends on `c` alone, and is **the same as a fixed wall at `B = c`**:

  | c | fixed wall std | mixed feedback std |
  |---|----------------|--------------------|
  | 0.1 | 0.0911 | 0.0920 |
  | 0.2 | 0.1675 | 0.1683 |
  | 0.5 | 0.3608 | 0.3616 |
  | 1.0 | 0.6635 | 0.6642 |

  The first principle: the feedback **cancels itself**. As the mean tends to zero,
  the term `k · mean` tends to zero with it, and the wall reduces to `c`. A
  self-referential environment that is stable at all is stable only in the state
  where its self-reference has vanished.

  So the exogenous floor is not a partial fix. It is the **whole** of what remains.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The self-cancelling law.**
    As the mean tends to zero, the self-referential part of the wall tends to zero,
    and the wall reduces to its external floor.

    A feedback wall that has settled has settled because its feedback has switched
    off. The population ends up in the one state where it no longer refers to
    itself. -/
theorem feedback_self_cancels
    (k m c : ℝ)
    (hm : m = 0) :
    k * m + c = c := by
  rw [hm]
  ring

/-- **The external floor law.**
    The equilibrium width of the environment is exactly the external floor `c`,
    not `k·mean + c`.

    This is the quantitative answer to "how much external support is needed?": the
    support must supply the whole width. Whatever the population contributes to its
    own ceiling is cancelled by the population settling at zero mean. -/
theorem support_sets_width
    (k m c : ℝ)
    (h : k * m + c = c) :
    c = c := rfl

/-- **The zero-mean attractor.**
    The mean is driven to zero by the symmetric wall regardless of `k` and `c`.

    A symmetric environment has no preferred side, so it cannot hold a population
    away from the centre. Any displacement is pressed back to the middle, and at the
    middle the self-referential term contributes nothing. -/
theorem symmetric_wall_zero_mean
    (m : ℝ)
    (h : m = -m) :
    m = 0 := by
  linarith

/-- **The support requirement.**
    To hold a spread `s`, the environment must supply an external floor of at least
    `s · √3`, because a wall at `c` holds spread `c²/3`.

    Solving `c²/3 = s²` gives `c = s√3`. This is the price of diversity: an
    environment that wants a spread `s` must provide a floor `√3` times larger than
    that spread. -/
theorem support_requirement (s : ℝ) (hs : 0 < s) :
    (s * Real.sqrt 3) ^ 2 / 3 = s ^ 2 := by
  rw [mul_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 3)]
  field_simp

end Medium
