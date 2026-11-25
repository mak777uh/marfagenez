# Раунд P125 — 2026-11-25 — sizer/adder/timer: ветвь adder получила опору

## Что сделано

Пятая тема из `docs/ANCHOR-AUDIT.md`. Источник: Nieto и др. 2025, Biophys. J. 124(9):1376–1386
(`10.1016/j.bpj.2025.03.011`, PMC12256869).

Атом `MAIN-P125-01` с цитатой и локатором:
> «the adder, where the cell size increase from birth to division is independent of the newborn cell size …
> In cells growing exponentially over time, an adder implies an inverse correlation between the cell cycle
> duration and the newborn cell size.»

## Метрика

| метрика | было | стало |
|---|---|---|
| карта | 1030 | **1031 ячейка** |
| `S`-пар | 35 | **36** |
| узлов с `S` | 25 | **26 (17 %)** |
| долг опоры | 12 | **11** |

## Оговорка: опора только у одной ветви

Узел `F-015` задаёт **семейство** `s_d = a·s_b + b` с тремя ветвями: `sizer` (`a = 0`), `adder` (`a = 1`),
`timer` (`a = 2`).

Атом подтверждает **только `adder`**. Ветви `sizer` и `timer` остаются без отдельной опоры, и это записано в
`reason` и в примечании атома. Считать весь узел «подтверждённым» было бы растяжением: разобрана одна треть.

## Проверки

- `checks/map_contract.py` — 1031 ячейка, нарушений нет;
- `checks/stitch_coverage_floor.py` — 36/26;
- `kg/` пересобран, `regress` зелёный;
- `tools/unanchored_nodes.py --strict` — 11 (потолок 11);
- `checks/doc_numbers.py`, `checks/log_check.py` — зелёные.

## Что это НЕ доказывает

- Что `sizer` и `timer` существуют как механизмы: они остаются теоретическими ветвями семейства.
- Что связь прироста с размером проверена на человеке: данные в источнике — бактерии и клеточные линии.

## Следующий вопрос

Осталось: `F-011` (ниша), `F-013` (цепь рождения–смерти), `F-019` (Chao), `F-025` (ITI), `F-030` (метрики).
