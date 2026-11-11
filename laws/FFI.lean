import Std

/-!
  # FFI: законы, вызываемые из Rust

  Здесь только то, что Rust может вызвать напрямую: `UInt64` и `Bool`.
  Экспортируется через `@[export]`, компилируется в C (`lean -c`), линкуется
  с `libleanshared`.

  ## Почему только UInt64

  `Nat` в Lean — это `lean_object*` (указатель на кучу), а `UInt64` — это
  настоящий `uint64_t`. Для моста нужен второй: без боксинга, без сборки
  мусора, без инициализации рантайма.

  ## Что экспортируется

  Законы из `laws/`, переписанные на целых числах:

  1. **Насыщение**: `spread = min(freeWalk, wallLaw)`.
  2. **Гонка**: время заполнения `(b/σ)²`.
  3. **Ширина насыщения**: `√3·σ·√t` в целых числах.
  4. **Складка**: отражение точки в комнату.

  ## Что это даёт

  Rust может **спросить Lean**, что предсказывает закон, и сравнить с тем, что
  дала симуляция. Это третий слой связи: не «Lean и Rust отдельно», а
  **Rust спрашивает Lean**.
-/

namespace Marfagenez.FFI

/-! ## 1. Насыщение -/

/-- Разброс как минимум двух пределов. -/
@[export marfa_saturation]
def saturation (freeWalk wallLaw : UInt64) : UInt64 :=
  if freeWalk < wallLaw then freeWalk else wallLaw

/-- Доля закона в процентах: `100 * spread / law`. -/
@[export marfa_fraction_pct]
def fractionPct (spread law : UInt64) : UInt64 :=
  if law = 0 then 0 else (100 * spread) / law

/-! ## 2. Гонка -/

/-- Время заполнения `(b/σ)²`. -/
@[export marfa_fill_time]
def fillTime (b sigma : UInt64) : UInt64 :=
  if sigma = 0 then 0 else (b / sigma) * (b / sigma)

/-- Комната реагирует за один шаг. -/
@[export marfa_reaction_time]
def reactionTime : UInt64 := 1

/-- Гонка проиграна, если время заполнения больше времени реакции. -/
@[export marfa_race_lost]
def raceLost (b sigma : UInt64) : Bool :=
  decide (reactionTime < fillTime b sigma)

/-! ## 3. Складка -/

/-- Складка точки в комнату `[-b, b]`. Период `4b`, сдвиг на `b`.

    Возвращает `b - |u - 2b|`, где `u = (x + b) mod 4b`. В `UInt64` без знака,
    поэтому результат сдвинут на `b`: возвращается `u'` в `[0, 2b]`, и Rust
    вычитает `b`. -/
@[export marfa_fold_shifted]
def foldShifted (b x : UInt64) : UInt64 :=
  if b = 0 then 0
  else
    let period := 4 * b
    let u := (x + b) % period
    if u ≤ 2 * b then u else period - u

/-! ## 4. Проверка -/

#eval saturation 9 16
#eval saturation 9 4
#eval fractionPct 9 16
#eval fillTime 3 1
#eval raceLost 3 1
#eval foldShifted 3 4

end Marfagenez.FFI
