# literature/dips — постоянный научный агент

Очередь задач и отчёты дип-ресерчера. Протокол: `docs/DIP-RESEARCHER.md`.

- `tasks.jsonl` — очередь (одна задача на строку, статусы `queued`/`running`/`done`/`rejected`);
- `reports/<task_id>.jsonl` — партия ячеек по `docs/MAP-FORMAT.md`;
- `reports/<task_id>.md` — отчёт: проверено / отброшено / покрытие.

Приём: `python3 checks/dip_reports.py && python3 tools/map_ingest.py literature/dips/reports/<task_id>.jsonl --report literature/map/ingest-<task_id>.md`.
