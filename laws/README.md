# laws/ — законы среды, доказанные в Lean 4

**48 файлов. 180 теорем. Сборка зелёная.**

---

## Что это

Формальное описание среды, в которой может расти ребёнок. Не метафора — теоремы о
распределениях, мерах и отображениях, плюс явные границы того, что **не** доказано.

Каждая теорема — утверждение о модели. Модель — не жизнь. См. [`../docs/CLAIMS.md`](../docs/CLAIMS.md).

---

## Версии — зафиксированы

| | версия |
|---|---|
| **Lean** | `4.36.0-rc2` |
| **Lake** | `5.0.0-src+b35cb10` |
| **Mathlib** | `2ddf59c8f14245864e6c0ed227a2dab76b9efea2` |

**Не обновлять без полной пересборки и проверки 180 теорем.** Обновление Mathlib — 3 часа
и ~10 ГБ. Версии зафиксированы в `lake-manifest.json`.

### Почему именно эти версии

Проверено на совместимость с инструментами проекта:

| инструмент | версия | совместим |
|---|---|---|
| Rust | 1.85.0 (WSL) / 1.99.1 (Win) | ✅ |
| Verus | 0.2026.11.02 | ✅ |
| Z3 | 4.13.3 | ✅ |
| Python | 3.14.4 (WSL) / 3.13.11 (Win) | ✅ |
| SymPy / NumPy | 1.14.0 / 2.3.5 | ✅ |
| gcc | 15.2.0 | ✅ |
| Node | v24.14.1 | ✅ |

**Несовместимы и не подключены:** FloatLib (Lean 4.35), FloatSpec (4.34), Aeneas, Charon,
Flocq. Причины — в [`../docs/FINDING-floatlib-compat.md`](../docs/FINDING-floatlib-compat.md).

---

## Сборка

```bash
export PATH=/root/.elan/bin:$PATH
cd laws
lake build
```

**Ожидаемый результат:** `Build completed successfully (18314 jobs)`, exit 0.

**Время:** ~5 минут после того, как Mathlib собран. Первая сборка Mathlib — ~3 часа.

---

## Проверка

```bash
# файлов
ls Medium/*.lean | wc -l                    # 48

# теорем
grep -rhcE '^theorem ' Medium/*.lean | paste -sd+ | bc   # 180

# olean
ls .lake/build/lib/lean/Medium/*.olean | wc -l           # 48
```

---

## Что доказано, а что нет

### Доказано строго

| утверждение | файл |
|---|---|
| отражение сохраняет меру Лебега на `[-B,B]` | `Stationary.lean` |
| обрезка неинъективна — атом на стене | `Walls.lean` |
| изометрия сохраняет разброс | `Rotation.lean` |
| `Var(X+c) = Var(X)` — детерминированная мутация не создаёт разнообразия | `Novelty.lean` |
| `Var(X+Y) = Var(X)+Var(Y)` — независимая создаёт | `Novelty.lean` |
| граница Поповичу и Бхатиа–Дэвиса | `Compression.lean` |
| `Var/w² → 1/12` при сужении окна | `Walls.lean` |
| `B = k·mean` коллапсирует, `B = k·std` взрывается | `Feedback.lean` |
| равные среды не дают границы | `Boundary.lean` |
| `break_even` — материя сохраняется при равенстве дохода и расхода | `Matter.lean` |
| `large_body_cannot_split` — большое тело не делится | `Structure.lean` |
| `selection_raises_mean` — отбор поднимает среднее | `Probability.lean` |
| мост между счётной и мерной половинами | `Bridge.lean` |

### Не доказано

- **Сходимость из произвольного начального состояния.** Численно согласовано, но не теорема.
- **Динамика обратной связи.** Доказано алгебраическое ядро, не сходимость траекторий.
- **Формула дисперсии `Var(α)` для экспоненциальной плотности.** Выведена в SymPy,
  проверена в Rust (37 тестов), но **не в Lean**.
