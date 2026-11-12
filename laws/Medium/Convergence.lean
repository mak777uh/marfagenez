import Mathlib
import Medium.Field

/-!
# The field: convergence to equilibrium

`Field.lean` proved the equilibrium `c* = M - t*(1-r)/r`. This file proves that the
step **moves the cell toward** that equilibrium and never past it.

## Why this and not "the spread shrinks"

The measurement in `EXP-09` suggested that a sighted organism levels the field.
The natural theorem would be "the spread of the field shrinks monotonically".

**That theorem is false.** Two cells with the same `M` and `r` but different
takes cross over:

| step | rich (taken from) | poor (not taken) | spread |
|---|---|---|---|
| 0 | 2.000 | 0.200 | 1.800 |
| 1 | 1.840 | 1.640 | 0.200 |
| 2 | 1.808 | 1.928 | **−0.120** |

The rich cell falls, the poor cell rises, and after two steps the poor cell is
richer. The spread changes sign, so its absolute value does not shrink
monotonically.

What *is* true, and what this file proves, is the local statement: from either
side, the step moves the cell toward `c*` and does not overshoot it.

## What is proved

* `step_lt_self` — above the equilibrium, the step decreases the cell
* `step_gt_self` — below the equilibrium, the step increases the cell
* `step_at_equilibrium` — at the equilibrium, the step leaves the cell alone
* `step_approaches` — the gap to the equilibrium is multiplied by `(1-r)`
* `gap_shrinks` — the absolute gap shrinks by `(1-r)`
* `gap_strictly_shrinks` — and strictly, unless already at equilibrium

## What is NOT proved

That a *field* of many cells converges to a uniform one. The cells interact only
through which organism stands where, and that is a different model.
-/

namespace Medium

/-- The equilibrium of a cell taken from every step.

The model takes first and regrows after, so the fixed point is
`M - t*(1-r)/r`, not `M - t/r`. See `docs/FINDING-correct-equilibrium.md`. -/
noncomputable def equilibrium (M r t : ℝ) : ℝ := M + t - t / r

/-- **Above the equilibrium, the step decreases the cell.**

`cellStep - c = (M - c + t) * r - t`, which is negative exactly when
`c > M + t - t/r`. -/
theorem step_lt_self {M r t c : ℝ} (hr : 0 < r) (h : equilibrium M r t < c) :
    cellStep M r t c < c := by
  unfold cellStep equilibrium at *
  -- c* = M + t - t/r, so c > c* gives (M - c + t) * r < t.
  have h1 : (M - c + t) * r < t := by
    have h2 : M + t - t / r < c := h
    have h3 : M + t - c < t / r := by linarith
    rw [lt_div_iff₀ hr] at h3
    linarith
  -- cellStep - c = (M - c + t) * r - t < 0
  have hd : (c - t) + (M - (c - t)) * r - c = (M - c + t) * r - t := by ring
  linarith

/-- **Below the equilibrium, the step increases the cell.** -/
theorem step_gt_self {M r t c : ℝ} (hr : 0 < r) (h : c < equilibrium M r t) :
    c < cellStep M r t c := by
  unfold cellStep equilibrium at *
  have h1 : t < (M - c + t) * r := by
    have h2 : c < M + t - t / r := h
    have h3 : t / r < M + t - c := by linarith
    rw [div_lt_iff₀ hr] at h3
    linarith
  have hd : (c - t) + (M - (c - t)) * r - c = (M - c + t) * r - t := by ring
  linarith

/-- **At the equilibrium, the step leaves the cell alone.** -/
theorem step_at_equilibrium {M r t : ℝ} (hr : r ≠ 0) :
    cellStep M r t (equilibrium M r t) = equilibrium M r t := by
  unfold cellStep equilibrium
  field_simp
  ring

/-- **The gap to the equilibrium is multiplied by `(1 - r)` every step.**

This is the quantitative form of "the step approaches". With `0 < r < 1` the
factor is in `(0, 1)`, so the gap goes to zero. -/
theorem step_approaches {M r t c : ℝ} (hr : r ≠ 0) :
    cellStep M r t c - equilibrium M r t = (c - equilibrium M r t) * (1 - r) := by
  unfold cellStep equilibrium
  field_simp
  ring

/-- **The absolute gap shrinks by the factor `(1 - r)`.** -/
theorem gap_shrinks {M r t c : ℝ} (hr0 : 0 < r) (hr1 : r < 1) :
    |cellStep M r t c - equilibrium M r t|
      = |c - equilibrium M r t| * (1 - r) := by
  rw [step_approaches (ne_of_gt hr0), abs_mul]
  have : |1 - r| = 1 - r := abs_of_pos (by linarith)
  rw [this]

/-- **The gap strictly shrinks** unless the cell is already at equilibrium. -/
theorem gap_strictly_shrinks {M r t c : ℝ} (hr0 : 0 < r) (hr1 : r < 1)
    (h : c ≠ equilibrium M r t) :
    |cellStep M r t c - equilibrium M r t| < |c - equilibrium M r t| := by
  rw [gap_shrinks hr0 hr1]
  have hpos : 0 < |c - equilibrium M r t| := abs_pos.mpr (sub_ne_zero.mpr h)
  nlinarith

/-- **No overshoot: from above, the cell stays above the equilibrium.**

The gap is multiplied by `1 - r`, which is non-negative when `r ≤ 1`, so the
cell cannot jump past `c*`. -/
theorem no_overshoot {M r t c : ℝ} (hr0 : 0 < r) (hr1 : r ≤ 1)
    (h : equilibrium M r t ≤ c) :
    equilibrium M r t ≤ cellStep M r t c := by
  have hgap := step_approaches (M := M) (r := r) (t := t) (c := c) (ne_of_gt hr0)
  have hnonneg : 0 ≤ (c - equilibrium M r t) * (1 - r) :=
    mul_nonneg (by linarith) (by linarith)
  linarith

end Medium
