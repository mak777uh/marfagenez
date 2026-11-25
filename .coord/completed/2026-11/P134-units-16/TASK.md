# P134-units-16 — 16 из 17 пропущенных символов получили единицы

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T13:00:59Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `kg/migrate.py`
- `docs/UNITS-AUDIT.md`
- `docs/UNITS-SYMBOLS-BASELINE.json`
- `tools/units_symbol_audit.py`

## Что нужно сделать

L оказался артефактом ссылки; d в F-027 остался неизвестным.

## Критерии приёмки (прогоняет только main)

- `python3 tools/units_symbol_audit.py --strict`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
