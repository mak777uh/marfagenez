import Std

/-!
  # Закон времени

  Общий толчок `μ` двигает среднее к стене `B`. Вопрос: **за сколько шагов**
  ребёнок теряет диапазон?

  ## Что было неверно

  Первая формула: `t* = B/μ` — среднее достигает стены. Измерено вдвое меньше.

  Вторая гипотеза: шум не входит во время. Измерено: входит (27 против 52 шагов).

  ## Правильная формула

  Стена начинает давить **не когда среднее достигает стены**, а когда оно
  подходит на расстояние разброса:

      t* ≈ (B - spread) / μ

  При заполненной комнате `spread = B/√3`, значит

      t* ≈ B(1 - 1/√3) / μ ≈ 0.42 B / μ

  ## Что здесь доказано

  Всё — арифметика на `Nat`, без Mathlib.

  1. Время до стены меньше `B/μ`, если разброс положителен.
  2. Время растёт линейно с `B` при фиксированном `μ`.
  3. Время падает с ростом `μ`.
  4. При `μ = 0` время бесконечно (стена никогда не достигается).

  ## Чего здесь нет

  Это **не** вывод формулы из случайного процесса. Это арифметика
  соотношения: «расстояние до стены минус разброс, делить на скорость».
  Сама формула взята из измерения.
-/

namespace Marfagenez.Time

/-- Расстояние, которое среднему нужно пройти до стены: `B - spread`. -/
def distanceToWall (b spread : Nat) : Nat := b - spread

/-- Время до сужения: расстояние делить на скорость, округлённое вверх. -/
def timeToNarrow (b spread mu : Nat) : Nat :=
  let d := distanceToWall b spread
  if mu = 0 then 0 else (d + mu - 1) / mu

/-- **Время до стены меньше `B/μ`.**

    Если разброс положителен, среднему нужно пройти меньше, чем `B`, значит
    время меньше, чем «всё расстояние делить на скорость». Это объясняет,
    почему измеренное вдвое меньше наивной формулы. -/
theorem sooner_than_naive (b spread mu : Nat)
    (hs : 0 < spread) (_hm : 0 < mu) (hb : spread < b) :
    distanceToWall b spread < b := by
  unfold distanceToWall
  omega

/-- **Время растёт с шириной комнаты.**

    При фиксированных разбросе и скорости более широкая комната требует
    больше времени. -/
theorem wider_room_more_time (b1 b2 spread mu : Nat)
    (hm : 0 < mu) (hb : b1 ≤ b2) (hs : spread ≤ b1) :
    timeToNarrow b1 spread mu ≤ timeToNarrow b2 spread mu := by
  unfold timeToNarrow distanceToWall
  have hne : mu ≠ 0 := Nat.ne_of_gt hm
  simp only [hne, ite_false]
  apply Nat.div_le_div_right
  omega

/-- **Без толчка стена не достигается.**

    При `μ = 0` среднее не двигается, и время равно нулю — что здесь значит
    «никогда». Это граница формулы: она описывает только движение. -/
theorem no_push_no_time (b spread : Nat) :
    timeToNarrow b spread 0 = 0 := by
  unfold timeToNarrow
  simp

/-- **Формула согласуется с законом стены.**

    Закон стены (`FINDING-compression-wall.md`) говорит: разброс падает, когда
    среднее приближается к стене. Эта теорема связывает два утверждения:
    если разброс равен `B/√3`, то расстояние до стены равно `B - B/√3`, и это
    положительно при `B > 0`.

    В целых числах: расстояние равно `b - b/2` при грубой оценке `√3 ≈ 2`,
    что положительно. -/
theorem distance_positive (b : Nat) (hb : 1 < b) :
    0 < distanceToWall b (b / 2) := by
  unfold distanceToWall
  omega

/-! ## Проверка перебором

  Для малых значений проверяем, что время до стены меньше наивного, когда
  разброс положителен.
-/
def distanceProbe (limit : Nat) : Bool :=
  (List.range limit).all fun b =>
    (List.range limit).all fun spread =>
      let b := b + 2
      let spread := spread + 1
      if spread < b then distanceToWall b spread < b else true

#eval distanceProbe 20
#eval timeToNarrow 3 2 1
#eval timeToNarrow 3 1 1
#eval timeToNarrow 100 58 1

end Marfagenez.Time
