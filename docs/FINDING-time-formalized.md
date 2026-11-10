# Находка: время до стены — формализовано

**Дата:** 2026-11-10
**Проект:** МАРФАГЕНЕЗ++
**Где:** `laws/Time.lean` (4 теоремы + проба)

---

## Что формализовано

Формула из прошлого раунда:

$$t^* \approx \frac{B - \text{spread}}{\mu}$$

Теперь она в Lean — как арифметика соотношения, не как вывод из случайного процесса.

## Доказано (`laws/Time.lean`)

| теорема | утверждение |
|---|---|
| `sooner_than_naive` | расстояние до стены меньше `B`, если разброс положителен |
| `wider_room_more_time` | шире комната → больше времени |
| `no_push_no_time` | без толчка время нулевое (значит «никогда») |
| `distance_positive` | при `B > 1` расстояние до стены положительно |

Проба: `distanceProbe 20 = true`.

Проверка чисел: `timeToNarrow 3 2 1 = 1`, `timeToNarrow 3 1 1 = 2`, `timeToNarrow 100 58 1 = 42`.

## Почему первая теорема объясняет ошибку

Наивная формула `B/μ` — это «всё расстояние делить на скорость». Но среднему нужно пройти **меньше**, чем `B`:

$$\text{расстояние} = B - \text{spread} < B$$

Значит время **меньше** наивного. Это ровно то, что измерено: 11 вместо 30, 32 вместо 60, 83 вместо 150.

## Что не доказано

**Формула `t* = (B - spread)/μ` не выведена.** Доказано только, что она **меньше** наивной. Сама формула взята из измерения.

Это честная граница: Lean подтверждает **направление**, не **точность**.

## Что не получилось доказать

Две теоремы пришлось упростить или убрать:

**1. `faster_push_less_time`** — «сильнее толчок → меньше времени». Требует связи между `(d+μ₁−1)/μ₁` и `(d+μ₂−1)/μ₂` для разных `μ`, и `omega` её не видит. Убрана.

**2. `time_bounded_by_distance`** — «время не больше расстояния + 1». Тоже не поддалась.

Обе — арифметика округления вверх на `Nat`, не физика. Записано в `ELIMINATED.md`.

## Для ребёнка

> **Стена настигает раньше, чем кончается расстояние до неё. Потому что ребёнок занимает место — он не точка.**

Это то же, что закон стены из прошлого проекта: стена давит на **разброс**, а не на точку.

## Состояние

```
laws:   Bridge (309/309), Race (3), Reaction (6), Time (4)
core:   88 тестов
checks: verify_all 10/10, audit 7/7
docs:   16 заметок + ELIMINATED.md
```

---

## Серия

1. `docs/VISION.md` — манифест
2. `NOT-CLAIMED.md`
3. `docs/ELIMINATED.md`
4. `docs/FINDING-noise-creates-not-preserves.md`
5. `docs/FINDING-narrow-period.md`
6. `docs/FINDING-answering-room.md`
7. `docs/FINDING-optimum-answer.md`
8. `docs/FINDING-measuring-medium.md`
9. `docs/FINDING-self-measuring.md`
10. `docs/FINDING-memory-without-action.md`
11. `docs/FINDING-damping-threshold.md`
12. `docs/FINDING-brake-knee.md`
13. `docs/FINDING-reaction-law.md`
14. `docs/FINDING-common-reaction.md`
15. `docs/FINDING-time-to-narrow.md`
16. `docs/FINDING-time-formalized.md` — эта заметка
