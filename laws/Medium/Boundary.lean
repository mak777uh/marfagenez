import Std

/-!
  The boundary law, proved without Mathlib.

  A boundary is a difference between two environments. If the inside is richer than the
  outside, the inside holds more cells.

  What this file proves: a difference in the environment gives a difference in the
  population, and the difference is monotone in the environment.
-/

namespace Medium

/-- The number of cells in a region. -/
abbrev Population := Nat

/-- The environment: a richness per site. -/
abbrev Richness := Nat

/-- The growth of a population: proportional to the richness, with a floor at zero. -/
def growth (richness : Richness) (rate : Nat) : Population :=
  richness * rate

/-- **The boundary law.**
    If the inside is richer than the outside, and the growth is monotone in the
    richness, then the inside holds at least as many cells as the outside. -/
theorem richer_holds_more
    (inside outside rate : Nat)
    (h : outside <= inside) :
    growth outside rate <= growth inside rate := by
  unfold growth
  exact Nat.mul_le_mul_right rate h

/-- **The strict boundary law.**
    If the inside is strictly richer, and the rate is positive, the inside holds
    strictly more cells. -/
theorem strictly_richer_holds_more
    (inside outside rate : Nat)
    (h : outside < inside)
    (hrate : 0 < rate) :
    growth outside rate < growth inside rate := by
  unfold growth
  exact Nat.mul_lt_mul_of_pos_right h hrate

/-- **The no-difference law.**
    If the two environments are equal, the two populations are equal: there is no
    boundary. -/
theorem equal_env_no_boundary
    (inside outside rate : Nat)
    (h : inside = outside) :
    growth inside rate = growth outside rate := by
  rw [h]

end Medium
