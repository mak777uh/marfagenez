import Std

/-!
  The learning law, part two, proved without Mathlib.

  A cell's learning rate is inherited with mutation, clamped at a ceiling.

  What this file proves: the clamped rate never exceeds the ceiling, and without a
  mutation the clamped rate is the parent's rate.
-/

namespace Medium

/-- The clamped inheritance. -/
def inheritClamped (parent mutation ceiling : Nat) : Nat :=
  if ceiling < parent + mutation then ceiling else parent + mutation

/-- **The ceiling law.** -/
theorem clamped_le_ceiling
    (parent mutation ceiling : Nat) :
    inheritClamped parent mutation ceiling <= ceiling := by
  unfold inheritClamped
  split
  · exact Nat.le_refl ceiling
  · exact Nat.le_of_not_lt ‹¬ ceiling < parent + mutation›

/-- **The no-mutation law.** -/
theorem clamped_no_mutation
    (parent ceiling : Nat)
    (h : parent < ceiling) :
    inheritClamped parent 0 ceiling = parent := by
  unfold inheritClamped
  rw [Nat.add_zero]
  rw [ite_eq_right (Nat.not_lt.mpr (Nat.le_of_lt h))]

/-- **The at-ceiling law.** -/
theorem clamped_at_ceiling
    (parent mutation ceiling : Nat)
    (h : ceiling < parent + mutation) :
    inheritClamped parent mutation ceiling = ceiling := by
  unfold inheritClamped
  rw [ite_eq_left h]

end Medium
