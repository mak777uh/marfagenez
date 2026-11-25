# Инструкция внешнему агенту: работа с картой и графом (со ссылками)

**Кому:** агенту с доступом к **Windows** и **открытому вебу**, без доступа к WSL.
**Дата:** 26.11.2026. **Версия:** 2 (со ссылками).

---

## 0. Три адреса, которые нужны всегда

| что | где |
|---|---|
| **обменник** (сюда пишешь) | `C:\111\graph-bridge\outbox\` |
| **ответы** (сюда читаешь) | `C:\111\graph-bridge\ack\` |
| **состояние** (читаешь первым) | `C:\111\graph-bridge\STATE.md` |

**Репозиторий только для чтения:** [https://github.com/mak777uh/marfagenez](https://github.com/mak777uh/marfagenez)
Он живёт в WSL, но всё содержание доступно на GitHub — читай по ссылкам ниже, менять там ничего нельзя.

| файл | ссылка | зачем |
|---|---|---|
| план проекта | [https://github.com/mak777uh/marfagenez/blob/master/docs/AUTONOMOUS-PLAN.md](https://github.com/mak777uh/marfagenez/blob/master/docs/AUTONOMOUS-PLAN.md) | приоритеты и правила |
| **очередь источников** (40 DOI) | [https://github.com/mak777uh/marfagenez/blob/master/docs/L-DOI-GAPS.md](https://github.com/mak777uh/marfagenez/blob/master/docs/L-DOI-GAPS.md) | что вносить в карту |
| литература (откуда узлы `L-*`) | [https://github.com/mak777uh/marfagenez/blob/master/docs/ELEPHANT-LITERATURE.md](https://github.com/mak777uh/marfagenez/blob/master/docs/ELEPHANT-LITERATURE.md) | здесь лежат тексты узлов и их источники |
| линии слона | [https://github.com/mak777uh/marfagenez/blob/master/kg/lines.json](https://github.com/mak777uh/marfagenez/blob/master/kg/lines.json) | 10 линий, к каждой нужна привязка |
| открытые вопросы | [https://github.com/mak777uh/marfagenez/blob/master/docs/QUESTIONS.md](https://github.com/mak777uh/marfagenez/blob/master/docs/QUESTIONS.md) | что ещё не отвечено |
| пробелы литературы | [https://github.com/mak777uh/marfagenez/blob/master/docs/LITERATURE-GAPS.md](https://github.com/mak777uh/marfagenez/blob/master/docs/LITERATURE-GAPS.md) | формат «не найдено в поиске» |
| результаты (числа проекта) | [https://github.com/mak777uh/marfagenez/tree/master/results](https://github.com/mak777uh/marfagenez/tree/master/results) | прогоны, на которые опираются узлы |
| индекс графа | [https://github.com/mak777uh/marfagenez/blob/master/kg/INDEX.md](https://github.com/mak777uh/marfagenez/blob/master/kg/INDEX.md) | все 580 узлов списком |

---

## 1. Два канала работы

| канал | файл | что даёт карте |
|---|---|---|
| **A. Ячейки литературной карты** | `outbox\<имя>.atoms.jsonl` + `.edges.jsonl` | новые факты с числами и локаторами |
| **B. Предложения для графа знаний** | `outbox\<имя>.kg.jsonl` | цитаты к существующим узлам, рёбра, новые узлы |

**Начни с канала B, цикл A** (§6): там **136 узлов уже в графе**, им не хватает только цитаты. Это самый
дешёвый и самый полезный вклад.

---

## 2. Как брать цитаты, когда полный текст закрыт

Это главный практический навык. Четыре API отдают метаданные и аннотации **без ключей**:

| что нужно | адрес | пример |
|---|---|---|
| метаданные, авторы, журнал | `https://api.crossref.org/works/<DOI>` | <https://api.crossref.org/works/10.1186/s12934-016-0501-z> |
| **аннотация** (inverted index → текст) | `https://api.openalex.org/works/doi:<DOI>` | <https://api.openalex.org/works/doi:10.1186/s12934-016-0501-z> |
| есть ли полный текст в PMC | `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"<DOI>"&format=json` | <https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1186/s12934-016-0501-z%22&format=json> |
| бесплатная копия PDF | `https://api.unpaywall.org/v2/<DOI>?email=you@example.com` | <https://api.unpaywall.org/v2/10.1186/s12934-016-0501-z?email=test@example.com> |
| поиск по тексту статьи | `https://api.openalex.org/works?search=<слова>` | <https://api.openalex.org/works?search=retentostat%20maintenance%20coefficient> |

