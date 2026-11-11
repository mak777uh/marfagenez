import Mathlib
import Medium.Walls

/-!
  The novelty law: where diversity comes from, and where it goes.

  Every file so far studied how variation **dies**: selection reweights it, a ceiling
  presses it to zero, closing walls erase its shape. None studied how it is **born**.

  Looking at the repo from a distance, the answer is that the project does not have
  the mechanism at all. `Learning.lean` models mutation as

      inherit parent mutation = parent + mutation

  This is **deterministic**. If every cell receives the same mutation, every cell is
  shifted by the same amount, and the spread does not change:

      Var(X + c) = Var(X)

  A deterministic mutation moves a population. It does not diversify it. The project
  has eleven files about counting, four about walls, and **no mechanism for novelty**.

  This file supplies the mechanism, and states the two laws that govern it.
-/

namespace Medium

open MeasureTheory ProbabilityTheory

/-- **The deterministic mutation law.**
    A mutation that adds the same constant to every cell does not change the spread.

    This is the formal statement that the project's model of inheritance cannot
    create diversity. Whatever `Learning.lean` proves about a rising learning rate,
    it is a statement about the **mean**, not about the spread. -/
theorem deterministic_mutation_no_diversity
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (c : ℝ)
    (hX : AEStronglyMeasurable X μ) :
    variance (fun x => X x + c) μ = variance X μ :=
  variance_add_const hX c

/-- **The independent mutation law.**
    Diversity is created only by **independent** mutation: noise that differs from
    cell to cell. For independent random variables, variances add. -/
theorem independent_mutation_adds_diversity
    {Ω : Type*} [MeasurableSpace Ω]
    (μ : Measure Ω) [IsProbabilityMeasure μ]
    {X Y : Ω → ℝ}
    (hX : MemLp X 2 μ) (hY : MemLp Y 2 μ)
    (hXY : X ⟂ᵢ[μ] Y) :
    variance (fun ω => X ω + Y ω) μ = variance X μ + variance Y μ :=
  hXY.variance_add hX hY

/-- **The wall caps diversity.**
    A wall at `±B` caps the variance at `B²`. -/
theorem wall_caps_diversity
    (μ : Measure ℝ) [IsProbabilityMeasure μ]
    (X : ℝ → ℝ)
    (B : ℝ)
    (hB : 0 < B)
    (h : ∀ᵐ x ∂μ, X x ∈ Set.Icc B (-B))
    (hX : AEMeasurable X μ) :
    variance X μ <= B ^ 2 := by
  have hbd : variance X μ <= ((-B - B) / 2) ^ 2 := variance_le_sq_of_bounded h hX
  have heq : (-B - B) / 2 = -B := by ring
  rw [heq] at hbd
  calc variance X μ <= (-B) ^ 2 := hbd
    _ = B ^ 2 := by ring

end Medium
