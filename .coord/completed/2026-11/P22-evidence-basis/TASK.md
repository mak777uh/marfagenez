# P22-evidence-basis — Опора = evidence, а не только литературная пара: проверить C-002 и C-004

- автор: `main`
- вид: `research`
- постоянная: нет
- приоритет: 7
- создана: 2026-11-25T00:50:26Z

## Рабочая область (файлы, которые задача вправе менять/создавать)

- `docs/STITCH-AUDIT.md`
- `tools/stitch_audit.py`

## Что нужно сделать

Учесть evidence (experiment/result/literature/formula); исправить вывод о C-002 и C-004.

## Критерии приёмки (прогоняет только main)

- `python3 checks/doc_links.py`

## Правила

- Взятая задача неизменяема: правки `TASK.md` после `take` запрещены (sha256 в `.claim.json`).
- Результат — `RESULT.md` в каталоге задачи; `DONE.json` строит `finish`.
- Чужие активные области не редактируются; нужное вне области — отдельной задачей.
- Heartbeat: `python3 tools/coord.py heartbeat <ID> --agent <имя>` не реже 15 минут.
