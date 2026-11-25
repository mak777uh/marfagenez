# P125-adder-atom — sizer/adder/timer: внесён атом по открытой статье

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T11:51:38Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `literature/map/inbox/main-p125-atoms-20261125.jsonl`
- `docs/STITCH-*.json`
- `docs/STITCH-S-READ.md`

## Что нужно сделать

Nieto et al. 2025 (Biophys J, PMC12256869): adder — прирост не зависит от размера при рождении.

## Критерии приёмки (прогоняет только main)

- `python3 checks/map_contract.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
