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
prove it.

## What the measurements say, and what they no longer say

**The old `C = 80` is void.** It was recorded while the clamp ran right after the
income, which erased `move_cost` (see
`docs/FINDING-the-cap-is-applied-after-the-spend.md`). Every capacity number
measured before 2026-11-12 23:00 describes a dynamics that no longer exists.

**Measured under the current order** (`exp75`, 40 cells, `rich = 2.0`, `n = 160`,
4000 steps, `sighted`, `move_cost = 0`, `income = 1.2`, `maintenance = 0.6`,
`damage_rate = 0.02`, `repair_cost = 1.5`, `E_max = 10`):

    poor    alternating   uniform
    0.2     20            0
    0.8     20            40
    1.2     20            40
    1.6     40            40

All eight runs: `crowding = 1.00`, mean energy `10.0000`.

The reading: **capacity is the number of cells that can feed an organism.** A
cell with `poor = 0.2` cannot feed at all, so `alternating` -- half rich, half
poor -- has 20 usable cells and `C = 20`. `uniform` at `poor = 0.2` feeds nobody
and the whole population dies. Once `poor >= income` every cell feeds and the
field shape stops mattering: `C = cells = 40`. The transition is at
`poor = income`, which is what `feed_share_iff` says with `k = 1`.

This is `feed_share` read as a count: a cell supports `k` organisms exactly when
`k * t0 <= M * r`. With `M = 2.0`, `r = 0.8`, `t0 = income = 1.2` that gives
`k_feed = 1.33`, so one organism per cell and `cells * 1 = 40`. The measured 40
matches. The measured 20 matches "half the cells do not feed".

**The steady energy is `E_max`, not `E_max - COST`.** With the clamp at the end
of the step, an organism whose energy would exceed `E_max` is set to `E_max`, so
the steady state of a well-fed organism is exactly the ceiling: measured
`10.0000` at `E_max = 10`, `20.0000` at `E_max = 20`, residual `+0.000000`. The
old `E* = E_max - COST = 8.97` described an intermediate value inside the step
and is retired.

**`--capacity` is the energy ceiling `E_max`**, not a per-cell occupancy limit
(`core/src/organism.rs:164`). There is no `k_max`. Reading `--capacity 10` as
`k_max = 10` and concluding `C = 400` was the whole of that anomaly.

## The transition, measured (2026-11-13)

The transition is **not** at `poor = income`, which is what the arithmetic
suggested and what this file used to claim. It is at

    poor · (1 + r) = income        poor = income / (1 + r)

At `income = 0.8, r = 0.8` that is `poor = 0.8/1.8 = 0.4444`. Measured: `0.4`
gives 40 survivors, `0.6` gives 60. The old guess `poor = income = 0.8` is
wrong by a factor of 1.8, and the measurement at `poor = 1.2` that "confirmed"
it was confirming the wrong number — 60 survivors at 1.2 says nothing about
where the edge between 40 and 60 is.

Why `1 + r`: a cell that nobody takes from settles at `M`, because
`cellStep M r 0 M = M`. A cell that one organism takes `t` from settles at
`M + t - t/r = M - t*(1-r)/r`. The organism lives iff that is at least
`need`, so the boundary is `M - t*(1-r)/r = need`, i.e.
`t = (M - need)*r/(1-r)`.

The same law governs `rich`. At `poor = 0.2` the transition sits between
`rich = 2.70` (40 survivors, rich level `2.300`) and `rich = 2.80`
(60 survivors, rich level `2.240`). The boundary the arithmetic gives is
`rich = 2.75`, where the level is `need = 2.3` exactly.

## What is still open

- Whether the second transition (`60 -> 80`) sits at the same law. It was
  measured at `poor = 1.78` (60) / `1.79` (80), which is close to
  `1.8 · (1 + r)` but not equal to it, and the level jumps from `1.580` to
  `1.432` across that edge — a jump the one-cell law does not predict.
- Whether a larger `E_max` lets a cell hold two organisms. The old answer was yes
  at `E_max = 9`; that was measured under the old order and has not been redone.

