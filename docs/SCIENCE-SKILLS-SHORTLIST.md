# SCIENCE-SKILLS-SHORTLIST.md — список всего присланного, к тестированию по очереди

**Дата:** 2026-11-21. **Статус:** **ничего не установлено и не проверено**; это реестр кандидатов и план проверки.
Всё, что ниже «работает без ключей» — **утверждение из присланных материалов, а не измерение**; проверяем по очереди.

**Зачем:** выбрать оптимальный стек, а не поставить десять дублей. Кандидат попадает в работу только после
прохождения §6 (тест), иначе остаётся в списке «обещано».

---

## 1. Навыки и пакеты Agent Skills (кандидаты)

| # | Название / репозиторий | Что даёт | Без ключей? | Лицензия | Статус |
|---|---|---|---|---|---|
| S1 | `K-Dense-AI/scientific-agent-skills` → `paper-lookup` | 18 научных API: PubMed, PMC, Europe PMC, bioRxiv/medRxiv, arXiv, OpenAlex, Crossref, S2, CORE, Unpaywall, OpenCitations, PubTator3, Zenodo, Figshare, ROR, BioStudies, DOAJ; пагинация со сверкой count'ов, JATS→текст | да (кроме CORE full text) | MIT | не проверен |
| S2 | там же → `database-lookup` | 80 предметных БД (GEO, ENA, PRIDE, ClinicalTrials.gov, PubChem и др.) | да, у части источников свои условия | MIT | не проверен |
| S3 | там же → `literature-review` | PRISMA-протоколы, отбор, журнал исключений | да (часть функций требует Parallel/OpenRouter) | MIT | не проверен |
| S4 | `openags/paper-search-mcp` | 20+ источников, PDF-скачивание, дедуп, цитатные графы; есть DSH-бандл | да, кроме опциональных | MIT | не проверен |
| S5 | `dsebastien/ai-skill-arxiv` → `arxiv-search`, `arxiv-analyze`, `arxiv-monitor` | поиск arXiv (JSON), многоуровневый fetch (arxiv2md → HTML → ar5iv → PDF → TeX), мониторинг запросов | **да, stdlib Python** | MIT | не проверен |
| S6 | `dsebastien/ai-skill-scholar` | поиск OpenAlex, цитатный граф, literature-review с состоянием на диске | да, stdlib | MIT | не проверен |
| S7 | `google-deepmind/science-skills` → `literature-search-openalex`, `literature-search-arxiv` | эталонные поддерживаемые скиллы под актуальные лимиты OpenAlex | да | Apache-2.0 | не проверен |
| S8 | `petar-nauka/search-science-literature` | 13 API, дедуп, retraction-check, BibTeX/RIS/CSV, fan-out | да (S2/CORE/WoS опционально) | не указана | не проверен, читать скрипты |
| S9 | `marciob/skill-research-papers` | arXiv/OpenAlex/DBLP/S2/PubMed, fetch_and_parse → Markdown, `pymupdf4llm` | да (email опционален) | не указана | не проверен |
| S10 | `KalarisLabs/research-agent-skills` | большая библиотека (обзоры, гипотезы, дизайн, ревью) | смешанно | не указана | брать поштучно |
| S11 | `saidsurucu/literature-review-skills` | 23 источника, часть через Chrome/Scopus | частично | не указана | для headless хуже |
| S12 | `Galaxy-Dawn/claude-scholar` | Evidence Records, Claim Promotion Gate, claim→evidence ledger | да | MIT | идеологически близко, брать `skills/*` |
| S13 | `Zilize/parallax-dsh` | корпус по arXiv: поиск, наборы, графы, экспорт | да | не указана | не проверен |
| S14 | `Zotero`-мост (`dsh-zotero-skill`) | локальная библиотека Zotero + OpenAlex | чтение без ключей | не указана | нужен Zotero |
| S15 | `keyless-research-mcp` | MCP: OpenAlex, arXiv, Crossref, Europe PMC, DOAJ, Unpaywall | заявлено да | не указана | MCP-путь, не skill |
| S16 | `O0000-code/awesome-academic-skills` | каталог 223 скиллов по стадиям | — | — | источник, не скилл |
| S17 | `awesome-deepseek-harness` → `SAC_search` (~200 поисковиков), пресеты `dsh-researchcraft`, `obsidian-knowledge-mode` | серая литература, дисциплина claim'ов | частично | — | проверить состав |
| S18 | `wentorai` → `dataset-finder-guide` | Kaggle/HF/Google Dataset Search/Zenodo/UCI | Kaggle требует `kaggle.json` | не указана | годится как памятка |

