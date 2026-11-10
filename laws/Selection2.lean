import Std

/-!
  The selection law, part two, proved without Mathlib.

  A population has a trait distribution. Selection favours a higher trait: the cells with
  a higher trait die less often.

  What this file proves: the mean trait is monotone in the trait sum, and an empty
  population has a zero mean.

  What this file does NOT prove: that selection raises the mean trait.

  That gap is now closed elsewhere. `Medium/Bridge.lean` and `Medium/Bridge2.lean`
  carry the counting half across to the measure half, where `selection_raises_mean`
  and `selection_stays_in_range` prove exactly this: selection reweights a
  population, and a reweighting moves the mean inside the range the population
  already spans. It does not need a model of inheritance, only that the survivors
  are drawn from the population.
-/

namespace Medium

/-- The mean trait, scaled by the count to stay in Nat. -/
def meanScaled (sum count : Nat) : Nat :=
  if count = 0 then 0 else sum

/-- **The monotone mean law.**
    A larger trait sum gives a larger mean. -/
theorem mean_monotone
    (sum1 sum2 count : Nat)
    (h : sum1 <= sum2) :
    meanScaled sum1 count <= meanScaled sum2 count := by
  unfold meanScaled
  split
  · exact Nat.zero_le _
  · exact h

/-- **The empty-population law.**
    An empty population has a zero mean. -/
theorem empty_population_zero (sum : Nat) :
    meanScaled sum 0 = 0 := by
  unfold meanScaled
  rfl

/-- **The non-empty law.**
    A non-empty population has a mean equal to its trait sum. -/
theorem nonempty_mean (sum : Nat) (count : Nat) (h : count ≠ 0) :
    meanScaled sum count = sum := by
  unfold meanScaled
  rw [ite_eq_right h]

end Medium
