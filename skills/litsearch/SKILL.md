---
name: litsearch
description: Литературный поиск этого репозитория — один вход, три канала, воспроизводимый снимок, карантин кандидатов. Использовать, когда нужен поиск научных работ по теме, когда надо проверить, что работа уже учтена в реестре, или когда кандидат должен стать свидетельством.
---

# litsearch — как искать в этом репозитории

Короткий навык. Он не объясняет, **что** искать (это дело владельца и `SEARCH-METHOD.md`), а объясняет,
**какими командами** это делать так, чтобы результат можно было перепроверить чужими руками.

## 1. Проверить, что машина готова

```bash
python3 tools/doctor.py            # venv, модели, ключ, файлы, навыки
python3 tools/doctor.py --budget   # плюс живой остаток OpenAlex
```

`MISS` в выводе значит «канал может ответить пусто, и это будет не „ничего не найдено“, а неготовность».

## 2. Поиск

```bash
python3 tools/litsearch.py "<запрос по-английски>" --seeds "термин1;термин2;термин3" --per-channel 10
```

- три канала: `paper-search` (Crossref/arXiv/PubMed/OpenAlex), `lixplore` (пять баз), `openalex` (API);
- дедуп `doi > arxiv > pmid > title_norm+year`, слияние RRF `k=60`;
- снимок: `literature/runs/<run_id>.json` + `raw/` с сырыми ответами и sha;
- повтор внутри TTL кэша бесплатен и стабилен.

Сравнение с прошлым прогоном (насыщение):

```bash
python3 tools/litsearch.py "<тот же запрос>" --compare <prev_run_id>
```

Повтор без сети:

```bash
python3 tools/litsearch.py --offline --from-run <run_id>
```

## 3. Проверить снимок

```bash
python3 checks/litsearch_contract.py                     # все снимки
python3 checks/litsearch_contract.py literature/runs/<run_id>.json
```

Он пересчитывает дедуп и RRF из рангов: если числа подправлены руками, будет FAIL.

## 4. Кандидаты — только через карантин

```bash
python3 tools/lit_ingest.py ingest --from-run <run_id> --top 20
python3 tools/lit_ingest.py list --status new
python3 tools/lit_ingest.py admit CAND-xxxxxxxxxx --claim C-001 --L L-060 --why "почему это свидетельство" --dry-run
python3 tools/lit_ingest.py reject CAND-yyyyyyyyyy --why "не по теме: …"
```

- `ingest` **пропускает** то, что уже есть в реестре;
- `admit` требует существующий claim, существующий `L-NNN` и причину ≥10 символов;
- допуск пишется в `kg/admissions.jsonl` (hash-chain), а не в `kg/nodes.jsonl`: кандидат в графе изменил бы
  навигацию, потому что фильтра по `lifecycle` нет;
- отклонённые — tombstone: повторный ингест их не воскресит.

## 5. Уровень доступа — не самооценка

Запись литературы живёт в `docs/ELEPHANT-LITERATURE.md` как проза **плюс** JSON-блок:

```bash
python3 checks/literature_contract.py          # 10 правил, обратный индекс papers/
python3 tools/lit_migrate.py                   # показать, что миграция сделала бы
```

Правило: `full_text_examined` требует непустого файла в `papers/` с совпадающим `sha256`; «полный текст
не читал» остаётся `abstract_read`, что бы ни было написано рядом.

## 6. Когда остановиться

`SEARCH-METHOD.md`, раздел «Критерий остановки»: два недеградированных прогона с одинаковым
`query.fingerprint`, прирост ниже порога, Jaccard выше порога, ноль `admit`, все каналы `ok|empty`.
Решение — датированной записью; метрика только триггерит проверку.

## Чего не делать

- не писать снимки в `results/` (`git checkout` их потеряет) — только в `literature/`;
- не класть кандидатов в `kg/nodes.jsonl`;
- не поднимать уровень записи правкой прозы без файла в `papers/`;
- не запускать два гейта одновременно и не править `run.sh` во время прогона.