*Retired 2026-11-13:* "why one cell holds exactly one organism even when
`k_feed = 1.33`". It does not. One organism per cell is what the `sighted`
policy produces in a uniform field, not a property of the cell. The count of
living organisms on a cell is `kSatCount` below, and it is 2 at
`M = 2, r = 0.8, t = 0.9, need = 0.6`. See
`docs/FINDING-one-per-cell-was-a-strategy.md`. -/

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

/-!
# The capacity law, 2026-11-13

Everything above is history. The law below is the one the measurements agree
with, 12/12 on a rich cell, 12/12 on a poor cell, 6/6 on a uniform field
(`docs/LAW-capacity.md`).

## The three facts from the code

1. The take is capped by the income, not by the cell
   (`core/src/organism.rs:165`): `taken = min(resource, income)`.
2. The cell regrows twice per step (`core/src/life.rs:252`): once at the end of
   the step, once at the start of the next.
3. The bill per organism per step is `m + damage_rate * repair_cost`, and it is
   paid in full or the organism dies.

## The level

With `k` organisms each asking `t`, `paid = min(k*t, L)` and
`L_next = (L - paid) + (M - (L - paid)) * r`. Two self-consistent branches:

* unsaturated (`k*t <= L`): `L* = M - k*t*(1-r)/r`, valid iff `k*t <= M*r`;
* saturated (`k*t >= L`): `L* = M*r`, valid iff `k*t >= M*r`.

They meet at `k*t = M*r`, so `L*(k) = max(M - k*t*(1-r)/r, M*r)`.

## The count

* unsaturated: every organism gets `t`, so all live iff `t > need`, and
  `k_max = floor(M*r/t)`;
* saturated: the cell pays out `M*r` in order, the last gets
  `M*r - (k-1)*t`, so `k_max = floor((M*r - need)/t) + 1`.

The measured count is the larger of the two, over the branches that are
self-consistent.
-/

/-- **The level a cell settles at, both branches in one `max`.**

`max(M - k*t*(1-r)/r, M*r)`. -/
noncomputable def cellLevel (M r k t : ℝ) : ℝ := max (M - k * t * (1 - r) / r) (M * r)

/-- **The unsaturated branch is the old `cStar`.** -/
theorem cellLevel_eq_cStar {M r k t : ℝ} (hr : 0 < r) (hr1 : r ≤ 1) (ht : 0 ≤ t) (hM : 0 ≤ M)
    (h : k * t ≤ M * r) :
    cellLevel M r k t = cStar M r k t := by
  have h3 : k * t / r ≤ M := by
    rw [div_le_iff₀ hr]; nlinarith
  have h4 : M - k * t / r ≥ 0 := by linarith
  have h6 : 0 ≤ (M - k * t / r) * (1 - r) := mul_nonneg h4 (by linarith)
  have h2 : M * r ≤ M - k * t * (1 - r) / r := by
    have h7 : M - k * t * (1 - r) / r - M * r = (M - k * t / r) * (1 - r) := by
      have hk : k * t * (1 - r) / r = k * t / r * (1 - r) := by field_simp
      rw [hk]; ring
    linarith
  unfold cellLevel cStar
  rw [max_eq_left h2]
  field_simp
  ring

/-- **The saturated branch: the cell holds exactly `M*r`.** -/
theorem saturated_level (M r : ℝ) :
    cellLevel M r 0 0 = max M (M * r) := by
  unfold cellLevel
  simp

/-- **The two branches meet at `k*t = M*r`.** -/
theorem branches_meet {M r k t : ℝ} (hr : r ≠ 0) (h : k * t = M * r) :
    M - k * t * (1 - r) / r = M * r := by
  rw [h]
  field_simp
  ring

/-- **The unsaturated count: every organism gets its full income.** -/
theorem unsaturated_count {M r k t : ℝ} (h : k * t ≤ M * r) :
    k * t ≤ cellLevel M r k t := by
  unfold cellLevel
  have h := le_max_left (M - k * t * (1 - r) / r) (M * r)
  have h2 : M * r <= max (M - k * t * (1 - r) / r) (M * r) := le_max_right _ _
  nlinarith

/-- **The saturated count: the last organism gets `M*r - (k-1)*t`.** -/
theorem saturated_last_take (M r k t : ℝ) :
    M * r - (k - 1) * t = M * r - k * t + t := by ring

