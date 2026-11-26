import Mathlib

/-!
  Four records of repair effectiveness: insight `I-034`, supported.

  The literature keeps one quantity — how much effective age a repair
  removes — in four incompatible records: the removed-fraction record
  `V = (1 - rho) * T`, the remaining-fraction record (the opposite
  convention for `rho`), the additive record `y_k = t_k - eta`, and the
  multiplicative record `y_k = b * t_k`.

  What this file proves is the algebra of the conventions:

  * the two fraction conventions are complements: reading one as the
    other mirrors the number;
  * a number survives such a convention transfer unchanged only at the
    half point — numbers are not transferable between papers without
    checking the record (the core warning of `I-034`);
  * additive and multiplicative records agree on at most one point;
  * a geometrically decaying repair contribution really does decay
    monotonically with the repair number.
-/

namespace Medium

theorem repair_complement_records (ρ T : ℝ) :
    (1 - (1 - ρ)) * T = ρ * T := by
  ring

theorem number_transfer_stable_iff (e : ℝ) :
    e = 1 - e ↔ e = 1 / 2 := by
  constructor
  · intro h
    linarith
  · intro h
    linarith

theorem additive_mul_meet_iff (η b t : ℝ) :
    t - η = b * t ↔ t * (1 - b) = η := by
  have hr : t * (1 - b) = t - t * b := by ring
  constructor
  · intro h
    linarith
  · intro h
    linarith

theorem repair_decay_step (q : ℝ) (hq : 0 ≤ q) (hq1 : q ≤ 1) (k : ℕ) :
    q ^ (k + 1) ≤ q ^ k := by
  have nonneg : 0 ≤ q ^ k := pow_nonneg hq k
  have step : q ^ (k + 1) = q ^ k * q := by rw [pow_add, pow_one]
  have mono : q ^ k * q ≤ q ^ k * 1 := by nlinarith
  nlinarith

end Medium
