import Mathlib
import Medium.Field
import Medium.Convergence

/-!
# Carrying capacity: how many organisms a cell can hold

## The law, corrected 2026-11-12 (measurement + sympy)

The step is: every organism on the cell takes `min(left, income)` in turn, then
the cell regrows once. If `k` organisms stand on the cell, the draw is `k*t`,
so the fixed point of `cellStep M r (k*t)` is

    c*(k) = M + k*t - k*t/r = M - k*t*(1-r)/r.

The take of the `k`-th organism is `min(t, c*(k) - (k-1)*t)`, and it lives iff
that is at least `maintenance`. Measured at `M = 2, r = 0.8, t = 0.8`
(`results/EXP-51/`): the cell sits at `M - 2t(1-r)/r` to `2.2e-16` for
`t = 0.62, 0.65, 0.70, 0.75, 0.80`, and at `M - t(1-r)/r` for `t >= 1.0` where
only one organism is left. At `t = 0.9` the two-organism level `1.55` is below
`2t = 1.8`, so the second organism is rationed and dies: the population drops
to one per cell at `t = 0.9`, not at `t = 0.8`.

Two old claims are now known to be wrong and are kept here only as history:

* `c* = M - t/r` — that is the *other* order of operations (regrow, then take,
  `Medium/Feed.lean`). With take-then-regrow it is `M + t - t/r`.
* `k_feed = 2.5` at `M = 2, r = 0.8, t₀ = 0.8` — this file used to say the
  "regrowth covers k full portions" story gives 2.5 while the measurement gives
  2. That was itself wrong: the story gives `M*r/t₀ = 2.0` exactly, and the
  measurement agrees. There was never a discrepancy. (Corrected 2026-11-12;
  see `Medium/Regimes.lean`, where `feedCapacity` had the same error.)

## What is proved

* `equilibrium_nonneg_iff` — `0 ≤ c*` exactly when `t*(1-r) ≤ M*r`
* `feed_share` — `k_feed = M*r / t₀`
* `feed_share_iff` — the cell's regrowth covers `k` full portions exactly when `k ≤ k_feed`
* `feed_share_equals_give_back` — `k_feed * t₀ = M*r`, the whole content of the law
* `feed_share_mono_M`, `feed_share_mono_r`, `feed_share_anti_income`
* `feed_share_infinite_at_full_regrowth` — at `r = 1` no finite `k` starves the cell
* `no_second_place` — when `k_feed ≤ 1`, a second organism cannot be supported

## What is NOT proved

That the population actually reaches `cells * k_feed`. That needs a model of
movement and of who stands where; the experiments measure it, this file does not
prove it. The measurement gives `C = 80` at 40 cells with `k_feed = 2`
(`results/overcrowding/run-2026-11-11T22-20-40.json`).

**The `k_max = 10` anomaly, resolved 2026-11-12.** A claim circulated after the
formula fix that `k_max` is 10 and the capacity law gives `C = 400`. It has been
traced: `--capacity` in the Rust binary is **the energy ceiling `E_max`**, not a
per-cell occupancy limit (`core/src/organism.rs:164`). Reading `--capacity 10` as
`k_max = 10` is the whole of it. There is no `k_max = 10`.

**And `C` is not a single number.** Measured at `M = 2.0`, `r = 0.8`,
`income = 1.2`, `maintenance = 0.6`, `damage_rate = 0.02`, `repair_cost = 1.5`,
40 cells, 160 organisms, 8000 steps (`docs/FINDING-the-capacity-is-a-line-not-a-number.md`):

    E_max   alive   crowding   energy mean
      8       40      1.00        7.3700
      9       42      1.05        8.3481
     10       42      1.05        9.3481

The cost of staying alive one step is `COST = maintenance + damage_rate *
repair_cost = 0.63`, and the steady energy is `E* = E_max - COST` exactly
(8 - 0.63 = 7.37, 9 - 0.63 = 8.37, 10 - 0.63 = 9.37). The second organism on a
cell takes `c* - income = 1.7 - 1.2 = 0.5`, which is **below** the 0.63 it needs,
so at `E_max = 8` the capacity is exactly one per cell and `C = 40`. At
`E_max = 9` and 10 two organisms sit two to a cell, burning the `0.31` of savings
they have above the single-organism steady state at `0.13` per step. They are not
in equilibrium; the run stopped at 8000 steps before they finished sliding.

