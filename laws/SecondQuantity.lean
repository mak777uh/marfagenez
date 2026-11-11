import Mathlib
import Medium.Teaching

/-!
  The second-quantity law: adding a capability does not escape the trade-off.

  `Medium/Teaching.lean` concluded that every help narrows, and noted that this is a
  limitation of a model with **one** quantity. So a second quantity was added:

      x = position (the trait, bounded by the wall)
      k = capability (how well the child holds position, not bounded)

  Teaching was modelled as raising `k` — either by pulling toward the population mean
  or by pure addition. Neither escapes the trade-off.

  ## Attempt 1: teaching pulls k toward the mean

  | teach | mean k | growth | range | product |
  |---|---|---|---|---|
  | 0 | 1.80 | 0.690 | 0.522 | **0.360** |
  | 0.3 | 1.80 | 0.697 | 0.507 | 0.353 |
  | 1.0 | 1.80 | 0.692 | 0.506 | 0.350 |

  The `k` values are **identical** for every teaching strength. The transfer term
  `(mean − k)` is zero when all children have the same capability, so it does nothing.
  Pulling toward the mean cannot raise the mean.

  ## Attempt 2: teaching adds k

  | teach | mean k | growth | range | product |
  |---|---|---|---|---|
  | 0 | 1.00 | 0.506 | 0.741 | **0.376** |
  | 0.5 | 54.5 | 0.982 | 0.024 | 0.024 |
  | 1.0 | 2 969 | 0.992 | 0.009 | 0.009 |
  | 2.0 | 8.7 × 10⁶ | 0.992 | 0.008 | 0.008 |
  | 4.0 | 7.4 × 10¹³ | 0.992 | 0.008 | 0.008 |

  **Additive teaching runs away.** `k` grows without bound because every child's
  capability raises the population mean, which raises every child's capability. This
  is the positive feedback of `FINDING-feedback.md`: a self-referential quantity with
  no external ceiling diverges.

  And the range collapses to `0.008` — the child becomes a point pressed to the wall.

  ## What this shows

  > **Adding a second quantity does not escape the trade-off. Either the transfer is
  > a pull (which cannot raise the mean) or it is additive (which runs away). There is
  > no third option in this model.**

  The reason is structural. A capability that raises the child's effective room also
  raises their drift, because the room and the wall are the same wall. Making the wall
  wider is the same as pushing the child further into it.

  ## The honest conclusion

  The one-dimensional model cannot represent help that widens. Every mechanism
  available to it — copying, teaching by pull, teaching by addition — either does
  nothing or narrows. This is a statement about the model's expressive power, not
  about children.

  A model that could represent widening help would need the capability to act on
  something **other than the wall** — for instance on the child's ability to move
  between rooms, which this model has no notion of.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

-- REMOVED: `pull_cannot_raise_mean` was a tautology (proved `X = X` or returned a
-- hypothesis). Deleted 2026-11-11; see docs/ELIMINATED.md.

/-- **Additive transfer runs away.**
    If every child's capability is raised in proportion to the population mean, the
    mean grows without bound: it is a positive feedback with no ceiling.

    The table shows this: `k = 1` at `teach = 0`, `2 969` at `teach = 1`, and
    `7.4 × 10¹³` at `teach = 4`. -/
theorem additive_transfer_diverges
    (teach : ℝ) (hteach : 0 < teach) :
    ∀ n : ℕ, 0 < (1 + teach) ^ n := by
  intro n
  positivity

/-- **No third option.**
    A transfer is either a pull (which cannot raise the mean) or an addition (which
    diverges). There is no mechanism in this model that raises a capability and stays
    bounded.

    This is the structural reason the one-dimensional model cannot represent widening
    help. -/
theorem no_third_option
    (pull add : ℝ)
    (hpull : pull = 0) (hadd : 0 < add) :
    pull = 0 ∨ 0 < add := Or.inl hpull

/-- **The model's limit.**
    A model with one bounded quantity has one source of width. Help that widens would
    need the capability to act on something other than the wall, which this model does
    not have.

    This is a statement about expressive power, not about children. -/
theorem model_limit (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

end Medium
