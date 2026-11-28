# EXP-2026-4107: детерминированный контракт k-out-of-m и cost-yoked контроли

## Назначение и границы

Пайплайн проверяет механику B до стохастического pilot: `m=3`, `k=2`,
`R_t = min(R0, r0*n_t) * 1[n_t >= k_eff]`. Это unit-test, а не статистический
научный результат. Реальные эксперименты, git и control plane в локальной
проверке не используются; разрешены только synthetic fixtures.

Зафиксированные параметры:

- `R0=0.1`, `r0=0.05`, `k_D=0.3`, `T=40`;
- `D0=0.5`, `D-half=0.25`, `D-third=1/6` (не округлённый `0.1667`);
- `t*=5`, `t**=10`, `t***=15`;
- стоимость repair: `0.2` энергии и `0.2` субстрата на единицу `v`;
- maintenance: `0.01` энергии на оплачиваемый модуль;
- начальные запасы: `e=0.1`, `s=0.1`; рацион `0.05` за шаг до допуска на шум;
- детерминированные сиды; повторный запуск обязан быть побайтово идентичен.

## Рукава

| Рукав | Capacity | Расписание активных модулей `n_t` | Оплата maintenance | Внешний rescue |
|---|---|---|---|---|
| `A-control` | всегда `R0` | 3 | всегда 3 | нет |
| `B1-sham` | modular, `k_eff=2` | 3; sham в `t*` | активные `n_t` | нет |
| `B2-ko1` | modular, `k_eff=2` | 3 до `t*`, 2 после | активные `n_t` | нет |
| `B3-ko2` | modular, `k_eff=2` | 3 → 2 в `t*` → 1 в `t**` | активные `n_t` | нет |
| `rescue` | modular, `k_eff=2` | как B3, затем 2 в `t***` | активные `n_t` | 1 модуль, запас 1 → 0 |
| `A-B2-cost` | всегда `R0` | как B2 | как B2 | нет |
| `A-B3-cost` | всегда `R0` | как B3 | как B3 | нет |
| `A-rescue-cost` | всегда `R0` | как rescue | как rescue | как rescue |
| `D-half` | modular, `k_eff=2` | 3 | активные `n_t=3` | нет |
| `D-third` | modular, `k_eff=2` | 3 | активные `n_t=3` | нет |
| `ghost` | всегда `R0` | как B3 | как B3 | нет |
| `placebo-k1` | modular, `k_eff=1` | как B3 | как B3 | нет |

B-рукава платят за активные `n_t`; `A-control` платит 3. Cost-yoked
A-рукава воспроизводят `n`, стоимость и rescue-расписание соответствующего B,
но capacity у них всегда `R0`. Ghost — fixed capacity с B3-расписанием и
стоимостью. Placebo после `n=1` имеет `cap_now=0.05`; capacity не становится
нулём, пока рукав жив.

Каждый knockout переводит один модуль из активных в failed stock. Rescue не
«создаёт» модуль: `module_in=1` и `external_rescue_stock` уменьшается ровно на 1.

## Raw summary CSV

Заголовок обязан совпадать строго:

```text
arm,k_eff,d0,seed,aurd,aurd_abs,f_final,f_at_ko2,v_after_ko2,v_after_rescue,binary95_10,t_reach95,max_imbalance,v_first,n_final,aurd_observed,aurd_abs_observed,f_at_death,maint_short_total,maint_debt,rescue_in_total,external_rescue_stock,failed_module_stock,observed_steps,alive,death_step,death_cause,horizon_censored,state_hash,trajectory_hash
```

Ожидается ровно `12 * seeds` строк в указанном порядке рукавов, внутри рукава —
сиды `seed_base ... seed_base+seeds-1`. `failed_module_stock` — итоговый запас.
`state_hash` и `trajectory_hash` — 16 hex-символов FNV-1a 64. Драйвер фиксирует
байтовое представление хэшируемой траектории в исходнике; анализатор независимо
пересчитывает оба хэша из little-endian raw bits `f64`/`u64`, а затем проверяет
SHA256 артефактов, повтор и зарегистрированные равенства хэшей.

## Steps CSV

Заголовок обязан совпадать строго:

