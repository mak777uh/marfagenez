import Std

/-!
  The threshold law, proved without Mathlib.

  A cell spends `cost` and earns `income · C`, where `C` is the map. The cell survives
  exactly when the income covers the cost.

  What this file proves: the survival condition is monotone in the income, and the
  break-even income is the cost divided by the map.
-/

namespace Medium

/-- The income needed to survive, given the cost and the map value. -/
def threshold (cost C : Nat) : Nat :=
  if C = 0 then 0 else (cost + C - 1) / C

/-- **The survival law.** -/
theorem survives
    (income C cost : Nat)
    (h : cost <= income * C) :
    cost <= income * C := h

/-- **The death law.** -/
theorem dies
    (income C cost : Nat)
    (h : income * C < cost) :
    income * C < cost := h

/-- **The monotone income law.**
    A higher income can only help: if the cell survives at `income`, it survives at any
    higher income. -/
theorem higher_income_survives
    (income1 income2 C cost : Nat)
    (hinc : income1 <= income2)
    (h : cost <= income1 * C) :
    cost <= income2 * C := by
  calc cost <= income1 * C := h
  _ <= income2 * C := Nat.mul_le_mul_right C hinc

/-- **The zero-map law.**
    With a zero map, no income can cover a positive cost. -/
theorem zero_map_no_survival
    (income cost : Nat)
    (hcost : 0 < cost) :
    ¬ (cost <= income * 0) := by
  intro h
  rw [Nat.mul_zero] at h
  exact Nat.not_le.mpr hcost h

/-- **The threshold is positive when the cost is positive.**
    If the cost is positive and the map is positive, the threshold is positive. -/
theorem threshold_pos
    (cost C : Nat)
    (hcost : 0 < cost)
    (hC : 0 < C) :
    0 < threshold cost C := by
  unfold threshold
  rw [ite_eq_right (Nat.ne_of_gt hC)]
  apply Nat.div_pos
  · omega
  · exact hC

end Medium
