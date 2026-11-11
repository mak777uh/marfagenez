import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# Carrying capacity: how many organisms a cell can hold

The experiments measured a formula:

| `M` | `k_max` | predicted `C` | measured `C` |
|---|---|---|---|
| 2.0 | 2 | 80 | **80** |
| 1.0 | 1 | 40 | **40** |
| 4.0 | 4 | 160 | **160** |

with `C = cells * k_max` and `k_max = M * r / income`.

This file proves the arithmetic behind `k_max`: it is exactly the condition
under which the cell's equilibrium is non-negative.

## What is proved

* `equilibrium_nonneg_iff` — `0 ≤ c*` exactly when `t ≤ M * r`
* `capacity` — the number of organisms a cell can hold, `k_max = M * r / t₀`
* `capacity_iff` — `k ≤ k_max` exactly when the equilibrium is non-negative
* `capacity_mono_M` — a richer cell holds more
* `capacity_mono_r` — a faster regrowth holds more
* `capacity_anti_income` — a bigger take holds less

## What is NOT proved

That the population actually reaches `C = cells * k_max`. That needs a model of
movement and of who stands where; the experiments measure it, this file does not
prove it. The gap is stated at the end.
-/

namespace Medium

/-- **The equilibrium is non-negative exactly when the take is at most `M * r`.**

`c* = M - t/r`, so `0 ≤ c*` iff `t/r ≤ M` iff `t ≤ M * r`. -/
theorem equilibrium_nonneg_iff {M r t : ℝ} (hr : 0 < r) :
    0 ≤ equilibrium M r t ↔ t ≤ M * r := by
  unfold equilibrium
  constructor
  · intro h
    have : t / r ≤ M := by linarith
    rwa [div_le_iff₀ hr] at this
  · intro h
    have h2 : t / r ≤ M := by
      rw [div_le_iff₀ hr]
      linarith
    linarith

/-- **The carrying capacity of one cell.**

`k_max = M * r / t₀`, where `t₀` is what one organism takes per step. -/
noncomputable def capacity (M r t₀ : ℝ) : ℝ := M * r / t₀

/-- **A cell holds `k` organisms exactly when the equilibrium is non-negative.**

This is the arithmetic behind the measured capacity. -/
theorem capacity_iff {M r t₀ : ℝ} (hr : 0 < r) (ht₀ : 0 < t₀) (k : ℝ) :
    0 ≤ equilibrium M r (k * t₀) ↔ k ≤ capacity M r t₀ := by
  rw [equilibrium_nonneg_iff hr]
  unfold capacity
  rw [le_div_iff₀ ht₀]

/-- **A richer cell holds more.** -/
theorem capacity_mono_M {M₁ M₂ r t₀ : ℝ} (hr : 0 < r) (ht₀ : 0 < t₀) (h : M₁ ≤ M₂) :
    capacity M₁ r t₀ ≤ capacity M₂ r t₀ := by
  unfold capacity
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **Faster regrowth holds more.** -/
theorem capacity_mono_r {M r₁ r₂ t₀ : ℝ} (hM : 0 < M) (h : r₁ ≤ r₂)
    (ht₀ : 0 < t₀) :
    capacity M r₁ t₀ ≤ capacity M r₂ t₀ := by
  unfold capacity
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **A bigger take holds less.** -/
theorem capacity_anti_income {M r t₁ t₂ : ℝ} (hM : 0 < M) (hr : 0 < r)
    (ht₁ : 0 < t₁) (h : t₁ ≤ t₂) :
    capacity M r t₂ ≤ capacity M r t₁ := by
  unfold capacity
  have hpos : 0 < M * r := mul_pos hM hr
  exact div_le_div_of_nonneg_left (le_of_lt hpos) ht₁ h

/-- **The total capacity of a field.** -/
noncomputable def totalCapacity (cells : ℕ) (M r t₀ : ℝ) : ℝ :=
  (cells : ℝ) * capacity M r t₀

/-- **The total capacity is the number of cells times the per-cell capacity.** -/
theorem totalCapacity_eq (cells : ℕ) (M r t₀ : ℝ) :
    totalCapacity cells M r t₀ = (cells : ℝ) * (M * r / t₀) := by
  unfold totalCapacity capacity
  rfl

/-- **A cell that holds one organism gains nothing from a second place.**

When `capacity M r t₀ ≤ 1`, the number of organisms a cell can hold is at most
one, so movement cannot find a second place. This is the arithmetic behind the
`M = 1.0` measurement, where movement made no difference. -/
theorem no_second_place {M r t₀ : ℝ} (hr : 0 < r) (ht₀ : 0 < t₀)
    (h : capacity M r t₀ ≤ 1) :
    ∀ k : ℝ, 1 < k → ¬ (0 ≤ equilibrium M r (k * t₀)) := by
  intro k hk hnonneg
  have hcap := (capacity_iff hr ht₀ k).mp hnonneg
  linarith

end Medium
