import Mathlib

/-!
# `%` on `ℝ` is zero — and the fold as it was written does nothing

`Legacy/Convergence2.lean` carried `fold_identifies` as a `sorry`. The honest
finding is that **the statement was false**, and for a reason that is worth
recording: `%` on a field is `Field.toEuclideanDomain`, whose remainder is
`a - a * b / b = 0`. So `x % b = 0` for every `x` and every `b ≠ 0`.

The "fold" in `Legacy/Convergence2.lean` was therefore the constant `B - |0 - 2B| = -B`.
It did not fold anything, and the `sorry` was hiding a definition that had no
content. This file proves the zero law and the resulting collapse, so the
mistake cannot be repeated silently.

## What is proved

* `mod_field_eq_zero` — `a % b = 0` for `b ≠ 0` in a field
* `real_mod_eq_zero` — the `ℝ` case
* `fold_collapse` — `fold B x = -B` for `0 < B` (the fold is constant)

## What this does NOT prove

That a fold into `[-B, B]` is impossible. It is possible — with `Int.fmod` on the
floor, or with `x - 4B * ⌊(x+B)/(4B)⌋` — but it is **not** what `Legacy` wrote,
and it is not what `%` gives. See `docs/FINDING-percent-on-real-is-zero.md`.
-/

namespace Medium

/-- In a field, `a % b = a - a * b / b`, which is `0` when `b ≠ 0`. -/
theorem mod_field_eq_zero {K : Type*} [Field K] (a b : K) (hb : b ≠ 0) :
    a % b = 0 := by
  have h : a % b = a - a * b / b := Field.mod_eq a b
  rw [h]
  rw [show a * b / b = a by field_simp]
  ring

/-- The `ℝ` case of `mod_field_eq_zero`. -/
theorem real_mod_eq_zero (a b : ℝ) (hb : b ≠ 0) : a % b = 0 :=
  mod_field_eq_zero a b hb

/-- The fold as written in `Legacy/Convergence2.lean` is the constant `-B`.

Note the hypothesis: `0 < B`, not merely `B ≠ 0`. For `B < 0` the expression is
`B - |2B| = 3B ≠ -B`, so the collapse holds only on the positive range that the
legacy code actually used. -/
theorem fold_collapse (B x : ℝ) (hB : 0 < B) :
    B - |((x + B) % (4 * B) + 4 * B) % (4 * B) - 2 * B| = -B := by
  have h4 : (4 : ℝ) * B ≠ 0 := by linarith
  have h0 : (x + B) % (4 * B) = 0 := by
    have h : (x + B) % (4 * B) = (x + B) - (x + B) * (4 * B) / (4 * B) := Field.mod_eq _ _
    rw [h, show (x + B) * (4 * B) / (4 * B) = (x + B) by field_simp]
    ring
  have h0' : (4 * B) % (4 * B) = 0 := by
    have h : (4 * B) % (4 * B) = (4 * B) - (4 * B) * (4 * B) / (4 * B) := Field.mod_eq _ _
    rw [h, show (4 * B) * (4 * B) / (4 * B) = (4 * B) by field_simp]
    ring
  rw [h0, zero_add, h0']
  rw [abs_of_neg (show (0 : ℝ) - 2 * B < 0 by linarith)]
  ring

end Medium