So `C` is a **line in `E_max`**, not a number, and any `C` quoted without `E_max`
is not a law. The `C = 80` above was taken at different parameters
(`results/overcrowding/run-2026-11-11T22-20-40.json`) and has not been re-run.
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

/-- **The largest number of organisms a cell can hold, counting the draw.**

`k_max = M*r / t`, where `t` is what one organism takes per step. The cell
gives back `M*r` per cycle and `k` organisms draw `k*t`, so `k` of them fit
exactly when `k*t ≤ M*r`.

This is the same formula the file used to call `capacity` (renamed `feed_share` on 2026-11-12: it is how much the cell hands out, not how much it holds), and it is still
**not** the count the experiments measure: the count is the largest `k` with
`k*t ≤ M*r` **and** the `k`-th take at least `maintenance`. The second
condition is what `kMaxCount` below adds. -/
noncomputable def feed_share (M r t₀ : ℝ) : ℝ := M * r / t₀

/-- **The law in one line: `k` portions of `t₀` exactly exhaust the regrowth.** -/
theorem feed_share_equals_give_back {M r t₀ : ℝ} (ht₀ : t₀ ≠ 0) :
    feed_share M r t₀ * t₀ = M * r := by
  unfold feed_share
  field_simp

/-- **A cell feeds `k` organisms exactly when its regrowth covers `k` portions.** -/
theorem feed_share_iff {M r t₀ : ℝ} (ht₀ : 0 < t₀) (k : ℝ) :
    k * t₀ ≤ M * r ↔ k ≤ feed_share M r t₀ := by
  unfold feed_share
  rw [le_div_iff₀ ht₀]

/-- **A richer cell holds more.** -/
theorem feed_share_mono_M {M₁ M₂ r t₀ : ℝ} (hr : 0 ≤ r) (ht₀ : 0 < t₀)
    (h : M₁ ≤ M₂) :
    feed_share M₁ r t₀ ≤ feed_share M₂ r t₀ := by
  unfold feed_share
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **Faster regrowth holds more.** -/
theorem feed_share_mono_r {M r₁ r₂ t₀ : ℝ} (hM : 0 < M)
    (ht₀ : 0 < t₀) (h : r₁ ≤ r₂) :
    feed_share M r₁ t₀ ≤ feed_share M r₂ t₀ := by
  unfold feed_share
  exact div_le_div_of_nonneg_right (by nlinarith) (le_of_lt ht₀)

/-- **A bigger take holds less.** -/
theorem feed_share_anti_income {M r t₁ t₂ : ℝ} (hM : 0 < M) (hr : 0 < r)
    (ht₁ : 0 < t₁) (h : t₁ ≤ t₂) :
    feed_share M r t₂ ≤ feed_share M r t₁ := by
  unfold feed_share
  have hMr : 0 < M * r := mul_pos hM hr
  exact div_le_div_of_nonneg_left (le_of_lt hMr) ht₁ (by linarith)

/-- **At full regrowth nothing starves the cell.** -/
theorem feed_share_infinite_at_full_regrowth {M t₀ k : ℝ} (hM : 0 < M) :
    0 ≤ equilibrium M 1 (k * t₀) := by
  unfold equilibrium
  norm_num
  linarith

/-- **The total capacity of a field.** -/
noncomputable def totalCapacity (cells : ℕ) (M r t₀ : ℝ) : ℝ :=
  (cells : ℝ) * feed_share M r t₀

/-- **A cell that holds one organism gains nothing from a second place.**

When `feed_share M r t₀ ≤ 1`, movement cannot find a second place. This is the
arithmetic behind the `M = 1.0` measurement, where movement made no difference. -/
theorem no_second_place {M r t₀ : ℝ} (ht₀ : 0 < t₀) (h : feed_share M r t₀ ≤ 1) :
    ∀ k : ℝ, 1 < k → ¬ (k * t₀ ≤ M * r) := by
  intro k hk hcover
  have hk_le : k ≤ feed_share M r t₀ := (feed_share_iff ht₀ k).mp hcover
  linarith

/-!
## `k_max` as a count: the recursion the model actually runs

`feed_share` above answers "how much does the cell hand out". It does not answer
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
that is a **floor**. This is where the model stops being linear: `feed_share` is
continuous in `r` and `M`, the count is not.

The floor is also the reason a small change in `r` can cost a whole organism:
at `M = 2, t₀ = 0.8` the count is `⌊2.5 r⌋`, so it drops from 2 to 1 the
moment `r` falls below `0.8`, and from 1 to 0 below `0.4`.
-/

