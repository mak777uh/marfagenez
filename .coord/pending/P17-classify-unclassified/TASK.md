# P17-classify-unclassified — Классифицировать 57 пар «не задан» из базовой таблицы сшивки

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 6
- создана: 2026-11-25T00:41:36Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-UNCLASSIFIED.md`
- `docs/STITCH-UNCLASSIFIED-VERDICTS.json`
- `literature/map/inbox/fast-*.jsonl`

## Что нужно сделать

В STITCH-TABLE 57 пар без классификации. По каждой: shared quantity, вердикт S/Ch/N, основание. Это самый дешёвый рост строгого покрытия. Артефакты передавать через finish --artifacts.

## Критерии приёмки (прогоняет только main)

- `python3 checks/map_contract.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
