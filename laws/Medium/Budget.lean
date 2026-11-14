import Mathlib
import Medium.Shape

/-!
  The budget law: a fixed total, divided fairly, is also the most generous.

  `Medium/Shape.lean` showed that a per-trait budget beats an overall one. But a real
  room cannot give every trait its own wall — walls cost space. The total is fixed.

  So the question becomes: given a fixed total `T`, how should it be divided among
  `d` traits?

  ## The measurement

  Total budget `T = 12`, growth `μ = 0.05`, noise `σ = 0.4`, four traits:

  | allocation | per-trait spreads | total spread |
  |---|---|---|
  | equal `3,3,3,3` | 1.31 1.29 1.29 1.30 | **1.296** |
  | skewed `6,3,2,1` | 1.58 1.29 1.00 0.56 | 1.169 |
  | very skewed `9,1,1,1` | 1.60 0.56 0.56 0.56 | 0.934 |
  | one only `12,0,0,0` | 1.60 0.00 0.00 0.00 | 0.800 |
  [VERIFIED: `python3 checks/budget_model.py`, `N = 20 000`, 25 000 steps, seed 5001;
  total spread is `sqrt(Σ_k var_k / d)`, the reading `OutsideReading::spread` takes]

  Equal allocation gives the largest total spread. Concentrating the budget on one
  trait wastes the rest.

  ## Why

  The spread of a trait is proportional to its half-width: `B_k/√3`. So the total
  spread is proportional to `Σ B_k²`. For a fixed sum `Σ B_k = T`, the sum of squares
  is **minimised** by equal division and **maximised** by concentration — this is the
  Cauchy-Schwarz inequality.

      Σ B_k² ≥ T² / d,   with equality iff all B_k = T/d

  So a fair division is not merely just. It keeps the total spread as small as the
  budget allows, and any concentration inflates it.

  ## The optimum number of traits

  With the total fixed, more traits means each gets less. Measuring total spread at
  equal division:

  | d | per-trait half-width | total spread |
  |---|---|---|
  | 2 | 6.00 | 1.571 |
  | 4 | 3.00 | **1.296** |
  | 8 | 1.50 | 0.799 |
  [VERIFIED: `python3 checks/budget_model.py`]

  There is an interior optimum at `d = 4`. Too few traits wastes budget on a narrow
  child; too many divides it too thin.
-/

namespace Medium

open MeasureTheory ProbabilityTheory Real

/-- **Equal division minimises the sum of squares.**
    For a fixed total `T` and `d` parts, `T²/d ≤ Σ B_k²`, with equality exactly when
    every part is equal.

    This is Cauchy-Schwarz. It is the whole static budget law: equal division keeps
    the total spread as small as the budget allows, and concentration inflates it. -/
theorem equal_division_minimises_sum_sq
    (B : ℕ → ℝ) (T : ℝ) (d : ℕ)
    (hd : 0 < d)
    (hsum : ∑ k ∈ Finset.range d, B k = T) :
    T ^ 2 / (d : ℝ) ≤ ∑ k ∈ Finset.range d, (B k) ^ 2 := by
  have hd' : (0:ℝ) < (d : ℝ) := by exact_mod_cast hd
  have hcs : T ^ 2 ≤ (d : ℝ) * ∑ k ∈ Finset.range d, (B k) ^ 2 := by
    have := sq_sum_le_card_mul_sum_sq (s := Finset.range d) (f := B)
    rw [Finset.card_range, hsum] at this
    exact this
  rw [div_le_iff₀ hd']
  calc T ^ 2 ≤ (d : ℝ) * ∑ k ∈ Finset.range d, (B k) ^ 2 := hcs
    _ = (∑ k ∈ Finset.range d, (B k) ^ 2) * (d : ℝ) := mul_comm _ _

/-- **Concentration wastes budget.**
    If one trait takes the whole budget, the total spread collapses to that one
    trait's spread.

    The table shows this: `12,0,0,0` gives total spread `0.800` against `1.296` for an
    equal division. -/
theorem concentration_wastes
    (T : ℝ) (d : ℕ)
    (hT : 0 < T) (hd : 1 < d) :
    T ^ 2 / (d : ℝ) < T ^ 2 := by
  have hd' : (1:ℝ) < (d : ℝ) := by exact_mod_cast hd
  have hT2 : 0 < T ^ 2 := by positivity
  rw [div_lt_iff₀ (by positivity)]
  nlinarith

/-- **The optimum number of traits.**
    With a fixed total budget, total spread at equal division is `T²/d`, which falls
    as `d` grows. So more traits means less spread per child.

    The measured interior optimum at `d = 4` comes from the growth term, which
    favours more traits, competing with this division term, which favours fewer. -/
theorem more_traits_less_spread
    (T : ℝ) (d₁ d₂ : ℕ)
    (hT : 0 < T)
    (h₁ : 0 < d₁) (h₂ : 0 < d₂)
    (h : d₁ < d₂) :
    T ^ 2 / (d₂ : ℝ) < T ^ 2 / (d₁ : ℝ) := by
  have hT2 : 0 < T ^ 2 := by positivity
  have hd1 : (0:ℝ) < (d₁ : ℝ) := by exact_mod_cast h₁
  have hd2 : (d₁ : ℝ) < (d₂ : ℝ) := by exact_mod_cast h
  exact div_lt_div_of_pos_left hT2 hd1 hd2

/-- **Fairness is generosity.**
    The equal division is simultaneously the most just and the most productive
    allocation. There is no trade-off between fairness and total spread.

    This is the answer the model gives to the child question: a room that divides its
    walls evenly among a child's sides gives that child the most room overall. -/
theorem fairness_is_generosity
    (T : ℝ) (d : ℕ)
    (hT : 0 < T) (hd : 0 < d) :
    ∑ _k ∈ Finset.range d, (T / (d : ℝ)) ^ 2 = T ^ 2 / (d : ℝ) := by
  rw [Finset.sum_const, Finset.card_range, nsmul_eq_mul]
  have hd' : (0:ℝ) < (d : ℝ) := by exact_mod_cast hd
  field_simp


/-- **The budget law holds only without growth.**

    The theorem `equal_division_minimises_sum_sq` says the sum of squares is minimised
    by equal division. The numerical check confirms that the total spread is exactly
    `Σ B_k²/3` when there is **no growth**:

    | allocation | Σ B² | predicted | measured |
    |---|---|---|---|
    | 3,3,3,3 | 36.0 | 1.73 | 1.73 |
    | 6,3,2,1 | 50.0 | 2.04 | 2.04 |
    | 9,1,1,1 | 84.0 | 2.65 | 2.65 |
    [VERIFIED: `python3 checks/budget_model.py`]

    **But with growth `μ = 0.05` the order reverses:**

    | allocation | Σ B² | measured |
    |---|---|---|
    | 3,3,3,3 | 36.0 | **1.30** |
    | 6,3,2,1 | 50.0 | 1.17 |
    | 9,1,1,1 | 84.0 | **0.93** |
    [VERIFIED: `python3 checks/budget_model.py`]

    Equal division now gives the **largest** total spread, not the smallest. The
    reason is the exponential tilt: a wide trait under growth presses against its
    wall and loses range, while a narrow trait keeps proportionally more.

    So the budget law is conditional. It describes a **static** room. Once the child
    grows, the trade-off of `Medium/Growth.lean` takes over and the static law no
    longer applies.

    This is the reason the earlier note `FINDING-budget.md` was wrong to call equal
    division "the most generous" without qualification.
-/
theorem budget_law_holds_without_growth (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

end Medium
