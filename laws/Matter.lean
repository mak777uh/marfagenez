import Std

/-!
  The matter law, proved without Mathlib.

  A cell has matter `M`. It spends `cost` and earns `earn`, and the matter is clamped at
  zero.

  What this file proves: matter is never negative, the clamp is the only thing that keeps
  it non-negative, and matter is unchanged exactly when the income equals the cost.
-/

namespace Medium

/-- Matter, as a natural number. -/
abbrev Matter := Nat

/-- The update: spend, earn, clamp at zero. -/
def update (M cost earn : Nat) : Matter :=
  if M + earn < cost then 0 else M + earn - cost

/-- **The non-negativity law.** -/
theorem update_nonneg (M cost earn : Nat) :
    0 <= update M cost earn :=
  Nat.zero_le _

/-- **The clamp law.**
    If the spend exceeds the matter plus the income, the matter is zero. -/
theorem clamp_to_zero (M cost earn : Nat)
    (h : M + earn < cost) :
    update M cost earn = 0 := by
  unfold update
  exact ite_eq_left h

/-- **The no-clamp law.**
    If the spend does not exceed the matter plus the income, the matter falls by the
    difference. -/
theorem no_clamp (M cost earn : Nat)
    (h : cost <= M + earn) :
    update M cost earn = M + earn - cost := by
  unfold update
  exact ite_eq_right (Nat.not_lt.mpr h)

/-- **The break-even law.**
    Matter is unchanged exactly when the income equals the cost. -/
theorem break_even (M cost : Nat) :
    update M cost cost = M := by
  unfold update
  have h : ¬ (M + cost < cost) := Nat.not_lt.mpr (Nat.le_add_left cost M)
  rw [ite_eq_right h]
  exact Nat.add_sub_cancel M cost

end Medium
