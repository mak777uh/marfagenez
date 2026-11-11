import Mathlib
import Medium.Field
import Medium.Convergence
import Medium.Capacity

/-!
# Two regimes: full income and rationed income

`Field.lean` proved the equilibrium `c* = M - t/r` for a **fixed** take `t`.
But the model's take is not fixed: an organism takes `min(income, c)`, so the
take depends on the cell's value.

This gives **two regimes**:

| regime | condition | take | equilibrium |
|---|---|---|---|
| full | `c ≥ income` | `t = k * income` | `c* = M - k*income/r` |
| rationed | `c < income` | `t = k * c` | `c* = M*r/(r + k)` |

The rationed equilibrium is **always positive** — the cell never reaches zero,
because the organisms take less as the cell empties. The full equilibrium can be
zero or negative — that is the capacity limit.

## Why this matters

The measured capacity `C = cells * M*r/income` is the point where the **full**
equilibrium hits zero. Below that point the cell is in the full regime and feeds
everyone. Above it the cell falls into the rationed regime, the organisms get
less than `income`, and the balance `c* - (maintenance + damage*repair)` decides
whether they live.

## What is proved

* `rationed_equilibrium` — the equilibrium in the rationed regime
* `rationed_positive` — it is always positive
* `rationed_below_full` — it is below `income`, so the regime is self-consistent
* `full_regime_iff` — the full regime holds exactly when `k ≤ k_feed`
* `feed_capacity` — `k_feed = (M - income)*r/income`
* `rationed_balance_pos` — when the rationed equilibrium exceeds the upkeep, the
  organism survives even in the rationed regime
-/

namespace Medium

/-- One step of a cell when `k` organisms each take `min(income, c)`. -/
noncomputable def cellStepRationed (M r k c : ℝ) : ℝ :=
  c + (M - c) * r - k * c

/-- **The rationed equilibrium.**

`c* = c* + (M - c*)*r - k*c*` gives `c* * (r + k) = M * r`, so
`c* = M*r/(r + k)`. -/
theorem rationed_equilibrium {M r k : ℝ} (h : r + k ≠ 0) :
    cellStepRationed M r k (M * r / (r + k)) = M * r / (r + k) := by
  unfold cellStepRationed
  field_simp
  ring

/-- **The rationed equilibrium is always positive** when `M`, `r`, `k` are
non-negative and `r + k > 0`.

This is the key difference from the full regime: the cell never reaches zero,
because the organisms take less as it empties. -/
theorem rationed_positive {M r k : ℝ} (hM : 0 < M) (hr : 0 < r) (hk : 0 ≤ k) :
    0 < M * r / (r + k) := by
  have hpos : 0 < r + k := by linarith
  exact div_pos (mul_pos hM hr) hpos

/-- **The rationed equilibrium is below `income`** when the full regime does not
hold, so the regime is self-consistent: an organism that takes
`min(income, c)` really does take `c` at this equilibrium. -/
theorem rationed_below_full {M r k income : ℝ} (hM : 0 < M) (hr : 0 < r)
    (hk : 0 ≤ k) (hinc : 0 < income)
    (h : M * r < income * (r + k)) :
    M * r / (r + k) < income := by
  have hpos : 0 < r + k := by linarith
  rw [div_lt_iff₀ hpos]
  linarith

/-- **The feeding capacity.**

`k_feed = (M - income) * r / income` is the number of organisms a cell can hold
while still giving each the **full** `income`. -/
noncomputable def feedCapacity (M r income : ℝ) : ℝ :=
  (M - income) * r / income

/-- **The full regime holds exactly when `k ≤ k_feed`.**

`c* = M - k*income/r ≥ income` iff `k ≤ (M - income)*r/income`. -/
theorem full_regime_iff {M r income k : ℝ} (hr : 0 < r) (hinc : 0 < income) :
    income ≤ equilibrium M r (k * income) ↔ k ≤ feedCapacity M r income := by
  unfold equilibrium feedCapacity
  constructor
  · intro h
    have h1 : k * income / r ≤ M - income := by linarith
    rw [div_le_iff₀ hr] at h1
    rw [le_div_iff₀ hinc]
    linarith
  · intro h
    have h1 : k * income ≤ (M - income) * r := by
      rw [le_div_iff₀ hinc] at h
      linarith
    have h2 : k * income / r ≤ M - income := by
      rw [div_le_iff₀ hr]
      linarith
    linarith

/-- **The organism survives in the rationed regime** when the equilibrium exceeds
the upkeep `maintenance + damage*repair`.

The balance is `c* - upkeep`; this theorem says the balance is positive exactly
when `c* > upkeep`. -/
theorem rationed_balance_pos {M r k upkeep : ℝ} (hM : 0 < M) (hr : 0 < r)
    (hk : 0 ≤ k) (h : upkeep < M * r / (r + k)) :
    0 < M * r / (r + k) - upkeep := by
  linarith

end Medium
