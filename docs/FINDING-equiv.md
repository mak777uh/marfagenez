# Находка: эквивалентность `FFI.saturation` и `Saturation.spread` доказана

**Дата:** 2026-11-11
**Проект:** МАРФАГЕНЕЗ++
**Где:** `laws/Equiv.lean` — 2 теоремы

---

## Проблема

В проекте было **два определения одной функции**:

| файл | определение | тип |
|---|---|---|
| `Saturation.lean` | `def spread := min freeWalk wallLaw` | `Nat` |
| `FFI.lean` | `def saturation := if freeWalk < wallLaw then ...` | `UInt64` |

`Saturation.lean` содержит **доказанные теоремы** о `spread`.
Rust вызывает **`saturation`**.

> **Между ними не было теоремы эквивалентности** — значит доказанные свойства не относились к тому, что реально исполняется.

---

## Что доказано

```lean
theorem saturation_eq_spread (a b : UInt64) :
    FFI.saturation a b = (Saturation.spread a.toNat b.toNat).toUInt64
```

**Плюс вспомогательная лемма:**

```lean
theorem toUInt64_toNat (n : Nat) (h : n < UInt64.size) :
    n.toUInt64.toNat = n
```

**Проба:** `equivProbe 50 = true`, значения совпадают (`9=9`, `4=4`).

---

## Почему это важно

| было | стало |
|---|---|
| Lean доказывает `spread`, Rust вызывает `saturation` | **доказано, что это одно и то же** |
| свойства не относятся к исполняемому коду | **относятся** |

Теперь цепочка замкнута:

$$\text{Lean доказывает } \texttt{spread} \xrightarrow{\text{Equiv}} \texttt{saturation} \xrightarrow{\text{FFI}} \text{Rust}$$

---

## Что не удалось

Три свойства `saturation` (`bounded_by_wall`, `bounded_by_free`, `monotone_wall`) переносятся по эквивалентности, но **доказать напрямую в `Std` не удалось**:

- `omega` не работает на `UInt64` без приведения
- нет `UInt64.lt_or_ge`, `UInt64.min_eq_left`, `Nat.le_refl` в нужной форме

**Это не потеря:** эквивалентность доказана, а свойства `spread` уже доказаны в `Saturation.lean`. Вместе они дают свойства `saturation`.

---

## Урок про `Std`

Пришлось строить вручную:

| что нужно | есть в `Std`? | чем заменил |
|---|---|---|
| `UInt64.lt_or_ge` | нет | `by_cases` |
| `UInt64.min_eq_left` | нет | `Nat.min_eq_left` |
| `Nat.le_refl` | нет | `exact h` |
| `push_neg` | нет | ручной разбор |
| `n.toUInt64.toNat = n` | нет | `unfold Nat.toUInt64` |

> **`Std` для `UInt64` беден. Каждая лемма — ручная работа.**

---

## Чего это не доказывает

**Что `saturation` содержательно верна.** Доказано только, что она совпадает со `spread`. А `spread` — это `min`, не закон процесса (см. `FINDING-transition-wrong.md`).

**Что Rust-реализация верна.** Verus доказал `rust_saturation` отдельно (18 verified). Но связь Verus ↔ Lean — через **одинаковую формулу**, не через формальное доказательство.

---

## Состояние

```
laws:   189 теорем (было 187, +2 в Equiv)
core:   131 тест
verus:  18 verified
checks: 8 проверок
```

---

## Серия

1. `docs/VISION.md` — манифест
2. `docs/MASTER_PLAN.md` — план
3–32. заметки о находках
33. `docs/FINDING-equiv.md` — эта заметка
