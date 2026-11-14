import Medium.Capacity

/-!
# The settled level of a cell

`Field::regrow_all` moves a cell by `c ← c + (M - c) * r` once per step,
after every organism on the cell has taken. So one step of a cell that
holds `k` organisms, each taking `t`, is

    L' = (L - min(k*t, L)) + (M - (L - min(k*t, L))) * r

This file proves the fixed point of that map, which is the law EXP-94
measured on 21 arms with no mismatch.

The two branches are separate theorems because they are separate worlds:
in the first the cell is not emptied, in the second it is.
-/

namespace Medium

open Real

/-- One step of a cell that holds organisms taking `taken` in total.
`taken` is already clamped to what the cell had, which is what
`Field::take` does (`cells[cell].min(amount)`). -/
noncomputable def cellStepWith (M r taken L : ℝ) : ℝ :=
  (L - min taken L) + (M - (L - min taken L)) * r

/-- `cellStep` from `Field.lean` is the one-organism case of this. -/
theorem cellStepWith_one (M r t L : ℝ) (h : t ≤ L) :
    cellStepWith M r t L = cellStep M r t L := by
  unfold cellStepWith cellStep
  rw [min_eq_left h]

/-- The cell is not emptied: `taken ≤ L`. Then the step is affine and the
fixed point is `M - taken*(1-r)/r`. -/
theorem cellStepWith_fixed (M r taken : ℝ) (hr : r ≠ 0) (hL : taken ≤ M - taken * (1 - r) / r) :
    cellStepWith M r taken (M - taken * (1 - r) / r) = M - taken * (1 - r) / r := by
  unfold cellStepWith
  rw [min_eq_left hL]
  field_simp
  ring

/-- The cell is emptied: `taken ≥ M*r`. Then the step takes the cell to
`M*r` and leaves it there. This is the second branch of the law. -/
theorem cellStepWith_emptied (M r taken : ℝ) (hL : M * r ≤ taken) :
    cellStepWith M r taken (M * r) = M * r := by
  unfold cellStepWith
  rw [min_eq_right hL]
  ring

/-- The emptied branch is stable: if the cell is at `M*r` and the organisms
take at least `M*r`, the cell stays at `M*r`. -/
theorem emptied_is_stable (M r taken : ℝ) (hL : M * r ≤ taken) :
    cellStepWith M r taken (M * r) = M * r := by
  exact cellStepWith_emptied M r taken hL

/-!
## The fixed point, stated against `cellLevel`

`cellLevel` (`Capacity.lean`) is what a cell settles at. The two theorems
below say it is a fixed point of `cellStepWith`, branch by branch: the same
content as `cellStepWith_fixed` and `cellStepWith_emptied`, but stated so the
law and the fixed point are visibly one object.
-/

/-- **The unsaturated branch is a fixed point.**  While `k*t ≤ M*r` the cell
settles at `M - k*t*(1-r)/r` and stays there. -/
theorem cellLevel_fixed_unsaturated {M r k t : ℝ} (hr0 : 0 < r) (hr1 : r ≤ 1)
    (hM : 0 ≤ M) (h : k * t ≤ M * r) :
    cellStepWith M r (k * t) (cellLevel M r k t) = cellLevel M r k t := by
  -- The draw clears the cell's own level, which is what `cellStepWith_fixed`
  -- needs as its hypothesis. `linarith` cannot see this through the
  -- subtraction, so the inequality is normalised by hand first.
  have hL : k * t ≤ M - k * t * (1 - r) / r := by
    rw [le_sub_iff_add_le]
    have hk : k * t + k * t * (1 - r) / r = k * t / r := by
      field_simp
      ring
    rw [hk]
    have h1 : k * t * r ≤ M * r * r := mul_le_mul_of_nonneg_right h hr0.le
    have h2 : M * r * r ≤ M * r := by
      nlinarith [mul_nonneg hM hr0.le, mul_nonneg (mul_nonneg hM hr0.le) hr0.le]
    have hMr : 0 ≤ M * r := mul_nonneg hM hr0.le
    rw [div_le_iff₀ hr0]
    nlinarith
  have hcl : cellLevel M r k t = M - k * t * (1 - r) / r := by
    have hMr : M * r ≤ M - k * t * (1 - r) / r := by
      have hgap : M - k * t * (1 - r) / r - M * r = (M - k * t / r) * (1 - r) := by
        have hk : k * t * (1 - r) / r = k * t / r * (1 - r) := by field_simp
        rw [hk]; ring
      have h3 : k * t / r ≤ M := by
        rw [div_le_iff₀ hr0]; nlinarith
      have h4 : 0 ≤ M - k * t / r := by linarith
      have h6 : 0 ≤ (M - k * t / r) * (1 - r) := mul_nonneg h4 (by linarith)
      linarith
    unfold cellLevel
    exact max_eq_left hMr
  rw [hcl]
  exact cellStepWith_fixed M r (k * t) (ne_of_gt hr0) hL

/-- **The saturated branch is a fixed point.**  Once `M*r ≤ k*t` the cell is
emptied of the draw and sits at `M*r`. -/
theorem cellLevel_fixed_saturated {M r k t : ℝ} (hr0 : 0 < r) (hr1 : r ≤ 1)
    (h : M * r ≤ k * t) :
    cellStepWith M r (k * t) (cellLevel M r k t) = cellLevel M r k t := by
  have hgap : M - k * t * (1 - r) / r - M * r = (M - k * t / r) * (1 - r) := by
    have hk : k * t * (1 - r) / r = k * t / r * (1 - r) := by field_simp
    rw [hk]; ring
  have h3 : M ≤ k * t / r := by
    rw [le_div_iff₀ hr0]; nlinarith
  have h4 : M - k * t / r ≤ 0 := by linarith
  have h6 : (M - k * t / r) * (1 - r) ≤ 0 := mul_nonpos_of_nonpos_of_nonneg h4 (by linarith)
  have h2 : M - k * t * (1 - r) / r ≤ M * r := by linarith
  have hcl : cellLevel M r k t = M * r := by
    unfold cellLevel
    rw [max_eq_right h2]
  rw [hcl]
  exact cellStepWith_emptied M r (k * t) h


end Medium