**Правило цитаты:** годится любая **дословная** подстрока — из аннотации тоже. В `source.level` пиши честно:
`abstract_read`, если читал аннотацию; `fragment_read`, если видел фрагмент; `full_text_examined`, только если
открывал полный текст.

---

## 3. Канал A: ячейки литературной карты

Партия = **один DOI**, 3–5 ячеек, у каждой — связь.

```json
{"atom": "WIN-041-01",
 "statement": "У E. coli в ретентостате при μ < 8·10⁻⁴ ч⁻¹ удельное потребление глюкозы сходится к m_S = 0.039 ± 0.003 ммоль/(г·ч).",
 "kind": "measurement", "confidence": "medium", "domain": "micro.bioenergetics",
 "formula": "m_S = 0.039 ± 0.003 ммоль/(г·ч)",
 "works": [{"doi": "10.1186/s12934-016-0501-z",
            "locator": "Results, «Retentostat culture»",
            "quote": "converged to 0.039 ± 0.003 mmol g X −1 h −1"}],
 "kg_ref": ["L-041"],
 "notes": "прямое измерение при near-zero росте"}
```

```json
{"from": "WIN-041-01", "to": "FAST-S2M-01", "type": "refines", "note": "тот же штамм, прямое измерение вместо экстраполяции"}
```

| проверяется машинно | отказ |
|---|---|
| `atom` начинается с `WIN-`, уникален | «должен начинаться с WIN-» |
| `statement` ≥ 40 символов | «короче 40» |
| `works[0]`: **doi + locator + quote** | «works[0].locator обязателен» |
| `kind` + `confidence` (`high`/`medium`/`low`) | «confidence должен быть high / medium / low» |
| `kg_ref` заполнен | «kg_ref обязателен» |
| **связь** у каждой ячейки | «N новых ячеек без единой связи» |

---

## 4. Очередь источников — со ссылками

