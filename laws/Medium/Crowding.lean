/-
# The crowding law: how many organisms survive on one cell

`Capacity.lean` counts organisms by how much the cell hands out. That count
ignores two things the Rust model actually charges: `maintenance`, a fixed
per-step cost, and `damage_rate`, which the organism pays to repair itself.

This file states the law that measurement confirmed (`EXP-25`,
`results/crowding-law-law3/run-exp25.json`, 10/10 arms, all three controls):

    k_max = 1 + ⌊(M*r − maintenance − damage) / income⌋

The jump from `k` to `k+1` sits at `r = (income + maintenance + damage) / M`.

## Where the law comes from

`core/src/life.rs:429-441` runs the draws for every organism first and calls
`regrow_all()` once at the end. So on one cell the draws are **sequential with
no regrowth between them**: the cell is drained to zero and regrows from zero
to `M*r`. The step therefore starts at `c = M*r`, and the `k`-th organism gets

    take(k) = min(income, M*r − (k−1)*income).

`core/src/organism.rs:148-182` gives the per-step ledger

    net = take − maintenance − damage,

so an organism lives iff `take ≥ maintenance + damage`. Substituting the
smallest take, the `k`-th, and solving for `k` gives the law above.

## What the old count missed

The old count was `⌊M*r/income⌋`, which is the law with `maintenance = damage
= 0`. It is not a small error: at `M = 2, income = 0.8, maintenance = 0.6,
damage = 0.02` the old count jumps 1→2 at `r = 0.8` and the measured count jumps
at `r = 0.71`. `old_law_is_wrong` below is the arithmetic of that difference.
-/

import Medium.Capacity

namespace Medium

open Real

/-!
## The law as a real number, then as a count
-/

/-- The continuous version: how many organisms the cell's net budget covers. -/
noncomputable def kMaxReal (M r income maint damage : ℝ) : ℝ :=
  1 + (M * r - maint - damage) / income

/-- **The count is the floor of the real version.** -/
noncomputable def kMax (M r income maint damage : ℝ) : ℕ :=
  ⌊kMaxReal M r income maint damage⌋₊

/-- **The count is a floor: `k` organisms live exactly when `k ≤ kMax`.** -/
theorem kMax_iff {M r income maint damage : ℝ} (_hincome : 0 < income)
    (hnn : 0 ≤ kMaxReal M r income maint damage) (k : ℕ) :
    k ≤ kMax M r income maint damage ↔
      (k : ℝ) ≤ kMaxReal M r income maint damage := by
  unfold kMax
  exact Nat.le_floor_iff hnn

/-- **The law rewritten as the budget condition it came from.**

`k ≤ 1 + (M*r − maint − damage)/income` is the same statement as
`(k−1)*income ≤ M*r − maint − damage`, which is what the ledger says: after
`k−1` full takes there must be at least `maint + damage` left. -/
theorem kMaxReal_iff_budget {M r income maint damage : ℝ} (hincome : 0 < income)
    (k : ℝ) :
    k ≤ kMaxReal M r income maint damage ↔
      (k - 1) * income ≤ M * r - maint - damage := by
  unfold kMaxReal
  constructor
  · intro h
    have h' : k - 1 ≤ (M * r - maint - damage) / income := by linarith
    rw [le_div_iff₀ hincome] at h'
    linarith
  · intro h
    have h' : (k - 1) * income ≤ M * r - maint - damage := h
    have h'' : k - 1 ≤ (M * r - maint - damage) / income := by
      rw [le_div_iff₀ hincome]
      linarith
    linarith

/-!
## The threshold where the count jumps

The count is `k` while `k−1 ≤ (M*r − maint − damage)/income < k`. The jump from
`k` to `k+1` happens exactly at

    M*r = maint + damage + k*income,

i.e. at `r = (maint + damage + k*income)/M`. For `k = 1` that is
`r = (income + maint + damage)/M`, the number the experiment measured.
-/

/-- **The jump point.** -/
noncomputable def jumpR (M income maint damage k : ℝ) : ℝ :=
  (maint + damage + k * income) / M

