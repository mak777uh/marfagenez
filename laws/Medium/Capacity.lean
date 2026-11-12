import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# Carrying capacity: how many organisms a cell can hold

## Two different capacities — do not confuse them

* `capacity M r t₀ = M*r / t₀` — **feeding** capacity: how many full portions of
  `t₀` the regrowth puts back per step. This is a fact about the field alone.
* `M*r / (t₀*(1-r))` — **survival** capacity: how many organisms can stand on a
  cell without the cell's equilibrium falling below `t₀`. It is larger by the
  factor `1/(1-r)`, because a cell that is eaten from recovers only `r` of the
  gap per step.

The experiments measure the **feeding** one: `C = 80` at 40 cells with
`k_feed = 2` (`results/overcrowding/run-2026-11-11T22-20-40.json`).

## The mistake this file used to make

The first version of this file said `k_max = M*r / (t₀*(1-r))` and justified it
by "the equilibrium stays non-negative when all `k` organisms take `t₀` each".
That is algebraically true, but it is **not this model**. See
`docs/FINDING-crowding-is-two.md`.

## What the model actually does

`Field::take` hands out `min(cell, income)` to the **first** organism in the
array, then the remainder to the second, and so on (`core/src/field.rs:153`).
So the take is *sequential*, not simultaneous.

Over one full cycle a cell gives up at most `M*r`: that is what the regrowth
law puts back. Therefore the number of full portions of `t₀` a cell can hand
out is

    k_feed = M*r / t₀

and it does not depend on `k`. A third organism on a cell that already feeds
two gets nothing and starves.

## What is proved

* `equilibrium_nonneg_iff` — `0 ≤ c*` exactly when `t*(1-r) ≤ M*r`
* `capacity` — `k_feed = M*r / t₀`
* `capacity_iff` — the cell's regrowth covers `k` full portions exactly when `k ≤ k_feed`
* `capacity_equals_give_back` — `k_feed * t₀ = M*r`, the whole content of the law
* `capacity_mono_M`, `capacity_mono_r`, `capacity_anti_income`
* `capacity_infinite_at_full_regrowth` — at `r = 1` no finite `k` starves the cell
* `no_second_place` — when `k_feed ≤ 1`, a second organism cannot be supported

## What is NOT proved

That the population actually reaches `cells * k_feed`. That needs a model of
movement and of who stands where; the experiments measure it, this file does not
prove it. The measurement gives `C = 80` at 40 cells with `k_feed = 2`
(`results/overcrowding/run-2026-11-11T22-20-40.json`).
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

`k_feed = M*r / t₀`, where `t₀` is what one organism takes per step. The cell
gives back `M*r` per cycle, so it can hand out that many full portions. -/
noncomputable def capacity (M r t₀ : ℝ) : ℝ := M * r / t₀

/-- **The law in one line: `k` portions of `t₀` exactly exhaust the regrowth.** -/
theorem capacity_equals_give_back {M r t₀ : ℝ} (ht₀ : t₀ ≠ 0) :
    capacity M r t₀ * t₀ = M * r := by
  unfold capacity
  field_simp

/-- **A cell feeds `k` organisms exactly when its regrowth covers `k` portions.** -/
theorem capacity_iff {M r t₀ : ℝ} (ht₀ : 0 < t₀) (k : ℝ) :
    k * t₀ ≤ M * r ↔ k ≤ capacity M r t₀ := by
  unfold capacity
  rw [le_div_iff₀ ht₀]

/-- **A richer cell holds more.** -/
theorem capacity_mono_M {M₁ M₂ r t₀ : ℝ} (hr : 0 ≤ r) (ht₀ : 0 < t₀)
    (h : M₁ ≤ M₂) :
    capacity M₁ r t₀ ≤ capacity M₂ r t₀ := by
  unfold capacity
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **Faster regrowth holds more.** -/
theorem capacity_mono_r {M r₁ r₂ t₀ : ℝ} (hM : 0 < M)
    (ht₀ : 0 < t₀) (h : r₁ ≤ r₂) :
    capacity M r₁ t₀ ≤ capacity M r₂ t₀ := by
  unfold capacity
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **A bigger take holds less.** -/
theorem capacity_anti_income {M r t₁ t₂ : ℝ} (hM : 0 < M) (hr : 0 < r)
    (ht₁ : 0 < t₁) (h : t₁ ≤ t₂) :
    capacity M r t₂ ≤ capacity M r t₁ := by
  unfold capacity
  have hMr : 0 < M * r := mul_pos hM hr
  exact div_le_div_of_nonneg_left (le_of_lt hMr) ht₁ (by linarith)

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
theorem no_second_place {M r t₀ : ℝ} (ht₀ : 0 < t₀) (h : capacity M r t₀ ≤ 1) :
    ∀ k : ℝ, 1 < k → ¬ (k * t₀ ≤ M * r) := by
  intro k hk hcover
  have hk_le : k ≤ capacity M r t₀ := (capacity_iff ht₀ k).mp hcover
  linarith

end Medium
