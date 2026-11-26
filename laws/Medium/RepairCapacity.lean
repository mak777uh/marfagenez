import Mathlib

/-!
  The collapse threshold of repair capacity: insight `I-018`, supported.

  The model of `I-018`: repair ability is a state `C` suppressed by the
  damage load, `dC/dt = (C0 - C) / tau - gamma * d * C`, with base capacity
  `C0`, relaxation time `tau`, suppression strength `gamma` and load `d`.
  The insight claims a threshold, not a smooth speedup: below a critical
  suppression the system holds a stationary capacity, at or above it the
  capacity sinks under any viability floor and risk grows exponentially.

  What this file proves is the arithmetic of that threshold. The stationary
  capacity is `C0 / (1 + tau * gamma * d)`; it is positive, balances the
  differential equation's gain and loss, and falls monotonically in
  `gamma`. Given a viability floor `Cmin`, the critical strength

      gamma* = (C0 - Cmin) / (tau * d * Cmin)

  is exact: the stationary capacity drops to the floor precisely when
  `gamma` reaches `gamma*`, and `gamma*` is positive whenever the floor
  is below the base capacity. The empirical part of `I-018` stays with
  the data; `I-019`'s second death mode (starvation under costly repair)
  is a different mechanism and is NOT claimed here.
-/

namespace Medium

/-- Stationary repair capacity of `I-018` under constant load and
    suppression strength. -/
noncomputable abbrev stationaryCapacity (C0 tau gamma d : ℝ) : ℝ :=
  C0 / (1 + tau * gamma * d)

theorem stationary_pos (C0 tau gamma d : ℝ) (hC0 : 0 < C0) (htau : 0 < tau)
    (hgamma : 0 ≤ gamma) (hd : 0 ≤ d) :
    0 < stationaryCapacity C0 tau gamma d := by
  have htauγ : 0 ≤ tau * gamma := mul_nonneg htau.le hgamma
  have hprod : 0 ≤ tau * gamma * d := mul_nonneg htauγ hd
  have hden : 0 < 1 + tau * gamma * d := by nlinarith
  exact div_pos hC0 hden

theorem stationary_balance (C0 tau gamma d : ℝ) (htau : 0 < tau)
    (hgamma : 0 ≤ gamma) (hd : 0 ≤ d) :
    stationaryCapacity C0 tau gamma d * (1 + tau * gamma * d) = C0 := by
  have htauγ : 0 ≤ tau * gamma := mul_nonneg htau.le hgamma
  have hpos : 0 < 1 + tau * gamma * d := by nlinarith
  have hne : (1:ℝ) + tau * gamma * d ≠ 0 := ne_of_gt hpos
  rw [stationaryCapacity]
  field_simp

theorem stationary_anti_mono (C0 tau gamma gamma' d : ℝ) (hC0 : 0 < C0)
    (htau : 0 < tau) (hgamma : 0 ≤ gamma) (hd : 0 ≤ d) (hγγ' : gamma ≤ gamma') :
    stationaryCapacity C0 tau gamma' d ≤ stationaryCapacity C0 tau gamma d := by
  have hgamma' : 0 ≤ gamma' := hgamma.trans hγγ'
  have hτγ : 0 ≤ tau * gamma := mul_nonneg htau.le hgamma
  have hτγ' : 0 ≤ tau * gamma' := mul_nonneg htau.le hgamma'
  have pos1 : 0 < 1 + tau * gamma * d := by nlinarith
  have pos2 : 0 < 1 + tau * gamma' * d := by nlinarith
  have d1 : (1:ℝ) + tau * gamma * d ≠ 0 := ne_of_gt pos1
  have d2 : (1:ℝ) + tau * gamma' * d ≠ 0 := ne_of_gt pos2
  have hgd : gamma * d ≤ gamma' * d := by nlinarith
  have hprod : tau * gamma * d ≤ tau * gamma' * d := by nlinarith [hgd, htau]
  have hstep : 1 + tau * gamma * d ≤ 1 + tau * gamma' * d := by linarith
  rw [stationaryCapacity, stationaryCapacity]
  field_simp
  nlinarith [hC0, hstep]

theorem collapse_threshold (C0 tau gamma d Cmin γcrit : ℝ)
    (htau : 0 < tau) (hgamma : 0 ≤ gamma) (hd : 0 < d) (hmin : 0 < Cmin)
    (hcrit : γcrit = (C0 - Cmin) / (tau * d * Cmin)) :
    stationaryCapacity C0 tau gamma d ≤ Cmin ↔ γcrit ≤ gamma := by
  rw [stationaryCapacity, hcrit]
  constructor
  · intro h
    field_simp at h ⊢
    nlinarith
  · intro h
    field_simp at h ⊢
    nlinarith

theorem collapse_threshold_pos (C0 tau d Cmin : ℝ) (htau : 0 < tau)
    (hd : 0 < d) (hmin : 0 < Cmin) (hminlt : Cmin < C0) :
    0 < (C0 - Cmin) / (tau * d * Cmin) := by
  have h1 : 0 < C0 - Cmin := by linarith
  have h2 : 0 < tau * d * Cmin := mul_pos (mul_pos htau hd) hmin
  exact div_pos h1 h2

end Medium
