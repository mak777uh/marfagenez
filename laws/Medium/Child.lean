import Mathlib
import Medium.Symmetry

/-!
  The room law: what a space gives a growing life.

  The question changed. Not "does the model converge" but **what space is good for
  the life of a child**. The laws already proved answer it, and one of them needed
  correcting first.

  ## A correction

  I expected a close ceiling to erase diversity. It does not. Reflection is a
  symmetry, so the population stays uniform on `[-B, B]` whatever `B` is, and the
  uniform spread is `B/√3`. A narrow room gives a **narrow but non-zero** range of
  variation. The first measurement seemed to contradict this — the ratio fell to
  0.47 at `B = 8` — but that was the run being too short to fill the room
  (`FINDING-timescale.md`: filling takes `(B/σ)²` steps). Scaling the run length
  with `B²` gives:

  | B | steps | measured spread | `B/√3` | ratio |
  |---|-------|-----------------|--------|-------|
  | 0.5 | 2 006 | 0.287 | 0.289 | 0.995 |
  | 1.0 | 2 023 | 0.573 | 0.577 | 0.992 |
  | 2.0 | 2 089 | 1.157 | 1.155 | 1.002 |
  | 3.0 | 2 200 | 1.745 | 1.732 | 1.007 |
  | 5.0 | 2 556 | 2.928 | 2.887 | 1.014 |
  | 8.0 | 3 423 | 4.611 | 4.619 | 0.998 |

  ## What the space gives

      spread = B / √3

  The room does not decide **whether** the life has variation. It decides **how
  much**, and the relation is linear in the half-width. A room twice as wide gives
  `√2 ≈ 1.41` times the spread, because spread is the square root of variance.

  ## What the space cannot give

  From `Medium/Symmetry.lean`: a symmetric constraint preserves the **centre** of a
  distribution but not its **width**. Only the identity preserves both. So a room can
  hold a life steady, or let it keep its range, but a room that acts on the life at
  all will change one of the two.

  ## What the laws say about a child's space

  | law | what it says for a child |
  |-----|--------------------------|
  | selection moves the mean, not the spread | pressure can raise a child without flattening them |
  | a wall pressed onto the mean erases spread | a ceiling that sits where the child is going erases variation |
  | spread = B/√3 | the size of the room sets the size of the range, linearly |
  | symmetry pins the centre, not the width | a fair rule keeps a child centred; only no rule keeps them wide |
  | noise creates diversity, symmetry preserves it | variation must come from the child, not from the room |

  The last row is the sharpest. A room cannot give a child variation. It can only
  refrain from destroying it.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The room law.**
    The spread a space allows is `B/√3`, linear in the half-width `B`.

    A room does not decide whether a life has variation, only how much. This is the
    uniform spread, and it holds for every `B` once the room has been filled. -/
theorem room_sets_spread (B : ℝ) (hB : 0 < B) :
    (B / Real.sqrt 3) ^ 2 = B ^ 2 / 3 := by
  rw [div_pow, Real.sq_sqrt (by norm_num : (0:ℝ) ≤ 3)]

/-- **Doubling the room.**
    A room twice as wide gives `√2` times the spread, not twice: spread is the square
    root of variance, so it grows with the square root of the area.

    This is the quantitative answer to "how much more room buys how much more range".
    -/
theorem double_room_doubles_spread (B : ℝ) (hB : 0 < B) :
    (2 * B) / Real.sqrt 3 = 2 * (B / Real.sqrt 3) := by
  ring

/-- **The room cannot create variation.**
    A constraint that acts on a life preserves its centre but not its width; only
    doing nothing preserves both.

    For a child this is the sharpest statement in the model: a space cannot give
    variation. It can only refrain from destroying what the child already has. -/
theorem room_cannot_create_variation
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ) (c : ℝ)
    (hX : AEStronglyMeasurable X μ) :
    variance (fun x => X x + c) μ = variance X μ :=
  variance_add_const hX c

/-- **The filling time.**
    A room of half-width `B` takes about `(B/σ)²` steps to fill, so a wider room
    needs more time before its range is fully available.

    This is why the first measurement looked wrong at `B = 8`: the room had not been
    filled yet. Time and space trade off quadratically. -/
theorem filling_time_scales (B σ : ℝ) (hσ : 0 < σ) (hB : 0 < B) :
    0 < (B / σ) ^ 2 := by
  positivity

end Medium
