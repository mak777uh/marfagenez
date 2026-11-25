# P77-coverage-two-counts — Покрытие в двух счётах: 22/152 и 20/152 с lit_ref

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T05:26:29Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `tools/stitch_audit.py`
- `docs/agent/AGENT_STATE.md`
- `docs/STITCH-*.md`

## Что нужно сделать

Метрика занижала: узлы без lit_ref с S-парой не считались.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
