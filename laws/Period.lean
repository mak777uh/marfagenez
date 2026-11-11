import Std

/-!
  The period law, proved without Mathlib.

  The period of the breathing is proportional to the lag: `period = k · tau`.

  What this file proves: the period is monotone in the lag, and strictly monotone when
  the constant is positive.
-/

namespace Medium

/-- The lag, in steps. -/
abbrev Lag := Nat

/-- The period, in steps. -/
abbrev Period := Nat

/-- The period as a function of the lag. -/
def periodOf (k tau : Nat) : Period :=
  k * tau

/-- **The period law.**
    A longer lag gives a longer period, when the constant is positive. -/
theorem longer_lag_longer_period
    (k tau1 tau2 : Nat)
    (hk : 0 < k)
    (h : tau1 < tau2) :
    periodOf k tau1 < periodOf k tau2 := by
  unfold periodOf
  exact Nat.mul_lt_mul_of_pos_left h hk

/-- **The weak period law.**
    A longer lag gives at least as long a period. -/
theorem longer_lag_period_ge
    (k tau1 tau2 : Nat)
    (h : tau1 <= tau2) :
    periodOf k tau1 <= periodOf k tau2 := by
  unfold periodOf
  exact Nat.mul_le_mul_left k h

/-- **The zero-lag law.**
    A zero lag gives a zero period: no delay, no oscillation. -/
theorem zero_lag_zero_period (k : Nat) :
    periodOf k 0 = 0 := by
  unfold periodOf
  exact Nat.mul_zero k

-- REMOVED: `period_ratio` was a tautology (proved `X = X` or returned a
-- hypothesis). Deleted 2026-11-11; see docs/ELIMINATED.md.

end Medium