**Исключены как платные/с авторизацией** (записаны, чтобы не терять): `research-lookup` (Parallel + OpenRouter),
`parallel-web`, `exa-search`, `paperclip`, `bgpt-paper-search`; CORE full text (ключ), BASE (регистрация IP),
IEEE/WoS/Scopus/Web of Science, Kaggle downloads, Lens, Dimensions.

---

## 2. Прямые API (без ключей), которые можно дёргать самим

| API | Что | Лимит (по присланным данным) | Проверено нами |
|---|---|---|---|
| OpenAlex | 250M+ работ, цитаты, **датасеты через DataCite** | 10 req/s; спорный «дневной бюджет на IP» — **проверить** | да, отвечает |
| Crossref | DOI и метаданные | ~50 req/s, `mailto` для polite pool | да |
| arXiv | препринты, полный текст | **1 запрос / 3 с**, одно соединение | да (через ar5iv) |
| PubMed E-utilities | биомедицина | 3 req/s без ключа | нет |
| Europe PMC | биомедицина + OA full text | без ключа и email | да |
| Semantic Scholar | граф цитирований | общий пул, частые 429 | нет |
| Zenodo | данные, код, DOI | 30 req/min, 25 на страницу анонимно | нет |
| Figshare | данные, рисунки | поиск **POST**, не GET | нет |
| DataCite | DOI исследовательских данных | без ключа | да |
| DOAJ, dblp, HAL, OpenCitations, PubTator3, ROR, BioStudies, bioRxiv/medRxiv | по назначению | мягкие | нет |
| Unpaywall | OA-копии | требует **реальный email** в параметре | нет |

**Проверено живьём уже сейчас:** `example.com` (HTTP 200 после правки прокси), `ar5iv` (полный текст
L-060, 81 691 байт в `papers/`), PMC (полный текст Chao 2010), Crossref/OpenAlex/Europe PMC/DataCite/Zenodo —
отвечают через `domain_search`.

---

## 3. Каталоги и агрегаторы, которые присланы как «смотреть дальше»

- <https://orkg.org> — Open Research Knowledge Graph (структурированные утверждения; идеологически ближе всего к нашему KG).
- <https://explore.openaire.eu/search/advanced/research-outcomes> — OpenAIRE Explore (публикации, данные, проекты).
- <https://semopenalex.org> — SPARQL/RDF-версия OpenAlex (граф, а не список).
- `free-apis-list` (GitHub) — реестр API без ключей.
- `re3data` — реестр репозиториев данных.
- `PaperPanda` — браузерное расширение для поиска OA-копий (в headless не применимо).

---

## 4. Что именно мы хотим получить (критерии выбора)

1. **Полный текст**, а не сниппет: PDF/HTML/XML читается и сохраняется в `papers/`.
2. **Провенанс**: endpoint, параметры, дата, идентификаторы (DOI/PMID/arXiv) — под наши поля `evidence`.
3. **Дедуп** по DOI/arXiv-id/нормализованному заголовку.
4. **Retraction-проверка** (Crossref `update-type:retraction`, OpenAlex `is_retracted`).
5. **Честные ошибки**: пустой ответ ≠ «не существует»; 200 ≠ успех (пагинация, игнорируемый параметр).
6. **Работа без ключей** и без регистрации в основной цепочке.
7. **Совместимость с DSH**: `<name>/SKILL.md`, kebab-case, stdlib/Python 3.11+.

---

## 5. Порядок тестирования (по одному, не всё сразу)