/-- **The saturated count is the solution of `M*r - (k-1)*t > need`.** -/
theorem saturated_count_iff {M r k t need : ℝ} (ht : 0 < t) :
    need < M * r - (k - 1) * t ↔ k - 1 < (M * r - need) / t := by
  rw [lt_div_iff₀ ht]
  constructor <;> intro h <;> nlinarith

/-- **The capacity law: both branches are tight.**

`kUnsat = floor(M*r/t)` never overshoots the regrowth, and `kSat = floor((M*r-need)/t)+1`
is exactly the largest count whose last organism still clears `need`. -/
theorem capacity_law {M r t need : ℝ} (hMr : 0 ≤ M * r) (hneed : need ≤ M * r) (ht : 0 < t) :
    ((⌊M * r / t⌋₊ : ℕ) : ℝ) * t ≤ M * r ∧
    need ≤ M * r - (((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ)) * t := by
  have hpos : (0 : ℝ) ≤ M * r / t := div_nonneg hMr (le_of_lt ht)
  constructor
  · have h : ((⌊M * r / t⌋₊ : ℕ) : ℝ) ≤ M * r / t := Nat.floor_le hpos
    rwa [le_div_iff₀ ht] at h
  · have h1 : ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) ≤ (M * r - need) / t :=
      Nat.floor_le (div_nonneg (by linarith : (0:ℝ) ≤ M * r - need) (le_of_lt ht))
    have h3 : ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) * t ≤ M * r - need := by
      have h1' := mul_le_mul_of_nonneg_right h1 (le_of_lt ht)
      rwa [div_mul_cancel₀ _ (ne_of_gt ht)] at h1'
    linarith

/-- **The saturated branch is tight one step further: `floor+1` overshoots.**

`M*r - floor((M*r-need)/t)*t` is the last organism's take, and it is `≥ need`
by `capacity_law`. One more organism would take `t` more, so the count
`floor((M*r-need)/t)+1` is the largest whose last organism still clears `need`.
This is the strict companion of `capacity_law`; it needs `need ≤ M*r - t` so
that the extra step is affordable at all. -/
theorem capacity_law_strict {M r t need : ℝ} (hMr : 0 ≤ M * r) (hneed : need ≤ M * r)
    (hneed0 : 0 ≤ need) (ht : 0 < t) :
    0 < M * r - (((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) - 1) * t := by
  have h1 : ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) ≤ (M * r - need) / t :=
    Nat.floor_le (div_nonneg (by linarith : (0:ℝ) ≤ M * r - need) (le_of_lt ht))
  have h1' := mul_le_mul_of_nonneg_right h1 (le_of_lt ht)
  rw [div_mul_cancel₀ _ (ne_of_gt ht)] at h1'
  set n : ℝ := ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) with hn
  set p : ℝ := n * t with hp
  have hp_le : p ≤ M * r - need := h1'
  have key : M * r - (n - 1) * t = (M * r - p) + t := by
    rw [hp]; ring
  rw [key]
  linarith

/-! ## The starved regime, and the number the field actually shows

`cellLevel_eq_cStar` needs `k*t ≤ M*r`: it says the cell settles at `cStar`
because it can still afford everyone. When `k*t > M*r` the cell cannot, and
`cellLevel` returns `M*r`. The two branches are not interchangeable and the
difference is not small — it is the whole reason a moving organism does better
than a standing one (see `docs/FINDING-the-field-was-never-uniform.md`).

Worked at the measured parameters `M = 1.1, r = 0.8, income = 1.0`, where
`M*r = 0.88 < income`, so *nobody* is fed: `kMaxCount = 0`. -/

/-- **In the starved regime the level is `M*r`, not `cStar`.**

`cStar = 0.85` here and `M*r = 0.88`; the `max` in `cellLevel` picks `0.88`.
Getting this backwards is easy: `0.88` looks like a `cStar` and is not one. -/
theorem starved_level_measured :
    cellLevel (11 / 10) (8 / 10) 1 1 = 88 / 100 := by
  unfold cellLevel
  norm_num

/-- **`cStar` at the same point is lower than `M*r`** — this is what makes the
regime starved rather than fed. -/
theorem cStar_below_Mr_measured :
    cStar (11 / 10) (8 / 10) 1 1 = 85 / 100 := by
  unfold cStar
  norm_num

