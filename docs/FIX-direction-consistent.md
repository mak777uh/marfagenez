# Исправление: `direction` теперь показывает решение, а не пересчёт

**Дата:** 2026-11-12
**Файлы:** `core/src/memory.rs`, `core/src/life.rs`, `core/src/trace.rs`
**Тест:** `the_direction_is_the_decision_not_a_recomputation`

---

## Дефект

**`samples()` пересчитывал `direction` при чтении:**

```rust
// The direction is not stored; it is recomputed for the reading.
direction: r.direction(),
```

**`r.direction()` смотрит на поле СЕЙЧАС** — то есть **после** шага и **после**
`regrow_all`.

**Значит `direction` в `Sample` показывал не то, что организм сделал, а то, что
он сделал бы сейчас.**

---

## Как это проявлялось

**`n = 20`, 5 организмов «стоят»:**

| клетка | `here` | `left` | `right` |
|---|---|---|---|
| 17 | **1.8333** | **1.9667** | 1.8333 |
| 33 | **1.8333** | **1.9667** | 1.8333 |
| 37 | **1.8333** | **1.9667** | 1.8333 |
| 25 | **1.8333** | **1.9667** | 1.8333 |

**Сосед богаче, а организм «стоит».** Политика `sighted` так не поступила бы.

**Объяснение:** сосед стал богаче **после** шага (отрастание). Организм решил
стоять, когда сосед был **беднее**.

---

## Исправление

### 1. Сохраняем решение в организме

```rust
// memory.rs
pub struct Remembering {
    /// The direction chosen on the last step, stored so a reading can show the
    /// decision the organism actually made rather than the one it would make now.
    pub last_direction: i32,
    ...
}
```

### 2. Записываем решение при шаге

```rust
// life.rs, advance()
let direction = match self.policy { ... };

r.last_direction = direction;   // ← сохраняем

if direction != 0 && r.organism.spend(r.move_cost) { ... }
```

### 3. Читаем сохранённое

```rust
// life.rs, samples()
direction: r.last_direction,   // было: r.direction()
```

---

## Проверка до и после

| | до | после |
|---|---|---|
| стоят (`n = 20`) | **5** | **0** |
| из них с богатым соседом | **4** | **0** |

**После исправления ни один стоящий не видит соседа богаче.**

**И все 20 движутся** — потому что `sighted` в `alternating` **всегда** видит
разницу.

---

## Тест

```rust
#[test]
fn the_direction_is_the_decision_not_a_recomputation() {
    // Every sample that claims to stand still must not be standing next to a
    // neighbour that is richer by a wide margin.
}
```

**Проверено:** `112 passed` (было 111).

---

## Что это меняет в прошлых выводах

**Затронуты разборы поведения:**
- `_check_still.py` — «6% стоят», «25% стоят», «12% стоят» — **неверно**
- `_check_visits.py` — «9.8 клеток», «3.5 клеток» — **частично неверно**

**НЕ затронуты:**
- **ёмкость `C = cells × M·r/income`** — измерена по числу живых
- **поле стабилизируется** — измерено по разбросу и среднему
- **два режима** — доказаны в Lean
- **`c* = M − t/r`** — доказано
- **`разрыв × (1−r)`** — доказано

---

## Что это не доказывает

**Не доказано, что других рассогласований нет.** `taken` в `Sample` всегда
`0.0` — тоже не заполняется.

**Не проверено на всех политиках.** Тест только для `Sighted`.

**Не проверено, что `direction` до исправления влиял на эксперименты.** В
`EXP-12`–`EXP-16` он не использовался.

---

## Что делать дальше

**1. Заполнить `taken`.** Сейчас всегда `0.0` — ещё один незаполненный столбец.

**2. Перепроверить разборы поведения** с исправленной трассировкой.

**3. Записать в `LESSONS.md`.**

---

## Данные

```
results/sighted/trace-sighted-1794435228.json  (после исправления)
```

**Проверка:** `_verify_fix.sh`

---

## Серия

1. `docs/OBSERVATION-2026-11-11.md`
2. `docs/FINDING-frozen-ceiling.md`
3. `docs/FINDING-random-plateau-failed.md`
4. `docs/FINDING-remember-is-choice.md`
5. `docs/FINDING-memory-weak.md`
6. `docs/FINDING-sighted-depletes.md`
7. `docs/FINDING-field-law.md`
8. `docs/FINDING-convergence.md`
9. `docs/FINDING-capacity.md`
10. `docs/FINDING-motion-doubles.md`
11. `docs/FINDING-capacity-formula.md`
12. `docs/FINDING-formula-confirmed.md`
13. `docs/FINDING-capacity-exact.md`
14. `docs/FINDING-capacity-proved.md`
15. `docs/SYNTHESIS-2026-11-12.md`
16. `docs/FINDING-two-regimes.md`
17. `docs/FINDING-third-threshold.md`
18. `docs/FINDING-third-threshold-failed.md`
19. `docs/FINDING-field-stable.md`
20. `docs/FINDING-field-above-equilibrium.md`
21. `docs/FINDING-p-is-artifact.md`
22. `docs/FINDING-trace-inconsistent.md`
23. `docs/FIX-direction-consistent.md` — эта заметка
