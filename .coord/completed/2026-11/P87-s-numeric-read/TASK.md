# P87-s-numeric-read — Прочитать S-пары с числами: 2 понижения из 4

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T05:50:12Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-S-READ.md`
- `docs/STITCH-*.json`
- `checks/stitch_coverage_floor.py`
- `docs/STITCH-COVERAGE-FLOOR.json`
- `tools/stitch_s_screen.py`

## Что нужно сделать

Совпавшие «числа» — это 1/2/3; исключить их из признака совпадения.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
