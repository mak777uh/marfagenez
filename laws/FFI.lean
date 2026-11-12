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

  ## Все пять законов

  | закон | функции |
  |---|---|
  | насыщение | `marfa_saturation`, `marfa_fraction_pct`, `marfa_fold_shifted` |
  | гонка | `marfa_fill_time`, `marfa_reaction_time`, `marfa_race_lost` |
  | реакция | `marfa_reaction_changes`, `marfa_zero_gain_keeps` |
  | время | `marfa_distance_to_wall`, `marfa_time_to_narrow`, `marfa_sooner_than_naive` |
  | наклон | `marfa_tilt_num`, `marfa_tilt_den`, `marfa_tilt_sign` |
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

/-- Складка точки в комнату `[-b, b]`, сдвинутая на `b`: результат в `[0, 2b]`. -/
@[export marfa_fold_shifted]
def foldShifted (b x : UInt64) : UInt64 :=
  if b = 0 then 0
  else
    let period := 4 * b
    let u := (x + b) % period
    if u ≤ 2 * b then u else period - u

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

/-! ## 3. Реакция

Закон реакции: реакция с `g ≠ 0` меняет шаг; при `g = 0` не меняет.

В `UInt64` «нулевая реакция» — это `g = 0`, а «ненулевая» — `g ≠ 0`. Функция
отвечает, **меняет ли** реакция шаг.
-/

/-- Меняет ли реакция шаг: `g ≠ 0` и `reaction ≠ 0`. -/
@[export marfa_reaction_changes]
def reactionChanges (gain reaction : UInt64) : Bool :=
  decide (gain ≠ 0 ∧ reaction ≠ 0)

/-- Сохраняет ли нулевая реакция шаг: `g = 0`. -/
@[export marfa_zero_gain_keeps]
def zeroGainKeeps (gain : UInt64) : Bool :=
  decide (gain = 0)

/-! ## 4. Время

Закон времени: `t* = (B - spread)/μ`, и это меньше наивного `B/μ`.
-/

/-- Расстояние до стены: `b - spread` (не меньше нуля). -/
@[export marfa_distance_to_wall]
def distanceToWall (b spread : UInt64) : UInt64 :=
  if spread ≤ b then b - spread else 0

/-- Время до сужения: `ceil(distance / mu)`. -/
@[export marfa_time_to_narrow]
def timeToNarrow (b spread mu : UInt64) : UInt64 :=
  if mu = 0 then 0
  else
    let d := distanceToWall b spread
    if d = 0 then 0 else (d + mu - 1) / mu

/-- Наивное время: `ceil(b / mu)`. -/
@[export marfa_naive_time]
def naiveTime (b mu : UInt64) : UInt64 :=
  if mu = 0 then 0 else (b + mu - 1) / mu

/-- Время до стены меньше наивного — если разброс положителен. -/
@[export marfa_sooner_than_naive]
def soonerThanNaive (b spread mu : UInt64) : Bool :=
  decide (timeToNarrow b spread mu < naiveTime b mu)

/-! ## 5. Наклон

Закон наклона: `α = 2μ/σ²`. В `UInt64` это дробь: числитель `2μ`, знаменатель `σ²`.
-/

/-- Числитель наклона: `2μ`. -/
@[export marfa_tilt_num]
def tiltNum (mu : UInt64) : UInt64 := 2 * mu

/-- Знаменатель наклона: `σ²`. -/
@[export marfa_tilt_den]
def tiltDen (sigma : UInt64) : UInt64 := sigma * sigma

/-- Знак наклона: `+1`, `0` или `-1` (в `UInt64` как `1`, `0`, `2`).

    `0` — нет толчка, нет наклона. `1` — положительный. `2` — отрицательный
    (толчок вниз; в `UInt64` отрицательных нет, поэтому знак кодируется). -/
@[export marfa_tilt_sign]
def tiltSign (mu : UInt64) : UInt64 :=
  if mu = 0 then 0 else 1

/-- Наклон равен нулю тогда и только тогда, когда нет толчка. -/
@[export marfa_tilt_zero_iff]
def tiltZeroIff (mu : UInt64) : Bool :=
  -- `tiltNum mu = 2*mu`, so it is zero exactly when `mu` is zero.
  -- Checked as an implication in both directions, which `decide` can reduce.
  decide (mu = 0) == decide (tiltNum mu = 0) && mu = 0

/-! ## Проверка -/

#eval saturation 9 16
#eval fractionPct 9 16
#eval fillTime 3 1
#eval raceLost 3 1
#eval reactionChanges 1 1
#eval zeroGainKeeps 0
#eval distanceToWall 100 58
#eval timeToNarrow 100 58 1
#eval naiveTime 100 1
#eval soonerThanNaive 100 58 1
#eval tiltNum 5
#eval tiltDen 3
#eval tiltSign 5
#eval tiltZeroIff 0

end Marfagenez.FFI
