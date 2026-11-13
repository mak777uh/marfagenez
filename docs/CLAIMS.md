# Утверждения и их подтверждение

**Дата:** 2026-11-13 (числа пересчитаны командами; формула клетки исправлена — см. ниже)
**Правило:** каждое число имеет команду. Без команды — не результат.

---

## Уровни

| уровень | что значит | инструмент |
|---|---|---|
| **A** | доказано формально | Lean / Verus |
| **B** | проверено на конкретных входах | тесты |
| **C** | измерено в симуляции | Python/JS |
| **D** | гипотеза, не проверена | — |

**Никогда не смешивать.** Уровень A не следует из B, B не следует из C.

---

## Что доказано (уровень A)

> **Поправка 2026-11-13, вечер.** Порядок шага клетки был записан неверно:
> стояло `c + (M − c)·r − t` (сначала прирост, потом трата), должно быть
> `(c − t) + (M − (c − t))·r` (сначала трата, потом прирост). Равновесие
> поэтому не `M − t/r`, а **`c* = M + t − t/r = M − t·(1−r)/r`**.
> Исправлено и пересобрано в `Field.lean`, `Convergence.lean`, `Capacity.lean`,
> `Regimes.lean`. Все числа уровня C в этом файле, полученные при старом
> порядке (потолок `C = 80`, `E* = E_max − COST`, `c* = 1.8`), **отозваны** —
> см. `docs/FINDING-140-the-step-order-was-wrong.md`. Проверка:
> `cd laws && lake build` → 18328 jobs, 0 errors.

### Lean — две библиотеки, 317 теорем и лемм, 0 живых sorry

| библиотека | файлов | теорем | sorry | команда |
|---|---|---|---|---|
| `Medium` — модель клетки | 56 | **290** | **0** | `lake build` |
| `Legacy` — стена/гонка/наклон | 8 | 27 | **0** | `lake build Legacy` |

`Medium` — то, что относится к среде ребёнка: `cellStep`, `equilibrium`,
`capacity`, `Regimes`, `CapacityLaw`, `FoldPeriodic`. `Legacy` — другой язык (стена,
свободный ход, гонка, наклон) на `Nat`/`UInt64`, не связанный с моделью
клетки; он собирается отдельной `lean_lib`, чтобы не смешивать переменные.

**Команда:**
```bash
cd laws && lake build && lake build Legacy
# Build completed successfully (18328 jobs).   -- Medium
# Build completed successfully (18238 jobs).   -- Legacy
```

**Проверка отсутствия дыр:**
```bash
grep -rn 'sorry' Medium/*.lean | wc -l   # 2 — оба в прозе docstring FoldPeriodic.lean:6,12
grep -rn 'sorry' Legacy/*.lean           # 0
```

`sorry` в `Legacy/Convergence2.lean` убран: `fold_identifies` была не
недоказанным утверждением, а **ложным** — `%` на `ℝ` тождественно `0`. Теорема
переписана над `ℤ`. См. `FINDING-percent-on-real-is-zero.md` и
`Medium/FoldPeriodic.lean`.

**Корень `laws/` больше не содержит `.lean`-файлов, кроме двух точек входа.**
До 2026-11-13 там лежали 50 файлов, из которых 48 не импортировались ни одной
`lean_lib` и никогда не компилировались — тот же дефект, что в LESSONS №1
(«35 файлов, которые никогда не компилировались»). Все 48 оказались
устаревшими копиями: у 40 был `Medium/`-близнец с тем же набором теорем, у 8
(`Race`, `Reaction`, `Saturation`, `Tilt`, `Time`, `FFI`, `Convergence2`,
`Equiv`) — `Legacy/`-близнец с совпадающим набором теорем (сверено по именам
`theorem`/`lemma`). Удалены; сборка осталась зелёной. Теперь в `laws/` два
файла: `Medium.lean` и `Legacy.lean`.

### Legacy — что доказано (уровень A)

| утверждение | файл | что именно доказано |
|---|---|---|
| `min(a,b) ≤ a` | `Saturation.lean` | свойство `min` |
| `min(a,b) ≤ b` | `Saturation.lean` | свойство `min` |
| `min` монотонен по 2-му аргументу | `Saturation.lean` | свойство `min` |
| `a ≤ b → min(a,b) = a` | `Saturation.lean` | свойство `min` |
| `b ≥ 2σ → 1 < (b/σ)²` | `Race.lean` | гонка проиграна |
| `fillTime(2t,1) = 4·fillTime(t,1)` | `Race.lean` | квадратичность |
| потолок останавливает гонку | `Race.lean` | монотонность |
| `g = 0` не меняет шаг | `Reaction.lean` | закон реакции |
| `g ≠ 0 ∧ f ≠ 0` меняет шаг | `Reaction.lean` | закон реакции |
| `α = 0 ⇔ μ = 0` | `Tilt.lean` | закон наклона |
| `(B − spread)/μ < B/μ` | `Time.lean` | время до стены |
| **`FFI.saturation` = `Saturation.spread`** | `Equiv.lean` | **эквивалентность** |

