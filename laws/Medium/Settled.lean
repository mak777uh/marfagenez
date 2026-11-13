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
  rw [min_eq_right hL]
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

/-- The law, in the form EXP-94 tested: for `k` organisms taking `t` each,
the settled level is `M - k*t*(1-r)/r` while `k*t ≤ M*r`, and `M*r`
after that. -/
theorem settled_level (M r t : ℝ) (k : ℕ) (hr : r ≠ 0) (hr1 : r ≤ 1) (ht : 0 ≤ t) :
    (k * t ≤ M * r →
      cellStepWith M r (k * t) (M - k * t * (1 - r) / r) = M - k * t * (1 - r) / r) ∧
    (M * r ≤ k * t → cellStepWith M r (k * t) (M * r) = M * r) := by
  constructor
  · intro h
    have hkt : (0:ℝ) ≤ (k:ℝ) * t := by
      have : (0:ℝ) ≤ (k:ℝ) := by exact_mod_cast Nat.zero_le k
      exact mul_nonneg this ht
    have hL : (k:ℝ) * t ≤ M - (k:ℝ) * t * (1 - r) / r := by
      have hnonneg : (0:ℝ) ≤ (k:ℝ) * t * (1 - r) / r := by
        apply div_nonneg
        · nlinarith
        · linarith
      linarith
    exact cellStepWith_fixed M r ((k:ℝ) * t) hr hL
  · intro h
    exact emptied_is_stable M r ((k:ℝ) * t) h

end Medium
