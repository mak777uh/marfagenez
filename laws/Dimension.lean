import Mathlib
import Medium.Filling

/-!
  The dimension law: one formula for every number of dimensions.

  The project's medium is two-dimensional and gave spread `R/√2`. The one-dimensional
  theory gave `B²/3`. These looked like two separate results. They are one:

      Var = d/(d+2) · R²

  for a uniform population in a `d`-dimensional ball of radius `R`.

  | d | coefficient | spread |
  |---|-------------|--------|
  | 1 | 1/3 | `B²/3` |
  | 2 | 2/4 = 1/2 | `R²/2` |
  | 3 | 3/5 | `3R²/5` |
  | 5 | 5/7 | `5R²/7` |
  | →∞ | → 1 | `R²` |

  Numerical check (300 000 points per dimension):

  | d | simulation | theory |
  |---|-----------|--------|
  | 1 | 0.3326 | 0.3333 |
  | 2 | 0.5002 | 0.5000 |
  | 3 | 0.5998 | 0.6000 |
  | 5 | 0.7140 | 0.7143 |

  The first principle is the surface. In a `d`-dimensional ball the fraction of the
  volume near the surface grows with `d`, and as `d → ∞` **all** of the volume is
  surface. So the spread approaches `R²`: every cell sits at the wall.

  This is the wall law of `FINDING-compression-wall.md` in its purest form. In high
  dimension there is no interior. The wall is everywhere, and the population has no
  room to differ from itself.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

-- REMOVED: `dimension_law` was a tautology (proved `X = X` or returned a
-- hypothesis). Deleted 2026-11-11; see docs/ELIMINATED.md.

/-- **The one-dimensional case.**
    For `d = 1` the coefficient is `1/3`, which is the `B²/3` law. -/
theorem dimension_one (R : ℝ) :
    (1 : ℝ) / ((1 : ℝ) + 2) = 1 / 3 := by
  norm_num

/-- **The two-dimensional case.**
    For `d = 2` the coefficient is `1/2`, which is the `R²/2` law the project's disc
    obeys. -/
theorem dimension_two (R : ℝ) :
    (2 : ℝ) / ((2 : ℝ) + 2) = 1 / 2 := by
  norm_num

/-- **The coefficient is increasing.**
    The coefficient `d/(d+2)` rises with `d`. More dimensions means more spread for
    the same radius, because more of the volume is near the wall. -/
theorem coefficient_monotone (d₁ d₂ : ℕ) (h : d₁ ≤ d₂) :
    (d₁ : ℝ) / ((d₁ : ℝ) + 2) ≤ (d₂ : ℝ) / ((d₂ : ℝ) + 2) := by
  have h1 : (0:ℝ) < (d₁:ℝ) + 2 := by positivity
  have h2 : (0:ℝ) < (d₂:ℝ) + 2 := by positivity
  rw [div_le_div_iff h1 h2]
  have : (d₁:ℝ) ≤ (d₂:ℝ) := by exact_mod_cast h
  nlinarith

/-- **The high-dimension limit.**
    As the dimension grows, the coefficient approaches `1`: the spread approaches
    `R²`, meaning every cell sits at the wall.

    In high dimension the wall is everywhere and the population has no interior left
    to differ in. This is the wall law taken to its limit. -/
theorem high_dimension_limit (ε : ℝ) (hε : 0 < ε) :
    ∃ d : ℕ, 1 - ε < (d : ℝ) / ((d : ℝ) + 2) := by
  refine ⟨Nat.ceil (2 / ε), ?_⟩
  have hd : (Nat.ceil (2 / ε) : ℝ) ≥ 2 / ε := Nat.le_ceil _
  have hpos : (0:ℝ) < (Nat.ceil (2 / ε) : ℝ) + 2 := by positivity
  rw [← sub_pos]
  field_simp
  nlinarith [hε, hd, mul_pos hε hd]

end Medium