| шаг | кандидат | что проверяем | критерий «прошёл» |
|---|---|---|---|
| T1 | S1 `paper-lookup` | поиск по 3 источникам + JATS→текст на реальной статье | получаем текст и провенанс без ключей |
| T2 | S5 `ai-skill-arxiv` | `arxiv-search` → `arxiv-analyze` на одной статье | JSON + полный текст, лимит 1/3 с соблюдён |
| T3 | S3/S12 (контракт вывода) | можно ли взять дисциплину provenance и claim-gate | поля ложатся в `kg/` без переделки |
| T4 | S2 `database-lookup` | один предметный архив (Zenodo или GEO) | запись с версией/лицензией |
| T5 | S7 DeepMind | сравнение покрытия с S1 на одном запросе | не хуже по полноте, меньше кода |
| T6 | S4 `paper-search-mcp` | только если MCP-путь оправдан | выигрыш в покрытии, а не в удобстве |

После каждого шага записываем: команда, время, что вернулось, где ошибка, сколько токенов, и **вердикт**
«берём / не берём / только как памятка». Итог — `SCIENCE-STACK-DECISION.md`, выбранный набор ставим в
`~/.dsh/skills` (или проектный `.agents/skills`).

---

## 6. Протокол одного теста (шаблон)

```
кандидат:        S<n> <repo>
установка:       <команда>; куда: ~/.dsh/skills или .agents/skills
запрос:          "process-enablement graphs organisational closure" (фиксированный)
что ожидалось:   <по документации>
что получено:    <id, текст?, провенанс?, время, токены>
ошибки:          <429/403/пусто/200-но-не-то>
вердикт:         берём / не берём / памятка
```

---

## 8. Проверка 2026-11-21 — что реально отвечает

Прогон: `curl` из Windows (schannel), `-L --compressed`, до трёх попыток, UA `dsh-probe/1.0`. Один и тот же
концептуальный запрос для всех: «система, которая постоянно производит компоненты, производящие её».

### 8.1 Сеть (главное, что определяет доступность)

- **Выход есть только у Windows.** Из WSL `curl` наружу не идёт (таймаут 20 с), потому что fake-IP-прокси живёт
  на стороне Windows. Все пробы — через `curl.exe`, не через `wsl`.
- **Python `urllib` врёт о доступности:** у него TLS-рукопожатие рвётся (`UNEXPECTED_EOF`, `handshake timed out`)
  там, где `curl` получает 200 (openalex, europepmc, datacite, zenodo). Причина — прозрачный прокси не терпит
  своего TLS от клиента. **Вывод: проверять доступность только `curl`, а Python-клиенты (если ставить скиллы)
  считать ненадёжными в этом окружении.**

### 8.2 Что отвечает 200

| инструмент | вердикт | деталь |
|---|---|---|
| Crossref | ✅ | 200, 1.4 КБ, 8 с (первый холодный) |
| arXiv API (`export.arxiv.org`) | ✅ | 200, 2.7 КБ, 2.8 с |
| PubMed E-utilities | ✅ | 200, 2.2 КБ, 8.8 с |
| Europe PMC | ✅ | 200, `hitCount` 3209, 3.7 с |
| Europe PMC full-text (`BODY:"…"`) | ✅ технически | 200; синтаксис работает, но `BODY:"process-enablement graph"` дал **0** — фраза не находится дословно |
| DataCite | ✅ | 200, 33 КБ |
| Zenodo | ✅ | 200, 20 КБ |
| Figshare | ✅ | 200 |
| DOAJ | ✅ | 200, но релевантность плохая: на «organisational closure» отдал педагогику |
| dblp | ✅ | 202 (норма для dblp) |
| ROR | ✅ | 200, 24 КБ |
| BioStudies | ✅ | 200 |
| OpenAIRE | ✅ | 200, 70 КБ |
| OpenCitations | ✅ | 200, `count: 68` |
| SemOpenAlex (SPARQL) | ✅ | 200, XML-результат |
| Hugging Face Hub API | ✅ | 200 |
| GitHub API | ✅ | 200 у K-Dense, `paper-search-mcp`, DeepMind, `claude-scholar`, `ai-skill-arxiv` |
| `raw.githubusercontent.com` | ✅ | SKILL.md `paper-lookup` скачался, 26 136 байт |

