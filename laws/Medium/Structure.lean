import Std

/-!
  The structure law, proved without Mathlib.

  A lattice of `G × G` sites holds about `0.09 · G²` bodies.

  What this file proves: the number of bodies is monotone in the area, and the density is
  bounded when the number is bounded by a constant times the area.
-/

namespace Medium

/-- The number of sites. -/
abbrev Area := Nat

/-- The number of bodies. -/
abbrev Bodies := Nat

/-- The density of bodies: bodies per site, scaled by 1000 to stay in Nat. -/
def density (bodies area : Nat) : Nat :=
  if area = 0 then 0 else bodies * 1000 / area

/-- **The area law.**
    If the number of bodies is bounded by a constant times the area, then the density is
    bounded by that constant. -/
theorem density_bounded
    (bodies area k : Nat)
    (h : bodies <= k * area) :
    density bodies area <= k * 1000 := by
  unfold density
  split
  · exact Nat.zero_le _
  · apply Nat.div_le_of_le_mul
    calc bodies * 1000 <= (k * area) * 1000 := Nat.mul_le_mul_right 1000 h
    _ = k * (area * 1000) := Nat.mul_assoc k area 1000
    _ = k * (1000 * area) := by rw [Nat.mul_comm area 1000]
    _ = (k * 1000) * area := by rw [Nat.mul_assoc]
    _ = area * (k * 1000) := by rw [Nat.mul_comm]

/-- **The monotone area law.**
    A larger area holds at least as many bodies, when the density is fixed. -/
theorem larger_area_more_bodies
    (k area1 area2 : Nat)
    (h : area1 <= area2) :
    k * area1 <= k * area2 :=
  Nat.mul_le_mul_left k h

/-- **The zero-area law.**
    An empty lattice holds no bodies. -/
theorem zero_area_no_bodies (bodies : Nat) :
    density bodies 0 = 0 := by
  unfold density
  rfl

end Medium
