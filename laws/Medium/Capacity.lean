import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# Carrying capacity: how many organisms a cell can hold

The equilibrium of one cell is `c* = M + t - t/r` (see `Convergence`). A cell
survives `k` organisms when the equilibrium stays non-negative:

`0 ≤ M + k*t₀ - k*t₀/r`  ⟺  `k ≤ M*r / (t₀*(1-r))`.

So the per-cell capacity is `k_max = M*r / (t₀*(1-r))` and the field holds
`cells * k_max` organisms. When `r = 1` (instant regrowth) the capacity is
infinite: whatever is taken comes back at once.

## What is proved

* `equilibrium_nonneg_iff` — `0 ≤ c*` exactly when `t*(1-r) ≤ M*r`
* `capacity` — `k_max = M*r / (t₀*(1-r))`
* `capacity_iff` — `k ≤ k_max` exactly when the equilibrium is non-negative
* `capacity_mono_M`, `capacity_mono_r`, `capacity_anti_income`
* `capacity_infinite_at_full_regrowth` — at `r = 1` no finite `k` starves the cell
* `no_second_place` — when `k_max ≤ 1`, a second organism cannot be supported

## What is NOT proved

That the population actually reaches `cells * k_max`. That needs a model of
movement and of who stands where; the experiments measure it, this file does not
prove it.
-/

namespace Medium

/-- **The equilibrium is non-negative exactly when `t*(1-r) ≤ M*r`.**

`c* = M + t - t/r = M - t*(1-r)/r`. -/
theorem equilibrium_nonneg_iff {M r t : ℝ} (hr0 : 0 < r) :
    0 ≤ equilibrium M r t ↔ t * (1 - r) ≤ M * r := by
  unfold equilibrium
  have h2 : t - t / r = -(t * (1 - r) / r) := by field_simp; ring
  constructor
  · intro h
    have h1 : t * (1 - r) / r ≤ M := by linarith
    rwa [div_le_iff₀ hr0] at h1
  · intro h
    have h1 : t * (1 - r) / r ≤ M := by
      rw [div_le_iff₀ hr0]
      linarith
    linarith

/-- **The carrying capacity of one cell.**

`k_max = M*r / (t₀*(1-r))`, where `t₀` is what one organism takes per step. -/
noncomputable def capacity (M r t₀ : ℝ) : ℝ := M * r / (t₀ * (1 - r))

/-- **A cell holds `k` organisms exactly when the equilibrium is non-negative.** -/
theorem capacity_iff {M r t₀ : ℝ} (hr0 : 0 < r) (hr1 : r < 1) (ht₀ : 0 < t₀)
    (k : ℝ) :
    0 ≤ equilibrium M r (k * t₀) ↔ k ≤ capacity M r t₀ := by
  rw [equilibrium_nonneg_iff hr0]
  unfold capacity
  have hpos : 0 < t₀ * (1 - r) := mul_pos ht₀ (by linarith)
  rw [le_div_iff₀ hpos]
  constructor <;> intro h <;> nlinarith

/-- **A richer cell holds more.** -/
theorem capacity_mono_M {M₁ M₂ r t₀ : ℝ} (hr : 0 < r) (hr1 : r < 1)
    (ht₀ : 0 < t₀) (h : M₁ ≤ M₂) :
    capacity M₁ r t₀ ≤ capacity M₂ r t₀ := by
  unfold capacity
  have hpos : 0 < t₀ * (1 - r) := mul_pos ht₀ (by linarith)
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt hpos)

/-- **Faster regrowth holds more.** -/
theorem capacity_mono_r {M r₁ r₂ t₀ : ℝ} (hM : 0 < M) (hr₁ : 0 < r₁)
    (h : r₁ ≤ r₂) (hr₂ : r₂ < 1) (ht₀ : 0 < t₀) :
    capacity M r₁ t₀ ≤ capacity M r₂ t₀ := by
  unfold capacity
  have h1 : 0 < t₀ * (1 - r₁) := mul_pos ht₀ (by linarith)
  have h2 : 0 < t₀ * (1 - r₂) := mul_pos ht₀ (by linarith)
  -- Split into two monotone steps: first the numerator, then the denominator.
  have key1 : M * r₁ / (t₀ * (1 - r₁)) ≤ M * r₂ / (t₀ * (1 - r₁)) := by
    apply div_le_div_of_nonneg_right _ (le_of_lt h1)
    nlinarith
  have key2 : M * r₂ / (t₀ * (1 - r₁)) ≤ M * r₂ / (t₀ * (1 - r₂)) := by
    apply div_le_div_of_nonneg_left _ h2
    · nlinarith
    · nlinarith
  linarith

/-- **A bigger take holds less.** -/
theorem capacity_anti_income {M r t₁ t₂ : ℝ} (hM : 0 < M) (hr : 0 < r)
    (hr1 : r < 1) (ht₁ : 0 < t₁) (h : t₁ ≤ t₂) :
    capacity M r t₂ ≤ capacity M r t₁ := by
  unfold capacity
  have hpos : 0 < 1 - r := by linarith
  have hMr : 0 < M * r := mul_pos hM hr
  have h1 : 0 < t₁ * (1 - r) := mul_pos ht₁ hpos
  have h2 : 0 < t₂ * (1 - r) := mul_pos (by linarith) hpos
  exact div_le_div_of_nonneg_left (le_of_lt hMr) h1 (by nlinarith)

/-- **At full regrowth nothing starves the cell.** -/
theorem capacity_infinite_at_full_regrowth {M t₀ k : ℝ} (hM : 0 < M) :
    0 ≤ equilibrium M 1 (k * t₀) := by
  unfold equilibrium
  norm_num
  linarith

/-- **The total capacity of a field.** -/
noncomputable def totalCapacity (cells : ℕ) (M r t₀ : ℝ) : ℝ :=
  (cells : ℝ) * capacity M r t₀

/-- **A cell that holds one organism gains nothing from a second place.**

When `capacity M r t₀ ≤ 1`, movement cannot find a second place. This is the
arithmetic behind the `M = 1.0` measurement, where movement made no difference. -/
theorem no_second_place {M r t₀ : ℝ} (hr0 : 0 < r) (hr1 : r < 1) (ht₀ : 0 < t₀)
    (h : capacity M r t₀ ≤ 1) :
    ∀ k : ℝ, 1 < k → ¬ (0 ≤ equilibrium M r (k * t₀)) := by
  intro k hk hnonneg
  have hcap := (capacity_iff hr0 hr1 ht₀ k).mp hnonneg
  linarith

end Medium
