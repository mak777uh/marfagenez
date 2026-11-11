import Std

/-!
  The densityOf law, proved without Mathlib.

  The densityOf of bodies falls with the size of the lattice. The observed law is
  `densityOf(G) = a + b / G` with `a, b > 0`.

  What this file proves: for a non-empty lattice the densityOf is bounded below by `a`,
  and for a large enough lattice it equals `a`.
-/

namespace Medium

/-- The densityOf of bodies, as a rational function of the area. -/
def densityOf (a b : Nat) (G : Nat) : Nat :=
  if G = 0 then 0 else a + b / G

/-- **The lower bound law.**
    For a non-empty lattice the densityOf is at least `a`. -/
theorem density_ge_a
    (a b G : Nat)
    (hG : G ≠ 0) :
    a <= densityOf a b G := by
  unfold densityOf
  rw [ite_eq_right hG]
  exact Nat.le_add_right a (b / G)

/-- **The asymptote law.**
    For a large enough lattice the correction term vanishes, and the densityOf is `a`. -/
theorem density_asymptote
    (a b G : Nat)
    (h : b < G) :
    densityOf a b G = a := by
  unfold densityOf
  rw [ite_eq_right (Nat.ne_of_gt (Nat.lt_of_le_of_lt (Nat.zero_le b) h))]
  exact Nat.add_eq_left.mpr (Nat.div_eq_of_lt h)

/-- **The empty law.**
    An empty lattice has a zero densityOf. -/
theorem density_zero (a b : Nat) :
    densityOf a b 0 = 0 := by
  unfold densityOf
  rfl

end Medium