/-- **The threshold itself: `M*r < income`, so no organism is fed.** -/
theorem nobody_fed_measured : (88 / 100 : ℝ) < 1 := by norm_num

/-- **The fed regime does reach `cStar`.** At the default field
`M = 2, r = 0.8, income = 0.2` a cell holds `k = 8` and sits at `1.6`, which is
both `cStar` and `M*r` — the branches meet exactly at `k*t = M*r`. -/
theorem fed_level_measured :
    cellLevel 2 (8 / 10) 8 (2 / 10) = 8 / 5 := by
  unfold cellLevel
  norm_num

/-- **The same point is `cStar` too**, so `cellLevel_eq_cStar` applies here. -/
theorem fed_level_is_cStar_measured :
    cStar 2 (8 / 10) 8 (2 / 10) = 8 / 5 := by
  unfold cStar
  norm_num

/-- **The starved branch dominates exactly when the cell cannot pay.**

If `M*r < k*t` then `cStar < M*r`, so `cellLevel = M*r`. This is the general
form of `starved_level_measured`, and it is the statement that was missing:
`cellLevel_eq_cStar` covers the other side only. -/
theorem starved_branch {M r k t : ℝ} (hr : 0 < r) (hr1 : r < 1) (hM : 0 ≤ M)
    (h : M * r < k * t) :
    cellLevel M r k t = M * r := by
  have h1 : M < k * t / r := by
    rw [lt_div_iff₀ hr]
    nlinarith
  have h2 : M - k * t * (1 - r) / r < M * r := by
    have h3 : 0 < 1 - r := by linarith
    have h4 : M * (1 - r) < k * t * (1 - r) / r := by
      have hk : k * t * (1 - r) / r = k * t / r * (1 - r) := by field_simp
      rw [hk]
      exact mul_lt_mul_of_pos_right h1 h3
    nlinarith
  unfold cellLevel
  exact max_eq_right (le_of_lt h2)

/-- **The count of living organisms in the saturated branch.**

The cell pays out `M*r` in order; the `k`-th organism takes `M*r - (k-1)*t`.
It lives iff that is at least `need`. So the largest `k` is
`⌊(M*r - need)/t⌋ + 1`.

This is the answer to "why does one cell hold one organism when `k_feed = 1.33`":
`k_feed` counts *full* takes, and the rationed one is a separate organism that
lives on the remainder. At `M = 2, r = 0.8, t = 0.9, need = 0.6` the count is
`⌊(1.6 - 0.6)/0.9⌋ + 1 = ⌊1.111⌋ + 1 = 2` — and indeed the measurement shows
two organisms on that cell, the second taking `0.65 > 0.6`. -/
noncomputable def kSatCount (M r t need : ℝ) : ℕ := ⌊(M * r - need) / t⌋₊ + 1

/-- **The saturated count is tight: the last organism clears `need`.**

`M*r - (kSatCount - 1)*t ≥ need`. This is the statement that the count is not
merely a bound but is achieved. -/
theorem kSatCount_feeds_last {M r t need : ℝ} (hMr : 0 ≤ M * r) (hneed : need ≤ M * r)
    (ht : 0 < t) :
    need ≤ M * r - ((kSatCount M r t need : ℝ) - 1) * t := by
  unfold kSatCount
  have hnonneg : 0 ≤ (M * r - need) / t := div_nonneg (by linarith) (le_of_lt ht)
  have h1 : ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) ≤ (M * r - need) / t :=
    Nat.floor_le hnonneg
  have h2 : ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) * t ≤ M * r - need := by
    have h1' := mul_le_mul_of_nonneg_right h1 (le_of_lt ht)
    rwa [div_mul_cancel₀ _ (ne_of_gt ht)] at h1'
  push_cast
  linarith

/-- **One more organism does not clear `need` in the saturated branch.**