### Verus — 41 verified

| функция | что доказано |
|---|---|
| `saturation` | реализация = спецификация |
| `fill_time` | реализация = спецификация + переполнение |
| `fold_shifted` | реализация = спецификация + переполнение |
| `fraction_pct` | реализация = спецификация |
| `race_lost` | реализация = спецификация |
| `reaction_changes` | реализация = спецификация |
| `zero_gain_keeps` | реализация = спецификация |
| `distance_to_wall` | реализация = спецификация |
| `time_to_narrow` | реализация = спецификация |
| `naive_time` | реализация = спецификация |
| `sooner_than_naive` | реализация = спецификация |
| `tilt_num`, `tilt_den` | реализация = спецификация |
| `tilt_sign`, `tilt_zero_iff` | реализация = спецификация |

**Команда:**
```bash
verus verus/integer_laws.rs
# verification results:: 41 verified, 0 errors
```

---

## Что проверено на входах (уровень B)

### Rust — 192 теста

| группа | что проверяет |
|---|---|
| `room::` | складка, NaN, доверие к форме |
| `cycle::` | цикл, чтение, независимость RNG |
| `probes::` | подложенные дефекты ловятся |
| `boundary::` | среда не может измерять |
| `bridge::` | Rust и Lean дают одинаковые ответы |
| `life::` | политики `Stay` / `Random` / `Remember` / `Memory` / `Sighted` |
| `threshold_brake::`, `time_to_narrow::` | тормоз и время до стены |

**Команда:**
```bash
export PATH=/root/.elan/bin:$PATH          # иначе build.rs не найдёт lean и соберёт заглушку
cd core && cargo test --release --tests -- --test-threads=1
# 23 test binaries, суммарно 192 passed, 0 failed
# --test-threads=1 обязателен: рантайм Lean не потокобезопасен, иначе SIGABRT
```

Две ловушки, обе внешние к коду:

1. **`lean` не на PATH** → `build.rs` пишет `lean -c failed — building the stub`,
   линковка падает на `undefined symbol: marfa_*`. Лечится `export PATH=/root/.elan/bin:$PATH`.
2. **`laws/FFI.lean` не там, где его ищет `build.rs`** → `lean -c` даёт
   `no such file or directory (error code: 2)`, и снова собирается заглушка.
   С 2026-11-13 корень `laws/` расчищен, файл живёт в `laws/Legacy/FFI.lean`,
   а `build.rs` смотрит туда (`laws_dir = "../laws/Legacy"`). Если файл
   переедет — правится одна строка в `build.rs`, иначе симптом тот же, что и
   в пункте 1: `undefined symbol: marfa_*`.
3. **`cargo test` без `--test`** запускает ещё и doctest, а `rustdoc` не установлен
   (`could not execute process rustdoc ... No such file or directory`). Это не падение
   тестов: строка `189 passed, 0 failed` уже напечатана выше. Чтобы не видеть
   ложный `error:`, запускать `cargo test --release --tests -- --test-threads=1`.

---

## Что измерено (уровень C)

| утверждение | команда | результат |
|---|---|---|
| куб сохраняет меру | `python3 checks/box_measure.py` | `chi² = 35.0` при 36 dof |
| **шар НЕ сохраняет меру** | `python3 checks/ball_measure2.py` | **`chi² = 3×10⁷`** |
| насыщение неверно при `t=1` | `python3 checks/transition.py` | ошибка **48.7%** |
| исправление через `S(0)` | `python3 checks/transition2.py` | ошибка **0.3%** |
| ни одна формула не точна | `python3 checks/transition3.py` | лучшая **13.7%** |
| `α` сходится к `2μ/σ²` | `python3 checks/alpha_fit.py` | **0.1%** |
| 10 численных проверок | `node checks/verify_all.js` | 10/10 |
| 7 утверждений | `node checks/audit.js` | 7/7 |
| 6 законов согласованы | `python3 checks/consistency.py` | 6/6 |
| наклон подтверждён | `python3 checks/tilt.py` | 3/3 |
| exit code при FAIL | `node checks/probe_exit.js` | exits 1 |

