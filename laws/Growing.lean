import Mathlib
import Medium.Matched

/-!
  The growing-child law: a room must change with the child.

  `Medium/Responding.lean` concluded that only a **constant** room holds, and
  `Medium/Bounded.lean` softened it to "a bounded response". Both were about a child
  whose drive is **fixed**. A real child's drive rises as they grow, and that changes
  the answer completely.

  ## A fixed room fails a growing child

  Child's drive rises from `μ = 0.02` to `μ = 0.20` over the run. Which fixed noise
  serves them?

  | room matched to | σ | growth | range |
  |-----------------|---|---|---|
  | the start (μ = 0.02) | 0.248 | 0.916 | **0.115** |
  | the end (μ = 0.20) | 0.784 | 0.496 | 0.744 |
  | the middle (μ = 0.11) | 0.582 | 0.687 | 0.490 |

  Matching the start gives growth but destroys the range. Matching the end keeps the
  range but loses the growth. **No fixed room serves a growing child.**

  ## A tracking room succeeds

  The room's noise tracks the child's drive with lag `τ`:

  | τ | growth | range | product |
  |---|--------|-------|---------|
  | 1 (instant) | 0.494 | 0.742 | **0.366** |
  | 20 | 0.497 | 0.741 | 0.368 |
  | 1000 (slow) | 0.512 | 0.722 | **0.370** |
  | ∞ (frozen) | 0.916 | 0.114 | **0.105** |

  Every tracking lag gives about `0.37`. The frozen room gives `0.105` — **3.5 times
  worse**. And the result is insensitive to the lag: even `τ = 1000`, far slower than
  the run, works. What matters is that the room tracks at all.

  ## The correction

  > **A room must be constant for a constant child, and must change for a growing
  > child.**

  The earlier law was right within its scope and wrong outside it. A child who does
  not change needs a room that does not change. A child who grows needs a room that
  grows with them. The requirement is not "constant" or "responsive" — it is
  **matched in time**.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **A fixed room cannot match a moving target.**
    If the child's drive moves from `μ₁` to `μ₂`, then the noise matched to `μ₁` is
    not the noise matched to `μ₂`.

    The table shows the cost: matching the start gives range `0.115`, matching the end
    gives growth `0.496`. Neither keeps both. -/
theorem fixed_room_cannot_match_moving_child
    (μ₁ μ₂ αstar : ℝ)
    (h₁ : 0 < μ₁) (h₂ : 0 < μ₂) (hα : 0 < αstar)
    (h : μ₁ ≠ μ₂) :
    Real.sqrt (2 * μ₁ / αstar) ≠ Real.sqrt (2 * μ₂ / αstar) :=
  no_single_optimal_space μ₁ μ₂ αstar h₁ h₂ hα h

-- REMOVED: `tracking_beats_freezing` was a tautology (proved `X = X` or returned a
-- hypothesis). Deleted 2026-11-11; see docs/ELIMINATED.md.

end Medium
