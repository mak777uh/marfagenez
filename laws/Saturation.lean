import Std

/-!
  # Закон насыщения

  Разброс в комнате полуширины `B` после `t` шагов при шуме `σ`:

      spread(t, B) = min( σ√t,  B/√3 )

  * **ниже насыщения** стена давит, разброс `B/√3`;
  * **выше насыщения** ребёнок не доходит до стены, разброс `σ√t`.

  Ширина насыщения — где они встречаются:

      σ√t = B/√3   ⇒   B_sat = √3 σ√t

  Подтверждено численно (`core/tests/optimal_width.rs`, 4/4): при `B = 32, 64, 128`
  измерено 9.60–9.61 против `σ√t = 9.49`.

  ## Что здесь доказано

  Формула — это `min` двух величин. Здесь доказано то, что следует из `min`
  без вещественного анализа:

  1. Разброс никогда не больше `B/√3` — стена ограничивает сверху.
  2. Разброс никогда не больше `σ√t` — свободный ход ограничивает сверху.
  3. Разброс **монотонен** по ширине комнаты: шире никогда не хуже.
  4. Насыщение: если комната уже `σ√t·√3`, разброс равен `σ√t`.

  ## Чего здесь нет

  Что разброс **достигает** обоих пределов — это свойство случайного процесса,
  а не арифметики. Проверено численно, не доказано.
-/

namespace Marfagenez.Saturation

/-- Разброс как минимум двух пределов. В целых числах, чтобы остаться в `Std`. -/
def spread (freeWalk wallLaw : Nat) : Nat := min freeWalk wallLaw

/-- **Стена ограничивает сверху.**

    Разброс никогда не больше `B/√3`. -/
theorem bounded_by_wall (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw ≤ wallLaw :=
  Nat.min_le_right _ _

/-- **Свободный ход ограничивает сверху.**

    Разброс никогда не больше `σ√t`. -/
theorem bounded_by_free_walk (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw ≤ freeWalk :=
  Nat.min_le_left _ _

/-- **Шире никогда не хуже.**

    Если комната шире, её закон `B/√3` не меньше, и разброс не меньше. Это и есть
    замена «оптимума»: монотонность, а не компромисс. -/
theorem wider_never_worse (freeWalk wallLaw1 wallLaw2 : Nat)
    (h : wallLaw1 ≤ wallLaw2) :
    spread freeWalk wallLaw1 ≤ spread freeWalk wallLaw2 := by
  unfold spread
  omega

/-- **Насыщение.**

    Если комната достаточно широка — её закон не меньше свободного хода — то
    разброс равен свободному ходу. Шире этой границы комната не добавляет
    ничего. -/
theorem saturation (freeWalk wallLaw : Nat)
    (h : freeWalk ≤ wallLaw) :
    spread freeWalk wallLaw = freeWalk := by
  unfold spread
  exact Nat.min_eq_left h

/-- **Ниже насыщения стена давит.**

    Если закон стены меньше свободного хода, разброс равен закону стены. -/
theorem wall_binds (freeWalk wallLaw : Nat)
    (h : wallLaw ≤ freeWalk) :
    spread freeWalk wallLaw = wallLaw := by
  unfold spread
  exact Nat.min_eq_right h

/-- **Ширина насыщения.**

    Насыщение наступает ровно тогда, когда закон стены догоняет свободный ход.
    В целых числах это условие `freeWalk ≤ wallLaw`. -/
theorem saturation_width (freeWalk wallLaw : Nat) :
    spread freeWalk wallLaw = freeWalk ↔ freeWalk ≤ wallLaw := by
  unfold spread
  omega

/-! ## Проверка перебором

  Для малых значений проверяем оба режима.
-/
def saturationProbe (limit : Nat) : Bool :=
  (List.range limit).all fun f =>
    (List.range limit).all fun w =>
      let f := f + 1
      let w := w + 1
      -- The spread is never above either bound.
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
#eval spread 9 9

end Marfagenez.Saturation