### 8.3 Что не отвечает или отвечает плохо

| инструмент | вердикт | причина |
|---|---|---|
| **OpenAlex** | ⚠️ работает, но дорого | 200 за 1 с, **но сам API пишет**: «No API key, so this request shares one free daily budget ($0.10) with everyone on your network's IP». Значит присланное про $0.10/день — **правда, подтверждено ответом сервера**. Массовый сбор через него не строим |
| **Semantic Scholar** | ❌ без ключа | сначала 429, затем **403 Forbidden** — общий пул закрыт. Это единственный настоящий семантический (embedding) поиск в списке, поэтому без бесплатного ключа «семантики по всем публикациям» нет |
| **ORKG** | ❌ | `api.orkg.org` **не резолвится** (curl: could not resolve host). Сайт в реестре есть, API в этом окружении недоступен |
| **exa** (нейронный) | ❌ | ключ отклонён (HTTP 403), движок молча падает на `keenable` |
| **google** | ❌ | `GOOGLE_CSE_API_KEY` не настроен, тоже падение на `keenable` |
| Semantic Scholar как `domain_search s2` | ⚠️ | отдаёт сниппеты, но это не API-поиск, а движок |

### 8.4 Семантический поиск: что есть на самом деле

| способ | что это | вердикт |
|---|---|---|
| OpenAlex `?search=` | ранжирование по релевантности (лексическое, не эмбеддинги) | ✅ работает: на запрос без ключевых слов вернул ровно нужное — «On the naturalisation of teleology», «Closure of Constraints in the Earth System», «Organisational teleology 2.0» |
| OpenAlex `filter=fulltext.search:` | поиск по полному тексту | ✅ работает (autocatalytic closure → 3 точные статьи) |
| Europe PMC `BODY:` | булев поиск по телу статей | ✅ синтаксис, но дословные редкие фразы дают 0 |
| Semantic Scholar `/paper/search` | эмбеддинги + рекомендации | ❌ 403/429 без ключа |
| SemOpenAlex SPARQL | структурные запросы по графу | ✅, но это не ранжирование |
| `keenable` (через наш поиск) | веб-поиск по смыслу | ✅ на концептуальный запрос вернул Википедию/Springer/энциклопедию про автопоэзис — **как «семантический по литературе» это веб, а не индекс публикаций** |

**Итог по семантике:** бесплатного ключевого семантического поиска по массиву публикаций в этом окружении
**нет**. Ближайшее: OpenAlex relevance + fulltext filter (лексика, но хорошая) и Europe PMC full text. Настоящий
семантический поиск = Semantic Scholar, но он требует **бесплатного ключа (одна кнопка)**, иначе 403.

### 8.5 Что делаем дальше (уточнённый порядок)

1. **T0 (готово):** доступность измерена, см. §8.2–8.3.
2. **T1:** `paper-lookup` — проверить на нём, что скрипты переживают `curl`-только сеть и не падают на Python-TLS.
3. **T2:** `ai-skill-arxiv` — arXiv API отвечает, значит поиск и fetch реальны; проверить лимит 1/3 с.
4. **T3:** решить по **двум бесплатным ключам**: Semantic Scholar (семантика) и OpenAlex ($1/день вместо $0.10).
   Без них стек остаётся лексическим.
5. **T4:** `database-lookup` на Zenodo/DataCite — оба отвечают.
6. **Вне списка:** ORKG и exa вычеркнуть из рабочих кандидатов (DNS / ключ).

---

## 9. Установка и первый живой тест (T1), 2026-11-21

### 9.1 Что установлено

| навык | путь | файлов | SKILL.md |
|---|---|---|---|
| `paper-lookup` | `C:\Users\Admin\.dsh\skills\paper-lookup` | 24 (5 скриптов + 18 `references/`) | есть |
| `database-lookup` | `...\skills\database-lookup` | 83 (80 `references/`) | есть |
| `literature-review` | `...\skills\literature-review` | 12 | есть |

