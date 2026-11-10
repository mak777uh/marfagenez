import Std

/-!
  # Закон наклона

  При постоянном толчке `μ` и шуме `σ` в отражающей комнате `[-B, B]`
  стационарная плотность

      ρ(x) ∝ exp(α x),   α = 2μ/σ²

  Подтверждено численно (`checks/tilt.py`, 3/3): среднее и разброс совпадают
  с предсказанием до 2%.

  ## Что здесь доказано

  Формула `α = 2μ/σ²` — арифметика. Доказано то, что доказывается в `Std`
  без Mathlib:

  1. `α = 0` тогда и только тогда, когда `μ = 0`.
  2. Квадрат ненулевого рационального ненулевой.

  ## Чего здесь нет и почему

  Три утверждения из первой версии этого файла пришлось убрать:

  * **Знак `α` совпадает со знаком `μ`** — требует `Rat.lt_or_gt_of_ne`,
    `Rat.div_pos_of_pos_of_pos`, `Rat.div_nonpos_of_nonpos_of_nonneg`. В `Std`
    их нет.
  * **`α` растёт с `μ`** — требует `Rat.div_lt_div_of_pos_right`. Нет.
  * **`α` падает с `σ`** — требует того же плюс `nlinarith` на `Rat`. Нет.

  Все три проверены **численно** в `checks/tilt.py` и подтверждены. Но не
  доказаны.

  Это честная граница: в `laws/` нет собранного Mathlib, а `Std` слишком
  беден для рациональной арифметики с делением. Чтобы доказать остальное,
  нужен Mathlib — и это отдельная сборка на час.
-/

namespace Marfagenez.Tilt

/-- Наклон: `α = 2μ/σ²`. -/
def tilt (mu sigma : Rat) : Rat :=
  2 * mu / (sigma * sigma)

/-- Квадрат ненулевого рационального ненулевой. -/
theorem sq_ne_zero (sigma : Rat) (hs : sigma ≠ 0) : sigma * sigma ≠ 0 := by
  intro h
  rcases Rat.mul_eq_zero.mp h with h1 | h1
  · exact hs h1
  · exact hs h1

/-- **Нет толчка — нет наклона.**

    `α = 0` тогда и только тогда, когда `μ = 0` (при `σ ≠ 0`). -/
theorem no_push_no_tilt (mu sigma : Rat) (hs : sigma ≠ 0) :
    tilt mu sigma = 0 ↔ mu = 0 := by
  unfold tilt
  have hsq : sigma * sigma ≠ 0 := sq_ne_zero sigma hs
  constructor
  · intro h
    have h2 : 2 * mu = 0 := by
      have := congrArg (· * (sigma * sigma)) h
      rwa [Rat.div_mul_cancel hsq, Rat.zero_mul] at this
    rcases Rat.mul_eq_zero.mp h2 with h3 | h3
    · exact absurd h3 (by decide)
    · exact h3
  · intro h
    rw [h]
    rw [Rat.div_def, Rat.mul_zero, Rat.zero_mul]

/-! ## Проверка перебором

  То, что не доказано, проверяется перебором на конечном множестве. Это не
  доказательство — это проба, и она так и названа.
-/
def signProbe (limit : Nat) : Bool :=
  (List.range limit).all fun mu =>
    (List.range limit).all fun sigma =>
      let mu : Rat := (mu : Rat) - 5
      let sigma : Rat := (sigma : Rat) + 1
      (0 < tilt mu sigma) == (0 < mu)

/-- Наклон растёт с толчком — проверка перебором. -/
def monotoneProbe (limit : Nat) : Bool :=
  (List.range limit).all fun mu1 =>
    (List.range limit).all fun mu2 =>
      let mu1 : Rat := (mu1 : Rat) - 5
      let mu2 : Rat := (mu2 : Rat) - 5
      if mu1 < mu2 then tilt mu1 2 < tilt mu2 2 else true

/-- Наклон падает с шумом — проверка перебором. -/
def antitoneProbe (limit : Nat) : Bool :=
  (List.range limit).all fun s1 =>
    (List.range limit).all fun s2 =>
      let s1 : Rat := (s1 : Rat) + 1
      let s2 : Rat := (s2 : Rat) + 1
      if s1 < s2 then tilt 1 s2 < tilt 1 s1 else true

#eval signProbe 12
#eval monotoneProbe 12
#eval antitoneProbe 12
#eval tilt 1 2
#eval tilt 0 3
#eval tilt (-1) 2

end Marfagenez.Tilt