- **Погрешность `f64`.** Lean доказывает о `ℝ`, Rust считает в `f64`. Моста нет.

### Что оказалось неверным

Честный список — в [`../docs/CLAIMS.md`](../docs/CLAIMS.md). Кратко:

| утверждение | что было не так |
|---|---|
| `no_noise_no_range` | доказывала `0 < μ` из `0 < μ` — тавтология |
| `learning_destroys_product` | доказывала `p₁ < p₀` из `p₁ < p₀` — тавтология |
| `exploration_is_not_optional` | доказывала `0 < σ` из `0 < σ` — тавтология |
| `fold_identifies` | использовала `%` на `ℝ` как периодичность — **ложно** |
| `mean_le_of_all_le` | требовала `X ≥ 0`, но не имела этой гипотезы |
| `coefficient_monotone` | использовала `div_le_div_iff`, которой нет в Mathlib |

**Три тавтологии в `Learning.lean` ждут замены** (см. план).

---

## Структура

```
Medium/
  Matter.lean          материя: break_even, clamp
  Boundary.lean        граница: equal_env_no_boundary
  Learning.lean        обучение (содержит 3 тавтологии — ждут замены)
  Learning2.lean       потолок скорости обучения
  Period.lean          лаг и период
  Structure.lean       структура: large_body_cannot_split
  Threshold.lean       порог дохода
  Threshold3.lean      порог карты
  Selection2.lean      отбор: mean_monotone
  Density.lean         плотность тел
  BodySize.lean        размер тела
  Probability.lean     selection_raises_mean
  MomentsLaw.lean      моменты
  Bridge.lean          мост счёт ↔ мера
  Bridge2.lean         мост, продолжение
  Compression.lean     Поповичу, Бхатиа–Дэвис
  Walls.lean           стены стирают форму
  Feedback.lean        обратная связь: три режима
  Support.lean         внешняя опора
  Novelty.lean         откуда разнообразие
  Timescale.lean       критическое время
  Stationary.lean      почему B²/3
  Convergence.lean     сходимость
  Convergence2.lean    сходимость, продолжение
  Corrected.lean       исправленная модель
  Project.lean         модель проекта обнуляет себя
  Rotating.lean        изометрия
  Symmetry.lean        симметрия
  Child.lean           комната ребёнка
  Bounded.lean         ограниченный отклик
  Budget.lean          бюджет по Коши-Буняковскому
  Shape.lean           форма: куб vs шар
  Dimension.lean       размерность
  TwoD.lean            двумерный случай
  Radial.lean          радиальная плотность
  Filling.lean         время заполнения
  Noise.lean           шум
  Growth.lean          рост
  Growing.lean         растущий ребёнок
  Matched.lean         совпадение
  Choice.lean          выбор
  Effort.lean          усилие
  Teaching.lean        обучение
  Others.lean          другие дети
  Responding.lean      отклик
  Reweight.lean        перевзвешивание
  SecondQuantity.lean  вторая величина
  Circle.lean          окружность
```

---

## Правила

Из [`../AGENTS.md`](../AGENTS.md):

1. **Утверждение без команды — не утверждение, а мнение.**
2. **Контроль должен срабатывать, молчать и быть специфичным.**
3. **Пустой эксперимент — не отрицательный результат.**
4. **В каждом отчёте — раздел «что это не доказывает».**
5. **Не заполнять пробел правдоподобным числом.**

**Теорема, которая доказывает гипотезу гипотезой, — не теорема.** Три такие найдены в
`Learning.lean` и ждут замены.

---

## История

- **2026-11-11:** `Medium.lean` импортировал только 13 из 48 файлов. **35 файлов никогда не
  компилировались.** Исправлено: 5 ошибок в 4 файлах, из них 2 содержательные
  (`fold_identifies` была ложной, `mean_le_of_all_le` не имела нужной гипотезы).
  Итог: 48 файлов, 48 olean, 180 теорем.

---

## Лицензия

MIT.
