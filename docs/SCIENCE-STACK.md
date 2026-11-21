# SCIENCE-STACK.md — рабочий стек исследования литературы (2026-11-21)

**Это единственный файл, по которому надо выбирать инструмент.** Реестр кандидатов и отчёты о проверках —
`docs/SCIENCE-SKILLS-SHORTLIST.md`; здесь только то, что измерено и принято в работу.

## 1. Шесть каналов и чем именно они закрыты

| канал | инструмент и команда | что даёт | проверено |
|---|---|---|---|
| **1. Точный поиск** | `paper-search search "<q>" -s arxiv,openalex,crossref,pubmed -n 5` | дедуп по DOI/arXiv, провенанс по источнику | 4,0 с, топ-1 верный |
| **2. Широкий охват** | `lixplore -A -q "<q>" -m 5 -X json -o out.json` | PubMed + Crossref + DOAJ + EuropePMC + arXiv, дедуп | 4,6 с, 7 результатов |
| **3. Семантический** | OpenAlex `?search=` и `filter=fulltext.search:` с ключом | ранжирование по релевантности, полный текст | 17 366 записей на концептуальный запрос |
| **4. Обход цитат** | OpenCitations `.../v1/citations/<doi>`, OpenAlex `cited_by_api_url`, Crossref `reference` | кто цитирует / кого цитирует | 200, реальные DOI |
| **5. Полный текст** | `paper-lookup/scripts/jats_to_text.py`, `arxiv_atom.py`, `openalex_abstract.py`, Unpaywall | текст статьи, а не сниппет | PMC 4 461 симв., arXiv 81 691 Б, абстракт 2 035 симв. |
| **6. Аудит** | `literature-review/scripts/verify_citations.py <file.md>`, Crossref `filter=update-type:retraction` | несуществующие DOI, отозванные статьи | фальшивый DOI поймал; 81 816 отзывов в индексе |

## 2. Порядок работы над литературным вопросом

1. **Сформулировать вопрос и 3–5 терминов**, включая синонимы и исторические названия.
2. **Точный поиск** `paper-search` — получить 5–10 якорей с DOI.
3. **Широкий охват** `lixplore -A` — проверить, что якоря не единственные; разница в выдаче = новые каналы.
4. **Семантика** OpenAlex `search=<концепция без ключевых слов>` — найти работы, где терминология другая.
5. **Цитаты** OpenCitations/OpenAlex: назад (что цитирует) и вперёд (кто цитирует) от лучшего якоря.
6. **Полный текст** через `jats_to_text.py` / ar5iv / Unpaywall; сохранить в `papers/` и записать локатор.
7. **Аудит** `verify_citations.py` по документу, где будут ссылки; проверить `update-type:retraction`.
8. **Запись** в `ELEPHANT-LITERATURE.md` (`L-NNN`) с уровнем доступа: аннотация / фрагмент / **полный текст**.
9. **Остановка**: новый проход даёт <2 новых релевантных работ — считать насыщением, записать это в журнал.

## 3. Что отвергнуто и почему (чтобы не возвращаться)

| инструмент | причина |
|---|---|
| ORKG, exa, ACM DL, scite, SciSpace, Scilit, BASE API, CORE API (полный текст), NASA ADS, fatcat, RetractionWatch API | DNS/403/500/нужен токен — измерено, см. §8–§12 реестра |
| Semantic Scholar API | 403 без ключа; ключ нужен, если хотим настоящие эмбеддинги |
| `litstudy` | падает при импорте (несовместимость `bibtexparser`) |
| `paperseek` | агентный режим требует LLM-ключа; без него — только список источников |
| JabRef, Paperlib, VOSviewer, LitSift, ResearchRabbit, Connected Papers, Litmaps, Inciteful, Elicit, Consensus, Undermind, Lens, Dimensions | GUI/веб без API для агента |
| Google Scholar | скрейпинг и нарушение ToS |

## 4. Ключи и где они лежат

| ключ | файл | бюджет |
|---|---|---|
| OpenAlex | `~/.dsh/secrets/openalex.key` (ACL только владельцу) | $1/день |

Без ключа OpenAlex даёт $0.10/день на общий IP — массовый сбор через него не вести.

## 5. Установленное окружение

- `~/.dsh/skills/paper-lookup`, `database-lookup`, `literature-review` — навыки DSH.
- `~/.dsh/tools/sci-venv` — `paper-search`, `lixplore`, `mosaic`, `scholar-mcp`, `paper-search-mcp`, `academic-mcp`, `scimesh`.
- `papers/` — скачанные полные тексты; `docs/SCIENCE-TOOLING.md` — как качать и что чем читать.
