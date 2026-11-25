# P119-anchor-pairs — Три новые ссылки как пары: два узла получили S

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T11:18:26Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-*.json`
- `docs/STITCH-S-READ.md`
- `checks/stitch_coverage_floor.py`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

F-008 ← V-0001 (S), F-010 ← DIP3-0001 и P-0009 (S); остальные четыре — Ch.

## Критерии приёмки (прогоняет только main)

- `python3 checks/stitch_coverage_floor.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
