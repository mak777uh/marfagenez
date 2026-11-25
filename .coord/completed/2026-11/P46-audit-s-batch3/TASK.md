# P46-audit-s-batch3 — Аудит S-пар, партия 3: добить остаток до полного

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T02:23:16Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-OVERRIDES.json`
- `docs/STITCH-ADJUDICATION.md`
- `docs/STITCH-AUDIT.md`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

Зафиксировать и подтверждённые пары, чтобы аудит был прослеживаем.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
