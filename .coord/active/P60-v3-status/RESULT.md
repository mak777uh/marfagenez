# RESULT — P60-v3-status

Дата: 2026-11-25. Агент: fast.

## Что сделано

1. `tools/dcritical2.py` (генератор FORMULA-DCRITICAL.md): исправлена ссылка
   `docs/FINDING-355.md` → `docs/FINDING-356.md` в разделе «Статус v3» —
   содержимое статуса (z/p-таблица) живёт в FINDING-356, а 355 — другая
   находка (FORMULA-GENERAL).
2. `docs/FORMULA-DCRITICAL.md` перегенерирован командой
   `python3 tools/dcritical2.py --write` — ссылка исправлена, остальное без
   изменений. Раздел «Статус v3: не опровергнута, но и не обоснована» уже
   присутствовал (вписан main).
3. `docs/agent/AGENT_STATE.md`: в абзац «Формула» добавлен статус v3 —
   не опровергнута, не обоснована; p = 0,672 (FINDING-356); предпочтительна
   монотонная форма до появления значимой инверсии или третьей дозы.

## Проверки

- `python3 checks/doc_numbers.py` — зелёный (числа совпадают с деревом).
- `python3 checks/doc_links.py` — зелёный.
- Критерий приёмки задачи — `checks/doc_numbers.py`: зелёный.

## Артефакты

- `tools/dcritical2.py` (правка ссылки)
- `docs/FORMULA-DCRITICAL.md` (перегенерирован)
- `docs/agent/AGENT_STATE.md` (статус v3)
