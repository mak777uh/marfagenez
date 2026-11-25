# P122-eigen-atom — Порог ошибок Эйгена: внесён атом по открытому обзору

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T11:34:50Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `literature/map/inbox/main-p122-atoms-20261125.jsonl`
- `docs/STITCH-*.json`
- `docs/STITCH-S-READ.md`

## Что нужно сделать

Sardanyés et al. 2024 (npj Viruses, PMC11721110): μc = 1 − f1/f0 и смысл порога.

## Критерии приёмки (прогоняет только main)

- `python3 checks/map_contract.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