```text
arm,seed,step,n_t,event,u_e,u_s,e_in,s_in,e_unc,s_unc,maint_e,maint_short,v,d,e,s,cap_now,f,imbalance,maint_debt,debt_imbalance,module_in,module_out,module_imbalance,failed_module_in,failed_module_stock,failed_module_imbalance,external_rescue_stock,rescue_stock_imbalance,d_before,e_before,s_before,alive,death_cause
```

Для живых зарегистрированных рукавов ожидается `12 * seeds * 40` строк:
arm-major, затем seed, затем `step=0..39`. События: `sham`, `ko1`, `ko2`,
`rescue`; отсутствие события допускается как `none` или пустая строка.

`d_before`, `e_before`, `s_before` — состояние непосредственно перед repair:
intervention уже применён, приток и maintenance уже учтены. Поэтому независимая
формула repair использует именно эти поля.

Все float-значения выводятся shortest round-trip представлением Rust `f64`, а не
фиксированным числом десятичных знаков. CSV не содержит `inf`. `NaN` допускается
только в явно смертных/отсутствующих итоговых метриках, описанных ниже.

## Независимый пересчёт шага

Обозначения `prev_*` — состояние предыдущего шага; начальные значения:
`d=d0`, `e=s=0.1`, `n=3`, `debt=0`, failed stock `0`, external rescue stock `1`
только для `rescue` и `A-rescue-cost`.

1. Принятый приток: `e_add=e_in-e_unc`, `s_add=s_in-s_unc`.
2. `maint_need=0.01*cost_modules`, где `cost_modules=3` для `A-control`, иначе `n_t`.
3. `maint_e=min(max(prev_e+e_add,0),maint_need)`, `maint_short=maint_need-maint_e`.
4. `e_before=prev_e+e_add-maint_e`, `s_before=prev_s+s_add`, `d_before=prev_d`.
5. Capacity вычисляется из зарегистрированного рукава и пост-intervention `n_t`.
6. Repair:

```text
v = max(0, min(k_D*d_before, cap_now,
              e_before/0.2, s_before/0.2, d_before))
d = d_before - v
e = e_before - 0.2*v
s = s_before - 0.2*v
f = (d0-d)/d0
```

7. Долг и материальные балансы:

```text
debt_imbalance = maint_debt - (prev_debt + maint_short)
module_imbalance = prev_n + module_in - module_out - n_t
failed_module_imbalance = prev_failed + failed_module_in - failed_module_stock
rescue_stock_imbalance = prev_external - module_in - external_rescue_stock
energy_residual = e_before - 0.2*v - e
substrate_residual = s_before - 0.2*v - s
imbalance = max(abs(all six residuals))
```

`failed_module_in=module_out` на knockout. Все компонентные residual-поля и
`imbalance` пересчитываются анализатором. Требование: `imbalance < 1e-12`.

Смерть проверяется после repair: `e<=0` или `d>=1`. После смерти строк нет.
Для живого рукава `alive=1`, `death_step=-1`, `death_cause=none`,
`horizon_censored=1`, `f_at_death=NaN`. Для мёртвого `alive=0`,
`death_step>=0`, `death_cause` равен `energy` или `damage`,
`horizon_censored=0`; `aurd`, `aurd_abs`, `f_final` равны `NaN`, а
`f_at_death` конечно. Смерть любого зарегистрированного рукава делает весь
результат `void`: это отказ идентифицируемости, а не научный `failed`.

Итоговые `aurd`, `aurd_abs`, observed-метрики, `f_final`, `f_at_ko2`,
`v_after_ko2`, `v_after_rescue`, `binary95_10`, `t_reach95`, `max_imbalance`,
`v_first`, `n_final`, debt/rescue/stocks и `observed_steps` пересчитываются из steps.

## Предсказания и контроли

Научные предсказания:

1. `A-control.trajectory_hash == B1-sham.trajectory_hash` для каждого сида.
2. `A-B2-cost.trajectory_hash == B2-ko1.trajectory_hash`; B2 воспроизводит
   recovery B1, поскольку `n=2>=k`.
