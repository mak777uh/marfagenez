# P86-s-read-7 — Чтение S-пар: партия 7 и сводка по 28 парам

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T05:46:44Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-S-READ.md`
- `docs/STITCH-*.json`
- `checks/stitch_coverage_floor.py`
- `docs/STITCH-COVERAGE-FLOOR.json`
- `docs/agent/AGENT_STATE.md`

## Что нужно сделать

Последние четыре пары: A-0002, C-0002, FAST-S2-01|L-009, W4-0014.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