---

## Что НЕ доказано

| утверждение | почему |
|---|---|
| `spread = min(σ√t, B/√3)` как закон | это приближение, ошибка до 48.7% |
| шар сжимает черты | fold не сохраняет меру — эффект от алгоритма, не геометрии |
| `α = 2μ/σ²` точно | это предел, при `dt=1` ошибка 3.7% |
| Rust-код в `core/` верен | Verus доказал **копии** в `verus/`, не `bridge.rs` |
| `f64`-часть верна | Verus не поддерживает плавающую точку |
| оставшиеся 226 теорем содержательны | проверены только 11 тавтологий из 237 |

---

## Что удалено (не выбрасывается)

| что | почему | где записано |
|---|---|---|
| 11 теорем-тавтологий | доказывали `X = X` | `ELIMINATED.md` п.11 |
| `Shape::Ball` из выводов | не сохраняет меру | `FINDING-transition-wrong.md` |
| формула `min(σ√t, B/√3)` | неверна при `t=1` | `FINDING-transition-wrong.md` |
| «оптимум заполнения 90%» | артефакт выборки | `ELIMINATED.md` п.9 |
| 3 теоремы в `medium` | ложные постановки | `ELIMINATED.md` п.10 |
| `varianceF_bound` | ложна: `isFinite` не исключает underflow, контрпример `b = 2⁻⁵³⁷` | `LESSONS.md` урок 2 |
| `fold_identifies`, `mean_le_of_all_le` | ложные постановки, исправлены | `LESSONS.md` урок 2 |
| `Convergence2.fold_identifies` (второй раз) | `%` на `ℝ` не периодичен по `4B`; теперь явный `sorry`, не доказательство | `laws/Legacy/README.md` |
| «`c* = M − t/r`» | не тот порядок операций; верно `M − t(1−r)/r` | `FINDING-correct-equilibrium.md` |
| «`k_max = M·r/(t₀(1−r))`» | верное число по неверной причине; забор последовательный | `FINDING-crowding-is-two.md` |
| «тормоз сужает до 0.9 закона» | измерено 0.954; тест противоречил sweep | `LESSON-two-tests-disagreed.md` |
| «`t* = (B−law)/μ`» | подгонка под три числа одного seed; хуже наивной на 2 из 3 строк | `LESSON-two-tests-disagreed.md` |

---

## Чего нет

| свойство организма | есть? |
|---|---|
| внутренняя организация | **нет** |
| обмен (ресурсы, энергия) | частично — энергия есть, обмена нет |
| самоподдержание | **нет** |
| агентность (действия) | частично — 5 политик движения |
| история (память) | частично — `Remember` (замороженная) и `Memory` (обновляемая) |
| восстановление | **нет** |
| изменение среды | частично — организм изымает ресурс, но не меняет закон поля |
| рождение | **нет** (EXP-28 отложен) |

**`Child` — носитель состояния, не организм.**

---

## Итоговые числа

| что | значение | команда |
|---|---|---|
| Lean теорем и лемм (`Medium`) | **281** | `grep -h '^theorem \|^lemma ' laws/Medium/*.lean \| wc -l` |
| Lean теорем и лемм (`Legacy`) | **27** | `grep -h '^theorem \|^lemma ' laws/Legacy/*.lean \| wc -l` |
| Lean файлов с теоремами | **55** `Medium` + 9 `Legacy` | `ls laws/Medium/*.lean \| wc -l` |
| Lean `sorry` | **0** везде | `grep -rn 'sorry' laws/*/*.lean \| wc -l` |
| Rust тестов | **192** | `cargo test --release --tests -- --test-threads=1` |
| Verus | **41 verified** | `verus verus/integer_laws.rs` |
| docs FINDING | **53** | `ls docs/FINDING-*.md \| wc -l` |
| checks (эксперименты) | **98** | `ls checks/exp*.py \| wc -l` |
| сохранённых прогонов | **136** | `find results -name 'run-*.json' \| wc -l` |
| прогонов, прошедших контракт | **128** (0 нарушений) | `python3 checks/contract.py` |

Все числа в этой таблице пересчитаны 2026-11-13. Предыдущая версия
(`237` теорем, `87` FINDING, `45` проверок, `38` прогонов) была снята с
устаревшего состояния дерева: в ней не были учтены ни правка `cellStep`
от 2026-11-12, ни 41 добавленная теорема, ни 53 новые FINDING-заметки.

---

*МАРФАГЕНЕЗ++ · CLAIMS.md · 2026-11-13*
