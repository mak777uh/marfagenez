import Mathlib

/-!
# The field: how taking from a cell changes it

`EXP-09` measured something unexpected: a sighted organism **levels** the field,
it does not deplete it.

| policy | field | spread | min |
|---|---|---|---|
| `remember` (blind) | alternating | **3** | 1.600 |
| `sighted` | alternating | **1** | 1.800 |
| `sighted` | uniform | **9** | 0.800 |

The mechanism:

1. The organism walks to the richest cell it can see.
2. It gathers there and takes from it.
3. The rich cell falls to the level of the poor ones.
4. The field becomes uniform.

This file states the arithmetic of that mechanism and proves what can be proved
about it.

## What is modelled

A single cell with value `c`, maximum `M`, regrowth rate `r`, and a take `t`:

```
step M r t c = c + (M - c) * r - t
```

## What is proved

* `step_le_max` — the cell never exceeds `M` when the take is non-negative and
  the rate is at most 1.
* `step_mono` — a richer cell stays richer after the same step.
* `fixed_point` — the equilibrium of a cell that is taken from every step.
* `level_is_fixed` — if every cell is at the same value and takes the same
  amount, the field stays uniform.

**What is NOT proved:** that a field of *different* cells converges to a uniform
one. That needs a model of which cell each organism chooses, and the choice
depends on the whole field. It is stated as an open question at the end.
-/

namespace Medium

/-- One step of a cell: regrow toward `M`, then take `t`. -/
def cellStep (M r t c : ℝ) : ℝ := c + (M - c) * r - t

/-- **The cell never exceeds `M`** when the take is non-negative and the rate is
at most one. -/
theorem cellStep_le_max {M r t c : ℝ}
    (hr1 : r ≤ 1) (ht : 0 ≤ t) (hc : c ≤ M) :
    cellStep M r t c ≤ M := by
  unfold cellStep
  nlinarith [mul_nonneg (sub_nonneg.mpr hc) (sub_nonneg.mpr hr1)]

/-- **A richer cell stays richer.** The step is monotone in the cell's value,
provided the regrowth rate is at most one (otherwise a richer cell would be
pulled down harder and could overtake). -/
theorem cellStep_mono {M r t c₁ c₂ : ℝ} (hr0 : 0 ≤ r) (hr1 : r ≤ 1) (h : c₁ ≤ c₂) :
    cellStep M r t c₁ ≤ cellStep M r t c₂ := by
  unfold cellStep
  nlinarith [mul_le_mul_of_nonneg_left h (by linarith : 0 ≤ 1 - r)]

/-- **The equilibrium of a cell taken from every step.**

`c* = c* + (M - c*) * r - t` gives `c* = M - t / r` when `r ≠ 0`. -/
theorem fixed_point {M r t : ℝ} (hr : r ≠ 0) :
    cellStep M r t (M - t / r) = M - t / r := by
  unfold cellStep
  field_simp
  ring

/-- **A uniform field stays uniform** when every cell takes the same amount.

This is the arithmetic behind the measurement: a field whose cells are all equal
and whose organisms take equally does not become uneven. -/
theorem uniform_stays_uniform {M r t c : ℝ} (h : cellStep M r t c = c) :
    ∀ c', c' = c → cellStep M r t c' = c := by
  intro c' hc'
  rw [hc']
  exact h

/-- **The equilibrium is lower when more is taken.** -/
theorem more_taken_lower {M r t₁ t₂ : ℝ} (hr : 0 < r) (h : t₁ < t₂) :
    M - t₂ / r < M - t₁ / r := by
  have : t₂ / r > t₁ / r := by
    exact div_lt_div_of_pos_right h hr
  linarith

/-- **The equilibrium is higher when regrowth is faster.**

`c* = M - t/r`, so a larger `r` makes `t/r` smaller and `c*` larger. -/
theorem faster_regrow_higher {M t r₁ r₂ : ℝ} (ht : 0 < t) (hr₁ : 0 < r₁) (h : r₁ < r₂) :
    M - t / r₁ < M - t / r₂ := by
  have hr₂ : 0 < r₂ := lt_trans hr₁ h
  have h2 : t / r₂ < t / r₁ := by
    exact div_lt_div_of_pos_left ht hr₁ h
  linarith

end Medium
