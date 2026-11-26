import Mathlib

/-!
  The two-axis threshold law: insight `I-039`, collected but open.

  The literature collected a joint safety condition on the dimensionless load
  `L / L*` and the dimensionless rate `v / v*`:

      (L / L*) + (v / v*)^2 <= 1

  `L*` is the static load limit — what the structure holds with the rate off.
  `v*` is the rate limit — what it survives with the load off. The insight is
  collected but NOT verified on data (`I-039` open): `I-040` records that
  literature outcomes are binary, so the form of the rate member has never
  been identified empirically.

  What this file proves is the arithmetic of the condition itself:

  * zero rate buys the full static limit, and no more;
  * zero load buys the full rate limit, and no more;
  * the safe region is down-closed: a smaller load preserves safety;
  * at a load that leaves budget `1 - L / L*`, the allowed speed squared is
    that budget times `v*^2` — the rate member is quadratic, which is the
    universal fold scale of `FINDING-316`.
-/

namespace Medium

/-- The two-axis survival condition of `I-039`: dimensionless load plus
    squared dimensionless rate at most one. -/
abbrev twoAxes (L Lstar v vstar : ℝ) : Prop :=
  L / Lstar + (v / vstar) ^ 2 ≤ 1

/-- **The static limit law.** At zero rate the condition allows at most the
    static load limit `Lstar`, and nothing beyond it. -/
theorem twoAxes_static_limit
    (L Lstar vstar : ℝ) (hLstar : 0 < Lstar)
    (h : twoAxes L Lstar 0 vstar) : L ≤ Lstar := by
  simp only [twoAxes, zero_pow two_ne_zero, zero_div, add_zero] at h
  field_simp at h
  linarith

/-- **The rate limit law.** At zero load the condition allows at most the rate
    limit, in the squared sense: `v` cannot exceed `vstar` in magnitude. -/
theorem twoAxes_rate_limit
    (Lstar v vstar : ℝ) (hvstar : 0 < vstar)
    (h : twoAxes 0 Lstar v vstar) : v ^ 2 ≤ vstar ^ 2 := by
  simp only [twoAxes, zero_div, add_zero, div_pow] at h
  field_simp at h
  linarith

/-- **The down-closure law.** A smaller load is safe whenever the larger one
    was: the safe region is closed under decreasing the load axis. -/
theorem twoAxes_mono_load
    (L L' Lstar v vstar : ℝ) (hLstar : 0 < Lstar) (hL : L' ≤ L)
    (h : twoAxes L Lstar v vstar) : twoAxes L' Lstar v vstar := by
  simp only [twoAxes] at h ⊢
  have hr : L' / Lstar ≤ L / Lstar := by
    field_simp
    nlinarith [mul_le_mul_of_nonneg_right hL hLstar.le,
               mul_le_mul_of_nonneg_left hL hLstar.le]
  linarith

/-- **The rate budget law (`FINDING-316` scale).** A load `L` leaves the budget
    `1 - L / L*`; the condition then bounds the squared rate by exactly that
    budget times `v* ^ 2`. The rate member is quadratic. -/
theorem twoAxes_rate_budget
    (L Lstar v vstar : ℝ) (hLstar : 0 < Lstar) (hvstar : 0 < vstar)
    (h : twoAxes L Lstar v vstar) :
    v ^ 2 ≤ (1 - L / Lstar) * vstar ^ 2 := by
  simp only [twoAxes, div_pow] at h
  field_simp at h ⊢
  nlinarith

end Medium
