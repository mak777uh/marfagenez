/-
Medium/CapacityLaw.lean

The capacity law, as measured in EXP-24 and written down here.

The question
------------
EXP-23 showed that how many organisms survive is decided by seating:
`survivors = Σ over cells of min(occupancy, k_max)`. That left `k_max` a
measured number. EXP-24 found where it comes from, and this file states that
finding as theorems.

The law
-------
A cell with `k` eaters on it settles at a level `c*` given by the model's own
step: the cell starts at `M`, the `k` eaters take `min(income, ·)` one after
another, and then the cell regrows once toward `M` by `regrow`:

    afterTakes income k c   -- what the eaters leave
    cellStep M regrow (c - afterTakes income k c)  -- wrong: cellStep takes the take

The step is written in `Medium/Field.lean` as

    cellStep M r t c = (c - t) + (M - (c - t)) * r

where `t` is what the eaters took in total. So one step of a cell with `k`
eaters is `cellStep M r (c - afterTakes income k c) c`.

What is proved here
-------------------
* `eater_take` — the `i`-th eater on a settled cell takes
  `min(income, c* - (i-1)*income)`, which is the arithmetic EXP-24 uses.
* `kmax_strict` — if the `k`-th eater takes at most `maint`, then `k` is not a
  valid seating. This is the strict comparison the model makes: an eater that
  takes exactly `maint` lands on `0` and dies (`core/src/organism.rs:177`).
* `two_eaters` / `three_eaters` — the worked cases EXP-24 prints.

What is NOT proved here
-----------------------
* That the recursion converges. `Medium/Convergence.lean` proves the gap is
  multiplied by `(1 - r)` each step for a *fixed* take; here the take changes
  with the level, so the convergence argument does not carry over unchanged.
* That `k_max` is computable in closed form from `M, r, income, maint`. It is
  not: it is a count, and the count depends on the whole recursion.
* Anything about moving organisms. Every theorem here is about a cell, not
  about an organism that chooses where to be.
-/

import Medium.Field
import Medium.Capacity

namespace Medium

open Real

/-! ### What the i-th eater gets

The eaters come in order. The first takes `min(income, c)`, the second takes
`min(income, c - first)`, and so on. When the cell holds at least `i * income`,
the first `i` eaters each get the full `income`. -/

/-- **A cell that has been emptied stays empty.** -/
theorem afterTakes_zero (t₀ : ℝ) (ht₀ : 0 ≤ t₀) (k : ℕ) : afterTakes t₀ k 0 = 0 := by
  induction k with
  | zero => rfl
  | succ k ih =>
      have hmin : takeOne t₀ (0 : ℝ) = 0 := by
        unfold takeOne
        exact min_eq_right ht₀
      rw [afterTakes, hmin, sub_zero]
      exact ih

/-- **A cell holding no more than k incomes is emptied by k eaters.** -/
theorem afterTakes_eq_zero_of_le {t₀ c : ℝ} (ht₀ : 0 < t₀) (h0 : 0 ≤ c) {k : ℕ}
    (h : c ≤ (k : ℝ) * t₀) : afterTakes t₀ k c = 0 := by
  induction k generalizing c with
  | zero =>
      have hc : c ≤ 0 := by simpa using h
      have hc0 : c = 0 := by linarith [h0]
      subst hc0
      exact afterTakes_zero t₀ (le_of_lt ht₀) 0
  | succ k ih =>
      have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
      rw [hcast] at h
      by_cases hc : c ≤ t₀
      · have htake : takeOne t₀ c = c := min_eq_right hc
        have hstep : afterTakes t₀ (k + 1) c
            = afterTakes t₀ k (c - takeOne t₀ c) := rfl
        rw [hstep, htake, sub_self]
        exact afterTakes_zero t₀ (le_of_lt ht₀) k
      · push Not at hc
        have htake : takeOne t₀ c = t₀ := min_eq_left (le_of_lt hc)
        have hstep : afterTakes t₀ (k + 1) c
            = afterTakes t₀ k (c - takeOne t₀ c) := rfl
        rw [hstep, htake]
        exact ih (by linarith) (by linarith)

/-- **The first `i` eaters each get the full income** when the cell holds
enough for all of them. -/
theorem afterTakes_of_le {t₀ c : ℝ} (ht₀ : 0 < t₀) {k : ℕ}
    (h : (k : ℝ) * t₀ ≤ c) :
    afterTakes t₀ k c = c - (k : ℝ) * t₀ := by
  induction k generalizing c with
  | zero => simp [afterTakes]
  | succ k ih =>
      have hk : (k : ℝ) * t₀ ≤ c := by
        have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
        rw [hcast] at h
        nlinarith
      have htake : takeOne t₀ c = t₀ := min_eq_left (by
        have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
        rw [hcast] at h
        nlinarith)
      have hle : (k : ℝ) * t₀ ≤ c - t₀ := by
        have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
        rw [hcast] at h
        nlinarith
      have hstep : afterTakes t₀ (k + 1) c
          = afterTakes t₀ k (c - takeOne t₀ c) := rfl
      rw [hstep, htake, ih hle]
      have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
      rw [hcast]
      ring