/-- The count of organisms a cell feeds: the largest `k` with `k*t₀ ≤ M*r`. -/
noncomputable def kFeedCount (M r t₀ : ℝ) : ℕ :=
  ⌊M * r / t₀⌋₊

/-- **The count never exceeds the continuous capacity.** -/
theorem kFeedCount_le_feed_share {M r t₀ : ℝ} (hM : 0 ≤ M) (hr : 0 ≤ r)
    (ht₀ : 0 < t₀) :
    (kFeedCount M r t₀ : ℝ) ≤ feed_share M r t₀ := by
  unfold kFeedCount feed_share
  exact Nat.floor_le (div_nonneg (mul_nonneg hM hr) (le_of_lt ht₀))

/-- **The count is tight: one more organism does not fit.** -/
theorem kFeedCount_tight {M r t₀ : ℝ} :
    feed_share M r t₀ < (kFeedCount M r t₀ : ℝ) + 1 := by
  unfold kFeedCount feed_share
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
just below. This is the discontinuity the continuous `feed_share` does not have. -/
theorem count_jumps_at_threshold :
    kFeedCount 2 (4 / 5) (4 / 5) = 2 ∧ kFeedCount 2 (79 / 100) (4 / 5) = 1 := by
  constructor
  · unfold kFeedCount
    norm_num
  · unfold kFeedCount
    norm_num

/-!
## The corrected law: the draw is `k*t`, not `t`

`cellStep M r x = (x - t) + (M - (x - t)) * r` has the fixed point
`M + t - t/r` for a draw `t`. When `k` organisms stand on the cell the draw is
`k*t`, so the level they settle at is

    cStar M r k t = M + k*t - k*t/r.

The `k`-th organism takes `min(t, cStar - (k-1)*t)`; it lives iff that is at
least `maintenance`. Both conditions are linear in `k`, so the count is a floor.
-/

/-- The level a cell settles at when `k` organisms draw `t` each per step. -/
noncomputable def cStar (M r k t : ℝ) : ℝ := M + k * t - k * t / r

/-- **`cStar` in the form that clears the division.** -/
theorem cStar_eq (M r k t : ℝ) (hr : r ≠ 0) :
    cStar M r k t = M - k * t * (1 - r) / r := by
  unfold cStar
  have h : k * t - k * t / r = -(k * t * (1 - r) / r) := by
    rw [div_eq_mul_inv, div_eq_mul_inv]
    ring_nf
    rw [show k * t * r * r⁻¹ = k * t * (r * r⁻¹) by ring]
    rw [mul_inv_cancel₀ hr]
    ring
  linarith

/-- **`cStar` at `k = 1` is the equilibrium of `Convergence.lean`.** -/
theorem cStar_one (M r t : ℝ) : cStar M r 1 t = M + t - t / r := by
  unfold cStar
  ring

/-- **The level is a decreasing function of the number of organisms.** -/
theorem cStar_anti_k {M r t k₁ k₂ : ℝ} (hr : 0 < r) (hr1 : r < 1) (ht : 0 < t)
    (h : k₁ ≤ k₂) :
    cStar M r k₂ t ≤ cStar M r k₁ t := by
  rw [cStar_eq M r k₂ t (ne_of_gt hr), cStar_eq M r k₁ t (ne_of_gt hr)]
  have h1 : 0 < 1 - r := by linarith
  have h4 : k₁ * t * (1 - r) ≤ k₂ * t * (1 - r) := by
    have ht1 : 0 ≤ t * (1 - r) := by positivity
    nlinarith
  have h5 : k₁ * t * (1 - r) / r ≤ k₂ * t * (1 - r) / r :=
    div_le_div_of_nonneg_right h4 (le_of_lt hr)
  linarith

/-- **The draw fits the level exactly when `k*t ≤ M*r`.**

