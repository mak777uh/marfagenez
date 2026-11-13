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

          feedCapacity M r t₀ = M * r / t₀

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

At `M = 2, r = 0.8, t₀ = 0.8, maintenance = 0.6` the one-organism equilibrium is
`c* = M + t₀ - t₀/r = 1.2` and the two-organism level is
`cStar(2) = M - 2*t₀*(1-r)/r = 1.6`. With two organisms
standing on the cell the takes are 0.8, 0.8 — both full, and both above
`maintenance = 0.6`. A third would take `1.6 - 1.6 = 0.0`, below maintenance, so
the count of *full* takes is `k_max = ⌊M*r/t₀⌋ = ⌊2.0⌋ = 2`. The recursion that
the model actually executes is `takeOne` / `afterTakes` in `Capacity.lean`;
`results/EXP-22/` measured exactly `40 * min(k, 2)` survivors for `k = 1..4`.

`feedCapacity` (this file) is a different question: for which `k` is the cell
still in the FULL regime, i.e. `k * t0 <= c*` so nobody is rationed?

    feedCapacity M r t0 = M * r / t0

Numerically at `M = 2, r = 0.8, t0 = 0.8`:

    feedCapacity = 2.0

**This used to say 6.0, and 6.0 was wrong.** The old formula was
`(M - t₀) * r / (t₀ * (1 - r))`, derived from the pre-2026-11-12 equilibrium
`M - t/r`. Solving `k * t₀ = M + k*t₀ - k*t₀/r` symbolically (sympy) gives
`k = M * r / t₀` exactly — the `t₀` cancels out of the numerator. At the
project's numbers that is 2.0, not 6.0.

So the claim that "a cell stays in the full regime up to 6" is dead. The
measurement that used to accompany this paragraph (`crowding 2`, `C = 80` on 40
cells, `results/overcrowding/run-2026-11-11T22-20-40.json`) was recorded under
the old clamp order and is void; it is no longer cited here as support for
anything.

What the current measurement says (`exp75`, 40 cells, `rich = 2.0`,
`n = 160`, 4000 steps, `sighted`) is `crowding = 1.00` and mean energy
`10.0000` in all eight runs, with `C = 20` when half the cells are too poor to
feed and `C = 40` when every cell feeds. So the measured occupancy is one per
cell, below the `feedCapacity = 2` this file derives. The gap between the bound
and the measurement is recorded in `Medium/Capacity.lean` as open: this file
proves a cell *can* feed two, not that two ever arrive.
-/

import Medium.Field
import Medium.Convergence
import Medium.Capacity

namespace Medium

/-- Number of organisms a cell can feed in full (no rationing),
    as a function of the maintenance cost `t₀` per organism. -/
noncomputable def feedCapacity (M r t₀ : ℝ) : ℝ := M * r / t₀

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
    equilibrium level.  The two conditions are the same condition:
    `k * t₀ ≤ equilibrium M r (k * t₀)` iff `k ≤ M * r / t₀`. -/
theorem full_regime_of_le_feedCapacity {M r t₀ k : ℝ} (hr0 : 0 < r)
    (ht₀ : 0 < t₀) (h : k * t₀ ≤ M * r) :
    k ≤ feedCapacity M r t₀ := by
  unfold feedCapacity
  rw [le_div_iff₀ ht₀]
  nlinarith [h]

/-- The full regime and `feedCapacity` say the same thing — there is no
    gap between them.  (Before 2026-11-12 this file claimed a gap: `k_max = 2`
    but `feedCapacity = 6`.  That came from the pre-fix equilibrium
    `M - t/r`.  With `c* = M + t - t/r` the two coincide exactly.) -/
theorem full_regime_iff {M r t₀ k : ℝ} (hr0 : 0 < r) (ht₀ : 0 < t₀) :
    k * t₀ ≤ equilibrium M r (k * t₀) ↔ k ≤ feedCapacity M r t₀ := by
  rw [le_equilibrium_iff hr0]
  unfold feedCapacity
  rw [le_div_iff₀ ht₀]

end Medium
