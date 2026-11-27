# FINDING-EXP-2026-4103. Численная проверка полюса death-reset

**Дата:** 2026-11-27. **Задача:** `EXP-2026-4103` v4. **Научная классификация анализатора:** `void`.
**Submission outcome:** `void`. **Operational status:** `received`.
**Task version SHA256:** `a12176d4db8adf385bc8b28ad9273b0b6c304f02c67ff1c1b8483d259cfd5a86`. **Base commit:** `ee68a4b573aef20560a11e78731541cb8721d605`.
**Analyzer:** `dq6-analysis-1.0.1`. **Driver source SHA256:** `0759ffd7fc0469f6289ef99a6959510422ba5ef557a002cabbbdcf528c7353c8`.

## Зачем и что это даёт для слона

Проверено аналитическое предсказание standalone death-reset механизма: при `h→1` плато `D* ~ x^(-1/2)`, его производная `|dD*/dh| ~ x^(-3/2)`, а средний интервал death-reset `T_life ~ x^(1/2)` стремится к нулю. Для слона это проверка численного контракта смертного канала и его специфичности, а не новый биологический закон, не перевод к Chao и не изменение live core.

## Предсказание и правило до прогона

Цели: `alpha_D=0.5`, `alpha_deriv=1.5`, `alpha_Tlife=0.5`; каждый 95% seed-bootstrap CI должен пересекать цель с допуском `0.15`. `h=1` должен расти без cap и выходить на плато с cap. Yoked sham не должен воспроизводить полюс, а удалённый диапазон `h={0.9,0.95,0.98,0.99}` — не воспроизводить все три асимптотических показателя. Сходимость: `|D800-D400|/D800 <= 0.01` минимум у 10/12 seeds; для fit требуется минимум четыре сходимых `h_fit`. Гипотеза, сетка, seeds и gates не менялись после просмотра данных.

## Результат

`void`: Instrument gate fires и/или silent провален. Научная классификация endpoint не используется как evidence; это корректный инструментальный исход, а не passed/failed гипотезы.

Причина анализатора: instrument control failed: fires and/or silent.

| endpoint | target | оценка | 95% CI | status | passes |
|---|---:|---:|---|---|---|
| alpha_D | 0.5 | 0.52535 | [0.5242465, 0.5263307] | ok | да |
| alpha_deriv | 1.5 | 1.514452 | [1.509102, 1.520029] | ok | да |
| alpha_Tlife | 0.5 | 0.4511299 | [0.4509823, 0.4512778] | ok | да |

## Сходимость и горизонт

Сходимых `h_fit`: 4; значения: `[0.995, 0.998, 0.999, 0.9995]`.
Правило систематического сдвига `alpha_D`: estimable=да, systematic=нет, последовательные изменения=[0.009833338578175144, -0.0009044323941448384, 0.00013644153360337086].

| горизонт | alpha_D | alpha_deriv |
|---:|---:|---:|
| 100000 | 0.5162847 | 1.457156 |
| 200000 | 0.526118 | 1.512537 |
| 400000 | 0.5252136 | 1.511864 |
| 800000 | 0.52535 | 1.514452 |

## Контроли

| контроль | passed | роль |
|---|---|---|
| fires | да | instrument gate: рост без cap и плато с cap |
| silent | нет | instrument gate: удалённый диапазон не воспроизводит все цели |
| specific | нет | научный контроль специфичности |
| sham_schedule_exact | да | точность yoked schedule, включая корректные zero-event случаи |

### Yoked comparison по h

| h | schedule exact | median rel. diff 400k | median rel. diff 800k | воспроизводит полюс |
|---:|---|---:|---:|---|
| 0.995 | да | 0.0003488131 | 0.0002950207 | да |
| 0.999 | да | 5.635454e-05 | 4.924503e-05 | да |

## Прогон и provenance

- Attempt: `EXP-2026-4103-a2`; lease `LEASE-460020f8b730` epoch `2`.
- Старт: `2026-11-27T07:04:56Z`; завершение runner: `2026-11-27T07:12:14Z`; heartbeat failure: `None`.
- Seeds: `4301..4312`; `N=100`; шагов `800000`; замеры `[100000, 200000, 400000, 800000]`.
- Production histogram: `global-only`; organism bins запрещены; network не использовался; unseeded randomness отсутствует.
- Bootstrap: 10000 seed-репликаций, seed `20261103`; строк `seed_metrics.csv`: 336.

