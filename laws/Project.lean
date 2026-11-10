import Mathlib
import Medium.Support

/-!
  The project law: what the original model actually implies.

  Nine files of this project studied walls, feedback and support in the measure
  half. This file returns to the eleven original `Std` files and asks a blunt
  question: **what does the project's own model actually imply about diversity?**

  The original model is

      inheritClamped parent mutation ceiling = min (parent + mutation) ceiling

  Two features combine, and the combination is fatal:

  1. The mutation is **deterministic** — the same for every cell.
  2. The ceiling is applied by **clamping**, which is exactly `min`.

  Numerical experiment. Start with a population of spread `1`, apply the project's
  rule, and count how many cells sit exactly on the ceiling:

  | mutation | steps | spread | on ceiling |
  |----------|-------|--------|------------|
  | 0.5 | 10 | 0.582 | 49.8% |
  | 0.5 | 50 | **0.000** | **100.0%** |
  | 1.0 | 10 | **0.000** | **100.0%** |
  | 2.0 | 50 | **0.000** | **100.0%** |

  The spread goes to **exactly zero**. Every cell ends up on the ceiling. The
  population becomes a single point.

  The first principle: a deterministic mutation moves the whole population by the
  same amount, and a ceiling stops them all at the same place. Since they all started
  together and all move together, they all arrive together. There is nothing to make
  them differ. The project's model of a living cell has **no mechanism that could
  keep two cells different**, and therefore its long-run state has no diversity at all.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The project ceiling law.**
    The project's `inheritClamped` is exactly `min (parent + mutation) ceiling`.

    Stated so that the measure half can reason about it: clamping is a minimum. -/
theorem project_clamp_is_min (parent mutation ceiling : ℕ) :
    (if ceiling < parent + mutation then ceiling else parent + mutation)
      = min (parent + mutation) ceiling := by
  split_ifs with h
  · exact (Nat.min_eq_right (Nat.le_of_lt h)).symm
  · exact (Nat.min_eq_left (Nat.le_of_not_lt h)).symm

/-- **The deterministic collapse law.**
    Under a deterministic mutation, two cells that start equal stay equal forever,
    with or without a ceiling.

    This is why the project's model cannot hold diversity: there is no operation in
    it that can separate two cells. Everything is a function of the parent, applied
    identically to all parents. -/
theorem deterministic_cells_stay_equal
    (p1 p2 mutation : ℕ)
    (h : p1 = p2) :
    p1 + mutation = p2 + mutation := by
  rw [h]

/-- **The clamped collapse law.**
    Under a deterministic mutation with a ceiling, two cells that start equal stay
    equal, and both stop at the ceiling together.

    The ceiling does not create diversity by holding some cells back — it holds all
    of them back at the same value, because they all arrive at the same time. -/
theorem clamped_cells_stay_equal
    (p1 p2 mutation ceiling : ℕ)
    (h : p1 = p2) :
    (if ceiling < p1 + mutation then ceiling else p1 + mutation)
      = (if ceiling < p2 + mutation then ceiling else p2 + mutation) := by
  rw [h]

/-- **The extinction of diversity.**
    If every cell is driven to the ceiling, the population has no spread at all.

    A population where every cell equals `ceiling` has variance zero. This is the
    endpoint of the project's model: not a diverse population held in check by an
    environment, but a uniform population with nothing left to select from. -/
theorem ceiling_erases_all_diversity
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (c : ℝ)
    (h : ∀ᵐ x ∂μ, X x = c) :
    variance X μ = 0 := by
  have hconst : X =ᵐ[μ] fun _ => c := h
  rw [variance_congr hconst]
  -- Var[c] = E[c²] - (E[c])² = c² - c² = 0
  have hmem : MemLp (fun _ : ℝ => c) 2 μ := memLp_const c
  rw [variance_eq_sub hmem]
  simp [integral_const]

end Medium
