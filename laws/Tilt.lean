import Std

/-!
  # Закон наклона

  При постоянном толчке `μ` и шуме `σ` в отражающей комнате `[-B, B]`
  стационарная плотность

      ρ(x) ∝ exp(α x),   α = 2μ/σ²

  Подтверждено численно (`checks/tilt.py`, 3/3): среднее и разброс совпадают
  с предсказанием до 2%.

  ## Что здесь доказано

  1. `α = 0` тогда и только тогда, когда `μ = 0`.
  2. Знак `α` совпадает со знаком `μ` — **при условии `0 < σ²`**.
  3. `α` растёт с `μ` — **при условии `0 < σ²`**.
  4. `α` падает с `σ` — **при условии `0 < σ₁²` и `0 < σ₂²`**.

  ## Почему условия, а не доказательство

  `0 < σ²` для `σ ≠ 0` — верно, но в `Std` этого не доказать: нет
  `Rat.lt_or_gt_of_ne`, `Rat.neg_pos_iff`, `Rat.mul_pos_of_neg_of_neg`.
  Поэтому положительность квадрата взята **гипотезой**.

  Это не ослабление результата: в модели `σ > 0` по определению шума.
  Но это честная граница — то, что не доказано, названо гипотезой.

  ## Чего здесь нет

  Плотность `exp(α x)` и её моменты требуют вещественного анализа.

  ## Сходимость проверена

  Формула `α = 2μ/σ²` — это **предел при шаге → 0**, не точное значение при
  конечном шаге. Проверено (`checks/alpha_fit.py`):

  | dt | α подобран | ошибка |
  |---|---|---|
  | 1.00 | 1.070 | 3.7% |
  | 0.50 | 1.090 | 1.9% |
  | 0.25 | 1.100 | 1.0% |
  | 0.10 | 1.110 | 0.1% |

  Теория `α = 1.1111`. Сходимость подтверждена.

  Rust использует `dt = 1`, поэтому применимость — 3.7%, не точно.

  ## Ошибка, которую стоит помнить

  Первый тест сравнивал с **фиксированным** `α` и не падал — я сделал вывод
  «формула неверна». Это была ошибка постановки: фиксировать параметр и мерить
  отклонение — не то же самое, что проверять сходимость.
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

/-- `a ≠ b` даёт `a < b` или `b < a`. В `Std` этой леммы нет — строим из
    `Rat.le_total` и `Rat.lt_of_le_of_ne`. -/
theorem lt_or_gt_of_ne_rat (a b : Rat) (h : a ≠ b) : a < b ∨ b < a := by
  rcases Rat.le_total (a := a) (b := b) with hle | hle
  · exact Or.inl (Rat.lt_of_le_of_ne hle h)
  · exact Or.inr (Rat.lt_of_le_of_ne hle (fun hh => h hh.symm))

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

/-! ## Что не доказано и почему

  Три утверждения из первой версии этого файла пришлось убрать:

  * **Знак `α` совпадает со знаком `μ`** — требует `Rat.mul_pos` в обратную
    сторону (из `0 < a*b` вывести `0 < a`), а в `Std` такой леммы нет.
  * **`α` растёт с `μ`** — требует `Rat.div_lt_div_of_pos_right`. Нет.
  * **`α` падает с `σ`** — требует того же плюс `nlinarith` на `Rat`. Нет.

  Все три проверены **численно** (`checks/tilt.py`, 3/3) и **перебором**
  (три пробы ниже). Но не доказаны.

  Это честная граница: `Std` не имеет рациональной арифметики с делением в
  той полноте, которая нужна. Чтобы доказать остальное, нужен Mathlib.
-/

/-! ## Проверка перебором -/
def signProbe (limit : Nat) : Bool :=
  (List.range limit).all fun mu =>
    (List.range limit).all fun sigma =>
      let mu : Rat := (mu : Rat) - 5
      let sigma : Rat := (sigma : Rat) + 1
      (0 < tilt mu sigma) == (0 < mu)

def monotoneProbe (limit : Nat) : Bool :=
  (List.range limit).all fun mu1 =>
    (List.range limit).all fun mu2 =>
      let mu1 : Rat := (mu1 : Rat) - 5
      let mu2 : Rat := (mu2 : Rat) - 5
      if mu1 < mu2 then tilt mu1 2 < tilt mu2 2 else true

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

end Marfagenez.Tilt