Ставились **не клоном**, а по списку файлов из GitHub API (`trees/main?recursive=1`, 3 497 записей), скачано 119 объектов,
`ok=119 fail=0`. Причина: tarball репозитория — **244,7 МБ** (картинки в `docs/`), и `curl` оборвал загрузку на
180-й секунде (52,8 МБ). Клон через git в этом окружении тоже ненадёжен (TLS-рукопожатие). После установки
каталог навыков в сессии обновился сам — `paper-lookup`, `database-lookup`, `literature-review` видны.

**Ключ OpenAlex** положен в `C:\Users\Admin\.dsh\secrets\openalex.key` (22 байта, ACL только владельцу),
в вывод не печатается; в скриптах читается в `OPENALEX_API_KEY`.

### 9.2 Проверка ключа (то, что было под вопросом)

```
GET https://api.openalex.org/rate-limit?api_key=…
{"is_grandfathered":false,
 "rate_limit":{"daily_budget_usd":1,"daily_used_usd":0,"daily_remaining_usd":1,
               "resets_at":"2026-…"}}
```

Ключ работает: бюджет **$1/день** вместо общих **$0.10** на IP. То есть присланное про $0.10 было верно для
бесключевого режима, а ключ поднимает потолок в десять раз.

### 9.3 Скрипты навыка — живые результаты

| тест | что сделано | результат | время |
|---|---|---|---|
| `openalex` + ключ | поиск «process enablement graphs organisational closure» | **count 17 366**; топ-1 — **«Studying organisational closure in biological systems with process-enablement graphs»**, BioSystems 2025, `10.1016/j.biosystems.2025.105567` | 1,3 с |
| `openalex_abstract.py` | абстракт топ-хита из `abstract_inverted_index` | JSON: `count 1`, `with_abstract 1`, абстракт **2 035 символов** (без бага с дублями позиций) | 0,2 с |
| `arxiv_atom.py` | `id_list=2411.17012` | JSON: `arxiv_id_versioned 2411.17012v2`, версия, заголовок, абстракт, `query_as_executed` | 1,1 с |
| `jats_to_text.py` | `efetch db=pmc id=2928801` → секция `Model` | XML 102 371 Б → **4 461 символ** текста + метаданные (PMID, PMCID, DOI, авторы) | 1,6 с |
| `jats_to_text.py`, ошибка | запрос секции `ABSTRACT` | честная ошибка: `no section matched 'ABSTRACT'; available: Introduction, Model, Results, Discussion` — **правильное поведение**, а не пустой текст | — |
| `paginate.py --dry-run` | обход OpenAlex | URL с `api_key=REDACTED`, `delay_seconds 0.2` — ключ **не утекает** в провенанс | 0,4 с |

### 9.4 Найденная тонкость

`paginate.py` ждёт **сырую строку параметров**, а не фразу: `--query 'search=crispr'`, а не `--query 'crispr'`.
При фразе он собирает `…works?organisational+closure=&per_page=100` — URL формально валиден, но запрос пустой.
Записать в правила: для `paginate.py` всегда `--query 'search=…'`.

### 9.5 Побочная научная находка

У `L-060` есть **журнальная версия**: Brown & Vittadello, «Studying organisational closure in biological systems
with process-enablement graphs», *BioSystems* (2025), DOI `10.1016/j.biosystems.2025.105567`. То есть у записи
`L-060` (arXiv) появился рецензируемый двойник — это повышает вес моста `C-003 ↔ L-060`.
Записать в `ELEPHANT-LITERATURE.md` как `L-067` (или обновить `L-060` до `full_text` с журнальным DOI) — задача
следующего круга, в этот коммит не входит.

### 9.6 Что ещё не проверено

- `database-lookup` и `literature-review` установлены, но **не запускались** (T4, T7).
- `ai-skill-arxiv` (S5) не установлен: `arxiv_atom.py` из `paper-lookup` уже закрывает разбор Atom.
- Semantic Scholar по-прежнему 403 без ключа — семантика ждёт своего ключа.

---

## 10. T4 и T7 — что ещё работает (2026-11-21)

### 10.1 `database-lookup` — это **каталог**, а не код

