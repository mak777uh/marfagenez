# P114-coverage-from-fast — Рост покрытия за счёт атомов fast: m_S к L-013

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T10:57:42Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-*.json`
- `docs/STITCH-S-READ.md`
- `checks/stitch_coverage_floor.py`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

Три атома fast измеряют m_S — у узла L-013 не было S-пары.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
