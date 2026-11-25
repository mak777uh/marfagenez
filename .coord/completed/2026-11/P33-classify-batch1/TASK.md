# P33-classify-batch1 — Классифицировать первые 13 пар «не задан»

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T02:03:19Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-OVERRIDES.json`
- `docs/STITCH-AUDIT.md`
- `docs/STITCH-TABLE.md`
- `tools/stitch_table.py`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

Разобрать 13 пар из 57 неклассифицированных: общая величина, вердикт, причина.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