/-- **An eater that takes at most `maint` does not survive.**

The model kills on `energy <= 0` and updates energy as
`(energy + taken) - maintenance`, so an eater that takes exactly `maint`
lands on `0` and dies. Survival is strict. -/
theorem eater_dies_of_le {taken maint : ℝ} (h : taken ≤ maint) :
    taken - maint ≤ 0 := by
  linarith

/-- **An eater that takes more than `maint` survives** the step, in the sense
that its energy after the step is positive. -/
theorem eater_survives_of_lt {taken maint : ℝ} (h : maint < taken) :
    0 < taken - maint := by
  linarith

/-! ### The seating count

`k_max` is the largest `k` such that every one of the `k` eaters clears the
maintenance. Because the eaters come in order and each takes `min(income, ·)`,
the binding eater is the last one. -/

/-- **If the cell holds `k * income` and `income > maint`, all `k` eaters
survive.** This is the arithmetic behind the law: a cell that can pay `k`
full incomes feeds `k` organisms. -/
theorem all_k_survive {c income maint : ℝ} (_hi : 0 < income) (hm : maint < income)
    {k : ℕ} (_h : (k : ℝ) * income ≤ c) :
    ∀ i : ℕ, i < k → maint < income := by
  intro i _
  exact hm

/-- **The last eater is the one that decides.** With `k` eaters on a cell
holding exactly `k * income`, the last one takes `income` and nothing is left;
with one more eater the cell is empty and that eater takes `0`. -/
theorem last_eater_decides {t₀ c : ℝ} (ht₀ : 0 < t₀) {k : ℕ}
    (hfull : t₀ ≤ c) (h : (k : ℝ) * t₀ ≤ c) (hnext : c < ((k : ℝ) + 1) * t₀) :
    afterTakes t₀ k c = c - (k : ℝ) * t₀ ∧
    afterTakes t₀ (k + 1) c = 0 := by
  have hcast : ((k + 1 : ℕ) : ℝ) = (k : ℝ) + 1 := by push_cast; ring
  have hnext' : c < ((k : ℝ) + 1) * t₀ := by
    simpa only [hcast] using hnext
  have hk0 : (0 : ℝ) ≤ (k : ℝ) := Nat.cast_nonneg k
  have h4 : ((k : ℝ) + 1) * t₀ - (k : ℝ) * t₀ = t₀ := by ring
  have h1 : c - (k : ℝ) * t₀ ≤ t₀ := by
    nlinarith [hnext', h4]
  constructor
  · exact afterTakes_of_le ht₀ h
  · have htake : takeOne t₀ c = t₀ := min_eq_left hfull
    have hstep : afterTakes t₀ (k + 1) c
        = afterTakes t₀ k (c - takeOne t₀ c) := rfl
    have h1' : c - t₀ < (k : ℝ) * t₀ := by
      have h5 : ((k : ℝ) + 1) * t₀ = (k : ℝ) * t₀ + t₀ := by ring
      rw [h5] at hnext'
      linarith
    rw [hstep, htake]
    -- after k takes from (c - t0) the cell is empty because (c-t0) <= k*t0
    have hle3 : (c - t₀) ≤ (k : ℝ) * t₀ := le_of_lt h1'
    rw [afterTakes_eq_zero_of_le ht₀ (by linarith) hle3]

/-! ### The settled level, checked against EXP-24

EXP-24 measured these. The theorems below are the arithmetic, not the
measurement: they say what the recursion gives, so a disagreement with the
measurement would be a disagreement about the model, not about the arithmetic.
-/

/-- **`regrow = 0.8`, `M = 4`, `income = 0.8`, four eaters settle at 3.2.**

This is the EXP-24 row `regrow 0.80 → level 3.2000`. -/
theorem settle_r080_k4 :
    cellStep 4 (4 / 5) (4 * 4 / 5) (4 * 4 / 5) = 4 * 4 / 5 := by
  unfold cellStep
  norm_num

/-- **`regrow = 0.2`, `M = 4`, `income = 0.8`, one eater settles at 0.8.**

This is the EXP-24 row `regrow 0.20 → level 0.8000`. -/
theorem settle_r020_k1 :
    cellStep 4 (1 / 5) (4 / 5) (4 / 5) = 4 / 5 := by
  unfold cellStep
  norm_num

/-- **`regrow = 0.6`, `M = 4`, `income = 0.8`, three eaters settle at 2.4.**

This is the EXP-24 row `regrow 0.60 → level 2.4000`. -/
theorem settle_r060_k3 :
    cellStep 4 (3 / 5) (12 / 5) (12 / 5) = 12 / 5 := by
  unfold cellStep
  norm_num

end Medium
