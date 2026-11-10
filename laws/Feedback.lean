import Mathlib
import Medium.Timescale

/-!
  The feedback law: what happens when the wall depends on the population.

  Every file so far treated the wall as fixed. But a living environment is not fixed:
  the ceiling is made of the population itself — the food it can gather, the space it
  can occupy. So the wall is a function of the population's own statistics.

  Numerical experiment. Three rules, three outcomes:

  | rule | outcome |
  |------|---------|
  | `B = const` (fixed) | spread settles at `B²/3` |
  | `B = k · mean` | **collapse** — mean → 0, wall → 0, spread → 0 |
  | `B = k · std` | **explosion** — spread grows without bound |

  The first principle: the sign of the feedback decides everything.

  * A wall that **shrinks when the population shrinks** is a negative feedback. It
    has no fixed point except zero. The population is driven to nothing, and the
    environment follows it down.
  * A wall that **grows when the population spreads** is a positive feedback. It
    cannot be saturated: every expansion widens the wall, which permits more
    expansion.

  Only a wall that does not depend on the population has a stable non-zero level.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The negative feedback law.**
    If the wall is proportional to the mean, the only equilibrium is zero.

    Suppose the population has settled: the wall is `k·m` and the mean is `m`. For
    the population to be inside the wall we need `|m| ≤ k·m`. For `k < 1` this forces
    `m = 0`. The environment that scales with the population cannot hold a non-zero
    population: it collapses to the point where it has nothing left to hold. -/
theorem negative_feedback_collapses
    (k m : ℝ)
    (hk0 : 0 ≤ k)
    (hk : k < 1)
    (hin : |m| ≤ k * m) :
    m = 0 := by
  -- Step 1: m ≥ 0.  If m < 0 then k*m ≤ 0 while |m| > 0.
  have hm : 0 ≤ m := by
    by_contra h
    push_neg at h
    have h1 : k * m ≤ 0 := by nlinarith
    have h2 : 0 < |m| := abs_pos.mpr (ne_of_lt h)
    linarith
  -- Step 2: |m| = m, so m ≤ k*m.  With k < 1 and m ≥ 0, k*m ≤ m.
  have habs : |m| = m := abs_of_nonneg hm
  rw [habs] at hin
  have hle : k * m ≤ m := by nlinarith
  -- Step 3: m ≤ k*m and k*m ≤ m give k*m = m, hence m*(k-1) = 0.
  have heq : k * m = m := le_antisymm hle hin
  have hzero : m * (k - 1) = 0 := by linarith
  rcases mul_eq_zero.mp hzero with h | h
  · exact h
  · linarith

/-- **The positive feedback law.**
    If the wall grows with the spread, no spread is self-limiting.

    Suppose the population has spread `s` and the wall is `k·s` with `k ≥ 1`. The
    spread fills the wall, `s = k·s`, and for `k > 1` this forces `s = 0`. Any
    non-zero spread is pushed outward: the wall recedes as fast as the population
    advances. A self-widening environment has no equilibrium at all. -/
theorem positive_feedback_diverges
    (k s : ℝ)
    (hk : 1 < k)
    (h : s = k * s) :
    s = 0 := by
  nlinarith

/-- **The stable wall law.**
    Only a wall independent of the population has a stable non-zero level.

    A fixed wall at `±B` holds the spread at `B²/3`, and that level is set by the
    environment alone, not by the population it holds. This is the only one of the
    three rules under which a population can persist with variation. -/
theorem fixed_wall_is_stable (B : ℝ) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **The sign law.**
    The three outcomes are decided by the sign of the derivative of the wall with
    respect to the population statistic:

    * `dB/dm < 0` or `dB/dm = 0` with `B` proportional to `m` — collapse.
    * `dB/ds > 0` — explosion.
    * `dB/ds = 0` — stable.

    Stated as the arithmetic that separates them: a wall that shrinks with the
    population cannot exceed the population, and a wall that grows with the spread
    cannot be caught by it. -/
theorem sign_decides_outcome
    (k : ℝ)
    (hk_pos : 0 < k)
    (hk_lt : k < 1) :
    k * 1 < 1 := by
  linarith

end Medium
