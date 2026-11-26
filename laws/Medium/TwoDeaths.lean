import Mathlib
import Medium.RepairCapacity

/-!
  Two death modes: insight `I-019`, supported.

  When repair costs energy (`cR` per unit of repair capacity maintained,
  from an income `E` per unit time), the system has two distinct ways to
  die: collapse of repair capacity under strong suppression `gamma`
  (`I-018`), and starvation — affordability failing while the capacity
  itself would be fine. The insight's grid run (homеostаз 3, collapse 6,
  starvation 3 on the (gamma, cR) grid; starvation at cR = 5 even before
  damage accumulates) is simulation; what this file proves is the exact
  arithmetic of the two-threshold structure:

  * affordability is itself an exact threshold in the price: maintaining
    the stationary capacity fits the income iff cR is below a computable
    level;
  * a price above E / C0 starves the system even at ZERO suppression —
    the starvation-before-collapse regime of the insight;
  * homeostasis is the conjunction of the two exact thresholds: above the
    floor (`I-018` collapse threshold) AND affordable. Each mode rules
    out the other's region.
-/

namespace Medium

theorem afford_threshold (C0 tau gamma d E cR : ℝ) (hC0 : 0 < C0)
    (htau : 0 < tau) (hgamma : 0 ≤ gamma) (hd : 0 < d) (hE : 0 < E) :
    cR * stationaryCapacity C0 tau gamma d ≤ E
      ↔ cR ≤ E * (1 + tau * gamma * d) / C0 := by
  rw [stationaryCapacity]
  have hden : 0 < 1 + tau * gamma * d := by
    have hτγ : 0 ≤ tau * gamma := mul_nonneg htau.le hgamma
    have hprod : 0 ≤ tau * gamma * d := mul_nonneg hτγ hd.le
    nlinarith
  constructor
  · intro h
    field_simp at h ⊢
    nlinarith
  · intro h
    field_simp at h ⊢
    nlinarith

theorem starvation_at_zero_suppression (C0 tau d E cR : ℝ) (hC0 : 0 < C0)
    (htau : 0 < tau) (hd : 0 < d) (hE : 0 < E)
    (hstarve : E / C0 < cR) :
    E < cR * stationaryCapacity C0 tau 0 d := by
  have hC0star : stationaryCapacity C0 tau 0 d = C0 := by
    rw [stationaryCapacity]
    norm_num
  rw [hC0star]
  have hstarve' : E < cR * C0 := by
    field_simp at hstarve
    linarith
  exact hstarve'

theorem two_death_modes (C0 tau gamma d Cmin E cR γcrit : ℝ)
    (hC0 : 0 < C0) (htau : 0 < tau) (hgamma : 0 ≤ gamma) (hd : 0 < d)
    (hmin : 0 < Cmin) (hE : 0 < E)
    (hcrit : γcrit = (C0 - Cmin) / (tau * d * Cmin)) :
    (Cmin < stationaryCapacity C0 tau gamma d
        ∧ cR * stationaryCapacity C0 tau gamma d ≤ E)
      ↔ (gamma < γcrit ∧ cR ≤ E * (1 + tau * gamma * d) / C0) := by
  have hc := collapse_threshold C0 tau gamma d Cmin γcrit htau hgamma hd hmin hcrit
  have ha := afford_threshold C0 tau gamma d E cR hC0 htau hgamma hd hE
  constructor
  · rintro ⟨hf, haff⟩
    refine ⟨?_, ha.mp haff⟩
    by_contra hcon
    have hge : γcrit ≤ gamma := by linarith
    have hcollapse := hc.mpr hge
    linarith
  · rintro ⟨hg, haff⟩
    refine ⟨?_, ha.mpr haff⟩
    by_contra hcon
    have hle := le_of_not_gt hcon
    have hcrit2 := hc.mp hle
    linarith

end Medium