This is the condition that the cell's regrowth covers the total draw. It is the
same inequality the old `feed_share` story used, and it is still true — it is just
not sufficient for the organism to live. -/
theorem cStar_draw_le_iff {M r k t : ℝ} (hr : 0 < r) (hr1 : r < 1) :
    k * t ≤ cStar M r k t ↔ k * t ≤ M * r := by
  rw [cStar_eq M r k t (ne_of_gt hr)]
  have h1 : 0 < 1 - r := by linarith
  have hr' : 0 < r := hr
  rw [show M - k * t * (1 - r) / r = (M * r - k * t * (1 - r)) / r by field_simp]
  rw [le_div_iff₀ hr']
  constructor <;> intro h <;> nlinarith

/-- **What the `k`-th organism gets.**

After `k - 1` organisms have taken `t` each, the cell holds
`cStar M r k t - (k-1)*t`, and the `k`-th takes the smaller of that and `t`. -/
theorem kth_take_eq (M r k t : ℝ) (hr : 0 < r) (hr1 : r < 1) :
    cStar M r k t - (k - 1) * t = M - k * t / r + t := by
  rw [cStar_eq M r k t (ne_of_gt hr)]
  field_simp
  ring

/-- **The `k`-th organism is fed in full exactly when `M + t >= k*t/r + t`.**

Reading `kth_take_eq` back: the `k`-th take is `t` (full) when
`M - k*t/r + t >= t`, i.e. `k*t <= M*r`, which is the same condition as
`cStar_draw_le_iff`. So "the cell covers the draw" and "the last organism is
fed in full" are one and the same inequality — that is why the old story looked
right. What it missed is the `maintenance` threshold: an organism that takes
`min(t, left) < maintenance` still dies, and that happens for `k` one above
`M*r/t`. -/
theorem kth_take_full_iff {M r k t : ℝ} (hr : 0 < r) (hr1 : r < 1) (ht : 0 < t) :
    t ≤ cStar M r k t - (k - 1) * t ↔ k * t ≤ M * r := by
  rw [kth_take_eq M r k t hr hr1]
  constructor
  · intro h
    have h1 : k * t / r ≤ M := by linarith
    rw [div_le_iff₀ hr] at h1
    linarith
  · intro h
    have h1 : k * t / r ≤ M := by
      rw [div_le_iff₀ hr]
      linarith
    linarith

/-- **The count, with the maintenance threshold.**

`kMaxCount` is the largest `k` with `k*t ≤ M*r`. That is the count of organisms
whose take is full; the ones beyond it are rationed, and whether they live
depends on `maintenance`, which this definition does not see. The measurement
(`results/EXP-51/`) shows a rationed organism can live: at `t = 0.9` the level
is `1.55` and the second organism takes `0.75 > 0.6`. -/
noncomputable def kMaxCount (M r t : ℝ) : ℕ := ⌊M * r / t⌋₊

/-- **The count is a floor of the same ratio.** -/
theorem kMaxCount_eq_kFeedCount (M r t : ℝ) : kMaxCount M r t = kFeedCount M r t := rfl

/-- **The count is tight.** -/
theorem kMaxCount_tight {M r t : ℝ} (hM : 0 < M) (hr : 0 < r) (ht : 0 < t) :
    feed_share M r t < (kMaxCount M r t : ℝ) + 1 := by
  unfold kMaxCount feed_share
  exact Nat.lt_floor_add_one (M * r / t)

/-- **The measured numbers, as a check on the formula.**

At `M = 2, r = 0.8, t = 0.8` the level with two organisms is `1.6` and with one
is `1.8`; the count is `2`. At `t = 0.9` the count of *full* takes is still `2`
but the level `1.55` is below `2*0.9 = 1.8`, so the second is rationed to
`0.65`, which is above `maintenance = 0.6` — so it lives. The count of living
organisms is therefore not `kMaxCount`; it is the largest `k` with
`min(t, cStar - (k-1)*t) >= maintenance`. -/
theorem measured_levels :
    cStar 2 (4 / 5) 2 (4 / 5) = 8 / 5 ∧
    cStar 2 (4 / 5) 1 (4 / 5) = 9 / 5 ∧
    cStar 2 (4 / 5) 2 (9 / 10) = 31 / 20 := by
  refine ⟨?_, ?_, ?_⟩ <;>
    · unfold cStar
      norm_num

/-- **The rationed take at `t = 0.9` is `0.65`, above maintenance `0.6`.** -/
theorem rationed_second_lives :
    cStar 2 (4 / 5) 2 (9 / 10) - 1 * (9 / 10) = 13 / 20 := by
  have h : cStar 2 (4 / 5) 2 (9 / 10) = 31 / 20 := by
    unfold cStar
    norm_num
  rw [h]
  norm_num

/-- **And `0.65` is above the `0.6` maintenance, so the rationed organism lives.** -/
theorem rationed_take_above_maintenance : (13 / 20 : ℝ) > 6 / 10 := by norm_num

end Medium
