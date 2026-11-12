/-
  Medium/Regimes.lean

  Two regimes of a cell: the organism is either fed in full
  (`income ≤ c`, no rationing) or rationed (`c < income`).

  Rewritten for the corrected step order: the organism takes first,
  then the cell regrows.

      cellStep M r t c = (c - t) + (M - (c - t)) * r

  whose fixed point is

      c* = M + t - t / r.

  Consequences for a cell that must feed `k` organisms at cost `t₀` each:

    * income per organism is `t₀`; total draw is `k * t₀`;
    * the cell is in the full regime iff `k * t₀ ≤ c*`;
    * substituting `c*` and clearing denominators gives

          feedCapacity M r t₀ = (M - t₀) * r / (t₀ * (1 - r))

      so the full regime holds iff `k ≤ feedCapacity M r t₀`
      (requires `0 < r`, `r < 1`, `0 < t₀`).

  Everything here is stated for `r < 1`: at `r = 1` the cell refills
  completely and `feedCapacity` is infinite (see `Capacity.lean`).
-/
/-
## Two different capacities — do not confuse them

`capacity` (`Capacity.lean`) counts how many organisms a cell can FEED at all.
It is a COUNT, not a stock divided by a portion: the cell hands out
`min(t₀, what is left)` to each organism in turn, so the k-th organism gets
`min(t₀, c_k)` where `c_k` is what remained after `k - 1` takes. `k_max` is the
largest `k` with `min(t₀, c_k) ≥ maintenance`.

At `M = 2, r = 0.8, t₀ = 0.8, maintenance = 0.6` the equilibrium is `c* = 1.8`,
and the takes are 0.8, 0.8, 0.2 — so `k_max = 2`, not `M * r / t₀ = 2` by
coincidence of the numbers and not `2.25` from the old stock formula. The
recursion that the model actually executes is `takeOne` / `afterTakes` in
`Capacity.lean`; `results/EXP-22/` measured exactly `40 * min(k, 2)` survivors
for `k = 1..4`.

`feedCapacity` (this file) is a different question: for which `k` is the cell
still in the FULL regime, i.e. `k * t0 <= c*` so nobody is rationed?

    feedCapacity M r t0 = (M - t0) * r / (t0 * (1 - r))

Numerically at `M = 2, r = 0.8, t0 = 0.8`:

    k_max = 2,   feedCapacity = 6.0

So a cell can feed 2 organisms, but stays in the full regime (nobody rationed)
up to 6. Between 2 and 6 the cell is rationed; the measurement in
`results/overcrowding/run-2026-11-11T22-20-40.json` shows crowding 2 and
`C = 80` on 40 cells, i.e. `k_max`, not `feedCapacity`. Note that `k_max` here
is set by the `maintenance` threshold (0.6), not by the portion size `t₀` (0.8):
the third take of 0.2 is below `maintenance`, which is what kills it.
-/

import Medium.Field
import Medium.Convergence
import Medium.Capacity

namespace Medium

/-- Number of organisms a cell can feed in full (no rationing),
    as a function of the maintenance cost `t₀` per organism. -/
noncomputable def feedCapacity (M r t₀ : ℝ) : ℝ := (M - t₀) * r / (t₀ * (1 - r))

/-- Clearing the division in c* = M + x - x/r:
    x ≤ M + x - x/r iff x ≤ M * r. -/
theorem le_equilibrium_iff {M r x : ℝ} (hr : 0 < r) :
    x ≤ equilibrium M r x ↔ x ≤ M * r := by
  unfold equilibrium
  have e : M + x - x / r = (M * r + x * (r - 1)) / r := by
    field_simp
    ring
  rw [e, le_div_iff₀ hr]
  constructor <;> intro h <;> nlinarith

/-- The cell is in the full regime exactly when the draw fits the
    equilibrium level. -/
theorem full_regime_of_le_feedCapacity {M r t₀ k : ℝ} (hr0 : 0 < r) (hr1 : r < 1)
    (ht₀ : 0 < t₀) (hMr : t₀ ≤ M * r) (h : k * t₀ ≤ M * r) :
    k ≤ feedCapacity M r t₀ := by
  unfold feedCapacity
  rw [le_div_iff₀ (mul_pos ht₀ (by linarith : (0:ℝ) < 1 - r))]
  have h1 : k * t₀ * (1 - r) ≤ M * r * (1 - r) := by nlinarith [h, sub_pos.mpr hr1]
  have h2 : M * r * (1 - r) ≤ (M - t₀) * r := by nlinarith [hMr, hr0]
  linarith [h1, h2]

/-- The converse does **not** hold: `feedCapacity` is an upper bound on `k`
    that the equilibrium level allows, but the full regime needs the
    stronger `k * t₀ ≤ M * r`.  At `M = 2, r = 0.8, t₀ = 0.8` we get
    `feedCapacity = 6` while `M * r / t₀ = 2`, so `k = 3` satisfies the
    full-regime bound but violates `k * t₀ ≤ M * r`.
    The two coincide only when `k ≤ 1`. -/
theorem full_regime_iff {M r t₀ k : ℝ} (hr0 : 0 < r) (hr1 : r < 1) (ht₀ : 0 < t₀)
    (hMr : t₀ ≤ M * r) (hk : k ≤ 1) :
    k * t₀ ≤ equilibrium M r (k * t₀) ↔ k ≤ feedCapacity M r t₀ := by
  rw [le_equilibrium_iff hr0]
  constructor
  · intro h
    exact full_regime_of_le_feedCapacity hr0 hr1 ht₀ hMr h
  · intro h
    unfold feedCapacity at h
    rw [le_div_iff₀ (mul_pos ht₀ (by linarith : (0:ℝ) < 1 - r))] at h
    nlinarith [h, hr0, hr1, ht₀, hk]

end Medium
