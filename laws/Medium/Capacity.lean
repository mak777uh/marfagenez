import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# Carrying capacity: how many organisms a cell can hold

## Three quantities that were confused — keep them apart

* `capacity M r t₀ = M*r / t₀` — **feeding** capacity: how many full portions of
  `t₀` the regrowth puts back per step. A fact about the field alone.
* `M*r / (t₀*(1-r))` — the **stock** the cell settles at, expressed in portions.
  It is larger by `1/(1-r)`, and it is **not** a number of organisms.
* `k_max` — the **count** of organisms one cell actually feeds. This is the one
  the experiments measure. See `docs/FINDING-k-max-is-a-count.md`.

The first two are closed formulas. The third is not: it is a recursion, because
the cell is eaten sequentially and a cell that is eaten down to nothing falls to
`M*r`, not to `M*r/(1-r)`. At `M = 2, t₀ = 0.8, r = 0.8, maint = 0.6` the stock
formula says `2.25` and the count is `2`, giving `C = 40 * 2 = 80`
(`results/EXP-22/run-2026-11-12T12-46-12.json`: 40/40, 80/80, 80/120, 80/160).

Note on the sign of `t`: after the 2026-11-12 correction of `cellStep`
(take, then regrow) the equilibrium is `c* = M + t - t/r = M - t*(1-r)/r`.
The old form `M - t/r` belongs to the *other* order of operations
(regrow, then take — `Medium/Feed.lean`), and the two differ by exactly `t`.



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

/-!
## `k_max` as a count: the recursion the model actually runs

`capacity` above answers "how much does the cell hand out". It does not answer
"how many organisms survive", because the take is sequential and the cell
cannot go below zero. The two differ by a factor that depends on `income` and
`maintenance`, so no closed formula in `M, r, t₀` alone can give the count.

The recursion below is the one `core/src/field.rs` runs: the cell starts at
`M`, each organism takes `min(t₀, what is left)`, and an organism survives
only if what it took is at least `maint`.
-/

/-- One organism takes `t₀` from the cell, or whatever is left if less. -/
noncomputable def takeOne (t₀ c : ℝ) : ℝ := min t₀ c

/-- The cell after `k` organisms have taken from it in turn. -/
noncomputable def afterTakes (t₀ : ℝ) : ℕ → ℝ → ℝ
  | 0, c => c
  | k + 1, c => afterTakes t₀ k (c - takeOne t₀ c)

/-- **The cell never goes below zero, however many organisms take from it.** -/
theorem afterTakes_nonneg {t₀ c : ℝ} (hc : 0 ≤ c) (k : ℕ) :
    0 ≤ afterTakes t₀ k c := by
  induction k generalizing c with
  | zero => exact hc
  | succ k ih =>
      exact ih (by unfold takeOne; linarith [min_le_right t₀ c])

/-- **The cell never gains from being eaten.** -/
theorem afterTakes_le {t₀ c : ℝ} (ht₀ : 0 ≤ t₀) (hc : 0 ≤ c) (k : ℕ) :
    afterTakes t₀ k c ≤ c := by
  induction k generalizing c with
  | zero => exact le_rfl
  | succ k ih =>
      have h1 : afterTakes t₀ k (c - takeOne t₀ c) ≤ c - takeOne t₀ c :=
        ih (by unfold takeOne; linarith [min_le_right t₀ c])
      have h2 : 0 ≤ takeOne t₀ c := by unfold takeOne; exact le_min ht₀ hc
      show afterTakes t₀ k (c - takeOne t₀ c) ≤ c
      linarith

/-- **The first organism is fed exactly when the cell holds `maint`.** -/
theorem first_fed_iff {t₀ maint c : ℝ} :
    maint ≤ takeOne t₀ c ↔ maint ≤ t₀ ∧ maint ≤ c := by
  unfold takeOne
  exact le_min_iff

/-- **Two organisms on a cell that feeds them both: what is left after two.**

This is the arithmetic behind `EXP-22`: at `M = 2, t₀ = 0.8, r = 0.8` the
cell settles at `1.8`, one organism takes `0.8` and leaves `1.0`, a second
takes `0.8` and leaves `0.2`, and a third gets `0.2 < 0.6 = maint`. -/
theorem two_takes {t₀ c : ℝ} (ht₀ : 0 < t₀) (hc : 2 * t₀ ≤ c) :
    afterTakes t₀ 2 c = c - 2 * t₀ := by
  have h1 : takeOne t₀ c = t₀ := min_eq_left (by linarith)
  have h2 : takeOne t₀ (c - t₀) = t₀ := min_eq_left (by linarith)
  show c - takeOne t₀ c - takeOne t₀ (c - takeOne t₀ c) = c - 2 * t₀
  rw [h1, h2]
  ring