| артефакт | bytes | SHA256 |
|---|---:|---|
| death-reset/summary | 58282 | `2fdd47da1156a4f5f561a77d75fe6c8d9ca2fdfb21e5de474248669826c058d0` |
| death-reset/histogram | 456724 | `e2e7067c7bc6bb7e34b0831fd9c6614535920b90f7cd9326dbe81ea3a462d994` |
| cap/summary | 1654 | `1026d6d00949b36dee4fcd6390df211b75d9ecc80ca6896428bb58921437e7dc` |
| cap/histogram | 26162 | `67e69378d4e4ca3a0deab263086fe85909249932bbb3fc2b57fc3619ef7c3621` |
| sham/summary | 3922 | `adcd133e35a9d3eeaf95a8f8bb58962c744561dcfa47c4062b43697ae4900ae2` |
| sham/histogram | 32821 | `875d4d68aa1bdbd6bfc0a2772f672d04716b61abb72b3bbbcb0b48506f1d426a` |
| driver source | 40510 | `0759ffd7fc0469f6289ef99a6959510422ba5ef557a002cabbbdcf528c7353c8` |
| analyzer | 80765 | `20f147ad91de6655ca528702bdaff357dada9c581cc8e6570b86e09a8f27535c` |
| runner | 12659 | `db85e8a37d43c3295a0c8d6a25c13e092c3c226f3c0cb21c9bc7e8d531535a83` |
| lease wrapper | 11115 | `06012742167d8f16cf78cfe9537fe6fd00454d3122730a4d92d8dc2005827ea5` |
| task | 9975 | `712109535ca2d996fd6b0077f32c3eac78ee07687743a68f20a90c448dc58015` |
| run manifest | 7988 | `d256e9d014f14752eefb178db1e50603a1cd9390f7f6f079544ba71741584237` |
| environment | 2803 | `0d300e53e3eb3834bdfbba94975c8565b513fbab489dfe1ae71fa36e3ac39a24` |
| toolchain | 281 | `bea971e416797fce0036a200290074f366e97eb5013f7c2cd61ef56544bdc267` |

## Ограничения

- This is a numerical check of an analytic result, not a new scientific result by itself.
- T_life is the death-reset interval, not Chao senescence time; no equality between the definitions is assumed.
- Points near h=1 may not plateau by 800000 steps; such runs are horizon_limited rather than confirmed.
- Comparison with Chao is blocked by the missing Q-024 parameter translation.
- The driver rounds Dbar to six decimals; finite differences of nearby h can amplify this numerical error.
- Only four summary horizons are available, not full trajectories; the pre-run alpha_D same-sign/two-transition rule is an additional decision gate.
- The interval histogram has no event-step field, so exact prefix T_life moments before 800000 are not recoverable; cumulative event rates are not substituted for them.
- The schedule hash is two non-cryptographic 64-bit FNV-1a hashes and cannot exclude collisions or replace an event journal for forensic audit.
- Bootstrap uncertainty conditions on the observed final-converged h set and resamples all 12 seeds at those h; it does not include model-selection or horizon-selection uncertainty.
- Missing zero-event T_life values are omitted from the relevant seed mean and their counts are reported; no interval is imputed.
- A zero or non-positive log-log response, including a zero central derivative, is unestimable and fails the preregistered endpoint gate; it is never imputed or replaced by a positive floor.
- Equal zero-event yoked schedules are exact only when both strict summaries have zero counts, zero reset moments, blank hashes and no interval records.
- The synthetic self-test validates implementation behavior only and is never scientific evidence.
- Результат условен относительно закреплённого main-owned driver, task version, exact raw CSV и analysis code.
- `received` терминален для агента; переход `received → integrated` выполняет main.

## Статус сдачи

`received`. Авторитетный статус после отправки хранится в `submission-response.json`; этот FINDING не перезаписывается после sealing bundle.

**Слону:** закрыт самый дешёвый кандидат численного якоря смерти: коридоры полюса death-reset неспецифичны (удалённый диапазон воспроизводит все три показателя), инструмент объявлен невалидированным, вывод о механизме не делается. Для модели это честная граница вместо ложного якоря; следующий шаг к слону — связка FINDING-457 (износ ремонта как память) с повреждаемостью самого ремонтного аппарата (D-Q9) при выключаемых механизмах.