3. `A-B3-cost.trajectory_hash == ghost.trajectory_hash`: cost-yoked fixed-capacity
   контроль полностью совпадает с B3-расписанием, а ghost воспроизводит B1.
4. B3: `cap_now=0` и `v=0` начиная ровно с `t**=10`; `f_final=f_at_ko2`.
5. Rescue: возобновление с `t***=15`, расход ровно одного внешнего модуля,
   `B2.aurd < rescue.aurd < B3.aurd`, каждый запас строго `>1e-6`.
6. Абсолютный дефицит при `n=3`: `A-control.aurd_abs > D-half.aurd_abs > D-third.aurd_abs`.

Инструментальные контроли (все входят в outcome gate):

- точные заголовки, 12 рукавов, сиды, строки и порядок;
- task id/version/hash/base в manifest; SHA256 файлов и driver source hash;
- два запуска `run1/run2` побайтово идентичны;
- FNV-1a 64 hex и независимый raw-bit пересчёт state/trajectory hashes;
- точные события, `n_t`, capacity и cost-yoked расписания;
- independent repair formula на каждом шаге;
- закрытые energy/substrate/debt/active/failed/rescue ledger `<1e-12`;
- явные death/censoring и отсутствие смерти зарегистрированных рукавов;
- `A-B3-cost`/`A-rescue-cost` имеют ресурсные расписания B3/rescue;
- ghost имеет fixed `R0`, B3 schedule/cost и воспроизводит target recovery B1;
- placebo имеет `k_eff=1`, `cap_now=0.05` после `n=1`, не нулевой capacity и
  продолжающийся repair после `t**`.

## Исходы и приоритет

| Исход | Условие |
|---|---|
| `insensitive_by_construction` | оба запуска завершились кодом 3; marker, SHA/bytes/rows, driver/source provenance, task identity и побайтовый повтор валидны |
| `void` | другой nonzero driver rc, нарушение любого контроля, смерть/NaN, неидентичный повтор, ghost/placebo/schedule/ledger failure |
| `failed` | все контроли валидны, но нарушено хотя бы одно научное предсказание |
| `passed` | все предсказания и все контроли выполнены |

Sensitivity gate: `q0=0.5`, `need_r0=(0.95-q0)/40=0.01125`,
`need_kD=ln((1-q0)/(1-0.95))/40`; exit 3, если `r0<need_r0` или
`k_D<need_kD`. Другой nonzero rc не может стать `insensitive_by_construction`.
`void` не переименовывается в `failed`; `failed` требует валидных контролей.

## Два запуска и provenance

`b_run.sh driver out task.json driver.rs` выполняет драйвер дважды и сохраняет:

```text
out/run1/{raw.csv,steps.csv,driver.stderr.log,driver.rc,run-manifest.json}
out/run2/{raw.csv,steps.csv,driver.stderr.log,driver.rc,run-manifest.json}
out/{raw.csv,steps.csv,raw-manifest.json,environment.json,toolchain.json,environment.txt,task.json}
```

Корневые raw/steps являются копией run1. Manifest содержит return codes, argv,
SHA256/bytes/rows каждого файла, driver/source SHA256, toolchain/environment,
expected counts и фактический `repeat.byte_identical`. Analysis проверяет не
только флаги manifest, но и сами байты и SHA256.

`b_run_leased.py` добавляет lease heartbeat и копирует claim/task payload в
выходной каталог. Он не содержит закреплённой версии или task hash.

## Submit

`b_submit.py` принимает как прямой `task/v1`, так и wrapper с `payload`, `task`
или `task_payload`; для wrapper-формата текущего draft читаются `task_id`,
`current_version`, `current_sha256` и вложенный `payload`. На submit время
сверяются `id`, `version`, task-version SHA256 и `base_commit` между claim,
task payload, raw manifest, analysis summary, plan и lease-run (если он staged).
Любое расхождение отклоняет bundle. Submit поддерживает исходы, определённые
для этого пайплайна (passed, failed, void, insensitive_by_construction), и не
превращает non-passed в passed; общесистемный словарь исходов (пять, включая
not_applicable) описан в lab/schemas/v1/common.schema.json. Dry-run не использует внешние зависимости и не
обращается к control plane.
