import Mathlib

/-!
  The refuted channel-count law: claim node `C-007`, refuted.

  `C-007` claimed: the divergence exponent of the threshold response is
  1/(m+1), where m is the NUMBER of removal channels.

  The refutation (formula node `F-018`, literature `L-081`): channels add
  COEFFICIENTS, not orders. Two linear channels give a total (a+b)*x, so
  the response is linear in epsilon and its exponent is 1 — while
  1/(m+1) would predict 1/3. Two quadratic channels give (c+d)*x^2, the
  exponent is 1/2 — again not 1/3. The exponent tracks the ORDER of the
  leading member (rule 1/k), i.e. the channel TYPE, not the channel COUNT.

  What this file proves, with all-arithmetic witnesses at a fixed stretch:

  * two linear channels: the response at 8*epsilon is exactly 8 times the
    response at epsilon (ratio 8, exponent 1);
  * two quadratic channels: the response at 64*epsilon is exactly 8 times
    the response at epsilon (ratio 8 at stretch 64, exponent 1/2);
  * the 1/(m+1)-law at m = 2 demands a ratio whose cube is the stretch
    (8 for the linear witness, 64 for the quadratic one); both witnesses
    have ratio 8, whose cube is 512 — the law is violated by concrete
    counterexamples, for BOTH channel types at once.
-/

namespace Medium

theorem twoLinearChannels_ratio (a b ε x x8 : ℝ) (hε : 0 < ε) (hS : 0 < a + b)
    (h1 : (a + b) * x = ε) (h8 : (a + b) * x8 = 8 * ε) :
    x8 = 8 * x := by
  have hkey : (a + b) * x8 = (a + b) * (8 * x) := by
    calc (a + b) * x8 = 8 * ε := h8
      _ = 8 * ((a + b) * x) := by rw [h1]
      _ = (a + b) * (8 * x) := by ring
  exact mul_left_cancel₀ hS.ne' hkey

theorem twoLinearChannels_refute_count_law (a b ε x x8 : ℝ) (hε : 0 < ε) (hS : 0 < a + b)
    (h1 : (a + b) * x = ε) (h8 : (a + b) * x8 = 8 * ε)
    (hlaw : x8 ^ 3 = 8 * x ^ 3) : False := by
  have hr : x8 = 8 * x := twoLinearChannels_ratio a b ε x x8 hε hS h1 h8
  have he : (8 * x) ^ 3 = 512 * x ^ 3 := by ring
  rw [hr, he] at hlaw
  have hxne : x ≠ 0 := by
    intro h0
    have hz : (0:ℝ) = ε := by rw [← h1, h0]; ring
    linarith
  have hzz : (512 - 8) * x ^ 3 = 0 := by linarith
  have hx3 : x ^ 3 = 0 := (mul_eq_zero.mp hzz).resolve_left (by norm_num)
  have hxpos : 0 < x := by
    by_contra hcon
    have hxle : x ≤ 0 := by linarith
    nlinarith [h1, hS, hxle]
  have hcube : x * (x * x) ≠ 0 := by
    have hc : 0 < x * (x * x) := mul_pos hxpos (mul_pos hxpos hxpos)
    exact ne_of_gt hc
  rw [pow_three] at hx3
  exact absurd hx3 hcube

theorem twoQuadraticChannels_ratio (c d ε x x64 : ℝ) (hε : 0 < ε) (hS : 0 < c + d)
    (hx : 0 ≤ x) (hx64 : 0 ≤ x64)
    (h1 : (c + d) * x ^ 2 = ε) (h64 : (c + d) * x64 ^ 2 = 64 * ε) :
    x64 = 8 * x := by
  have hxne : x ≠ 0 := by
    intro h0
    have hz : (0:ℝ) = ε := by rw [← h1, h0]; ring
    linarith
  have hsq : x64 ^ 2 - 64 * x ^ 2 = 0 := by
    have e1 : (c + d) * (x64 ^ 2 - 64 * x ^ 2)
        = (c + d) * x64 ^ 2 - 64 * ((c + d) * x ^ 2) := by ring
    have e2 : (c + d) * (x64 ^ 2 - 64 * x ^ 2) = (c + d) * 0 := by
      rw [e1, h64, h1]
      ring
    exact mul_left_cancel₀ hS.ne' e2
  by_cases hx8 : x64 = 8 * x
  · exact hx8
  · exfalso
    have hf : (x64 - 8 * x) * (x64 + 8 * x) = 0 := by
      have e3 : (x64 - 8 * x) * (x64 + 8 * x) = x64 ^ 2 - 64 * x ^ 2 := by ring
      linarith
    rcases mul_eq_zero.mp hf with h | h
    · exact absurd (show x64 = 8 * x by linarith) hx8
    · have hx64e : x64 = 0 := by
        have hxle : x64 ≤ 0 := by linarith
        linarith
      have h8x : 8 * x = 0 := by linarith
      rcases mul_eq_zero.mp h8x with h8 | hxe2
      · exact absurd h8 (by norm_num)
      · exact absurd hxe2 hxne

theorem twoQuadraticChannels_refute_count_law (c d ε x x64 : ℝ) (hε : 0 < ε)
    (hS : 0 < c + d) (hx : 0 ≤ x) (hx64 : 0 ≤ x64)
    (h1 : (c + d) * x ^ 2 = ε) (h64 : (c + d) * x64 ^ 2 = 64 * ε)
    (hlaw : x64 ^ 3 = 64 * x ^ 3) : False := by
  have hr : x64 = 8 * x := twoQuadraticChannels_ratio c d ε x x64 hε hS hx hx64 h1 h64
  have he : (8 * x) ^ 3 = 512 * x ^ 3 := by ring
  rw [hr, he] at hlaw
  have hxne : x ≠ 0 := by
    intro h0
    have hz : (0:ℝ) = ε := by rw [← h1, h0]; ring
    linarith
  have hzz : (512 - 64) * x ^ 3 = 0 := by linarith
  have hx3 : x ^ 3 = 0 := (mul_eq_zero.mp hzz).resolve_left (by norm_num)
  have hxpos : 0 < x := by
    by_contra hcon
    have hxle : x ≤ 0 := by linarith
    exact absurd (le_antisymm hxle hx) hxne
  have hcube : x * (x * x) ≠ 0 := by
    have hc : 0 < x * (x * x) := mul_pos hxpos (mul_pos hxpos hxpos)
    exact ne_of_gt hc
  rw [pow_three] at hx3
  exact absurd hx3 hcube

end Medium
