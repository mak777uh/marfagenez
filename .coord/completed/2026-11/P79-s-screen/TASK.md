# P79-s-screen — Экран S-пар: нашёл переоценённую пару C-003

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 5
- создана: 2026-11-25T05:31:33Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `tools/stitch_s_screen.py`
- `docs/STITCH-*.json`
- `docs/STITCH-ADJUDICATION.md`
- `checks/stitch_coverage_floor.py`
- `docs/STITCH-COVERAGE-FLOOR.json`

## Что нужно сделать

B26-01-0004|C-003: та же мера (доля вершин в наибольшей SCC), но узел утверждает различение топологий 0.25/0.75/1.0 — атом этого не проверяет.

## Критерии приёмки (прогоняет только main)

- `python3 tools/stitch_s_screen.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
