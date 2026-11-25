# P133-blind-audit — Аудит единиц был слеп к однобуквенным символам: 17 пропусков

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T12:56:12Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `tools/units_symbol_audit.py`
- `docs/UNITS-SYMBOLS-BASELINE.json`
- `docs/FORMULA-COST-SPLIT.md`
- `PROTOCOL.md`

## Что нужно сделать

Фильтр len>1 скрывал d, L, V, b, x, w, t; потолок 17 вместо нуля.

## Критерии приёмки (прогоняет только main)

- `python3 tools/units_symbol_audit.py --strict`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
