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
step M r t c = (c - t) + (M - (c - t)) * r
```

The take happens first, then the cell regrows toward `M`. Its equilibrium is
`M - t*(1-r)/r`, which for `M = 2`, `r = 0.8`, `t = 1.0` is **1.75** - the value
the field actually settles at with one organism per cell (EXP-59).

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

/-- One step of a cell.

**The order matters.** The model takes first and regrows after:

1. the organisms take `t` from the cell: `c - t`
2. the field regrows toward `M`: `(c - t) + (M - (c - t)) * r`

An earlier version of this file wrote `c + (M - c) * r - t`, which regrows from
the full cell and then subtracts the take. That is a different model, and its
equilibrium is `M - t/r` instead of `M - t*(1-r)/r`. The measurement settled it:
at `M = 2`, `r = 0.8`, `t = 1.0` the field settles at **1.75**, which the second
form gives and the first does not. See `docs/FINDING-correct-equilibrium.md`. -/
def cellStep (M r t c : ℝ) : ℝ := (c - t) + (M - (c - t)) * r

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

`c* = (c* - t) + (M - (c* - t)) * r` gives `c* = M - t*(1-r)/r` when `r ≠ 0`. -/
theorem fixed_point {M r t : ℝ} (hr : r ≠ 0) :
    cellStep M r t (M - t * (1 - r) / r) = M - t * (1 - r) / r := by
  unfold cellStep
  field_simp
  ring

/-- **The field settles at 1.75**, not at `M*r = 1.6`.

This is the number EXP-59 measured directly: with one organism per cell,
`M = 2`, `r = 0.8`, `income = 1.0`, the cell value settles at **1.75**.

The difference `1.75 - 1.6 = 0.15` is the margin that decides whether a second
organism can live on the same cell. It gets `1.75 - 1.0 = 0.75`, and its net after
`need`, `move_cost` and damage is `+0.09`; on a cell that has fallen back to
`M*r = 1.6` it gets `0.6` and its net is `-0.06`. That is why the field holds
about 48 organisms and not `cells * k_max = 80`.
See `docs/FINDING-capacity-is-about-48.md`. -/
theorem settles_at_one_point_seven_five :
    cellStep 2 (4 / 5) 1 (7 / 4) = 7 / 4 := by
  unfold cellStep
  norm_num

/-- **A uniform field stays uniform** when every cell takes the same amount.

This is the arithmetic behind the measurement: a field whose cells are all equal
and whose organisms take equally does not become uneven. -/
theorem uniform_stays_uniform {M r t c : ℝ} (h : cellStep M r t c = c) :
    ∀ c', c' = c → cellStep M r t c' = c := by
  intro c' hc'
  rw [hc']
  exact h

/-- **The equilibrium is lower when more is taken.**

`c* = M - t*(1-r)/r`, so a larger take makes `c*` smaller. -/
theorem more_taken_lower {M r t₁ t₂ : ℝ} (hr : 0 < r) (hr1 : r < 1) (h : t₁ < t₂) :
    M - t₂ * (1 - r) / r < M - t₁ * (1 - r) / r := by
  have hpos : 0 < 1 - r := by linarith
  have hm : t₁ * (1 - r) < t₂ * (1 - r) := mul_lt_mul_of_pos_right h hpos
  have h2 : t₁ * (1 - r) / r < t₂ * (1 - r) / r :=
    div_lt_div_of_pos_right hm hr
  have e1 : M - t₁ * (1 - r) / r - (M - t₂ * (1 - r) / r)
      = t₂ * (1 - r) / r - t₁ * (1 - r) / r := by ring
  have h4 : 0 < M - t₁ * (1 - r) / r - (M - t₂ * (1 - r) / r) := by
    rw [e1]; linarith
  linarith

/-- **The equilibrium is higher when regrowth is faster.**

`c* = M - t*(1-r)/r = M - t/r + t`, so a larger `r` makes `t/r` smaller and
`c*` larger. -/
theorem faster_regrow_higher {M t r₁ r₂ : ℝ} (ht : 0 < t) (hr₁ : 0 < r₁) (h : r₁ < r₂) :
    M - t * (1 - r₁) / r₁ < M - t * (1 - r₂) / r₂ := by
  have hr₂ : 0 < r₂ := lt_trans hr₁ h
  have h2 : t / r₂ < t / r₁ := div_lt_div_of_pos_left ht hr₁ h
  have e1 : M - t * (1 - r₁) / r₁ = M - t / r₁ + t := by
    field_simp
    ring
  have e2 : M - t * (1 - r₂) / r₂ = M - t / r₂ + t := by
    field_simp
    ring
  rw [e1, e2]
  linarith

end Medium