/-- **At the jump point the cell exactly covers `k` organisms and no more.** -/
theorem jumpR_spec {M income maint damage k : ℝ} (hM : M ≠ 0) :
    M * jumpR M income maint damage k = maint + damage + k * income := by
  unfold jumpR
  field_simp

/-- **Just above the jump point `k+1` organisms live; just below, only `k`.**

This is the discontinuity. It is what makes the count a floor and not a ratio:
`kMaxReal` is continuous in `r`, `kMax` is not. -/
theorem count_jumps_at_jumpR {M income maint damage k : ℝ}
    (_hM : 0 < M) (hincome : 0 < income) (_hk : 0 < k) :
    (k + 1 : ℝ) ≤ kMaxReal M (jumpR M income maint damage k) income maint damage ∧
      kMaxReal M (jumpR M income maint damage k - 1 / M) income maint damage < k + 1 := by
  have hM0 : M ≠ 0 := ne_of_gt _hM
  have hspec := jumpR_spec (M := M) (income := income) (maint := maint)
    (damage := damage) (k := k) hM0
  constructor
  · rw [kMaxReal_iff_budget (k := k + 1) hincome]
    rw [hspec]
    nlinarith
  · have hbelow : M * (jumpR M income maint damage k - 1 / M)
        = maint + damage + k * income - 1 := by
      rw [mul_sub, hspec]
      field_simp
    rw [lt_iff_not_ge]
    show ¬ (k + 1 ≤ kMaxReal M (jumpR M income maint damage k - 1 / M)
      income maint damage)
    rw [kMaxReal_iff_budget (k := k + 1) hincome]
    rw [hbelow]
    intro hcon
    nlinarith

/-!
## The old count is a different law

The old count `⌊M*r/income⌋` is `kMax` with `maint = damage = 0`. The two agree
only when the charges are zero. `old_law_is_wrong` is the arithmetic of the
measured disagreement: at the parameters of `EXP-25` the old count is 2 at
`r = 0.8` and the new count is 1 until `r` reaches `0.71`.
-/

/-- **The old count is the new one with no charges.** -/
theorem old_law_is_zero_charge (M r income : ℝ) :
    kMaxReal M r income 0 0 = 1 + M * r / income := by
  unfold kMaxReal
  ring

/-- **The measured disagreement, as arithmetic.**

`M = 2, income = 0.8, maint = 0.6, damage = 0.02`:

* at `r = 0.70` the budget is `1.4 − 0.62 = 0.78 < 0.8`, so `kMax = 1`;
* at `r = 0.75` the budget is `1.5 − 0.62 = 0.88 ≥ 0.8`, so `kMax = 2`;
* the old count is `⌊2.5*0.7⌋ = 1` and `⌊2.5*0.75⌋ = 1` — it says 1 in both.

So at `r = 0.75` the measurement and the new law say 2, and the old law says 1.
That is the arm on which `EXP-25`'s `specific` control separates them. -/
theorem old_law_is_wrong :
    kMax 2 (7 / 10) (4 / 5) (3 / 5) (1 / 50) = 1 ∧
    kMax 2 (3 / 4) (4 / 5) (3 / 5) (1 / 50) = 2 := by
  refine ⟨?_, ?_⟩ <;>
    · unfold kMax kMaxReal
      norm_num

/-- The old count at the same parameters, unfolded separately because
`kFeedCount` lives in `Capacity.lean`. -/
theorem old_law_is_wrong_feed :
    kFeedCount 2 (7 / 10) (4 / 5) = 1 ∧
    kFeedCount 2 (3 / 4) (4 / 5) = 1 := by
  refine ⟨?_, ?_⟩ <;>
    · unfold kFeedCount
      norm_num

/-- **The jump point at the measured parameters is `0.71`.** -/
theorem measured_jump :
    jumpR 2 (4 / 5) (3 / 5) (1 / 50) 1 = 71 / 100 := by
  unfold jumpR
  norm_num

/-!
## What the law needs, and what it does not

The law needs the cell to be drained to zero every step, which is
`k*income ≥ M*r`. It says nothing about a sparse population that leaves the cell
half full, and nothing about movement — a moving population spreads the count
into a distribution rather than a single number. Both are stated as hypotheses
elsewhere in the repository, not here; this file is the count alone.
-/

end Medium
