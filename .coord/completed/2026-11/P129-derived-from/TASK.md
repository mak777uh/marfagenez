# P129-derived-from — Схема: тип derived_from, долг опоры 10 → 1

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T12:37:51Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `kg/node-refs.json`
- `kg/migrate.py`
- `kg/regress.py`
- `kg/kg.py`
- `docs/ANCHOR-AUDIT.md`
- `docs/ANCHOR-BASELINE.json`
- `PROTOCOL.md`

## Что нужно сделать

Связи «узел → узел» через relations, а не через lit_ref: разные вещи должны быть видны отдельно.

## Критерии приёмки (прогоняет только main)

- `python3 tools/unanchored_nodes.py --strict`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
