# KG-SEARCH-QUERIES.md — широкие запросы: как собрать базу знаний из первых принципов

**Дата:** 2026-11-20. **Зачем:** нам нужна память, где **формулы, данные (включая планетарные), эксперименты и
утверждения** лежат в одной машиночитаемой форме, а агент видит **карту** и **глаголы**, а не файлы. Ниже — вопросы
для поиска, сгруппированные по тому, **что мы хотим узнать**, а не по областям.

**Как пользоваться:** каждый пункт — запрос; в скобках — что он даёт. Приоритет — §1 (форматы), §2 (формулы),
§2.3 (единицы), §6 (внешние данные).

---

## 1. Форматы и стандарты представления знания

1. `Open Knowledge Format OKF v0.2 specification` — что именно стандартизовано, а что оставлено за скобками.
2. `OKF attested computation receipt executor` — как устроен детерминированный аттестер без LLM.
3. `RO-Crate specification provenance dataset software` — контейнер для данных+кода+метаданных.
4. `W3C PROV-O claim evidence graph pattern` — как выражать «откуда число».
5. `nanopublication RDF claim provenance structure` — атомарное утверждение как единица публикации.
6. `FAIR principles machine actionable metadata` — что значит «machine-actionable» формально.
7. `JSON Lines vs SQLite vs DuckDB for append-only knowledge base agent` — что дешевле для агента.
8. `OKF v0.2 stale_after status field semantics` — как заявлять устаревание.

## 2. Формулы как машиночитаемые объекты

1. `MathML vs OpenMath vs LaTeX machine readable formula semantic` — что даёт смысл, а не вид.
2. `MathML Content vs Presentation` — какая ветка нужна для вычислений.
3. `Lean 4 mathlib statement signature typeclass units` — можно ли выразить **размерности** типами.
4. `dimensional analysis type system units of measure F# Lean` — размерности как типы.
5. `NIST SI units ontology QUDT` — готовая онтология единиц.
6. `formula provenance: linking equation to experiment and dataset` — как связывать формулу с прогоном.
7. `symbolic regression equation discovery benchmark Feynman` — как проверять «правильность» найденной формулы.
8. `equation of state representation machine readable planetary` — формулы для планетарных величин.

## 2.3. Размерности и порядки величины (наши «невозможные числа»)

1. `order of magnitude sanity check physics dimensional analysis`
2. `unit checking linter scientific code`
3. `QUDT vs OM vs UCUM units comparison`
4. `Fermi estimation plausibility bounds scientific claim`

## 3. Извлечение утверждений и связей

1. `claim extraction scientific text benchmark SciFact` — что реально извлекается.
2. `relation extraction precision scientific LLM evaluation` — почему 21–53 % — верхняя граница.
3. `contradiction detection scientific claims dataset` — как измеряют противоречия.
4. `citation context classification support refute mention` — какой тип связи где встречается.
5. `same claim identification paraphrase scientific statement` — когда два утверждения — одно.
6. `context qualifier extraction experimental conditions` — как извлекать условия.

## 4. Карта графа и навигация

1. `community detection knowledge graph Leiden label propagation comparison`
2. `graph summarization hierarchy RAPTOR community summary`
3. `personalized pagerank subgraph retrieval knowledge graph`
4. `graph serialization for LLM adjacency list triples token cost`
5. `MCP verbs knowledge graph map hop path claims` — какие глаголы уже стандартизованы.
6. `context budget agent knowledge graph 10k tokens map`

## 5. Противоречия, доверие, устаревание

1. `trust tiers evidence grade machine readable` — как записывать силу свидетельства.
2. `GRADE evidence certainty levels structured` — формальные уровни.
3. `supersedes relation knowledge graph versioning`
4. `temporal validity interval claim database` — как хранить «когда верно».
5. `retraction propagation citation graph` — что делать с отозванными работами.

## 6. Внешние данные: планетарные и научные

1. `NASA PDS Planetary Data System API metadata search` — как получить PID и метаданные.
2. `USGS Astrogeology planetary GIS API` — слои, единицы.
3. `NASA Exoplanet Archive TAP service` — таблицы с единицами.
4. `JPL Horizons API ephemeris` — численные эфемериды.
5. `SPICE kernels toolkit planetary coordinates` — как хранить геометрию/время.
6. `XSD units planetary dataset metadata` — как узнавать единицы из метаданных.
7. `OpenAlex polite pool email only rate limits` — внешний слой литературы без ключей.
8. `Unpaywall API no key full text` — где брать полный текст.
9. `Zenodo DOI deposit metadata schema` — как публиковать свои данные.
10. `IVOA VO standards table units` — астрономические стандарты единиц.

## 7. Наш собственный корпус: эксперименты и код

1. `experiment tracking schema run parameters seeds hashes` — уже есть (`results/`), нужен ли стандарт (MLflow?).
2. `RO-Crate for computational experiments reproducibility`
3. `content addressed artifacts sha256 provenance`
4. `provenance graph of code commits and results`
5. `DVC vs git-annex vs plain git for results` — надо ли отдельное хранилище.

## 8. Что не искать (экономия)

1. Ещё одну RAG-обвязку: retrieval ≠ знание.
2. «Граф всей науки»: он есть (OpenAlex/S2/ORKG), наш — overlay.
3. Генераторы слайдов/постеров.
4. Готовые «AI-вики» продукты: ищем только **формат** и **глаголы**.

---

## 9. Что мы хотим получить из каждого блока (критерий)

| блок | критерий «достаточно» |
|---|---|
| §1 форматы | можно задать **один** JSONL-схему, которая переживёт импорт без потерь |
| §2 формулы | формула имеет сигнатуру: символы, единицы, Lean-имя, ссылку на проверку |
| §3 извлечение | мы знаем реальную точность и не строим на ней критичных выводов |
| §4 карта | карта укладывается в ≤ 10 тыс. токенов и всегда в контексте |
| §5 доверие | сила свидетельства — поле, а не мнение; отзыв работы распространяется |
| §6 данные | любая внешняя величина приходит с PID, единицей и датой доступа |
| §7 свой корпус | каждый прогон восстановим из git + `results/` + команды |