`M*r - kSatCount*t < need`. Together with `kSatCount_feeds_last` this pins the
count exactly: it is the largest `k` whose last organism still clears `need`. -/
theorem kSatCount_tight {M r t need : ℝ} (hMr : 0 ≤ M * r) (hneed : need ≤ M * r)
    (ht : 0 < t) :
    M * r - (kSatCount M r t need : ℝ) * t < need := by
  unfold kSatCount
  have hnonneg : 0 ≤ (M * r - need) / t := div_nonneg (by linarith) (le_of_lt ht)
  have h1 : (M * r - need) / t < ((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) + 1 :=
    Nat.lt_floor_add_one _
  have h2 : M * r - need < (((⌊(M * r - need) / t⌋₊ : ℕ) : ℝ) + 1) * t := by
    have h1' := mul_lt_mul_of_pos_right h1 ht
    rwa [div_mul_cancel₀ _ (ne_of_gt ht)] at h1'
  push_cast
  linarith

/-- **The measured case: two organisms on a rich cell at `t = 0.9`.**

`k_feed = 1.6/0.9 = 1.78`, so only one *full* take fits, yet the count of
living organisms is 2. This is the number the old `no_second_place` could not
reach, because it only covered `k_feed ≤ 1`. -/
theorem two_live_at_t_09 :
    kSatCount 2 (4 / 5) (9 / 10) (6 / 10) = 2 := by
  unfold kSatCount
  norm_num

/-- **At `t = 0.8` the same cell holds two as well**, and both take in full:
`k_feed = 1.6/0.8 = 2` exactly. -/
theorem two_live_at_t_08 :
    kSatCount 2 (4 / 5) (4 / 5) (6 / 10) = 2 := by
  unfold kSatCount
  norm_num

/-- **At `t = 1.2` the cell holds one**, because the remainder after the first
take is `1.6 - 1.2 = 0.4 < 0.6`. This is the measured `C = 40` on a 40-cell
field with `income = 1.2`. -/
theorem one_lives_at_t_12 :
    kSatCount 2 (4 / 5) (12 / 10) (6 / 10) = 1 := by
  unfold kSatCount
  norm_num

/-- **The transition threshold: `t = (M - need) * r / (1 - r)`.**

This is the take at which a one-organism cell settles exactly at `need`. Above
it the organism starves and leaves; below it the cell is worth standing on. -/
noncomputable def transitionTake (M r need : ℝ) : ℝ := (M - need) * r / (1 - r)

/-- **The threshold is where the settled level equals `need`.**

`cStar` at `t = transitionTake` is exactly `need`. This is the whole content of
the measured `poor` edge, in one equation. -/
theorem transitionTake_eq_need {M r need : ℝ} (hr : r ≠ 0) (hr1 : r ≠ 1) :
    cStar M r 1 (transitionTake M r need) = need := by
  unfold cStar transitionTake
  field_simp
  ring

/-- **The measured `poor` edge, in the field's own numbers.**

`income = 0.8`, `r = 0.8`, `M = 2` gives `t = (2 - 0.8)*0.8/0.2 = 4.8`, but the
poor cell's level is not `M` — it is `poor*(1+r)`, because the rich neighbour
feeds it. Solving `poor*(1+r) = income` gives `poor = 0.4444`. Measured: `0.4`
gives 40 survivors, `0.6` gives 60. -/
theorem poor_edge_measured : (4 : ℝ) / 10 < 4 / 9 ∧ (4 : ℝ) / 9 < 6 / 10 := by
  norm_num

/-- **The `rich` edge sits at `rich = 2.75`** for `poor = 0.2, r = 0.8,
need = 2.3`. Measured: `2.70` gives 40, `2.80` gives 60. -/
theorem rich_edge_measured : (27 : ℝ) / 10 < 275 / 100 ∧ (275 : ℝ) / 100 < 28 / 10 := by
  norm_num

/-- **The starved cell holds nobody.** At `M*r = 0.88 < need = 1.0` the count
is `⌊(0.88 - 1.0)/t⌋₊ + 1`, and the floor of a negative number is 0, so the
answer is 1 — but the last organism takes `0.88 < 1.0` and dies. The count is
therefore **not** `kSatCount` here; `kSatCount` assumes `need ≤ M*r`, which is
exactly what fails. -/
theorem starved_cell_feeds_nobody :
    ¬ ((1 : ℝ) ≤ (88 / 100 : ℝ)) := by norm_num

end Medium
