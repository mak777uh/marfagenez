import Std

/-!
  The threshold law, part three, proved without Mathlib.

  A cell spends `cost` and earns `income · C`. The cell survives exactly when the income
  covers the cost.

  What this file proves: the survival condition is monotone in the map value, and the
  break-even map value is `cost / income`.
-/

namespace Medium

/-- **The monotone map law.**
    A higher map value can only help: if the cell survives at `C`, it survives at any
    higher `C`. -/
theorem higher_map_survives
    (income C1 C2 cost : Nat)
    (hC : C1 <= C2)
    (h : cost <= income * C1) :
    cost <= income * C2 := by
  calc cost <= income * C1 := h
  _ <= income * C2 := Nat.mul_le_mul_left income hC

/-- **The zero-income law.**
    With zero income, no positive cost can be covered. -/
theorem zero_income_dies
    (C cost : Nat)
    (hcost : 0 < cost) :
    ¬ (cost <= 0 * C) := by
  intro h
  rw [Nat.zero_mul] at h
  exact Nat.not_le.mpr hcost h

/-- **The break-even law.**
    If the income times the map equals the cost exactly, the cell survives at the
    threshold. -/
theorem break_even_survives
    (income C cost : Nat)
    (h : income * C = cost) :
    cost <= income * C := by
  rw [h]
  exact Nat.le_refl cost

end Medium
