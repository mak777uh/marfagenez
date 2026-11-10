import Std

/-!
  The body size law, proved without Mathlib.

  The size of a body grows with the growth rate: `size ≈ base + rate · grow`.

  What this file proves: the size is monotone in the growth rate, and the size is
  bounded below by the base.
-/

namespace Medium

/-- The body size as a function of the growth rate. -/
def bodySize (base rate grow : Nat) : Nat :=
  base + rate * grow

/-- **The monotone size law.**
    A higher growth rate gives a larger body. -/
theorem size_monotone
    (base rate grow1 grow2 : Nat)
    (h : grow1 <= grow2) :
    bodySize base rate grow1 <= bodySize base rate grow2 := by
  unfold bodySize
  exact Nat.add_le_add_left (Nat.mul_le_mul_left rate h) base

/-- **The strict size law.**
    A strictly higher growth rate gives a strictly larger body, when the rate is positive. -/
theorem size_strict
    (base rate grow1 grow2 : Nat)
    (hrate : 0 < rate)
    (h : grow1 < grow2) :
    bodySize base rate grow1 < bodySize base rate grow2 := by
  unfold bodySize
  exact Nat.add_lt_add_left (Nat.mul_lt_mul_of_pos_left h hrate) base

/-- **The base law.**
    With a zero growth rate the body is the base size. -/
theorem size_zero_grow (base rate : Nat) :
    bodySize base rate 0 = base := by
  unfold bodySize
  rw [Nat.mul_zero, Nat.add_zero]

/-- **The lower bound law.**
    The body is at least the base size. -/
theorem size_ge_base (base rate grow : Nat) :
    base <= bodySize base rate grow := by
  unfold bodySize
  exact Nat.le_add_right base (rate * grow)

end Medium
