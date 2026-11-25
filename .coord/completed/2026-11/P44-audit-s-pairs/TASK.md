# P44-audit-s-pairs — Выборочный аудит S-пар Red Team: проверить 6 пар руками

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T02:20:25Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-OVERRIDES.json`
- `docs/STITCH-ADJUDICATION.md`
- `docs/STITCH-AUDIT.md`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

Проверить, не завышены ли S-вердикты, как это было с Ch в P33.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