Внутри только `references/`, скриптов нет: восемьдесят два справочника. Проверено содержимое: **82 предметных базы**, среди них `geo`, `ena`,
`pride`, `sra`, `pdb`, `uniprot`, `chembl`, `pubchem`, `clinicaltrials`, `gwas-catalog`, `gnomad`, `reactome`,
`string`, `ncbi-gene`, `ncbi-protein`, `ncbi-taxonomy`, `metabolomics-workbench`, `hca`, `monarch`, `opentargets`,
`alphafold`, `fred`, `sec-edgar`, `worldbank`, `who`, `nasa`, `noaa`, `usgs`, `census`, `eurostat`, `bea`, `bls`.
Плюс `database_selection_guide.md` и `retrieval-contract.md`.

**Вывод:** это не «ещё один поиск», а справочник «какой базой отвечать на какой вопрос». Для нас полезен только тогда,
когда нужны **исходные данные**, а не статьи. Zenodo/DataCite/Figshare в нём **нет** — они закрыты `paper-lookup`.

Живая проверка документированного запроса к Zenodo (`/api/records?q=…`): 200, `hits 382727`, 1,7 с — но при
`sort=mostrecent` выдача нерелевантна, сортировку по релевантности надо задавать явно.

### 10.2 `literature-review` — два разных скрипта, оба полезны

| скрипт | что делает | тест | итог |
|---|---|---|---|
| `search_databases.py` | **не ищет**: обрабатывает уже собранные записи — дедуп, ранжирование, markdown/BibTeX | 3 записи (2 дубля) → `total_results 2`, дубль схлопнут, Chao (400 цит.) выше Brown (12), вывод markdown | ✅ работает **локально**, сети не требует |
| `verify_citations.py` | проверяет DOI в markdown через Crossref и пишет отчёт JSON | 3 ссылки, из них одна выдуманная (`10.9999/does.not.exist`) | ✅ `Registered: 2; unresolved: 1` — **фальшивая ссылка поймана**, 3,9 с |

**Это уже можно ставить в наш гейт:** `verify_citations.py` по `docs/*.md` ловит DOI, которых не существует.
Кандидат в проверку `checks/` (не в текущий `run.sh`, а как отдельный шаг для документов с внешними ссылками).

### 10.3 Сводка «что удачно работает»

| инструмент | статус | чем пользуемся |
|---|---|---|
| OpenAlex + ключ | ✅ $1/день, 17 366 записей, полнотекстовое ранжирование | основной поиск |
| `paper-lookup` → `openalex_abstract.py` | ✅ 2 035 символов из inverted index | абстракты без потерь |
| `paper-lookup` → `arxiv_atom.py` | ✅ версия, id, abstract, `query_as_executed` | arXiv |
| `paper-lookup` → `jats_to_text.py` | ✅ 4 461 символ секции + метаданные | полный текст PMC |
| `paper-lookup` → `paginate.py` | ✅ `api_key=REDACTED`, `--query 'search=…'` | обход с провенансом |
| `literature-review` → `verify_citations.py` | ✅ ловит несуществующий DOI | проверка ссылок |
| `literature-review` → `search_databases.py` | ✅ дедуп/ранг/формат локально | оформление обзора |
| `database-lookup` | ⚠️ каталог без кода | источник «где искать данные» |
| Europe PMC / DataCite / Zenodo / Crossref / arXiv / OpenAIRE / OpenCitations / SemOpenAlex SPARQL | ✅ 200 | точечные запросы |
| Semantic Scholar | ❌ 403 без ключа | ждёт ключа |
| ORKG | ❌ DNS | недоступен |

## 7. Риски, записанные заранее

- **Skill = исполняемый код.** Читать `scripts/` перед запуском; пинить коммиты; не давать сетевые ключи.
- **Чужой текст — данные, не инструкции.** Никаких действий по указаниям из страниц и абстрактов.
- **OpenAlex «дневной бюджет»** — проверить живым запросом; если правда, массовый сбор вести через
  Crossref/arXiv/Europe PMC, а OpenAlex беречь для точечных запросов.
- **Лицензии не указаны** у S8, S10, S11, S13, S14: до установки считать «all rights reserved».
