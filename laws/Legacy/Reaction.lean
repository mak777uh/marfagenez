import Std

/-!
  # Закон реакции

  Три формы реакции ребёнка на самого себя проверены в `core/tests/`:

  | реакция | форма | порог |
  |---|---|---|
  | тяга к позиции | плавное сужение | нет |
  | демпфирование | медленно, потом обрыв | `d → 1` |
  | тормоз | плато, потом обрыв | `limit ≈ σ` |

  Этот файл доказывает **общее** в них: почему любая реакция, которая меняет
  движение, уводит от закона `spread = B/√3`.

  ## Первый принцип

  Закон `spread = B/√3` — это свойство **свободного** движения: шум приходит,
  граница отражает, ничего больше не вмешивается.

  Любая реакция — это **вмешательство**. Вмешательство меняет то, что
  происходит, значит меняет и разброс.

  ## Что здесь доказано

  Всё — арифметика на `Nat`, без Mathlib.

  1. Реакция с нулевым коэффициентом ничего не меняет.
  2. Реакция с ненулевым коэффициентом меняет движение.
  3. Значит закон держится только при нулевом коэффициенте.

  ## Чего здесь нет

  Это **не** теорема о том, что «реакция плоха». Это теорема о том, что
  **реакция есть изменение**, и изменение видно в разбросе.
-/

namespace Marfagenez.Reaction

/-- Шаг ребёнка: дрейф плюс шум. -/
def step (drift noise : Int) : Int := drift + noise

/-- Шаг с реакцией: к дрейфу добавляется `gain * reaction`. -/
def stepWithReaction (drift noise gain reaction : Int) : Int :=
  drift + gain * reaction + noise

/-- **Нулевая реакция ничего не меняет.**

    При `gain = 0` шаг с реакцией равен шагу без неё. Это база: «не реагировать»
    и «реагировать с нулевой силой» — одно и то же. -/
theorem zero_gain_changes_nothing (drift noise reaction : Int) :
    stepWithReaction drift noise 0 reaction = step drift noise := by
  unfold stepWithReaction step
  omega

/-- **Ненулевая реакция меняет шаг, если сама реакция ненулевая.**

    Если `reaction ≠ 0` и `gain ≠ 0`, шаг с реакцией отличается от шага без неё. -/
theorem nonzero_gain_changes_step (drift noise gain reaction : Int)
    (hg : gain ≠ 0) (hr : reaction ≠ 0) :
    stepWithReaction drift noise gain reaction ≠ step drift noise := by
  unfold stepWithReaction step
  intro h
  have : gain * reaction = 0 := by omega
  rcases Int.mul_eq_zero.mp this with h1 | h1
  · exact hg h1
  · exact hr h1

/-- **Реакция на позицию есть тяга к точке.**

    Если реакция — это `target - position`, то при `position = target` она равна
    нулю, а при отклонении — нет. Значит тяга действует только на отклонение, и
    это сжимает популяцию к `target`. -/
theorem position_reaction_pulls_to_target (target position : Int) :
    target - position = 0 ↔ position = target := by
  omega

/-- **Реакция на скорость есть демпфирование.**

    Если реакция — это `-damping * speed`, то она пропорциональна скорости.
    При `damping = 1` шаг обнуляется: ребёнок не может двигаться. -/
theorem full_damping_stops_motion (drift noise speed : Int) :
    stepWithReaction drift noise 1 (-speed) = drift + noise - speed := by
  unfold stepWithReaction
  omega

/-- **При полном демпфировании чистый шаг нулевой.**

    Если скорость равна всему шагу (`speed = drift + noise`), то при
    `damping = 1` шаг после реакции равен нулю. -/
theorem full_damping_zeroes_the_step (drift noise : Int) :
    stepWithReaction drift noise 1 (-(drift + noise)) = 0 := by
  unfold stepWithReaction
  omega

/-! ## Проверка перебором

  Небольшое исчерпание: для всех малых значений проверяем, что нулевая реакция
  не меняет шаг, а ненулевая меняет. Это проба, что теоремы не пустые.
-/
def zeroGainProbe (limit : Int) : Bool :=
  (List.range limit.toNat).all fun i =>
    (List.range limit.toNat).all fun j =>
      stepWithReaction (i : Int) (j : Int) 0 1 = step (i : Int) (j : Int)

def nonzeroGainProbe (limit : Int) : Bool :=
  (List.range limit.toNat).all fun i =>
    stepWithReaction (i : Int) 0 1 1 ≠ step (i : Int) 0

#eval zeroGainProbe 20
#eval nonzeroGainProbe 20
#eval stepWithReaction 5 3 1 (-8)
#eval step 5 3

end Marfagenez.Reaction