/-- **A third organism on that cell gets `c - 2*t₀`.** -/
theorem three_takes {t₀ c : ℝ} (ht₀ : 0 < t₀) (hc : 2 * t₀ ≤ c) :
    afterTakes t₀ 3 c = c - 2 * t₀ - min t₀ (c - 2 * t₀) := by
  have h1 : takeOne t₀ c = t₀ := min_eq_left (by linarith)
  have h2 : takeOne t₀ (c - t₀) = t₀ := min_eq_left (by linarith)
  show c - takeOne t₀ c - takeOne t₀ (c - takeOne t₀ c)
      - takeOne t₀ (c - takeOne t₀ c - takeOne t₀ (c - takeOne t₀ c))
    = c - 2 * t₀ - min t₀ (c - 2 * t₀)
  rw [h1, h2]
  show c - t₀ - t₀ - min t₀ (c - t₀ - t₀) = c - 2 * t₀ - min t₀ (c - 2 * t₀)
  ring_nf

/-!
## The count is a floor, not a ceiling

`k_feed = M*r/t₀` is a real number. The number of organisms a cell actually
feeds is the largest integer `k` with `k*t₀ ≤ M*r`, which is `⌊M*r/t₀⌋`, and
that is a **floor**. This is where the model stops being linear: `capacity` is
continuous in `r` and `M`, the count is not.

The floor is also the reason a small change in `r` can cost a whole organism:
at `M = 2, t₀ = 0.8` the count is `⌊2.5 r⌋`, so it drops from 2 to 1 the
moment `r` falls below `0.8`, and from 1 to 0 below `0.4`.
-/

/-- The count of organisms a cell feeds: the largest `k` with `k*t₀ ≤ M*r`. -/
noncomputable def kFeedCount (M r t₀ : ℝ) : ℕ :=
  ⌊M * r / t₀⌋₊

/-- **The count never exceeds the continuous capacity.** -/
theorem kFeedCount_le_capacity {M r t₀ : ℝ} (hM : 0 ≤ M) (hr : 0 ≤ r)
    (ht₀ : 0 < t₀) :
    (kFeedCount M r t₀ : ℝ) ≤ capacity M r t₀ := by
  unfold kFeedCount capacity
  exact Nat.floor_le (div_nonneg (mul_nonneg hM hr) (le_of_lt ht₀))

/-- **The count is tight: one more organism does not fit.** -/
theorem kFeedCount_tight {M r t₀ : ℝ} :
    capacity M r t₀ < (kFeedCount M r t₀ : ℝ) + 1 := by
  unfold kFeedCount capacity
  exact Nat.lt_floor_add_one (M * r / t₀)

/-- **The count is a floor: `k` organisms fit exactly when `k ≤ ⌊M*r/t₀⌋`.** -/
theorem kFeedCount_iff {M r t₀ : ℝ} (hM : 0 < M) (hr : 0 ≤ r) (ht₀ : 0 < t₀)
    (k : ℕ) :
    (k : ℝ) * t₀ ≤ M * r ↔ k ≤ kFeedCount M r t₀ := by
  unfold kFeedCount
  have hnn : (0 : ℝ) ≤ M * r / t₀ := div_nonneg (mul_nonneg (le_of_lt hM) hr) (le_of_lt ht₀)
  rw [Nat.le_floor_iff hnn, le_div_iff₀ ht₀]

/-- **The count jumps down by a whole organism at a threshold.**

At `M = 2, t₀ = 0.8` the count is `⌊2.5 r⌋`: two organisms at `r = 0.8`, one
just below. This is the discontinuity the continuous `capacity` does not have. -/
theorem count_jumps_at_threshold :
    kFeedCount 2 (4 / 5) (4 / 5) = 2 ∧ kFeedCount 2 (79 / 100) (4 / 5) = 1 := by
  constructor
  · unfold kFeedCount
    norm_num
  · unfold kFeedCount
    norm_num

end Medium
