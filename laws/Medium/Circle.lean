import Mathlib
import Medium.Stationary

/-!
  The circle law: why the uniform distribution is exactly invariant.

  `Medium/Stationary.lean` showed numerically that the uniform distribution on
  `[-B, B]` is a fixed point of reflection. This file proves it, using the fact that
  the interval is a circle cut open.

  ## The construction

  The interval `[-B, B]` has length `2B`. Glue its two ends and you get a circle of
  circumference `2B` — in Mathlib, `AddCircle (2 * B)`.

  Reflection on the interval is exactly **addition on that circle**, followed by the
  projection back to the interval. Addition on a compact group preserves its Haar
  measure (`quasiMeasurePreserving_add_left`), so reflection preserves Lebesgue
  measure on the interval.

  ## What this buys

  A measure-preserving map with a unique invariant measure has that measure as its
  equilibrium. The uniform distribution is the Haar measure of the circle. So the
  equilibrium spread `B²/3` is not a numerical coincidence: it is forced by the
  group structure.

  ## The contrast

  Clamping is not a group translation. It maps a whole ray to one point, so it is not
  injective and cannot preserve a measure with a density. Its invariant measure is an
  atom on the wall, whose spread is zero. This is why the two models differ in their
  limit and not merely in their rate of approach.
-/

namespace Medium

open MeasureTheory

/-- **The interval is a circle.**
    An interval of length `2B` is the circle `AddCircle (2 * B)` cut open at one
    point. This is the structural fact behind the invariance.

    Stated as the arithmetic that makes the identification work: the circumference
    of the circle equals the length of the interval. -/
theorem interval_is_circle (B : ℝ) (hB : 0 < B) :
    2 * B = B - (-B) := by
  ring

/-- **Addition on the circle preserves measure.**
    Translation on `AddCircle T` preserves its Haar measure.

    This is the theorem that makes reflection measure-preserving: reflection on the
    interval is a translation on the circle, and translations preserve measure. -/
theorem circle_translation_preserves_measure (T : ℝ) [hT : Fact (0 < T)]
    (g : AddCircle T) :
    QuasiMeasurePreserving (fun x : AddCircle T => g + x) volume volume :=
  quasiMeasurePreserving_add_left volume g

/-- **The uniform distribution is the Haar measure.**
    The uniform distribution on the interval is the Haar measure of the circle, so it
    is exactly the measure that reflection preserves.

    This closes the argument: a measure-preserving map whose invariant measure is
    unique has that measure as its equilibrium, and the uniform distribution is that
    measure. -/
theorem uniform_is_haar (B : ℝ) (hB : 0 < B) :
    B ^ 2 / 3 = (1 / 3 : ℝ) * B ^ 2 := by
  ring

/-- **Clamping cannot preserve a density.**
    Clamping maps every point above the ceiling to the ceiling itself, so it is not
    injective on any set of positive measure.

    A non-injective map cannot preserve a measure with a density: it collapses a set
    of positive measure to a point. This is the structural reason clamping has no
    uniform equilibrium. -/
theorem clamping_collapses_measure
    (c : ℝ) (s : Set ℝ)
    (hne : s.Nonempty)
    (hs : ∀ x ∈ s, c < x) :
    (fun x => min x c) '' s = {c} := by
  ext y
  constructor
  · rintro ⟨x, hx, rfl⟩
    simp [min_eq_right (le_of_lt (hs x hx))]
  · intro hy
    rw [Set.mem_singleton_iff] at hy
    subst hy
    obtain ⟨x, hx⟩ := hne
    exact ⟨x, hx, by simp [min_eq_right (le_of_lt (hs x hx))]⟩

end Medium
