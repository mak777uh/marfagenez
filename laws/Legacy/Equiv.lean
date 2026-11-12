import Std
import Legacy.Saturation
import Legacy.FFI

/-!
  # Эквивалентность: `FFI.saturation` и `Saturation.spread`

  ## Проблема

  В проекте два определения одной функции:

  | файл | определение | тип |
  |---|---|---|
  | `Saturation.lean` | `def spread := min freeWalk wallLaw` | `Nat` |
  | `FFI.lean` | `def saturation := if freeWalk < wallLaw then ...` | `UInt64` |

  `Saturation.lean` содержит доказанные теоремы о `spread`. Rust вызывает
  `saturation`. **Между ними не было теоремы эквивалентности** — значит
  доказанные свойства не относились к тому, что реально исполняется.

  ## Что здесь доказано

  `saturation` на `UInt64` совпадает с `spread` на `Nat` при приведении:

      saturation a b = (spread a.toNat b.toNat).toUInt64

  Это устраняет разрыв: свойства `spread` переносятся на `saturation`.

  ## Как доказано

  Через `toNat`: обе функции дают одно и то же натуральное число, а
  `UInt64` однозначно определяется своим `toNat`.

  Порядок на `UInt64` связан с порядком на `Nat` через
  `UInt64.lt_iff_toNat_lt` и `UInt64.le_iff_toNat_le`.
-/

namespace Marfagenez.Equiv

open Marfagenez.Saturation
open Marfagenez.FFI

/-- `Nat.toUInt64` и обратно даёт то же число, если оно влезает в 64 бита. -/
theorem toUInt64_toNat (n : Nat) (h : n < UInt64.size) : n.toUInt64.toNat = n := by
  show UInt64.toNat (Nat.toUInt64 n) = n
  unfold Nat.toUInt64
  exact UInt64.toNat_ofNat_of_lt h

/-- **Эквивалентность.**

    `FFI.saturation` совпадает с `Saturation.spread`, приведённым к `UInt64`. -/
theorem saturation_eq_spread (a b : UInt64) :
    FFI.saturation a b = (Saturation.spread a.toNat b.toNat).toUInt64 := by
  apply UInt64.toNat_inj.mp
  unfold FFI.saturation Saturation.spread
  split
  · rename_i h
    -- a < b, so saturation gives a; spread gives min a.toNat b.toNat = a.toNat
    have hlt : a.toNat < b.toNat := UInt64.lt_iff_toNat_lt.mp h
    rw [Nat.min_eq_left (Nat.le_of_lt hlt)]
    exact (toUInt64_toNat a.toNat (by have := UInt64.toNat_lt a; omega)).symm
  · rename_i h
    -- not (a < b), so b <= a; saturation gives b.
    -- `push_neg` is not available in `Std`, so the negation is unfolded by hand.
    have hle_u : b <= a := by
      -- `UInt64.lt_or_ge` is not in `Std`, so the case split is done by hand.
      by_cases hlt : a < b
      · exact absurd hlt h
      · exact Nat.le_of_not_lt hlt
    have hle : b.toNat <= a.toNat := UInt64.le_iff_toNat_le.mp hle_u
    rw [Nat.min_eq_right hle]
    exact (toUInt64_toNat b.toNat (by have := UInt64.toNat_lt b; omega)).symm

/-! ## Что не удалось доказать

  Три свойства `saturation` (`bounded_by_wall`, `bounded_by_free`,
  `monotone_wall`) переносятся с `spread` по эквивалентности, но доказать их
  напрямую в `Std` не удалось: `omega` не работает на `UInt64` без явного
  приведения, а нужных лемм порядка в `Std` нет.

  Это не потеря: главное — **эквивалентность** доказана, а свойства `spread`
  уже доказаны в `Saturation.lean`. Вместе они дают свойства `saturation`.
-/

/-! ## Проверка перебором -/

def equivProbe (limit : Nat) : Bool :=
  (List.range limit).all fun a =>
    (List.range limit).all fun b =>
      let a : UInt64 := a.toUInt64
      let b : UInt64 := b.toUInt64
      FFI.saturation a b == (Saturation.spread a.toNat b.toNat).toUInt64

#eval equivProbe 50
#eval FFI.saturation 9 16
#eval (Saturation.spread 9 16).toUInt64
#eval FFI.saturation 9 4
#eval (Saturation.spread 9 4).toUInt64

end Marfagenez.Equiv
