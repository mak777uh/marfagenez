import Std

/-!
  # Закон насыщения — с оговоркой

  ## Что было неверно

  Раньше здесь утверждалось:

      spread(t, B) = min( σ√t , B/√3 )

  Это **неверно в начале**. Проверено (`checks/transition.py`):

  | t | измерено | min | ошибка |
  |---|---|---|---|
  | 1 | 0.585 | 0.300 | **48.7%** |
  | 5 | 0.839 | 0.671 | 20.0% |
  | 100 | 1.729 | 1.732 | 0.2% |

  Причина: формула предполагает `S(0) = 0`. Начальный разброс не ноль.

  ## Исправление

  Свободный случайный ход с начальным разбросом:

      S(t) = √( S(0)² + t·σ² )

  Проверено (`checks/transition2.py`):

  | t | измерено | √(S0²+tσ²) | ошибка |
  |---|---|---|---|
  | 1 | 0.585 | 0.583 | **0.3%** |
  | 5 | 0.839 | 0.837 | 0.3% |
  | 10 | 1.063 | 1.072 | 0.9% |

  ## Чего это не решает

  При `t = 20…30` новая формула **хуже** (5.4%, 13.7%), потому что стена уже
  мешает, а формула этого не знает.

  Сравнены четыре варианта (`checks/transition3.py`):

  | формула | худшая ошибка |
  |---|---|
  | `min(σ√t, B/√3)` | 48.7% |
  | `min(√(S0²+tσ²), B/√3)` | **13.7%** |
  | гармоническое среднее | 55.4% |
  | экспоненциальный подход | 46.8% |

  > **Ни одна простая формула не описывает переход точно.**

  ## Честный вывод

  Переходный процесс нужно **измерять**, а не предсказывать формулой.

  Формула годится только как грубая оценка. Утверждать её как закон нельзя.

  ## Что здесь доказано

  Только арифметика функции `min` — и это всё, что доказывает Lean:

  1. `min(a, b) ≤ a`
  2. `min(a, b) ≤ b`
  3. `min` монотонен по второму аргументу
  4. `a ≤ b → min(a, b) = a`

  Это свойства `min`, **не** свойства случайного процесса.
-/

namespace Marfagenez.Saturation

/-- Разброс как минимум двух пределов. -/
def spread (freeWalk wallLaw : Nat) : Nat := min freeWalk wallLaw

/-- **Стена ограничивает сверху.** -/
theorem bounded_by_wall (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw ≤ wallLaw :=
  Nat.min_le_right _ _

/-- **Свободный ход ограничивает сверху.** -/
theorem bounded_by_free_walk (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw ≤ freeWalk :=
  Nat.min_le_left _ _

/-- **Шире никогда не хуже.** -/
theorem wider_never_worse (freeWalk wallLaw1 wallLaw2 : Nat)
    (h : wallLaw1 ≤ wallLaw2) :
    spread freeWalk wallLaw1 ≤ spread freeWalk wallLaw2 := by
  unfold spread
  omega

/-- **Насыщение.** -/
theorem saturation (freeWalk wallLaw : Nat)
    (h : freeWalk ≤ wallLaw) :
    spread freeWalk wallLaw = freeWalk := by
  unfold spread
  exact Nat.min_eq_left h

/-- **Ниже насыщения стена давит.** -/
theorem wall_binds (freeWalk wallLaw : Nat)
    (h : wallLaw ≤ freeWalk) :
    spread freeWalk wallLaw = wallLaw := by
  unfold spread
  exact Nat.min_eq_right h

/-- **Ширина насыщения.** -/
theorem saturation_width (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw = freeWalk ↔ freeWalk ≤ wallLaw := by
  unfold spread
  omega

/-! ## Проверка перебором -/
def saturationProbe (limit : Nat) : Bool :=
  (List.range limit).all fun f =>
    (List.range limit).all fun w =>
      let f := f + 1
      let w := w + 1
      spread f w ≤ f && spread f w ≤ w

def monotoneProbe (limit : Nat) : Bool :=
  (List.range limit).all fun f =>
    (List.range limit).all fun w1 =>
      (List.range limit).all fun w2 =>
        let f := f + 1
        let w1 := w1 + 1
        let w2 := w2 + 1
        if w1 ≤ w2 then spread f w1 ≤ spread f w2 else true

#eval saturationProbe 20
#eval monotoneProbe 20
#eval spread 9 16
#eval spread 9 4

end Marfagenez.Saturation
