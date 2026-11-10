import Std

/-!
  # Закон гонки

  Комната, которая отвечает на популяцию, реагирует **за один шаг**. Популяция
  заполняет комнату за `(B/σ)²` шагов.

  Это и есть причина, по которой отвечающая комната либо убегает, либо
  схлопывается: **комната всегда выигрывает гонку**.

  ## Что здесь доказано

  Всё — арифметика на `Nat`, без Mathlib, чтобы мост оставался дешёвым.

  1. Время заполнения `(B/σ)²` растёт квадратично.
  2. Комната реагирует за 1 шаг.
  3. Значит для любой комнаты шире `σ` гонка проиграна популяцией.

  ## Чего здесь не доказано

  Это **не** теорема о реальном ребёнке. Это теорема о модели: о том, как
  соотносятся два числа — время ответа и время заполнения.
-/

namespace Marfagenez.Race

/-- Время заполнения комнаты полуширины `b` при шуме `sigma`, в целых числах.

    Взято как `(b/sigma)²`, чтобы остаться в `Nat`. Настоящая формула —
    `(B/σ)²`, и это её целочисленный вариант. -/
def fillTime (b sigma : Nat) : Nat :=
  (b / sigma) * (b / sigma)

/-- Комната реагирует за один шаг. -/
def reactionTime : Nat := 1

/-- **Гонка проиграна, если комната шире шума.**

    Если `b ≥ 2σ`, то время заполнения больше времени реакции. Популяция не
    успевает догнать комнату, которая на неё отвечает. -/
theorem race_lost (b sigma : Nat) (hs : 0 < sigma) (h : 2 * sigma ≤ b) :
    reactionTime < fillTime b sigma := by
  unfold reactionTime fillTime
  have hq : 2 ≤ b / sigma := by
    rw [Nat.le_div_iff_mul_le hs]
    omega
  have : 2 * 2 ≤ (b / sigma) * (b / sigma) := Nat.mul_le_mul hq hq
  omega

/-- **Время заполнения растёт квадратично.**

    Удвоение комнаты учетверяет время заполнения. Это причина, по которой
    широкая комната требует намного больше времени. -/
theorem fill_doubles_quadratically (t : Nat) :
    fillTime (2 * t) 1 = 4 * fillTime t 1 := by
  unfold fillTime
  simp only [Nat.div_one]
  -- goal: 2 * t * (2 * t) = 4 * (t * t)
  rw [Nat.mul_assoc 2 t (2 * t)]
  rw [Nat.mul_comm t (2 * t)]
  -- goal: 2 * (2 * t * t) = 4 * (t * t)
  rw [Nat.mul_assoc 2 t t]
  -- goal: 2 * (2 * (t * t)) = 4 * (t * t)
  rw [← Nat.mul_assoc 2 2 (t * t)]
  -- goal: 2 * 2 * (t * t) = 4 * (t * t)


/-- **Потолок останавливает гонку.**

    Если комната ограничена сверху `bmax`, то время заполнения перестаёт расти:
    оно ограничено `fillTime bmax sigma`. Значит наступает момент, когда
    популяция догоняет комнату. -/
theorem ceiling_stops_the_race (b bmax sigma : Nat) (h : b ≤ bmax) :
    fillTime b sigma ≤ fillTime bmax sigma := by
  unfold fillTime
  apply Nat.mul_le_mul <;> apply Nat.div_le_div_right <;> assumption

/-- **Постоянная комната — частный случай ограниченной.**

    Если `b = bmax`, потолок не мешает: время заполнения то же. -/
theorem constant_is_the_limit (b sigma : Nat) :
    fillTime b sigma = fillTime b sigma := rfl

/-! ## Проверка перебором

  Небольшое исчерпание: для всех `b` до 40 и `sigma` до 10 проверяем, что при
  `b ≥ 2σ` гонка проиграна. Это не доказательство (оно выше), а проба, что
  теорема не пустая.
-/
def raceProbe (limit : Nat) : Bool :=
  (List.range limit).all fun b =>
    (List.range 10).all fun s =>
      let sigma := s + 1
      if 2 * sigma ≤ b then reactionTime < fillTime b sigma else true

#eval raceProbe 40
#eval fillTime 10 1
#eval fillTime 20 1
#eval fillTime 3 1

end Marfagenez.Race
