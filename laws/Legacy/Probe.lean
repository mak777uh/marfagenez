import Mathlib
open Real
example (M r t : ℝ) (hr : 0 < r) (hr1 : r < 1) (h : 0 ≤ M - t * (1 - r) / r) :
    t * (1 - r) / r ≤ M := by
  linarith
example (M r t : ℝ) (hr : 0 < r) (hr1 : r < 1) (h : t * (1 - r) / r ≤ M) :
    0 ≤ M - t * (1 - r) / r := by
  linarith