Полный список: [https://github.com/mak777uh/marfagenez/blob/master/docs/L-DOI-GAPS.md](https://github.com/mak777uh/marfagenez/blob/master/docs/L-DOI-GAPS.md).
**Бери один DOI за партию.** Вторая колонка ссылок — сразу открывает метаданные и аннотацию.

| # | узел | DOI | ссылки |
|---|---|---|---|
| 1 | `L-001` | `10.1371/journal.pone.0233384` | [doi.org](https://doi.org/10.1371/journal.pone.0233384) · [OpenAlex](https://api.openalex.org/works/doi:10.1371/journal.pone.0233384) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1371/journal.pone.0233384%22&format=json) |
| 2 | `L-021` | `10.1371/journal.pcbi.1000872` | [doi.org](https://doi.org/10.1371/journal.pcbi.1000872) · [OpenAlex](https://api.openalex.org/works/doi:10.1371/journal.pcbi.1000872) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1371/journal.pcbi.1000872%22&format=json) |
| 3 | `L-038` | `10.1111/j.1469-185x.2012.00225.x` | [doi.org](https://doi.org/10.1111/j.1469-185x.2012.00225.x) · [OpenAlex](https://api.openalex.org/works/doi:10.1111/j.1469-185x.2012.00225.x) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1111/j.1469-185x.2012.00225.x%22&format=json) |
| 4 | `L-040` | `10.1198/016214506000001437` | [doi.org](https://doi.org/10.1198/016214506000001437) · [OpenAlex](https://api.openalex.org/works/doi:10.1198/016214506000001437) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1198/016214506000001437%22&format=json) |
| 5 | `L-041` | `10.1146/annurev-biophys-070317-032955` | [doi.org](https://doi.org/10.1146/annurev-biophys-070317-032955) · [OpenAlex](https://api.openalex.org/works/doi:10.1146/annurev-biophys-070317-032955) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1146/annurev-biophys-070317-032955%22&format=json) |
| 6 | `L-042` | `10.1007/s11538-006-9130-8` | [doi.org](https://doi.org/10.1007/s11538-006-9130-8) · [OpenAlex](https://api.openalex.org/works/doi:10.1007/s11538-006-9130-8) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1007/s11538-006-9130-8%22&format=json) |
| 7 | `L-046` | `10.1006/jtbi.1994.1089` | [doi.org](https://doi.org/10.1006/jtbi.1994.1089) · [OpenAlex](https://api.openalex.org/works/doi:10.1006/jtbi.1994.1089) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1006/jtbi.1994.1089%22&format=json) |
| 8 | `L-052` | `10.1162/isal_a_00722` | [doi.org](https://doi.org/10.1162/isal_a_00722) · [OpenAlex](https://api.openalex.org/works/doi:10.1162/isal_a_00722) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1162/isal_a_00722%22&format=json) |
| 9 | `L-055` | `10.1196/annals.1297.094` | [doi.org](https://doi.org/10.1196/annals.1297.094) · [OpenAlex](https://api.openalex.org/works/doi:10.1196/annals.1297.094) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1196/annals.1297.094%22&format=json) |
| 10 | `L-059` | `10.30707/lib1.2ledder` | [doi.org](https://doi.org/10.30707/lib1.2ledder) · [OpenAlex](https://api.openalex.org/works/doi:10.30707/lib1.2ledder) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.30707/lib1.2ledder%22&format=json) |
| 11 | `L-061` | `10.4324/9781003528937-24` | [doi.org](https://doi.org/10.4324/9781003528937-24) · [OpenAlex](https://api.openalex.org/works/doi:10.4324/9781003528937-24) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.4324/9781003528937-24%22&format=json) |
| 12 | `L-062` | `10.1103/physrevlett.99.108101` | [doi.org](https://doi.org/10.1103/physrevlett.99.108101) · [OpenAlex](https://api.openalex.org/works/doi:10.1103/physrevlett.99.108101) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1103/physrevlett.99.108101%22&format=json) |
| 13 | `L-063` | `10.46793/match.96-3.03426` | [doi.org](https://doi.org/10.46793/match.96-3.03426) · [OpenAlex](https://api.openalex.org/works/doi:10.46793/match.96-3.03426) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.46793/match.96-3.03426%22&format=json) |
| 14 | `L-067` | `10.1007/s12064-020-00313-7` | [doi.org](https://doi.org/10.1007/s12064-020-00313-7) · [OpenAlex](https://api.openalex.org/works/doi:10.1007/s12064-020-00313-7) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1007/s12064-020-00313-7%22&format=json) |
| 15 | `L-068` | `10.1007/s13194-023-00566-1` | [doi.org](https://doi.org/10.1007/s13194-023-00566-1) · [OpenAlex](https://api.openalex.org/works/doi:10.1007/s13194-023-00566-1) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1007/s13194-023-00566-1%22&format=json) |
| 16 | `L-070` | `10.1016/j.tree.2020.02.004` | [doi.org](https://doi.org/10.1016/j.tree.2020.02.004) · [OpenAlex](https://api.openalex.org/works/doi:10.1016/j.tree.2020.02.004) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1016/j.tree.2020.02.004%22&format=json) |
| 17 | `L-072` | `10.1098/rspb.2019.2070` | [doi.org](https://doi.org/10.1098/rspb.2019.2070) · [OpenAlex](https://api.openalex.org/works/doi:10.1098/rspb.2019.2070) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1098/rspb.2019.2070%22&format=json) |
| 18 | `L-074` | `10.1038/s41598-017-02799-6` | [doi.org](https://doi.org/10.1038/s41598-017-02799-6) · [OpenAlex](https://api.openalex.org/works/doi:10.1038/s41598-017-02799-6) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1038/s41598-017-02799-6%22&format=json) |
| 19 | `L-075` | `10.3390/life11090966` | [doi.org](https://doi.org/10.3390/life11090966) · [OpenAlex](https://api.openalex.org/works/doi:10.3390/life11090966) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.3390/life11090966%22&format=json) |
| 20 | `L-077` | `10.3389/fphy.2018.00064` | [doi.org](https://doi.org/10.3389/fphy.2018.00064) · [OpenAlex](https://api.openalex.org/works/doi:10.3389/fphy.2018.00064) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.3389/fphy.2018.00064%22&format=json) |
| 21 | `L-078` | `10.1038/s41540-024-00383-z` | [doi.org](https://doi.org/10.1038/s41540-024-00383-z) · [OpenAlex](https://api.openalex.org/works/doi:10.1038/s41540-024-00383-z) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1038/s41540-024-00383-z%22&format=json) |
| 22 | `L-079` | `10.31219/osf.io/ea6yx` | [doi.org](https://doi.org/10.31219/osf.io/ea6yx) · [OpenAlex](https://api.openalex.org/works/doi:10.31219/osf.io/ea6yx) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.31219/osf.io/ea6yx%22&format=json) |
| 23 | `L-080` | `10.1142/s0218127417501450` | [doi.org](https://doi.org/10.1142/s0218127417501450) · [OpenAlex](https://api.openalex.org/works/doi:10.1142/s0218127417501450) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1142/s0218127417501450%22&format=json) |
| 24 | `L-081` | `10.1016/j.cnsns.2016.04.008` | [doi.org](https://doi.org/10.1016/j.cnsns.2016.04.008) · [OpenAlex](https://api.openalex.org/works/doi:10.1016/j.cnsns.2016.04.008) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1016/j.cnsns.2016.04.008%22&format=json) |
| 25 | `L-082` | `10.1002/cpa.3160320103` | [doi.org](https://doi.org/10.1002/cpa.3160320103) · [OpenAlex](https://api.openalex.org/works/doi:10.1002/cpa.3160320103) · [EuropePMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1002/cpa.3160320103%22&format=json) |

---

## 5. Канал B: предложения для графа знаний (`kg/`)

Файл `outbox\<имя>.kg.jsonl`, **три типа строк**, всё остальное отклоняется. Лимит **50 строк**.

### 5.1 `check` — цитата к существующему узлу (цикл A, начинай с этого)

```json
{"kind":"check","id":"F-019",
 "quote":"If Πλ>1/6, the doubling time of a lineage never attains equilibrium",
 "verdict":"supported",
 "source":{"doi":"10.1371/journal.pgen.1001076","level":"abstract_read"},
 "note":"порог подтверждён аннотацией"}
```

`verdict`:
- `supported` — цитата подтверждает утверждение узла;
- `contradicted` — противоречит **при тех же условиях**;
- `not_found` — в открытом поиске не нашлось (уходит в `LITERATURE-GAPS` в формулировке «не найдено <дата>»).

**Все 580 узлов со текстами:** [https://github.com/mak777uh/marfagenez/blob/master/kg/INDEX.md](https://github.com/mak777uh/marfagenez/blob/master/kg/INDEX.md).
Первые 24 цели фронтира — ниже, остальные в `STATE.md`.

| # | узел | что проверять | где искать |
|---|---|---|---|
| 1 | `C-006` | Полоса допуска — проекция ядра выживания на ось доли дохода, | [поиск](https://www.google.com/search?q=Полоса+допуска+—+проекция+ядра+выживания+на+ось+доли+дохода,) · [OpenAlex](https://api.openalex.org/works?search=Полоса+допуска+—+проекция+ядра+выживания+на+ось+доли+дохода,) |
| 2 | `C-008` | Вина за потерю размера в линии морфологии — отсутствие механ | [поиск](https://www.google.com/search?q=Вина+за+потерю+размера+в+линии+морфологии+—+отсутствие+механ) · [OpenAlex](https://api.openalex.org/works?search=Вина+за+потерю+размера+в+линии+морфологии+—+отсутствие+механ) |
| 3 | `F-002` | Порог доли удержания | [поиск](https://www.google.com/search?q=Порог+доли+удержания) · [OpenAlex](https://api.openalex.org/works?search=Порог+доли+удержания) |
| 4 | `F-004` | Цена поддержания и замыкание | [поиск](https://www.google.com/search?q=Цена+поддержания+и+замыкание) · [OpenAlex](https://api.openalex.org/works?search=Цена+поддержания+и+замыкание) |
| 5 | `F-005` | Доля ресурса в поддержание (правило κ) | [поиск](https://www.google.com/search?q=Доля+ресурса+в+поддержание+(правило+κ)) · [OpenAlex](https://api.openalex.org/works?search=Доля+ресурса+в+поддержание+(правило+κ)) |
| 6 | `F-006` | Складка Chao и её универсальный масштаб | [поиск](https://www.google.com/search?q=Складка+Chao+и+её+универсальный+масштаб) · [OpenAlex](https://api.openalex.org/works?search=Складка+Chao+и+её+универсальный+масштаб) |
| 7 | `F-007` | Порог ошибок | [поиск](https://www.google.com/search?q=Порог+ошибок) · [OpenAlex](https://api.openalex.org/works?search=Порог+ошибок) |
| 8 | `F-008` | Viability kernel | [поиск](https://www.google.com/search?q=Viability+kernel) · [OpenAlex](https://api.openalex.org/works?search=Viability+kernel) |
| 9 | `F-009` | Замыкание ограничений (структурное) | [поиск](https://www.google.com/search?q=Замыкание+ограничений+(структурное)) · [OpenAlex](https://api.openalex.org/works?search=Замыкание+ограничений+(структурное)) |
| 10 | `F-010` | RAF | [поиск](https://www.google.com/search?q=RAF) · [OpenAlex](https://api.openalex.org/works?search=RAF) |
| 11 | `F-011` | Ниша и её изменение | [поиск](https://www.google.com/search?q=Ниша+и+её+изменение) · [OpenAlex](https://api.openalex.org/works?search=Ниша+и+её+изменение) |
| 12 | `F-012` | Многоуровневый отбор (Прайс) | [поиск](https://www.google.com/search?q=Многоуровневый+отбор+(Прайс)) · [OpenAlex](https://api.openalex.org/works?search=Многоуровневый+отбор+(Прайс)) |
| 13 | `F-013` | Цепь рождения–смерти и «честная вероятность» как медиана | [поиск](https://www.google.com/search?q=Цепь+рождения–смерти+и+«честная+вероятность»+как+медиана) · [OpenAlex](https://api.openalex.org/works?search=Цепь+рождения–смерти+и+«честная+вероятность»+как+медиана) |
| 14 | `F-014` | Порог полосы без возвращающей силы | [поиск](https://www.google.com/search?q=Порог+полосы+без+возвращающей+силы) · [OpenAlex](https://api.openalex.org/works?search=Порог+полосы+без+возвращающей+силы) |
| 15 | `F-015` | Sizer / adder / timer | [поиск](https://www.google.com/search?q=Sizer+/+adder+/+timer) · [OpenAlex](https://api.openalex.org/works?search=Sizer+/+adder+/+timer) |
| 16 | `F-016` | Цена страховки (Тулджапурак) | [поиск](https://www.google.com/search?q=Цена+страховки+(Тулджапурак)) · [OpenAlex](https://api.openalex.org/works?search=Цена+страховки+(Тулджапурак)) |
| 17 | `F-017` | Порог ошибок Эйгена | [поиск](https://www.google.com/search?q=Порог+ошибок+Эйгена) · [OpenAlex](https://api.openalex.org/works?search=Порог+ошибок+Эйгена) |
| 18 | `F-018` | Показатель и порядок нелинейности | [поиск](https://www.google.com/search?q=Показатель+и+порядок+нелинейности) · [OpenAlex](https://api.openalex.org/works?search=Показатель+и+порядок+нелинейности) |
| 19 | `F-019` | Критерий равновесия Chao (подтверждён локатором) | [поиск](https://www.google.com/search?q=Критерий+равновесия+Chao+(подтверждён+локатором)) · [OpenAlex](https://api.openalex.org/works?search=Критерий+равновесия+Chao+(подтверждён+локатором)) |
| 20 | `F-020` | Надёжность: Гомпертц, Макегам и плато из избыточности | [поиск](https://www.google.com/search?q=Надёжность:+Гомпертц,+Макегам+и+плато+из+избыточности) · [OpenAlex](https://api.openalex.org/works?search=Надёжность:+Гомпертц,+Макегам+и+плато+из+избыточности) |
| 21 | `F-021` | Правило κ и приоритет поддержания | [поиск](https://www.google.com/search?q=Правило+κ+и+приоритет+поддержания) · [OpenAlex](https://api.openalex.org/works?search=Правило+κ+и+приоритет+поддержания) |
| 22 | `F-024` | Ядро выживания и его граница | [поиск](https://www.google.com/search?q=Ядро+выживания+и+его+граница) · [OpenAlex](https://api.openalex.org/works?search=Ядро+выживания+и+его+граница) |
| 23 | `F-025` | ITI: разложение временной информации | [поиск](https://www.google.com/search?q=ITI:+разложение+временной+информации) · [OpenAlex](https://api.openalex.org/works?search=ITI:+разложение+временной+информации) |
| 24 | `F-026` | Зерно среды задаёт тип bet-hedging | [поиск](https://www.google.com/search?q=Зерно+среды+задаёт+тип+bet-hedging) · [OpenAlex](https://api.openalex.org/works?search=Зерно+среды+задаёт+тип+bet-hedging) |

### 5.2 `node` — предложение нового узла (цикл B)

```json
{"kind":"node","tmp":"n1","type":"literature",
 "text":"Bet-hedging: компромисс между текущей и будущей приспособленностью при мультипликативном критерии.",
 "quote":"bet-hedging is a trade-off between current and future fitness",
 "source":{"doi":"10.1111/j.1469-185X.2012.00225.x","level":"abstract_read"},
 "lines":["vybor"],
 "context":{"scope":"обзор bet-hedging, Biol Rev 87:742–755"},
 "notes":"что это меняет для нас"}
```

`lines` — **только из десяти** существующих линий:

| id | линия | определение |
|---|---|---|
| `granica` | Граница | Поверхность, которую надо поддерживать, ценой вещества. |
| `obmen` | Обмен | Поток вещества внутрь и наружу, с потерей. |
| `svoi-usloviya` | Свои условия | Система меняет то, от чего зависит. |
| `organizaciya` | Организация с разделением | Части делают то, чего целое не может само. |
| `proshloe` | Прошлое | Две системы с равным состоянием не равны. |
| `smert` | Смерть | Отказ как скорость, а не как бит. |
| `porog` | Порог и критичность | Переход между режимами по параметру. |
| `vybor` | Выбор | Деление ресурса между назначениями. |
| `individualnost` | Индивидуальность | Граница «я» как измерение, а не статус. |
| `agentnost` | Агентность | «Что форма делает», а не «чем является». |

`type` узла: `literature` / `claim` / `formula` / `definition` / `gap` / `correspondence`.

### 5.3 `edge` — связь (цикл C)

```json
{"kind":"edge","from":"n1","to":"F-016","type":"extends","note":"Тулджапурак — формальный аппарат для того же компромисса"}
```

`from`/`to` — либо `tmp` из этого же файла (`n1`, `n2`), либо существующий id. `type` — только из двенадцати:
`qualifies, tested_in, stated_in, extends, analogous_to, normalizes_to, refutes, refuted_by, supports,
derived_from, bridges, maps_to`.

**Перед `refutes` проверь условия:** другая доза, диапазон или метод — это НЕ опровержение.

---

## 6. Порядок работы (циклы)

| цикл | вход | что присылаешь | ценность |
|---|---|---|---|
| **A. Фронтир** | 136 узлов «только извлечено» | `check` с цитатой | **самая высокая**: дешёво, двигает граф |
| **C. Мосты** | новые узлы против `C-*`/`F-*` | `edge` с обоснованием | связность |
| **B. Новые узлы** | очередь DOI + `SEARCH-PLAN` | `node` + `edge` | масса |

**Пропорция на день:** 60% `check`, 25% `edge`, 15% `node`.

---

## 7. Что тебе запрещено

- править `atoms.jsonl`, `edges.jsonl`, `kg/`, `results/` — **только новые файлы в `outbox\`**;
- пушить в GitHub и вообще писать в репозиторий (он только для чтения);
- ставить `epistemic` (`established` и прочее) — **это делает только коллектор**;
- выдумывать числа: в `numbers` они сверяются с текстом ячейки машинно;
- выдавать пересказ за цитату: `quote` — **дословная подстрока**;
- ставить `analogous_to` без обоснования в `note`;
- присылать больше 50 строк в файле.

---

## 8. Чек-лист перед отправкой

1. `atom`/`tmp` уникальны и в правильном формате?
2. Есть **дословная** цитата и **точный** локатор (раздел/таблица/уравнение)?
3. `source.level` честный (`abstract_read`, если читал аннотацию)?
4. `lines` — из десяти, и узел действительно ложится в неё?
5. Тип ребра — из двенадцати, `note` объясняет «почему»?
6. Числа в тексте не противоречат друг другу? (сложить, поделить, проверить порядок)
7. Для `check`: `verdict` соответствует цитате, а не желанию?

---

## 9. Что произойдёт с принятым

| канал | файл у меня | что делаю |
|---|---|---|
| ячейки карты | `literature/map/inbox/` | прогоняю `map_ingest`, публикую, пересобираю `kg/` |
| `node`, `edge` | `docs/KG-INBOX.jsonl` | назначаю id, вношу в источник, пересобираю |
| `check` | `docs/KG-CHECKS.jsonl` | проверяю цитату, двигаю фронтир; `not_found` → `LITERATURE-GAPS` |

**Отказ не теряет партию:** файл остаётся в `outbox\`, правишь и кладёшь снова под тем же именем.

---

## 10. Три вещи, которые дают больше всего

1. **Найти узел, чей текст не подтверждается источником.** Присылай `check` с `contradicted` — это правка
   графа, которая иначе не случится.
2. **Закрыть `not_found`.** «В открытом поиске 26.11.2026 не найдено» — тоже результат: он снимает
   фантомные ссылки (у нас уже две: «Segura 2026» и «Tomasik 2024»).
3. **Принести число с таблицей и локатором.** Не пересказ — число, которое можно пересчитать.

---

## Коротко

**Выбери узел из списка → найди источник (ссылки в §2) → пришли `check` с дословной цитатой → прочитай
`ack` → следующий. Шестьдесят процентов времени — цитаты к фронтиру, остальное — рёбра и новые узлы.**
