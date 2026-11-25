# P123-insurance-atom — Цена страховки: атом по открытому обзору (Тулджапурак)

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T11:40:21Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `literature/map/inbox/main-p123-atoms-20261125.jsonl`
- `docs/STITCH-*.json`
- `docs/FORMULA-INSURANCE.md`

## Что нужно сделать

Gascoigne et al. 2025 (Ecol Lett, PMC11862329): log λs ≈ log λ1 − ½Σe²CV².

## Критерии приёмки (прогоняет только main)

- `python3 checks/map_contract.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
