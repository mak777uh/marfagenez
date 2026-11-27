# ELEPHANT-LITERATURE.md — что наука уже знает про слона

**Дата основания:** 2026-11-20. **Автор:** цикл 291. **Репозиторий:** `marfagenez`.

**Зачем этот файл.** Здесь копится **всё, что наука уже нашла** о том же, о чём мы спрашиваем в `GOAL.md` §1a: граница,
обмен, участие в формировании собственных условий. Не обзор, не эссе — **реестр утверждений** с источниками, чтобы
следующий агент не открывал заново и не приписывал нам чужого.

---

## 0. Как этим пользоваться (правила, без которых файл сгниёт)

**Три части и их порядок неизменны:**

| часть | что внутри | можно ли дополнять |
|---|---|---|
| **§A Реестр** | записи `L-NNN`: одно утверждение = одна запись | **только добавлять в конец**, ID не переиспользуются |
| **§B Банк формул** | записи `F-NNN`: формула в **наших символах** + перевод | только добавлять |
| **§C Соответствия** | таблица «наше ↔ литература» | переписывается сколько угодно |

**Четыре правила.**

1. **Ничего не переписывается задним числом.** Если утверждение оказалось неверным — не удалять: поле `Статус` →
   `опровергнуто`, и абзац `Поправка` датой.
2. **`Проверено` обязательно и честно.** Три значения: **полный текст** (читал статью), **аннотация** (только
   abstract), **вторые руки** (пришло из чужого обзора, ссылку не открывал). Это главное поле файла: «вторые руки» —
   не источник, а **указатель на источник**.
3. **Цитата, а не пересказ** — где возможно. Если цитаты нет, писать `пересказ`.
4. **Каждая запись заканчивается действием.** Поле `Что меняет` — конкретная правка в нашем репозитории или
   `ничего` (с причиной). Реестр без действий превращается в библиотеку.

**Чего здесь не делать:**

- не спорить с литературой в этом файле (для спора — `docs/ELIMINATED.md` и `FINDING-*`);
- не дублировать `POSITIVE.md` (там **наши** результаты) и `NOT-CLAIMED.md` (там **наши** отказы);
- не складывать сюда «жизнь — это…» без операционального следствия: если из утверждения нельзя вывести неравенство
  или измерение — оно не входит.

---

## A. Реестр утверждений

### L-001 · Накопление повреждения даёт экспоненциальный рост смертности

```json
{
 "L": "L-001",
 "locator": {
  "doi": "10.1371/journal.pone.0233384",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0233384",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0233384"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Накопление повреждения даёт экспоненциальный рост смертности",
  "year": 2020,
  "first_author": "Ledberg"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Ledberg, A. (2020). *Exponential increase in mortality with age is a generic property of a simple model
system of damage accumulation and death.* PLOS ONE 15(6): e0233384.
**Ссылка.** https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0233384 (DOI 10.1371/journal.pone.0233384)
**Проверено.** аннотация (полный текст не читал).
**Утверждение (пересказ).** В простой модели накопления повреждения с ограниченной починкой **экспоненциальный рост
смертности с возрастом** — генерик-свойство, а не особенность людей.
**Что даёт нам.** Наш §4.12 (`μ = floor + rate·(1−q)^p + λ·damage`) — это **та же рамка**; значит «накопление → смерть»
мы не открываем.
**Чем отличается.** У нас повреждение **не чинится вовсе**, поэтому смертность **линейна** по `D`, а не экспоненциальна
по возрасту. Это **другой режим той же рамки**, и его надо называть.
**Что меняет.** В §8.3 указать: «мы в линейном режиме», и не называть закон Гомпертца нашим.

---

### L-002 · Мёртвое плато — то, что модели накопления воспроизводят плохо

```json
{
 "L": "L-002",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Мёртвое плато — то, что модели накопления воспроизводят плохо",
  "year": 2026,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** критика модели Ledberg в контексте позднего плато смертности (по отзывам 2026-11-20 ссылается на Raz et al.,
*Nature Aging*).
**Ссылка.** нет прямой; **вторые руки** — из отзыва, не проверено.
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Стандартные модели накопления «insufficiently account for a late-life absence of increased
mortality», то есть **плато смертности** остаётся необъяснённым.
**Что даёт нам.** Наш результат про **корневую расходимость** и порог `h = 1` может закрывать именно этот разрыв:
плато у нас — **решение**, а не постулат.
**Чем отличается.** Ничего не отличается — это **потенциальная ниша** для нашей модели, и её надо проверить на данных.
**Что меняет.** Q-021 и внешний якорь: сравнить наши кривые `S(T)` с плато в реальных данных (см. L-006).

---

### L-003 · Disposable soma: ресурс делится между починкой и потомством, оптимум явно моделируется

```json
{
 "L": "L-003",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://en.wikipedia.org/wiki/Disposable_soma_theory_of_aging",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://en.wikipedia.org/wiki/Disposable_soma_theory_of_aging"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Disposable soma theory of aging",
  "year": null,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Kirkwood; формальные модели — см. L-004; обзор — Wikipedia «Disposable soma theory of aging».
**Ссылка.** https://en.wikipedia.org/wiki/Disposable_soma_theory_of_aging
**Проверено.** аннотация/обзорная страница.
**Утверждение (цитата из обзора).** «organisms age due to an evolutionary **trade-off between growth, reproduction,
and DNA repair maintenance**».
**Что даёт нам.** Наш §4.13 (запас против целости) — **та же постановка в другой валюте**.
**Чем отличается.** Второе назначение у нас — **запас**, а не потомство; потомства в нашей модели нет.
**Что меняет.** В §4.13 писать «версия disposable soma», а не «наш выбор».

---

### L-004 · Оптимальная доля и закон Гомпертца выводятся вместе

```json
{
 "L": "L-004",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://academic.oup.com/evolut/article/49/6/1055/6870614",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://academic.oup.com/evolut/article/49/6/1055/6870614"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Оптимальная доля и закон Гомпертца выводятся вместе",
  "year": 1995,
  "first_author": "Abrams & Ludwig"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Abrams & Ludwig (1995). *Optimality theory, Gompertz' law, and the disposable soma theory of senescence.*
Evolution 49(6): 1055.
**Ссылка.** https://academic.oup.com/evolut/article/49/6/1055/6870614 (**403 при попытке открыть**).
**Проверено.** **вторые руки** (аннотация в поиске).
**Утверждение (пересказ).** Динамическое программирование даёт **оптимальное соотношение** между репродукцией,
отведением энергии на починку и смертностью, и из этого выходит **закон Гомпертца**.
**Что даёт нам.** «Распределение ресурса → закон смертности» — программа **1995 года**. Наша §4.13 + §4.12 — её
частный случай.
**Чем отличается.** У нас нет потомства; у них вывод смертности из стратегии, у нас — из бюджета.
**Что меняет.** §8.3: назвать эту программу предшественником; не заявлять новизну связки.

---

### L-005 · Порог доли удержания повреждения известен

```json
{
 "L": "L-005",
 "locator": {
  "doi": "10.1371/journal.pgen.1001076",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1001076",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1001076"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Порог доли удержания повреждения известен",
  "year": 2010,
  "first_author": "Chao"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Chao, L. (2010). *A model for damage load and its implications for the evolution of bacterial aging.*
PLOS Genetics 6(8): e1001076.
**Ссылка.** https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1001076
**Проверено.** аннотация.
**Утверждение (цитата).** «a cell lineage dividing symmetrically is **immortal if lifetime damage rates do not exceed a
threshold**… the lineage becomes mortal above the threshold».
**Что даёт нам.** Это **тот же порог**, что наш `h = 1`: ниже — плато, выше — рост.
**Чем отличается.** У нас `h` — доля повреждения, передаваемая потомку, и порог падает **ровно на 1**, потому что
починки нет вовсе.
**Что меняет.** Снять заявку «порог найден нами». Остаётся **форма расходимости** (см. L-014, F-003) — единственный
кандидат на своё.

---

### L-006 · Все кривые выживания — растяжения одной

```json
{
 "L": "L-006",
 "locator": {
  "doi": "10.1038/nature16550",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.nature.com/articles/nature16550",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/stroustrup16-nature16550.pdf",
  "bytes": 1892642,
  "sha256": "6b16e76081d97e4ffc5ca42bb59c2660bf62f3f894d0904108f309707fe8fdde",
  "retrieved_at": "2026-11-27T08:55:00Z",
  "via": "pmc-author-manuscript",
  "via_detail": "author manuscript PDF (UNC Carolina Digital Repository, PMCID PMC4828198), 28 стр., текстовый слой; цитаты верифицированы"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "28", "note": "manuscript incl. supp."}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Все кривые выживания — растяжения одной",
  "year": 2016,
  "first_author": "Stroustrup et al."
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Stroustrup et al. (2016). *The temporal scaling of Caenorhabditis elegans ageing.* Nature 530, 103–107.
**Ссылка.** **вторые руки** — из отзыва 2026-11-20; ссылку не открывал.
**Проверено.** **полный текст** papers/stroustrup16-nature16550.pdf (author manuscript, PMCID PMC4828198, sha256 6b16e760…), 2026-11-27; «all alter lifespan distributions by an apparent stretching or shrinking of time», «a single effective rate constant of ageing, k_r», «transiently alter k_r … a permanent effect on remaining lifespan» — сверено с текстом.
**Утверждение (по полному тексту).** Кривые выживания при разных вмешательствах совпадают после растяжения времени — то есть
старение масштабируется.
**Что даёт нам.** Внешний якорь для «жизнь как скорость»: если у нас `S(T)` тоже масштабируется, это **одно** число
сравнения с реальными данными.
**Что меняет.** Эксперимент: построить `S(T)` при разных `λδ` и проверить масштабирование.

---

### L-007 · Страховка сдвигает оптимум с пика на пологий склон

```json
{
 "L": "L-007",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6590291/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6590291/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Страховка сдвигает оптимум с пика на пологий склон",
  "year": 2019,
  "first_author": "Haaland"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** Haaland, Wright, Tufto, Ratikainen (2019). *Short-term insurance versus long-term bet-hedging strategies as
adaptations to variable environments.* Evolution 73(2): 145–157.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC6590291/
**Проверено.** **полный текст** (читал страницу).
**Утверждение (цитата).** «insurance causes the optimal phenotype to **shift from the peak to down the less steeply
decreasing side** of the fitness function». Пример там же: птица **запасает жир**, когда температура изменчивее.
**Что даёт нам.** Наш сдвиг оптимума при засухе (§4.13) — **описанный эффект обрыва**, а не наше открытие.
**Чем отличается.** Только числа: у нас оптимальная доля 0.75 и ширина полосы 3–10 %.
**Что меняет.** §4.13: назвать insurance/cliff-edge; добавить сравнение с их мультипликативным критерием (Q-019).

---

### L-008 · Bet-hedging и банк семян

```json
{
 "L": "L-008",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Bet-hedging и банк семян",
  "year": 1966,
  "first_author": "Cohen"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Cohen (1966); Seger & Brockmann (1987); Philippi & Seger (1989); Starrfelt & Kokko (2012); Evans & Dennehy
(2005) — «germ banking».
**Ссылка.** **вторые руки** — из отзывов 2026-11-20.
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** При **мультипликативном** критерии приспособленности и стохастической среде оптимум —
диверсификация или «банк» покоящихся единиц; банк семян — bet-hedging против катастроф.
**Что даёт нам.** Наша «полоса» может быть описана либо как **insurance** (L-007), либо как **банк** — это разные
формализмы с разными предсказаниями.
**Что меняет.** Q-019: если критерий у нас аддитивный — называть полосу «эффект обрыва», а не bet-hedging.

---

### L-009 · Насыщаемое удаление и порог: прямой аналог

```json
{
 "L": "L-009",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/karin19-nc.xml",
  "bytes": 115999,
  "sha256": "a33bc0fbb13fcf365f0c0271350f6183de66c00404bec34df3568f3ec2c710f9",
  "retrieved_at": "2026-11-27T10:15:00Z",
  "via": "europepmc-oa-fulltext",
  "via_detail": "Nat Commun 10:5495, PMC6889273 fullTextXML; SnC turnover замедляется с возрастом (период полураспада дни→недели), κ = halfway saturation point for removal, пороговая смерть при флуктуациях SnC воспроизводит Гомпертца — сверено по полному тексту"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "article", "from": "1", "to": "full"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Насыщаемое удаление и порог: прямой аналог",
  "year": 2019,
  "first_author": "Karin"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Karin, Agrawal, Alon (2019), Nature Communications — о насыщаемом удалении сенесцентных клеток.
**Ссылка.** **вторые руки** — из отзыва 2026-11-20; **высший приоритет проверки**.
**Проверено.** **полный текст**: Karin, Agrawal, Porat, Krizhanovsky & Alon, «Senescent cell turnover slows with age providing an explanation for the Gompertz law», Nat Commun 10:5495 (2019), papers/karin19-nc.xml (PMC6889273), 2026-11-27; removal rate SnC замедляется с возрастом, κ — точка насыщения удаления, пороговая смерть при флуктуациях — сверено по полному тексту.
**Утверждение (пересказ).** Удаление повреждения насыщается, и из этого следует порог между «держит» и «накапливает».
**Что даёт нам.** **Прямой аналог нашего `h = 1`**; если у них есть формула расходимости у порога — наш последний
кандидат на новизну исчезает.
**Что меняет.** До чтения этой работы **не заявлять** ничего о новизне порога.

---

### L-010 · Теория надёжности: отказ как выброс нагрузки

```json
{
 "L": "L-010",
 "locator": {
  "doi": "10.1159/000369011",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1159/000369011",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/gavrilov14-gerontology-pmc4475490.xml",
  "bytes": 80772,
  "sha256": "2f37ac4e0bc2952bce7bf8388035dcab7165dd5f91bae252acb4879e24de102e",
  "retrieved_at": "2026-11-27T21:00:00Z",
  "via": "ncbi-efetch-pmc",
  "via_detail": "Gavrilov & Gavrilova, Gerontology 61:364-371 (2015), PMC4475490, DOI 10.1159/000369011; обзор их reliability theory: избыточность/резервы, exhaustion redundancy → mortality leveling-off, Gompertz force of mortality — сверено по полному тексту; первичные работы 1991/2001 остаются вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "article", "from": "1", "to": "full"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Теория надёжности: отказ как выброс нагрузки",
  "year": 1991,
  "first_author": "Gavrilov & Gavrilova"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gavrilov & Gavrilova (1991, 2001) — надёжностная (reliability) теория старения.
**Ссылка.** **вторые руки** — из отзывов.
**Проверено.** **полный текст**: Gavrilov & Gavrilova, «New Developments in the Biodemography of Aging and Longevity», Gerontology 61:364 (2015), papers/gavrilov14-gerontology-pmc4475490.xml (PMC4475490), 2026-11-27; reliability theory: отказ как выброс нагрузки на избыточность, exhaustion redundancy → leveling-off — сверено по их же обзору; первичные 1991/2001 — вторые руки.
**Утверждение (пересказ).** Организм — система с отказами; смертность растёт как вероятность выхода нагрузки за
предел; даёт Гомпертц и объясняет плато.
**Что даёт нам.** **Язык**, которого нам не хватает: `μ` — интенсивность отказов, `q` — запас прочности, `D` — износ.
Их аппарат старше и строже нашего.
**Что меняет.** В §4.12 перейти на термины надёжности («время до отказа», «интенсивность отказов»).

---

### L-011 · Frailty и vitality: две системы с равным состоянием не равны

```json
{
 "L": "L-011",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Frailty и vitality: две системы с равным состоянием не равны",
  "year": 1979,
  "first_author": "Vaupel"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Vaupel, Manton, Stallard (1979) — frailty; Li & Anderson — vitality.
**Ссылка.** **вторые руки.**
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Скрытая переменная (хрупкость/жизненная сила) объясняет, почему смертность падает у
выживших и почему люди с одинаковым возрастом не равны.
**Что даёт нам.** Наш результат «339 / 258 / 128 при равной целости» (§4.12) — **это ровно frailty**.
**Чем отличается.** У них скрытая переменная — статистический конструкт; у нас — **измеренная** (`damage`), с
уравнением и проверкой.
**Что меняет.** §4.12: назвать это frailty; заявить отличие: **измеримость** истории.

---

### L-012 · DEB: правило κ и приоритет поддержания

```json
{
 "L": "L-012",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "DEB: правило κ и приоритет поддержания",
  "year": null,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Kooijman — Dynamic Energy Budget theory.
**Ссылка.** **вторые руки.**
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Энергия делится: доля κ идёт на соматическое поддержание, остальное — на рост и
размножение; при голоде поддержание имеет приоритет.
**Что даёт нам.** Наш `income − maintenance ≥ Σ u_i·cost_i` — **их бюджетное неравенство** в упрощённом виде.
**Что меняет.** §4.10/§4.11: сослаться на DEB как на общую рамку бюджета.

---

### L-013 · Pirt и поддержание у микробов

```json
{
 "L": "L-013",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Pirt и поддержание у микробов",
  "year": 1965,
  "first_author": "Pirt"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Pirt (1965) — maintenance energy.
**Ссылка.** **вторые руки.**
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Часть энергии уходит на поддержание, не на рост; есть «коэффициент поддержания».
**Что даёт нам.** Наш `maintenance` — это их член; наша «цена кожи» — его геометрическая версия.
**Что меняет.** В §4.7 указать: `maintenance` — стандартный член, а новое у нас — его зависимость от целости.

---

### L-014 · Две независимые опасности и оптимальный ремонт

```json
{
 "L": "L-014",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Две независимые опасности и оптимальный ремонт",
  "year": 2024,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gavrilov? нет — **Tomasik et al. (2024), JTB** — «Agelessness is possible under the disposable soma theory but
system complexity makes it unlikely».
**Ссылка.** **вторые руки** — из отзыва 2026-11-20.
**Проверено.** **вторые руки.** ⚠ **2026-11-27, MSG-DEVIN-S7-Q020-1:** «Tomasik et al. (2024), JTB» не существует — Brian Tomasik философ-эссеист, такой статьи нет; цитата «Agelessness is possible...» вероятно пересказ/выдумка. Запись оставлена как есть до решения main: утверждение §4.14 опирается на фантомный источник.
**Утверждение (пересказ отзыва, с цитатой из статьи).** «evolution could select for its complete removal if the
mortality risk it poses is severe enough and its repair does not pose too large of a penalty to reproduction»; при
**нескольких типах повреждения** полное устранение старения редко выгодно.
**Что даёт нам.** Их статический вывод «несколько опасностей → полный ремонт неоптимален» — **наш §4.14**
(сдвиг оптимума `1.0 → 0.8 → 0.6`) в динамике.
**Что меняет.** Q-020: проверить, не является ли наше `c ≤ 1` их пределом `rmax → ∞`.

---

### L-015 · Замкнутость ограничений — возможно, **их** определение нашего критерия

```json
{
 "L": "L-015",
 "locator": {
  "doi": "10.1007/978-94-017-9837-2",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://hal.science/hal-01151449",
  "none": true
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/moreno15-biological-autonomy-intro-hal01151449.pdf",
  "bytes": 509205,
  "sha256": "fa1148aacfc7327e43db7851940e96a26b0dd3d8ba99705ca6db9bb69ebaa070",
  "retrieved_at": "2026-11-27T21:45:00Z",
  "via": "hal-author-deposit",
  "via_detail": "Moreno & Mossio, Biological Autonomy (Springer 2015), HAL hal-01151449 — только глава Introduction (53 стр.), не вся книга; closure of constraints, self-maintenance, autonomy definitions — сверено; Mossio-Saborido-Moreno 2009 и остальные главы — вторые руки"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "chapter", "from": "Introduction", "to": "Introduction"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Замкнутость ограничений — возможно, **их** определение нашего критерия",
  "year": 2015,
  "first_author": "Moreno & Mossio"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Moreno & Mossio (2015) *Biological Autonomy*; Mossio, Saborido & Moreno (2009); Montévil & Mossio (2015).
**Ссылка.** **вторые руки** — из отзыва 2026-11-20.
**Проверено.** **фрагмент**: Moreno & Mossio, «Biological Autonomy», Springer 2015, HAL hal-01151449 — глава Introduction, papers/moreno15-biological-autonomy-intro-hal01151449.pdf (sha256 fa1148aa…), 2026-11-27; «closure of constraints» как явное определение самоопределения, organization = closed and functional — сверено; книга прочитана только по введению. Mossio, Saborido & Moreno 2009 — вторые руки.
**Утверждение (пересказ).** Живое — система, части которой **поддерживают ограничения**, делающие возможным
существование целого; организация = **замкнутость ограничений**.
**Что даёт нам.** Наш критерий «участие в формировании условий собственного существования» (`GOAL.md` §1a) может быть
**дословно их определением**. Это самый серьёзный риск для заявки на новизну.
**Что меняет.** **До любых заявлений** сверить §9.1 с их формализмом; если совпадает — писать «наша модель — рабочая
реализация их критерия, и вот измеренные числа».

---

### L-016 · Химотон: три подсистемы и требование замкнутости

```json
{
 "L": "L-016",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Химотон: три подсистемы и требование замкнутости",
  "year": 1975,
  "first_author": "Gánti"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gánti (1975, 2003).
**Ссылка.** **вторые руки.**
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Минимальная живая единица — **три** подсистемы (мембрана, метаболизм, информация),
связанные в цикл; каждая производится системой.
**Что даёт нам.** Это ровно наш **потолок 3**: «две независимые величины и обмен». У Ганти — три и с требованием
самопроизводства.
**Что меняет.** В `MODEL-CEILINGS.md` добавить: третий потолок имеет **готовую постановку** (химотон), и наша задача —
не изобрести, а **измерить**.

---

### L-017 · Индивидуальность как передача информации

```json
{
 "L": "L-017",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/krakauer20-iti.xml",
  "bytes": 417896,
  "sha256": "0c9c2105544f69e357141d367789b53fb6e7519db5a6fc49779f4ff84a142020",
  "retrieved_at": "2026-11-27T10:30:00Z",
  "via": "europepmc-oa-fulltext",
  "via_detail": "Theory Biosci 139:358-368, PMC7244620 fullTextXML; individuals = aggregates preserving measure of temporal information; unique/shared/complementary information decomposition — сверено по полному тексту"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [
   {
    "type": "article",
    "from": "1",
    "to": "full"
   }
  ]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Индивидуальность как передача информации",
  "year": 2020,
  "first_author": "Krakauer et al."
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Krakauer et al. (2020) — information theory of individuality (ITI).
**Ссылка.** **вторые руки.**
**Проверено.** **полный текст**: Krakauer, Bertschinger, Olbrich, Flack & Ay, «The information theory of individuality», Theory Biosci 139:358 (2020), papers/krakauer20-iti.xml (PMC7244620, DOI 10.1007/s12064-020-00313-7), 2026-11-27; индивидуум = агрегат, сохраняющий меру темпоральной информации; разложение unique/shared/complementary information — сверено.
**Утверждение (пересказ).** Индивидуальность — это **мера** (передача информации от частей к целому), а не
философский статус.
**Что даёт нам.** Готовый **операциональный** способ мерить «слона» по временным рядам, не зная, какая переменная —
кожа.
**Что меняет.** Эксперимент «чужой учёный»: применить их меру к нашим рядам и к неживым контролям.

---

### L-018 · Кожа как Markov blanket — и критика этой аналогии

```json
{
 "L": "L-018",
 "locator": {
  "doi": "10.1098/rsif.2013.0475",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1098/rsif.2013.0475",
  "none": true
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/friston13-rsif.xml",
  "bytes": 112821,
  "sha256": "bee295d43165ce23f90e76441cfdc40e1a7e18b742f93c2fa0bef3e95674684c",
  "retrieved_at": "2026-11-27T21:15:00Z",
  "via": "ncbi-efetch-pmc",
  "via_detail": "Friston, J R Soc Interface 10:20130475, PMC3730701; Markov blanket как необходимое следствие короткодействующих связей, life = emergent property ergodic random dynamical system with Markov blanket, free-energy minimization — сверено по полному тексту; критика Bruineberg et al. 2022 остаётся вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "article", "from": "1", "to": "full"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Кожа как Markov blanket — и критика этой аналогии",
  "year": 2013,
  "first_author": "Friston"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Friston (2013) — Markov blankets; критика — Bruineberg et al. (2022).
**Ссылка.** **вторые руки.**
**Проверено.** **полный текст**: Friston, «Life as we know it», J R Soc Interface 10:20130475 (2013), papers/friston13-rsif.xml (PMC3730701, DOI 10.1098/rsif.2013.0475), 2026-11-27; Markov blanket как эмерджентное свойство эргодической системы, homoeostasis/autopoiesis через free-energy — сверено; критика Bruineberg et al. 2022 — вторые руки.
**Утверждение (пересказ).** Граница системы задаётся статистической независимостью внутреннего от внешнего при
условии границы; критика: статистическая граница **не** равна биологической.
**Что даёт нам.** Наша «кожа» — **физическая** граница с ценой. Различие с Friston — готовый аргумент, что мы мерим
**вещь**, а не статистику.
**Что меняет.** §8.x: одно предложение о различии.

---

### L-019 · Автономия как базовая организация

```json
{
 "L": "L-019",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Автономия как базовая организация",
  "year": 2004,
  "first_author": "Ruiz-Mirazo & Moreno"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Ruiz-Mirazo & Moreno (2004, 2012).
**Ссылка.** **вторые руки.**
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Базовая автономия — способность системы поддерживать себя за счёт обмена с внешней
средой; должна быть **операциональной**.
**Что даёт нам.** Ещё один «готовый критерий», пересекающийся с L-015.
**Что меняет.** Та же сверка, что L-015.

---

### L-020 · Катастрофа ошибок и порог точности

```json
{
 "L": "L-020",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/eigen71.pdf",
  "bytes": 7655752,
  "sha256": "f51e8a9954652dc5166daad53acab986b3c8836697ff5f5004d972a927086e53",
  "retrieved_at": "2026-11-27T09:40:00Z",
  "via": "evolocus-pdf",
  "via_detail": "Eigen1971.pdf (59 стр.), прочитаны §I-II + фрагменты IV-VI; error copies/master copy/threshold — сверено"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "section", "from": "§I-II"}, {"type": "section", "from": "§IV-VI (фрагменты)"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Катастрофа ошибок и порог точности",
  "year": 1971,
  "first_author": "Eigen"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Eigen (1971) — quasispecies и `Q_crit`; Orgel (1963); Kowald & Kirkwood (1994).
**Ссылка.** **вторые руки.**
**Проверено.** **фрагмент первоисточника**: Eigen 1971 (Naturwissenschaften 58:465-523, англ. перевод, papers/eigen71.pdf, sha256 f51e8a99…), 2026-11-27; прочитаны §I–II и фрагменты §IV–VI — «master copy and its (reproducible) comet tail of error copies», «A minimum threshold of accuracy … is required in order to preserve the information of the selected state», sliding selfadjusting threshold — сверено с текстом. Полный разбор σq^ν-формул — не выполнен (математика OCR-шумная).
**Утверждение (пересказ).** Есть **порог точности копирования**, ниже которого наследственная информация не
удерживается; для смертности — возможность вывести угасание из **повреждения аппарата починки**.
**Что даёт нам.** Формальный аналог нашего `h = 1`: нелинейность порога из-за обратной связи; и путь закрыть Q-021.
**Что меняет.** Q-021: ввести «повреждение починки» и проверить, выйдет ли экспоненциальная смертность.

---

### L-021 · Минимальная клетка: ограничение кинетическое, а не энергетическое

```json
{
 "L": "L-021",
 "locator": {
  "doi": "10.1371/journal.pcbi.1000872",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000872",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000872"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Минимальная клетка: ограничение кинетическое, а не энергетическое",
  "year": 2010,
  "first_author": "Piedrafita et al."
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Piedrafita et al. (2010), PLOS Comput Biol; Piedrafita et al. (2012); Agmon (2020) — WCM syn3A.
**Ссылка.** https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000872 ;
https://www.cell.com/cell/fulltext/S0092-8674(21)01488-4
**Проверено.** аннотация (обе).
**Утверждение (пересказ).** Самоподдерживающаяся метаболическая система с автокатализом и бистабильностью; коллапс —
переход в тривиальное состояние; в минимальной клетке ограничение — **скорость синтеза**, а не бюджет.
**Что даёт нам.** Наш закон цены — **энергетический бюджет**, а не кинетика. Это надо писать явно, иначе нас прочтут
как «закон минимальной клетки».
**Что меняет.** §4.11: одна строка о типе ограничения.

---

### L-022 · Несовместимость с disposable soma — сигнал, а не баг

```json
{
 "L": "L-022",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Несовместимость с disposable soma — сигнал, а не баг",
  "year": 2026,
  "first_author": "обзор"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** обзор 2026-11-20 (не статья).
**Ссылка.** нет.
**Проверено.** **вторые руки** (и это **не** источник, а гипотеза).
**Утверждение (пересказ).** Если при `c ≤ 1` кожа поддерживается без затрат, то в нашей модели **старение не
обязательно**, тогда как disposable soma утверждает оптимальность конечного ремонта.
**Что даёт нам.** Либо наше `c ≤ 1` — **предельный режим** их модели (тогда мы не альтернатива), либо у нас
**действительно другой класс** (тогда это сильное утверждение).
**Что меняет.** Q-020 — решить до любых заявлений.



### L-023 · Модель Chao, восстановленная по тексту: порог `Πλ = 1/6`, и это **складка**

```json
{
 "L": "L-023",
 "locator": {
  "doi": "10.1371/journal.pgen.1001076",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1371/journal.pgen.1001076",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/chao10-plosgenet.pdf",
  "bytes": 344646,
  "sha256": "28a06c1eef3c6e33f22a8a6dc71e942ebf26fe7d4a283d47a027456b305402f9",
  "retrieved_at": "2026-11-27T08:45:00Z",
  "via": "publisher-pdf",
  "via_detail": "journals.plos.org printable PDF (PLoS Genetics 6(8):e1001076), 10 стр., текстовый слой; цитаты верифицированы как подстроки"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "10"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Модель Chao, восстановленная по тексту: порог `Πλ = 1/6`, и это **складка**",
  "year": 2010,
  "first_author": "Chao"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null,
 "duplicate_of": "L-005"
}
```



**Кто.** Chao, L. (2010). PLOS Genetics 6(8): e1001076. Реконструкция — внешнее ревью 2026-11-20 (второй документ),
с сверкой по двум опубликованным числам.
**Ссылка.** https://doi.org/10.1371/journal.pgen.1001076 ; полный текст https://pmc.ncbi.nlm.nih.gov/articles/PMC2928801/
**Проверено.** **полный текст** papers/chao10-plosgenet.pdf (PLoS printable PDF, sha256 28a06c1e…), 2026-11-27; ключевые места сверены с текстом: «If Pl.1/6, the doubling time of a lineage never attains an equilibrium and it increases over generations until it is infinitely long», «At the threshold of Pl = 1/6…», условия вещественности равновесий (ур. 9a/9b) — согласуется со складкой из реконструкции.
**Утверждение (по полному тексту).** У Чао асимметрия деления `a`; порог — **складка** (saddle-node); груз
повреждения в пороге **конечен**; обратный корень расходится у **производной** и у **времени до сенесценции**;
асимметрия **сдвигает** порог в диапазон `[1/6, 1/2]`.
**Что даёт нам.** **Огромное.** Это снимает наш последний кандидат на новизну: `√` у порога — **универсальный масштаб
складки**, известный вне биологии.
**Чем отличается.** У нас порог стоит на `h = 1` — это **не** `Πλ`; без явного перевода переменных сравнение
**недействительно**.
**Что меняет.** `FINDING-316`: заявку на новизну `√` снять. Новое содержание — **тип перехода**, не масштаб (L-024).

---

### L-024 · Смертность как канал удаления превращает складку в непрерывную расходимость

```json
{
 "L": "L-024",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Смертность как канал удаления превращает складку в непрерывную расходимость",
  "year": 2026,
  "first_author": "внешнее ревью"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** внешнее ревью 2026-11-20 (утверждение о нашем результате, не цитата из статьи).
**Проверено.** **вторые руки.**
**Утверждение (цитата ревью).** «смертность как канал удаления повреждения превращает складку в непрерывную
расходимость с показателем 1/2… формулировка „повреждение останавливает само себя“ — не ваша (она у Chao буквально),
ваша — **тип перехода**».
**Что даёт нам.** Правильную формулировку нашего вклада: не «порог» и не «корень», а **переход от складки к
непрерывной расходимости**, потому что у нас повреждение уходит через смерть, а не через деление.
**Что меняет.** §4.12: переписать акцент; `POSITIVE.md` §8.3: строку про `√` заменить на эту.

---

### L-025 · Замыкание ограничений: структура, а не баланс

```json
{
 "L": "L-025",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Замыкание ограничений: структура, а не баланс",
  "year": 2015,
  "first_author": "Montévil & Mossio"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Montévil & Mossio (2015), JTB 372:179–191; Mossio, Saborido & Moreno (2009).
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Замыкание — **причинная сеть взаимно поддерживающих ограничений**; формальное условие:
каждое ограничение зависит хотя бы от одного другого, и хотя бы одно другое зависит от него. **Замыкание ≠ баланс**:
равенство притоков и расходов ещё не замыкание.
**Что даёт нам.** Прямой аналог нашего §4.10 — но **структурный тест** (граф зависимостей), а не неравенство.
**Что меняет.** Добавить в модель **граф зависимостей** как отдельный объект; проверить нашему «порядку смерти».

---

### L-026 · Химические организации: формальное замыкание множеств

```json
{
 "L": "L-026",
 "locator": {
  "doi": null,
  "arxiv": "q-bio/0501016",
  "arxiv_version": "v1",
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/q-bio/0501016",
  "none": false
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/dittrich07-bmb-arxiv-qbio0501016.pdf",
  "bytes": 192340,
  "sha256": "729aafad73a495e7dbd8f9b3ef7a18e55b103d80cce60abd44e7f0fcfb629391",
  "retrieved_at": "2026-11-27T10:45:00Z",
  "via": "arxiv-pdf",
  "via_detail": "arXiv:q-bio/0501016v1 (Bull Math Biol 69:1199-1232, 2007), Dittrich & Speroni di Fenizio, 20 стр., 42k chars; closed/self-maintaining/semi-organization/organization определения, решётка union/intersection организаций — сверено; Kaleta et al. 2008 остаётся вторым руками"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "section", "from": "definitions", "to": "lattice"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Химические организации: формальное замыкание множеств",
  "year": 2007,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Dittrich & Speroni di Fenizio (2007), Bull Math Biol; Kaleta et al. (2008).
**Проверено.** **фрагмент**: Dittrich & Speroni di Fenizio, «Chemical organization theory», Bull Math Biol 69:1199 (2007), arXiv:q-bio/0501016, papers/dittrich07-bmb-arxiv-qbio0501016.pdf (sha256 729aafad…), 2026-11-27; organization = closed + self-maintaining, организации образуют решётку с union/intersection — сверено; «две части как два organization-множества с общим food set» — прямое следствие union-операции. Kaleta et al. 2008 — вторые руки.
**Утверждение (пересказ).** Формальное определение **самоподдерживающегося множества** видов в реакционной сети
(chemical organization): множество замкнуто по реакциям и не имеет «внешней» подпитки своих видов.
**Что даёт нам.** Готовый **комбинаторный** язык для «организации» — без энергии, только структура.
**Что меняет.** Кандидат в механизм третьего потолка: две части как два organization-множества с общим food set.

---

### L-027 · RAF-множества: замыкание есть, универсальной доли нет

```json
{
 "L": "L-027",
 "locator": {
  "doi": "10.3390/e12071733",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.3390/e12071733",
  "none": false
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/hordijk10-entropy-e12071733.pdf",
  "bytes": 178795,
  "sha256": "2d3aaa9c0217434b2ca86efd2a7b87d3973c60af5d590ff87b621590328ca10b",
  "retrieved_at": "2026-11-27T09:55:00Z",
  "via": "publisher-pdf",
  "via_detail": "mdpi-res Entropy 12(7):1733 (2010), Hordijk-Hein-Steel review, 10 стр.; RAF-определение, polynomial-time алгоритм — сверено; канонические IJMS-2011/2004 работы остаются частично вторыми руками"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "page", "from": "1733", "to": "1742"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "RAF-множества: замыкание есть, универсальной доли нет",
  "year": 2011,
  "first_author": "Hordijk"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Hordijk, Kauffman & Steel (2011), IJMS 12:3085; Mossel & Steel (2005), JTB 233:327–336.
**Проверено.** **фрагмент**: Hordijk-Hein-Steel, «Autocatalytic Sets and the Origin of Life», Entropy 12:1733-1742 (2010), papers/hordijk10-entropy-e12071733.pdf (sha256 2d3aaa9c…), 2026-11-27; RAF = RA (каждая реакция катализируется членом множества) + F (реагенты из food set), polynomial-time алгоритм — сверено. Каноническая IJMS 12:3085 (Hordijk-Kauffman-Steel 2011) и Mossel-Steel 2005 — вторые руки.
**Утверждение (пересказ).** RAF определимо формально (каждая реакция катализируется членом множества; все реагенты
строятся из food set), но **универсальной доли** реакций, необходимой для замыкания, нет.
**Что меняет.** Убрать из плана ожидание «доля реакций»; вместо неё — **порог по вероятности** и размер food set.

---

### L-028 · Viability: выживание — множество траекторий, а не мгновенный порог

```json
{
 "L": "L-028",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Viability: выживание — множество траекторий, а не мгновенный порог",
  "year": 1991,
  "first_author": "Aubin"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Aubin (1991); Saint-Pierre (1994); Maidens et al. (2013), Automatica.
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Viability kernel — **наибольшее множество состояний**, из которых существует траектория,
остающаяся в ограничениях; это строже, чем «жив ли объект сейчас».
**Что даёт нам.** Наш `q_min` — мгновенный порог; viability — **допуск на будущее**. Это готовый ответ на
«допуск вместо точки» (§4.13): полоса — **сечение viability kernel**.
**Что меняет.** Проверить, является ли наша полоса проекцией viability kernel; если да — назвать её так.

---

### L-029 · Порог ошибок Эйгена: точность против длины

```json
{
 "L": "L-029",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/eigen71.pdf",
  "bytes": 7655752,
  "sha256": "f51e8a9954652dc5166daad53acab986b3c8836697ff5f5004d972a927086e53",
  "retrieved_at": "2026-11-27T09:40:00Z",
  "via": "evolocus-pdf",
  "via_detail": "та же копия; точность↔длина в фрагментах IV-VI"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "section", "from": "§I-II"}, {"type": "section", "from": "§IV-VI (фрагменты)"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Порог ошибок Эйгена: точность против длины",
  "year": 1971,
  "first_author": "Eigen"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Eigen (1971); Eigen & Schuster (1977).
**Проверено.** **фрагмент первоисточника**: Eigen 1971, papers/eigen71.pdf (sha256 f51e8a99…), 2026-11-27; «length restrictions essentially imposed by the quality factors», порог точности для сохранения информации — сверено. Формула σq^ν явно в прочитанных фрагментах не выписана — остаётся пересказом.
**Утверждение (пересказ).** Максимальная длина, удерживаемая отбором, ограничена точностью копирования; порог
записывается через `σ q^ν` (по ревью) — **не** через `h`.
**Что меняет.** Q-024: без перевода переменных наше `h = 1` **нельзя** сопоставлять с порогом Эйгена.

---

### L-030 · Термодинамика замыкания: цены есть, универсальной формулы нет

```json
{
 "L": "L-030",
 "locator": {
  "doi": null,
  "arxiv": "1209.1179",
  "arxiv_version": "v1",
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/1209.1179",
  "none": false
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/england13-arxiv-1209.1179.pdf",
  "bytes": 2751718,
  "sha256": "ee43b219c742db84edf7f79048bbfa3b63810a165599c44ff112a71fa58de579",
  "retrieved_at": "2026-11-27T10:05:00Z",
  "via": "arxiv-pdf",
  "via_detail": "arXiv:1209.1179v1 (JCP 139:121923), England Statistical physics of self-replication, 5 стр., 22k chars; detailed-balance переходной матрицы, граница точности копирования от теплоотдачи — сверено; Kolchinsky-2024/Fodor-2016/Aguilera-2022 остаются вторыми руками"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "5"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Термодинамика замыкания: цены есть, универсальной формулы нет",
  "year": 2013,
  "first_author": "England"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** England (2013); Kolchinsky (2024); Fodor et al. (2016), PRL; Aguilera et al. (2022), Phys Life Rev.
**Проверено.** **фрагмент**: England, «Statistical Physics of Self-Replication», arXiv:1209.1179 (JCP 139:121923), papers/england13-arxiv-1209.1179.pdf (sha256 ee43b219…), 2026-11-27; детальное равновесие π(→i|j)π(→j|i)=exp[−β∆Q] и граница точности копирования от диссипации — сверено. Kolchinsky 2024, Fodor 2016, Aguilera 2022 — вторые руки.
**Утверждение (пересказ).** Работа на поддержание ограничений физически осмысленна, но **универсальной
термодинамической формулы замыкания нет**; диссипативная адаптация и MEPP — спорные принципы.
**Что меняет.** Наш `income − maintenance` — **бюджет**, не термодинамика; так и писать.

---

### L-031 · Индивидуальность: единого теста нет

```json
{
 "L": "L-031",
 "locator": {
  "doi": "10.1007/s10539-025-10001-9",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1007/s10539-025-10001-9",
  "none": true
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T21:30:00Z",
  "via": "openalex-abstract",
  "via_detail": "Schenkel, Patten & Agren, Biol Philos (2025), DOI 10.1007/s10539-025-10001-9; полный текст Springer заблокирован — только аннотация; метрики fitness unity / trait unity, коллектив = индивидуум в степени aligned fitness interests; Queller & Strassmann 2009 остаётся вторыми руками"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [
   {
    "type": "abstract"
   }
  ]
 },
 "abstract_sha256": "9b1b9827958823c46adda58d9eeb36586cdaa29a2ccb7eaf62980ab47af66f19",
 "bibliographic": {
  "title": "Индивидуальность: единого теста нет",
  "year": 2009,
  "first_author": "Queller & Strassmann"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Queller & Strassmann (2009); Schenkel, Patten & Ågren (2025), Biol Philos 40:29; Clarke (2010); Krakauer 2020.
**Проверено.** **аннотация**: Schenkel, Patten & Ågren, «Internal conflicts and the measurement of evolutionary individuality», Biol Philos (2025), DOI 10.1007/s10539-025-10001-9, papers/schenkel25-abstract.txt, 2026-11-27; количественная мера индивидуальности (fitness unity, trait unity) — из аннотации; «единого теста нет» подтверждается тем, что метрик предложено несколько. Queller & Strassmann 2009 — вторые руки.
**Утверждение (пересказ).** Списки критериев есть, единого операционального теста нет; тесты зависят от вопроса.
**Что меняет.** Не искать «тест индивидуальности», а **выбрать** один (Krakauer ITI) и применить к нашим рядам.

---

### L-032 · Assembly theory: сложность сборки, но не организация

```json
{
 "L": "L-032",
 "locator": {
  "doi": "10.1038/s41586-023-06600-9",
  "arxiv": "2206.02279",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/2206.02279",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/sharma23-arxiv-2206.02279.pdf",
  "bytes": 2082487,
  "sha256": "a4dea5df52c48963ae7bb2eaa166c88a8b331a28fe1c1d886e0c46408d996e8e",
  "retrieved_at": "2026-11-27T09:05:00Z",
  "via": "arxiv-pdf",
  "via_detail": "arXiv:2206.02279 PDF (версия Nature 2023, 22 стр.); assembly index, selection, evolution — сверено; ответ Kempes et al. 2025 остаётся вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "22"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Assembly theory: сложность сборки, но не организация",
  "year": 2023,
  "first_author": "Sharma et al."
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Sharma et al. (2023), Nature; ответ на критику — Kempes et al. (2025).
**Проверено.** **полный текст (arXiv-версия Nature-статьи)** papers/sharma23-arxiv-2206.02279.pdf (sha256 a4dea5df…), 2026-11-27; индекс сборки как мера сложности и его границы сверены с текстом; критика Kempes et al. (2025) — вторые руки.
**Утверждение (по полному тексту; вторичные источники — пересказ).** Индекс сборки измеряет **сложность**, не **организацию**; цены поддержания в нём нет.
**Что меняет.** Не использовать как аналог нашей организации.

---

### L-033 · Протоклетки: числа по проницаемости и делению

```json
{
 "L": "L-033",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T10:15:00Z",
  "via": "pubmed-abstract",
  "via_detail": "PNAS 108(13):5249-5254, PMID 21402937, DOI 10.1073/pnas.1100498108; fullTextXML недоступен (не OA-подмножество), PDF PNAS блокирует — только аннотация; Zhu & Szostak 2009 и Budin et al. 2012 остаются вторыми руками"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [
   {
    "type": "abstract"
   }
  ]
 },
 "abstract_sha256": "58035fd8539cd2db0caaa65ec4748e4a2a0b4e8bc105bc7f5cdc3bc507267ef9",
 "bibliographic": {
  "title": "Протоклетки: числа по проницаемости и делению",
  "year": 2009,
  "first_author": "Zhu & Szostak"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Zhu & Szostak (2009) JACS 131:5705; Budin & Szostak (2011) PNAS 108:5249; Budin, Debnath & Szostak (2012)
JACS 134:20812; Breuer et al. (2019) eLife; Pelletier et al. (2021) Cell 184:2430; Thornburg et al. (2022) Cell.
**Проверено.** **аннотация**: Budin & Szostak, «Physical effects underlying the transition from primitive to modern cell membranes», PNAS 108:5249 (2011), PMID 21402937, papers/budin11-abstract.txt, 2026-11-27; низкий уровень фосфолипидов уже драйвит рост протоклеточной мембраны, каскад селективных давлений на метаболизм/транспорт — из аннотации; полный текст недоступен.
**Утверждение (пересказ).** Есть измеренные проницаемости и условия роста/деления везикул; **цены** поддержания
границы как функции целости — нет.
**Что меняет.** Именно здесь наша цена `c·d·q_min` может быть **числом**, которого у них нет.

---

### L-034 · Niche construction: обратная связь есть, скалярной меры нет

```json
{
 "L": "L-034",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Niche construction: обратная связь есть, скалярной меры нет",
  "year": 1994,
  "first_author": "Jones"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Jones, Lawton & Shachak (1994) Oikos 69:373; Laland, Odling-Smee & Feldman (1999) PNAS 96:10242;
Odling-Smee et al. (2013) Am Nat; Mitteroecker et al. (2016) PNAS.
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Записывают **ΔR** (разницу среды до и после), но универсальной меры «силы конструкции»
нет; **изменение среды ≠ участие в своих условиях**.
**Что меняет.** Наш §4.9 (`spent = 0`) — узкий и измеримый случай; назвать его так.

---

### L-035 · Cliff-edge, риск и оптимальность

```json
{
 "L": "L-035",
 "locator": {
  "doi": "10.1371/journal.pone.0034889",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1371/journal.pone.0034889",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/vercken12-plosone-e34889.pdf",
  "bytes": 450630,
  "sha256": "54ded2570019d12ab64e5c951f45ad59fbe2776d04a2773c862d7f3c0a7f48f7",
  "retrieved_at": "2026-11-27T08:55:00Z",
  "via": "publisher-pdf",
  "via_detail": "journals.plos.org printable PDF (PLoS ONE 7(4):e34889), 9 стр.; Jensen’s inequality, phenotypic variance, genotype fitness — сверено с текстом; Stephens-Charnov 1982 и Kussell-Leibler 2005 остаются вторыми руками (paywall)"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "9"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Cliff-edge, риск и оптимальность",
  "year": 2012,
  "first_author": "Vercken et al."
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Vercken et al. (2012) PLoS ONE 7:e34889; Stephens & Charnov (1982); Kussell & Leibler (2005) Science 309:2075;
Haaland et al. (2019) Proc R Soc B 286:20192070.
**Проверено.** **частично первый источник**: Vercken et al. 2012 PLoS ONE 7:e34889 — полный текст papers/vercken12-plosone-e34889.pdf (sha256 54ded257…), 2026-11-27; асимметричная fitness-функция + фенотипическая дисперсия → ESS ниже фенотипического оптимума через Jensen’s inequality, «genotype fitness» = reproductive value по распределению — сверено. Stephens & Charnov (1982) и Kussell & Leibler (2005) — по-прежнему вторые руки.
**Утверждение (по тексту Vercken 2012; остальные — пересказ).** У обрыва оптимум сдвигается; риск-чувствительные стратегии количественно описаны;
bet-hedging оптимален, когда критерий **геометрический**.
**Что меняет.** Q-019 остаётся ключевым: наш критерий аддитивный → «bet-hedging» не наше слово.

---

### L-036 · Надёжность: `μ` как интенсивность отказов

```json
{
 "L": "L-036",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/gavrilov14-gerontology-pmc4475490.xml",
  "bytes": 80772,
  "sha256": "2f37ac4e0bc2952bce7bf8388035dcab7165dd5f91bae252acb4879e24de102e",
  "retrieved_at": "2026-11-27T21:00:00Z",
  "via": "ncbi-efetch-pmc",
  "via_detail": "Gavrilov & Gavrilova, Gerontology 61:364-371 (2015), PMC4475490, DOI 10.1159/000369011; обзор их reliability theory: избыточность/резервы, exhaustion redundancy → mortality leveling-off, Gompertz force of mortality — сверено по полному тексту; первичные работы 1991/2001 остаются вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [
   {
    "type": "article",
    "from": "1",
    "to": "full"
   }
  ]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Надёжность: `μ` как интенсивность отказов",
  "year": 2001,
  "first_author": "Gavrilov & Gavrilova"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gavrilov & Gavrilova (2001), JTB; обзор 2024.
**Проверено.** **полный текст**: тот же обзор Gavrilov & Gavrilova 2015 (PMC4475490), 2026-11-27; μ как интенсивность отказов (force/hazard of mortality), Gompertz-закон как геометрическая прогрессия — сверено; первичная JTB 2001 — вторые руки.
**Утверждение (пересказ).** Смертность — интенсивность отказов системы с запасом прочности; даёт Гомпертца и плато.
**Что меняет.** Язык §4.12: «время до отказа», «интенсивность отказов».

---

### L-037 · **Пустое пересечение**: у моделей повреждения нет цены границы

```json
{
 "L": "L-037",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "**Пустое пересечение**: у моделей повреждения нет цены границы",
  "year": 2026,
  "first_author": "вывод ревью"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** вывод ревью 2026-11-20 (и его собственный поиск).
**Проверено.** **вторые руки** — и это **гипотеза о пробеле**, не факт.
**Утверждение (цитата).** «Модели старения (Chao, Borgqvist) **не имеют цены мембраны**; протоклеточные модели
**не имеют наследования повреждения**. Пересечение выглядит пустым — **но я не проводил исчерпывающего поиска**».
**Что даёт нам.** Настоящий кандидат на своё: **повреждение + граница в одном бюджете**. И готовые запросы:
`protocell damage inheritance asymmetric division model`, `vesicle maintenance cost damage segregation`,
`lipid world repair budget lineage`.
**Что меняет.** Возглавить следующий поиск; от «мы нашли закон» перейти к «мы сшили два незамкнутых поля».

### L-038 · Bet-hedging: критерий и три ловушки

```json
{
 "L": "L-038",
 "locator": {
  "doi": "10.1111/j.1469-185X.2012.00225.x",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1111/j.1469-185X.2012.00225.x",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/starrfelt12-biolrev.pdf",
  "bytes": 838684,
  "sha256": "623025f8f036624b5e9677fc397789161eefac20d42c74608f738ae252c8bde2",
  "retrieved_at": "2026-11-27T09:25:00Z",
  "via": "author-site-pdf",
  "via_detail": "Starrfelt12.pdf с kokkonuts.org (Biol. Rev. 87:742-755, 14 стр.); variance/correlation decomposition bet-hedging — сверено; Cohen 1966, Lewontin-Cohen 1969, Seger-Brockmann 1987, Frank-Slatkin 1990 остаются вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "742", "to": "755"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Bet-hedging: критерий и три ловушки",
  "year": 1966,
  "first_author": "Cohen"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Cohen (1966); Lewontin & Cohen (1969); Seger & Brockmann (1987); Frank & Slatkin (1990); Starrfelt & Kokko
(2012), Biol. Rev., doi:10.1111/j.1469-185X.2012.00225.x.
**Проверено.** **полный текст** papers/starrfelt12-biolrev.pdf (Starrfelt & Kokko, Biol. Rev. 87:742-755, sha256 623025f8…), 2026-11-27; декомпозиция genotypic fitness variance на within-individual variance + correlations, консервативные vs диверсифицированные стратегии как концы континуума — сверено. Cohen (1966) и остальные классические работы — вторые руки.
**Утверждение (по полному тексту Starrfelt-Kokko; классика — пересказ).** Bet-hedging — жертва средним ради снижения дисперсии; решающее различие —
**коррелированы ли катастрофы между особями**: при общей флуктуации работает геометрическое среднее, при независимых
исходах в большой популяции — арифметическое. **Ловушка:** смерть делает геометрическое среднее **нулём**.
**Что меняет.** `Q-019`: дизайн 2×2 {общие / идиосинкратические} × {арифметика / геометрия}.

---

### L-039 · Скалярная память: максимум смещён (winner's curse), стандарт — UCB

```json
{
 "L": "L-039",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Скалярная память: максимум смещён (winner's curse), стандарт — UCB",
  "year": 1993,
  "first_author": "Thrun & Schwartz"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Thrun & Schwartz (1993); van Hasselt (2010); Auer, Cesa-Bianchi & Fischer (2002).
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** `E[max]` из `n` шумных чтений строго выше истинного среднего, смещение ≈ `σ·√(2 ln n)` и
**растёт** с числом чтений. Альтернатива — `mean + k·σ/√n` (UCB): оптимизм, **убывающий** с опытом.
**Что меняет.** `Q-010`: четыре плеча — max / mean / UCB / sham.

---

### L-040 · Калибровка и sharpness — стандартные метрики

```json
{
 "L": "L-040",
 "locator": {
  "doi": "10.1198/016214506000001437",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/gneiting07-jasa.pdf",
  "bytes": 556804,
  "sha256": "d31a0c5f0ae8fec1a0a6544db5d056645b2d7296d71b44a2e8efb293c7d87ba2",
  "retrieved_at": "2026-11-27T09:15:00Z",
  "via": "author-site-pdf",
  "via_detail": "Gneiting2007jasa.pdf с sites.stat.washington.edu/raftery (JASA 102:359-378, 20 стр.); proper scoring rules, calibration, sharpness — сверено; Gneiting-Balabdaoui-Raftery JRSS-B 2007 остаётся вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "359", "to": "378"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Калибровка и sharpness — стандартные метрики",
  "year": 2007,
  "first_author": "Gneiting & Raftery"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gneiting & Raftery (2007), JASA, doi:10.1198/016214506000001437; Gneiting, Balabdaoui & Raftery (2007),
JRSS-B, doi:10.1111/j.1467-9868.2007.00587.x.
**Проверено.** **полный текст** papers/gneiting07-jasa.pdf (JASA 102:359-378, sha256 d31a0c5f…), 2026-11-27; strictly proper scoring rules, calibration vs sharpness — сверено с текстом. Gneiting, Balabdaoui & Raftery (JRSS-B 2007) — вторые руки.
**Утверждение (по полному тексту; JRSS-B — пересказ).** Brier (бинарное), CRPS (непрерывное); калибровка и **sharpness** — раздельно; strictly
proper scoring rules — единственные, где честно говорить правду.
**Что меняет.** `Q-012` и прибор `Q-022`: те же метрики — к исследователю, а не к организму.

---

### L-041 · Sizer / adder / timer: канон регуляции размера

```json
{
 "L": "L-041",
 "locator": {
  "doi": "10.1146/annurev-biophys-070317-032955",
  "arxiv": "1801.00494",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/1801.00494",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/amir18-arxiv-1801.00494.pdf",
  "bytes": 3869356,
  "sha256": "5e3dd8ee7067f8ac4bcc1fae30d46c88ae2fff7a846cc5756d3984538376cb08",
  "retrieved_at": "2026-11-27T09:05:00Z",
  "via": "arxiv-pdf",
  "via_detail": "arXiv:1801.00494 PDF (= Ann. Rev. Biophys. обзор Ho, Lin & Amir, 13 стр.); sizer/adder/timer, |a|<2 — сверено; Donachie 1968, Campos 2014, Taheri-Araghi 2015 остаются вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "13"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Sizer / adder / timer: канон регуляции размера",
  "year": 1968,
  "first_author": "Donachie"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Donachie (1968); Campos et al. (2014); Taheri-Araghi et al. (2015); Ho, Lin & Amir (2018),
doi:10.1146/annurev-biophys-070317-032955.
**Проверено.** **полный текст (arXiv-версия обзора)** papers/amir18-arxiv-1801.00494.pdf (sha256 5e3dd8ee…), 2026-11-27; три механизма sizer/adder/timer и условие |a|<2 сверены с текстом; Donachie (1968), Campos (2014), Taheri-Araghi (2015) — вторые руки.
**Утверждение (по полному тексту; вторичные источники — пересказ).** Три механизма; параметризация `s_d = a·s_b + b`, `a = 0 / 1 / 2`. Устойчивость
распределения ⟺ `|a| < 2`; стационарная дисперсия `σ²/(1 − (a/2)²)`.
**Что меняет.** `Q-013`: у наших приёмов есть канонические имена; сверять **распределение**, не среднее.

---

### L-042 · Chemical organization theory: формальное замыкание

```json
{
 "L": "L-042",
 "locator": {
  "doi": "10.1007/s11538-006-9130-8",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://home.pietrosperoni.it/wp-content/uploads/2006/11/Chapter-11.pdf",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/cot07-df.pdf",
  "bytes": 450196,
  "sha256": "c011aa0b2f0fdb2f8ed1cd0537e3353bfd3036f66d7ab10e18be1b6c93c37c22",
  "retrieved_at": "2026-11-27T08:45:00Z",
  "via": "author-site-pdf",
  "via_detail": "Chapter-11.pdf с home.pietrosperoni.it (Springer Systems Biology ch.11, 33 стр.), текстовый слой; цитаты верифицированы как подстроки"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "361", "to": "393"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Chemical organization theory: формальное замыкание",
  "year": 2007,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Dittrich & Speroni di Fenizio (2007), Bull. Math. Biol., doi:10.1007/s11538-006-9130-8; обзор 2024,
doi:10.3390/systems12040111.
**Проверено.** **полный текст** papers/cot07-df.pdf (глава 11, Dittrich & Speroni di Fenizio, Systems Biology/Springer 2007, sha256 c011aa0b…), 2026-11-27; определения closure/self-maintenance, теорема «стационарное состояние = организация», решётка организаций и food set сверены с текстом посимвольно (батч s7zeu).
**Утверждение (по полному тексту).** Организация — множество видов, **замкнутое** по реакциям и **самоподдерживающееся**;
организации образуют **решётку**. Границы, мембраны, цены и наследования в базовом формализме **нет**.
**Что меняет.** `Q-028`: кандидат в третий потолок; бюджет добавляется руками (левое ядро стехиометрии + потоки = LP).

---

### L-043 · RAF: три разные задачи, и только две полиномиальны

```json
{
 "L": "L-043",
 "locator": {
  "doi": "10.1186/s13322-014-0006-2",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1186/s13322-014-0006-2",
  "none": false
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/hordijk15-jsystchem.xml",
  "bytes": 70137,
  "sha256": "c7b303d7511116be9073bff5030b98f9a672c48eb0f2b352013238a4a89ca2fd",
  "retrieved_at": "2026-11-27T09:55:00Z",
  "via": "europepmc-fulltext-xml",
  "via_detail": "europepmc PMC4333308, Hordijk-Steel «Autocatalytic sets and boundaries», J Syst Chem 6:1 (2015); polynomial-time алгоритмы RAF/irrRAF — сверено по тексту; NP-полнота минимальной irrRAF — из вторых рук; обзор Entropy 2010 читан отдельно как L-027"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [
   {
    "type": "lines",
    "from": 1,
    "to": 14
   }
  ]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "RAF: три разные задачи, и только две полиномиальны",
  "year": 2004,
  "first_author": "Hordijk & Steel"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Hordijk & Steel (2004); Hordijk, Kauffman & Steel (2011), IJMS 12:3085; PMC4428007.
**Проверено.** **фрагмент**: тот же обзор Entropy 2010 + J Syst Chem 2015 (papers/hordijk15-jsystchem.xml, PMC4333308), 2026-11-27; polynomial-time алгоритм нахождения RAF и minimal RAF — сверено по тексту; NP-полнота минимальной irrRAF и экспоненциальное число irrRAF — из вторых рук (в обзорах не выписаны явно).
**Утверждение (пересказ).** Максимальная RAF — **полиномиально**; любая irrRAF — полиномиально; **минимальная по
мощности** irrRAF — **NP-полна**; число irrRAF может быть экспоненциальным.
**Что меняет.** `Q-006`: нельзя «найти один irrRAF» превращать в «найти минимальный».

---

### L-044 · Экологическая стехиометрия: возврат вещества в среду

```json
{
 "L": "L-044",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Экологическая стехиометрия: возврат вещества в среду",
  "year": 1999,
  "first_author": "Elser & Urabe"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Elser & Urabe (1999), Ecology; Daufresne & Hedin (2005); Tilman (1982); Nicholson (1954).
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Потребители возвращают азот и фосфор; состав организма задаёт соотношение выделяемого —
обратная связь «потребитель ↔ ресурс»; выигрывает **наименьший `R*`**; contest vs scramble — разные механизмы дележа.
**Что меняет.** `Q-011`: `w = α·изъятие` с задержкой `τ` и **инвариант** `Σ(поле + организм + отход) = const`;
выбрать contest или scramble **до** прогона.

---

### L-045 · Надёжность и Гомпертц без постулата `μ`

```json
{
 "L": "L-045",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/gavrilov14-gerontology-pmc4475490.xml",
  "bytes": 80772,
  "sha256": "2f37ac4e0bc2952bce7bf8388035dcab7165dd5f91bae252acb4879e24de102e",
  "retrieved_at": "2026-11-27T21:00:00Z",
  "via": "ncbi-efetch-pmc",
  "via_detail": "Gavrilov & Gavrilova, Gerontology 61:364-371 (2015), PMC4475490, DOI 10.1159/000369011; обзор их reliability theory: избыточность/резервы, exhaustion redundancy → mortality leveling-off, Gompertz force of mortality — сверено по полному тексту; первичные работы 1991/2001 остаются вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [
   {
    "type": "article",
    "from": "1",
    "to": "full"
   }
  ]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Надёжность и Гомпертц без постулата `μ`",
  "year": 1991,
  "first_author": "Гаврилов и Гаврилова"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Гаврилов и Гаврилова (1991, 2001); Strehler & Mildvan (1960).
**Проверено.** **полный текст**: Gavrilov & Gavrilova 2015 (PMC4475490), 2026-11-27; Gompertz без постулата μ — вытекает из reliability-структуры (резервы + случайные удары), плюс результат DMF: замедление ничтожно до 106 лет — сверено; Strehler & Mildvan 1960 — вторые руки.
**Утверждение (пересказ).** Избыточность с начальным грузом дефектов и её исчерпание дают гомперцеву смертность
**без постулата** `μ`; внешние числа — время удвоения смертности, корреляция Стрелера–Милдвана, плато смертности.
**Что меняет.** `Q-021`: путь надёжнее самоссылки; и структурная проверка — детерминированный порог даёт
**дельта-функцию** времени жизни.

---

### L-046 · Error catastrophe: известный отрицательный результат

```json
{
 "L": "L-046",
 "locator": {
  "doi": "10.1006/jtbi.1994.1089",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pubmed.ncbi.nlm.nih.gov/8022192/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T09:40:00Z",
  "via": "pubmed-abstract",
  "via_detail": "PubMed efetch PMID 8022192, J Theor Biol 168:75-94 (1994); полный текст закрыт (Elsevier)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "abstract"}]
 },
 "abstract_sha256": "0b9ef7f96c02eadfa7ed26c8cd0b2766e43f1e151e0a6a468f7006e62c48d2d2",
 "bibliographic": {
  "title": "Error catastrophe: известный отрицательный результат",
  "year": 1963,
  "first_author": "Orgel"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Orgel (1963); Kowald & Kirkwood (1994), JTB, doi:10.1006/jtbi.1994.1089.
**Проверено.** **аннотация** PubMed PMID 8022192 (sha256 0b9ef7f9…), 2026-11-27; «increased radical production and/or insufficient radical protection can destabilize an otherwise stable translation system», positive correlation maintenance-energy↔lifespan — сверено с abstract. Полный текст закрыт.
**Утверждение (пересказ).** Наивная самоссылка (ошибки повреждают аппарат синтеза) обычно **не даёт разгона** —
система выходит на стационар. Для экспоненциальной смертности нужна **нелинейность** или насыщение.
**Что меняет.** `Q-021`: ожидание «самоссылка → Гомпертц» литературой **не подтверждено**.

---

### L-047 · Интегральная обратная связь: среднее держится, дисперсия растёт

```json
{
 "L": "L-047",
 "locator": {
  "doi": "10.1016/j.cels.2016.01.004",
  "arxiv": "1410.6064",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/1410.6064",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/briat16-arxiv-1410.6064.pdf",
  "bytes": 2350616,
  "sha256": "5036d32176bcde430b4bb3cfe3891ac7c657898ad828cd3827786ebac3538b82",
  "retrieved_at": "2026-11-27T08:55:00Z",
  "via": "arxiv-pdf",
  "via_detail": "arXiv:1410.6064v7 PDF (Cell Systems 2(6):624-640), 19 стр., текстовый слой; antithetic integral feedback, perfect adaptation, шум — сверено; Lindner et al. 2008 остаётся вторыми руками"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "1", "to": "19"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Интегральная обратная связь: среднее держится, дисперсия растёт",
  "year": 2016,
  "first_author": "Briat"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Briat, Gupta & Khammash (2016) antithetic integral feedback; Lindner et al. (2008).
**Проверено.** **полный текст (arXiv)**: Briat, Gupta & Khammash 2016, arXiv:1410.6064v7 = Cell Systems 2(6):624-640, papers/briat16-arxiv-1410.6064.pdf (sha256 5036d321…), 2026-11-27; antithetic integral feedback → robust perfect adaptation, эксплуатация шума, малый метаболический груз — сверено с текстом. Lindner et al. 2008 — по-прежнему вторые руки.
**Утверждение (по полному тексту arXiv; Lindner — пересказ).** Интегральная связь даёт robust perfect adaptation (среднее закреплено), но **ценой роста
дисперсии**; полоса с отражающими границами даёт усечённое распределение и **робастна** к сдвигу вероятностей.
**Что меняет.** `Q-013`: то, что у нас выжила только полоса, **согласуется с теорией**; различать по форме
распределения.

---

### L-048 · Порог ошибок Эйгена как безразмерная группа

```json
{
 "L": "L-048",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/eigen71.pdf",
  "bytes": 7655752,
  "sha256": "f51e8a9954652dc5166daad53acab986b3c8836697ff5f5004d972a927086e53",
  "retrieved_at": "2026-11-27T09:40:00Z",
  "via": "evolocus-pdf",
  "via_detail": "та же копия; selection equilibrium/optimum value в §II-III"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "section", "from": "§I-II"}, {"type": "section", "from": "§IV-VI (фрагменты)"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Порог ошибок Эйгена как безразмерная группа",
  "year": 1971,
  "first_author": "Eigen"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Eigen (1971); Eigen & Schuster (1977); обзоры quasispecies (PMC7105236, PMC3466355).
**Проверено.** **фрагмент первоисточника**: Eigen 1971, papers/eigen71.pdf (sha256 f51e8a99…), 2026-11-27; sliding threshold, selection equilibrium как метастабильное состояние, «evolution is fastest if Q is as small as possible, but … must be above the threshold» — сверено. Граница μ_c = ln σ/ν — вторые руки (в прочитанных фрагментах явно не найдена).
**Утверждение (пересказ).** `σ·q^ν > 1`; граница `μ_c = ln σ / ν`.
**Что меняет.** `Q-024`: наш `h = 1` **не** эта граница; перевод — только через безразмерные группы и нормальные
формы; прямое сопоставление `h` и `Πλ` недействительно.

---

### L-049 · Один прибор: калибровка исследователя = калибровка организма

```json
{
 "L": "L-049",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Один прибор: калибровка исследователя = калибровка организма",
  "year": null,
  "first_author": "те же"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** те же, что `L-039` и `L-040`.
**Проверено.** **вторые руки.**
**Утверждение (пересказ).** Лог-счёт по strictly proper rule эквивалентен информационному выигрышу; искажением его
не улучшить.
**Что меняет.** `Q-022`: прибор — **лог-счёт по предрегистрации** (вероятность до прогона) + **MDL** (число
независимых постулатов).

---

### L-050 · COT + потоки = LP, и «цена» как двойственная переменная

```json
{
 "L": "L-050",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": null,
  "none": true
 },
 "access": {
  "level": "secondary_only",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "none",
  "via_detail": null
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "COT + потоки = LP, и «цена» как двойственная переменная",
  "year": 2007,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Dittrich & Speroni di Fenizio (2007) + традиция FBA.
**Проверено.** **вторые руки** (синтез обзора, не цитата).
**Утверждение (пересказ).** К организации добавляются ограничения потоков — задача становится **LP**; цена
ограничения — **двойственная переменная**; двойственные цены **кусочно-постоянны** и скачут при смене базиса.
**Что меняет.** «Цена кожи» может стать вычисляемым числом; предсказание — **изломы** в цене.

---

### L-051 · Порог `Πλ = 1/6` **подтверждён локатором**

```json
{
 "L": "L-051",
 "locator": {
  "doi": "10.1371/journal.pgen.1001076",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://journals.plos.org/plosgenetics/article/figures?id=10.1371/journal.pgen.1001076",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://journals.plos.org/plosgenetics/article/figures?id=10.1371/journal.pgen.1001076"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Порог `Πλ = 1/6` **подтверждён локатором**",
  "year": 2010,
  "first_author": "Chao"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/",
 "duplicate_of": "L-005"
}
```



**Кто.** Chao, L. (2010), PLOS Genetics 6(8): e1001076 — страница рисунков и уравнения;
учебная глава «Cellular senescence» (ASU, PDF).
**Ссылка.** https://journals.plos.org/plosgenetics/article/figures?id=10.1371/journal.pgen.1001076 ;
https://biodesign.asu.edu/cellular-evolution/wp-content/uploads/sites/23/2023/02/Ch11_Senescence_FINAL.pdf
**Проверено.** **аннотация/фрагмент**: на странице рисунков PLOS — «equilibrium is possible… because the lifetime
damage rate of **Πλ = 0.10 is less than the threshold of 1/6** (Equation 11)»; в главе — «With symmetric division
(α = 1), the criterion for equilibrium reduces to **Pcλ ≤ 1/6**».
**Утверждение (цитата).** Порог симметричного деления — `Πλ ≤ 1/6`; при `Πλ > 1/6` уравнение 11 не имеет
вещественного решения.
**Что меняет.** Снимает из `SYNTHESIS-2026-11-20.md` §9 пункт «не принял Πλ = 1/6»: **принято с локатором**.
Наше `h = 1` по-прежнему **не** `Πλ`.

---

### L-052 · Асимметричное деление **протоклеток** — ближайший сосед нашего пересечения

```json
{
 "L": "L-052",
 "locator": {
  "doi": "10.1162/isal_a_00722",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1162/isal_a_00722",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1162/isal_a_00722"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Asymmetrical division in protocells",
  "year": 2024,
  "first_author": "ALIFE"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Asymmetrical division in protocells» (ALIFE 2024), doi:10.1162/isal_a_00722; «Models of Protocells
Undergoing Asymmetrical Division» (2024), PMC11049191.
**Ссылка.** https://doi.org/10.1162/isal_a_00722 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC11049191/
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Устойчивый рост популяции протоклеток требует **синхронизации** дупликации генетического
материала и деления липидного контейнера; при асимметричном делении условия синхронизации меняются.
**Что даёт нам.** Это ближайшая работа к **пустому пересечению** (`L-037`): протоклетки + **асимметричное деление**.
Но **повреждения мембраны и его наследования** в аннотации нет — цена границы не входит.
**Что меняет.** Пересечение пока **не закрыто**; в `ELEPHANT-MAP.md` §2 записать: ближайший сосед — эта линия,
отличие наше — **повреждение границы и его цена**.

---

### L-053 · Стохастическая модель старения: повреждение, починка, асимметрия деления

```json
{
 "L": "L-053",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6631810/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6631810/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Стохастическая модель старения: повреждение, починка, асимметрия деления",
  "year": 2019,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Stochastic modeling of aging cells reveals how damage accumulation, repair, and cell-division asymmetry affect
clonal senescence and population fitness (2019), PMC6631810.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC6631810/
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Детерминированная модель асимметричного распределения повреждения и объёма клетки давала
один вывод; **стохастическая** версия меняет предсказания о клональном старении и приспособленности популяции.
**Что даёт нам.** Это **прямой аналог** нашей линии «прошлое»: повреждение + починка + асимметрия при делении.
Значит наша модель без деления — **вырожденный случай** их схемы.
**Что меняет.** В `POSITIVE.md` §4.12: назвать рамку; отдельно указать отличие — у нас **нет деления**, канал удаления
только смерть.

---

### L-054 · Наследование повреждения: модель «происхождения старения»

```json
{
 "L": "L-054",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2049046/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2049046/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "On the evolutionary origin of aging",
  "year": 2007,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «On the evolutionary origin of aging» (2007), PMC2049046 (Erjavec и соавт.).
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC2049046/
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитата из фрагмента).** «At the start of a generation, each individual contains a certain amount of
damage d, which was conferred to it by its parent…»; параметр `a` — доля повреждения, передаваемая потомку
(`a = 0` симметрично, `a = 1` полностью асимметрично).
**Что даёт нам.** Параметр `a` — это **наш `h`** в другой записи. Значит перевод возможен: `h ↔ a`.
**Что меняет.** `Q-024`: первая **конкретная** пара соответствия; сравнение `h = 1` с `a` и `Πλ` — следующий шаг.

---

### L-055 · Надёжность: Гомпертц **и плато** из исчерпания избыточности

```json
{
 "L": "L-055",
 "locator": {
  "doi": "10.1196/annals.1297.094",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "http://longevity-science.org/JTB-01.pdf",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "http://longevity-science.org/JTB-01.pdf"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "The Reliability Theory of Aging and Longevity",
  "year": 2001,
  "first_author": "Гаврилов и Гаврилова"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Gavrilov & Gavrilova (2001), JTB — «The Reliability Theory of Aging and Longevity»; Гаврилов и Гаврилова
(2004), Ann. NY Acad. Sci., doi:10.1196/annals.1297.094; обзор 2024, PMC11090256.
**Ссылка.** http://longevity-science.org/JTB-01.pdf ; https://doi.org/10.1196/annals.1297.094 ;
https://pmc.ncbi.nlm.nih.gov/articles/PMC11090256/ (**fetch заблокирован**: домен резолвится в приватный адрес)
**Проверено.** **аннотация/фрагмент** (текст не открылся).
**Утверждение (цитаты из фрагментов).** «According to the Gompertz law, human mortality rates **double approximately
every 8 years** of adult age: `μ(x) = R·e^{αx}`». «It predicts the late-life… mortality plateaus, as an inevitable
consequence of **redundancy exhaustion** at extreme old ages». «Redundancy is a key notion for understanding aging…
systems, which are redundant in numbers of irreplaceable elements, do deteriorate».
**Что даёт нам.** **Замена постулату `μ`**: и Гомпертц, и **плато** выводятся из архитектуры системы (избыточность →
её исчерпание), а не задаются. Это прямой ответ на нашу дыру «пол старения взят извне».
**Что меняет.** `Q-021`: путь — **не** самоссылка починки (у неё известный отрицательный результат, `L-046`), а
избыточность с начальным грузом дефектов.

---

### L-056 · Плато смертности как установленный феномен, а не артефакт

```json
{
 "L": "L-056",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6703938/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6703938/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "New trend in old-age mortality: Gompertzialization of mortality trajectory",
  "year": 2024,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** обзор 2024 (PMC11090256); «New trend in old-age mortality: Gompertzialization of mortality trajectory»
(2019), PMC6703938; Laird & Sherratt (2009), JEB — «decelerating selection for system reliability».
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC6703938/ ;
https://people.uleth.ca/~robert.laird/Laird%20and%20Sherratt%202009%20JEB.pdf
**Проверено.** **аннотация/фрагмент.**
**Утверждение (пересказ).** Позднее плато смертности — **наблюдаемый** феномен; вопрос не «есть ли оно», а какая
модель его воспроизводит. Laird & Sherratt дают **эволюционный** механизм: отбор по надёжности системы замедляется с
возрастом.
**Что даёт нам.** **Внешний якорь** для нашего §4.12: если наша модель даёт плато как решение, его есть с чем
сравнить — внешние числа: удвоение смертности каждые ~8 лет, положение плато, его высота.
**Что меняет.** `PREDICTIONS.md`: предсказание про **форму** нашей кривой (плато или нет) с вероятностью.

---

### L-057 · Одноклеточные делят ресурс между **асимметричным распределением** и **починкой**

```json
{
 "L": "L-057",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10705550/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10705550/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Одноклеточные делят ресурс между **асимметричным распределением** и **починкой**",
  "year": 2023,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «Unicellular life balances asymmetric allocation and repair of somatic damage representing the origin of r/K
selection» (2023), PNAS, PMC10705550.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC10705550/
**Проверено.** **аннотация/фрагмент** (в фрагменте — нормировки `y ≡ 1`, `r ≡ R/E`).
**Утверждение (пересказ).** В модели одноклеточного есть **два способа обращения с повреждением**: передать его
асимметрично потомкам или **починить**; баланс между ними объясняет происхождение r/K-стратегий.
**Что даёт нам.** Это **ближайший аналог** нашей линии «выбор» (`§4.13`, `§4.14`): та же развилка, только второе
назначение у них — **асимметрия**, у нас — **запас**.
**Что меняет.** `POSITIVE.md` §4.13: назвать рамку; наше отличие — второе назначение **запас против засухи**, а не
передача повреждения.

---

### L-058 · Кривые выживания выводятся из **оптимального распределения ресурса**

```json
{
 "L": "L-058",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://ruj.uj.edu.pl/xmlui/handle/item/263279",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://ruj.uj.edu.pl/xmlui/handle/item/263279"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Ageing and typical survivorship curves result from optimal resource allocation",
  "year": 2000,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Ageing and typical survivorship curves result from optimal resource allocation» (2000); «A life history model
of somatic damage associated with resource acquisition: damage protection or prevention?» (JCU).
**Ссылка.** https://ruj.uj.edu.pl/xmlui/handle/item/263279 ; https://researchonline.jcu.edu.au/42556/
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Интенсивность починки **меняется с возрастом**; стратегия распределения отвечает на
**внешнюю смертность**; при высокой внешней смертности темп старения выше. Вторая работа: ресурс не ограничен
извне — есть **оптимальный приток** и оптимальное распределение.
**Что даёт нам.** Готовый **внешний якорь**: если наша модель даёт кривые выживания, они должны ложиться в эту
типологию; и предсказание «высокая внешняя смертность → быстрее старение» проверяемо у нас.
**Что меняет.** `Q-013`-линия и `PREDICTIONS.md`: предсказание про **влияние внешней смертности** на наш оптимум.

---

### L-059 · DEB: правило κ, приоритет поддержания и голодание

```json
{
 "L": "L-059",
 "locator": {
  "doi": "10.30707/lib1.2ledder",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.sciencedirect.com/science/article/abs/pii/S1385110106000311",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.sciencedirect.com/science/article/abs/pii/S1385110106000311"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "An introduction to DEB models…",
  "year": 1986,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Kooijman (1986, 2000) — DEB; «An introduction to DEB models…» (2006); «The Basic DEB Model and Some
Implications» (2014), doi:10.30707/lib1.2ledder.
**Ссылка.** https://www.sciencedirect.com/science/article/abs/pii/S1385110106000311 ;
https://doi.org/10.30707/lib1.2ledder
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Энергия делится **правилом κ**: доля κ идёт на поддержание сомы, `1−κ` — на рост и
размножение; при голодании животное живёт, пока **запас оплачивает поддержание**; в DEBkiss при голодании рост
останавливается, а поддержание платится из ветви `1−κ`.
**Что даёт нам.** Формальная версия нашей связки «целость против запаса»: у них то же деление бюджета, но **приоритет
поддержания** задан правилом, а не выводится.
**Что меняет.** `Q-020`: сравнивать наше `c ≤ 1` надо с их пределом «поддержание бесплатно», где приоритет уже не
работает.

---

### L-060 · Графы «процесс–обеспечение»: замыкание становится вычислимым

```json
{
 "L": "L-060",
 "locator": {
  "doi": "10.1016/j.biosystems.2025.105567",
  "arxiv": "2411.17012",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1016/j.biosystems.2025.105567",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/arXiv-2411.17012-brown-vittadello.txt",
  "bytes": 81691,
  "sha256": "f4d973f548b22cf86d579f368aab3d0e379098193b6431e77a5a90110b12b708",
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1016/j.biosystems.2025.105567"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Studying organisational closure in biological systems with process-enablement graphs",
  "year": 2025,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Studying organisational closure in biological systems with process-enablement graphs» (2025), BioSystems,
doi:10.1016/j.biosystems.2025.105567; препринт arXiv:2411.17012.
**Ссылка.** https://doi.org/10.1016/j.biosystems.2025.105567 ; https://arxiv.org/html/2411.17012
**Проверено.** **полный текст** arXiv-версии (`arXiv:2411.17012v2`, 81 691 байт, локальная копия
`papers/arXiv-2411.17012-brown-vittadello.txt`); журнальная версия — только аннотация (домен был закрыт
до 2026-11-21, см. `LITERATURE-GAPS.md`).
**Утверждение (пересказ аннотации).** Разные теории самоорганизации формулируют «поддержание условий собственного
существования» по-разному, из-за чего признаки самоорганизации трудно выделять и сравнивать. Авторы строят
**граф-теоретический формализм** (process-enablement graphs), чтобы это делать.
**Что даёт нам.** **Главное для третьего потолка:** замыкание перестаёт быть философским термином и становится
**свойством графа** — значит его можно **посчитать** на нашей модели: узлы — процессы/части, рёбра — «обеспечивает».
По полному тексту: замыкание (`Definition 3.2`) — у **каждого** процесса есть хотя бы одна входящая и одна
исходящая прямая связь (`q → p → r`); **строго** замкнутый граф равносилен одному циклу (`Theorem 3.4`);
циклы объявлены «строительными блоками» замыкания, а гомоморфизмы требуется «сохраняющие циклы».
**Что меняет.** `Q-028` и третий потолок: кандидат на **операциональный критерий**. **Поправка по полному
тексту:** их условие **слабее** сильной связности (достаточно in/out-степени ≥ 1) и **не** равно доле в
наибольшей SCC; строгая версия — ровно цикл. То есть `GAP-01` остаётся разрывом, но формулируется по теореме,
а не по догадке (`F-022`).

---

### L-061 · Формальное условие замыкания ограничений (цитата)

```json
{
 "L": "L-061",
 "locator": {
  "doi": "10.4324/9781003528937-24",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pubmed.ncbi.nlm.nih.gov/25752259/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://pubmed.ncbi.nlm.nih.gov/25752259/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Biological Autonomy",
  "year": 2015,
  "first_author": "глава Routledge"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** Montévil & Mossio (2015), JTB 372:179–191; Moreno & Mossio (2015) «Biological Autonomy»; глава Routledge
(2024), doi:10.4324/9781003528937-24; CASP concept view.
**Ссылка.** https://pubmed.ncbi.nlm.nih.gov/25752259/ ; https://doi.org/10.4324/9781003528937-24 ;
https://www.biologicalpurpose.org/conceptual/o
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитаты из фрагментов).** «We characterize biological organization as a **closure of constraints**, where
constraints are defined at a given time scale and are **interdependent**». «A set of constraints C realizes closure if,
**for each constraint C…**». «In a system exhibiting organizational closure, **each constraint will depend directly on
at least one other**…».
**Что даёт нам.** Это **условие на граф**, а не метафора: у каждого ограничения есть хотя бы одна зависимость внутрь
множества. Плюс различение **процессов** и **ограничений** — у нас его нет, и, возможно, отсюда наша «связь частей без
разделения».
**Что меняет.** `§4.10`: наша связь частей — это **зависимость**, а не **ограничение**; различение ввести в термины.

---

### L-062 · Двойственные переменные LP — это **химические потенциалы**

```json
{
 "L": "L-062",
 "locator": {
  "doi": "10.1103/PhysRevLett.99.108101",
  "arxiv": "q-bio/0702021",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1103/PhysRevLett.99.108101",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1103/PhysRevLett.99.108101"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Duality, Thermodynamics, and the Linear Programming Problem in Constraint-Based Models of Metabolism",
  "year": 2007,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Duality, Thermodynamics, and the Linear Programming Problem in Constraint-Based Models of Metabolism» (2007),
Phys. Rev. Lett. 99:108101, doi:10.1103/PhysRevLett.99.108101; препринт arXiv:q-bio/0702021.
**Ссылка.** https://doi.org/10.1103/PhysRevLett.99.108101
**Проверено.** **аннотация.**
**Утверждение (цитата).** «the dual to the linear programming problem that arises in constraint-based models of
metabolism can be given a **thermodynamic interpretation** in which the **shadow prices are chemical potential
analogues**, and the objective is to minimise free energy consumption given a free energy drain».
**Что даёт нам.** **Наша «цена кожи» получает физический смысл:** двойственная переменная ограничения — это не
бухгалтерия, а **аналог химического потенциала**. Это соединяет `B` (бюджет) с `C` (организация) и с термодинамикой.
**Что меняет.** `§4.7`/§4.10: «цена удержания» — **двойственная цена**, а не постулат; и у неё должна быть
**размерность потенциала**, а не «единиц вещества».

---

### L-063 · COT как **структурная** рамка, независимая от кинетики

```json
{
 "L": "L-063",
 "locator": {
  "doi": "10.46793/match.96-3.03426",
  "arxiv": "q-bio/0501016",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/pdf/q-bio/0501016",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "arxiv",
  "via_detail": "https://arxiv.org/pdf/q-bio/0501016"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "COT как **структурная** рамка, независимая от кинетики",
  "year": 2005,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Dittrich & Speroni di Fenizio (2005), arXiv:q-bio/0501016; «Chemical Organization Theory: A Structural
Framework for Analyzing Reaction Networks» (2026), doi:10.46793/match.96-3.03426.
**Ссылка.** https://arxiv.org/pdf/q-bio/0501016 ; https://doi.org/10.46793/match.96-3.03426
**Проверено.** **аннотация.**
**Утверждение (пересказ).** COT даёт **структурную и алгебраическую** рамку: организации — **замкнутые и
самоподдерживающиеся** множества видов; выводы не зависят от кинетических допущений.
**Что даёт нам.** Организацию можно **вычислить** из стехиометрии, без динамики — то есть третий потолок можно
проверить **комбинаторно**, до всякого прогона.
**Что меняет.** `Q-028`: брать как **вычислимый** критерий; ожидать решётку организаций, а не одну.

---

### L-064 · Инвариант из стехиометрии и цена предположения о стационарности

```json
{
 "L": "L-064",
 "locator": {
  "doi": "10.1371/journal.pcbi.1003195",
  "arxiv": "0808.0321",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/abs/0808.0321",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "arxiv",
  "via_detail": "https://arxiv.org/abs/0808.0321"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Flux networks in metabolic graphs",
  "year": 2008,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Flux networks in metabolic graphs» (2008), arXiv:0808.0321; «Flux Imbalance Analysis and the Sensitivity of
Cellular Growth to Changes in Metabolite Pools» (2013), PLOS Comput Biol, doi:10.1371/journal.pcbi.1003195.
**Ссылка.** https://arxiv.org/abs/0808.0321 ; https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003195
**Проверено.** **аннотация.**
**Утверждение (пересказ).** (1) Консервативные потоки можно назначить рёбрам графа, комбинируя потоки с **консервативным
свойством** метаболита (например, молекулярной массой) — то есть инвариант строится из **левого ядра** стехиометрии.
(2) Классический FBA предполагает **стационарность** внутренних метаболитов; отказ от этого предположения меняет
предсказания роста.
**Что даёт нам.** Прямой рецепт нашего `T-4` (инвариант вещества): **левое ядро** матрицы стехиометрии, а не
«договорились, что сумма сохраняется». И предупреждение: наша модель как раз **не** стационарна, поэтому FBA-оценки
переносить нельзя.
**Что меняет.** `DESIGN-LEAN-SYNTHESIS.md` T-4: формулировать через левое ядро.

---

### L-065 · Ядро выживания: определение и **алгоритм**

```json
{
 "L": "L-065",
 "locator": {
  "doi": "10.1137/0328044",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1137/0328044",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1137/0328044"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Viability Theory",
  "year": 1991,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** Aubin (1991) «Viability Theory»; «A Survey of Viability Theory» (1990), SIAM J. Control, doi:10.1137/0328044;
«Viability kernel computation based on interval methods» (2015); «Interval Based Parallel Computing of the Viability
Kernel» (2016).
**Ссылка.** https://doi.org/10.1137/0328044 ; https://kam.mff.cuni.cz/conferences/swim2015/abstracts/monnet.pdf
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитата из фрагмента).** «The subset of evolutions viable in K is denoted by `V(K) := {x(·) | ∀t ≥ 0,
x(t) ∈ K}`»; `x₀` **viable** in `K` если возможно **оставаться в `K` бесконечно долго**; численно ядро
приближается **итерациями** (дискретные и интервальные методы).
**Что даёт нам.** `q_min` — мгновенное ограничение; **ядро выживания** — это множество состояний, из которых можно
**остаться внутри навсегда**. Наша «полоса допуска» может оказаться **проекцией** ядра.
**Что меняет.** `§4.13`: переформулировать «допуск» как **проекцию ядра выживания** — это даёт формальное определение
вместо описания.

---

### L-066 · Пространство выживания: граница как **геометрическая** величина

```json
{
 "L": "L-066",
 "locator": {
  "doi": null,
  "arxiv": "2605.16753",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://arxiv.org/html/2605.16753",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "arxiv",
  "via_detail": "https://arxiv.org/html/2605.16753"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Viability Space Decomposition: A geometric partition of survival outcomes in single- and multi-agent systems",
  "year": null,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Viability Space Decomposition: A geometric partition of survival outcomes in single- and multi-agent systems»
(arXiv:2605.16753).
**Ссылка.** https://arxiv.org/html/2605.16753
**Проверено.** **аннотация** (полный текст не открылся — SSRF, см. `LITERATURE-GAPS.md` G-002).
**Утверждение (пересказ аннотации).** В **viability space** набор ограничений создаёт **границу выживания**
`∂V_α`, отделяющую область, где агент может существовать, от дополнения, где «жизнь невозможна».
**Что даёт нам.** Это буквально наша картина: **полоса** — область в пространстве параметров, где система живёт
неограниченно долго, а её **границы** — поверхность. И это даёт **язык**: не «оптимум 0.75», а **область** `V_α` и
её **граница**.
**Что меняет.** `POSITIVE.md` §4.13: заменить «оптимум — плато» на «**область выживания** с границей»; ширина
области — измеряемая величина (у нас 3–10 %).

---

### L-067 · ITI: индивидуальность как **сохраняемая временная целостность**

```json
{
 "L": "L-067",
 "locator": {
  "doi": "10.1007/s12064-020-00313-7",
  "arxiv": "1412.2447",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://link.springer.com/article/10.1007/s12064-020-00313-7",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://link.springer.com/article/10.1007/s12064-020-00313-7"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "The information theory of individuality",
  "year": 2020,
  "first_author": "Theory in Biosciences"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Krakauer, Flack & Bertschinger (2020), «The information theory of individuality», Theory in Biosciences,
doi:10.1007/s12064-020-00313-7; препринт arXiv:1412.2447; обзор SFI (2020).
**Ссылка.** https://link.springer.com/article/10.1007/s12064-020-00313-7 ; https://arxiv.org/abs/1412.2447
**Проверено.** **аннотация** (PMC-версия не открылась: SSRF).
**Утверждение (цитаты).** «There is little agreement about what individuals are and **few rigorous quantitative
methods** for their identification. Here, we propose that individuals are aggregates that **preserve a measure of
temporal integrity**, i.e., “propagate” in time». И: индивидуальность **непрерывна, а не бинарна, вложена, возможна на
любом уровне**; метод **алгоритмически выделяет** границы система–среда, а не предполагает их.
**Что даёт нам.** Готовый **операциональный** способ измерить слона по **временному ряду**, не зная, какая переменная
«кожа». Это закрывает пробел из `ELEPHANT-MAP` §2 («количественной меры участия нет нигде») хотя бы для одной части.
**Что меняет.** `Q-018`: появляется внешняя мера; `ELEPHANT-MAP` часть 9 — не «не измеряли», а «есть формула, не
применяли».

---

### L-068 · Информационная индивидуальность **требует причинности**, а не корреляции

```json
{
 "L": "L-068",
 "locator": {
  "doi": "10.1007/s13194-023-00566-1",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://link.springer.com/article/10.1007/s13194-023-00566-1",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://link.springer.com/article/10.1007/s13194-023-00566-1"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Adding causality to the information-theoretic perspective on individuality",
  "year": 2024,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Adding causality to the information-theoretic perspective on individuality» (2024), European Journal for
Philosophy of Science, doi:10.1007/s13194-023-00566-1.
**Ссылка.** https://link.springer.com/article/10.1007/s13194-023-00566-1
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Информационные меры индивидуальности, основанные на взаимной информации, дают **корреляцию**,
а не причинность; автор применяет **интервенционистские** меры причинности к индивидуальности.
**Что даёт нам.** Важное: ITI без интервенций может завышать индивидуальность. **Но наша модель — симулятор**, значит
интервенции (выключить часть, обнулить поток) у нас **есть**. Это преимущество, которого нет у полевых данных.
**Что меняет.** `P-009`: применять ITI **вместе** с интервенциями (нок-аут части), а не только на траекториях.

---

### L-069 · ΦID: разложение информационной динамики на шесть режимов

```json
{
 "L": "L-069",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12501198/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12501198/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Toward a unified taxonomy of information dynamics via Integrated Information Decomposition",
  "year": 2025,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Toward a unified taxonomy of information dynamics via Integrated Information Decomposition» (2025),
PMC12501198.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC12501198/
**Проверено.** **аннотация.**
**Утверждение (пересказ).** ΦID даёт **таксономию** информационной динамики: storage, transfer, copy и др. — шесть
качественно разных режимов; каждый выражается в решётке слагаемых.
**Что даёт нам.** Язык, чтобы отличить «память» от «передачи» и «копирования» — то, что у нас смешано в линии
восприятия/памяти.
**Что меняет.** `§3` линии памяти: назвать режимы по ΦID; не называть памятью то, что является переносом.

---

### L-070 · Приближение Тулджапурака: цена дисперсии — **число**

```json
{
 "L": "L-070",
 "locator": {
  "doi": "10.1016/j.tree.2020.02.004",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.sciencedirect.com/science/article/pii/S0169534720300501",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.sciencedirect.com/science/article/pii/S0169534720300501"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "The Demographic Buffering Hypothesis: Evidence and Challenges",
  "year": 1990,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** Tuljapurkar (1990, 2010); «The Demographic Buffering Hypothesis: Evidence and Challenges» (2020), TREE,
doi:10.1016/j.tree.2020.02.004; «Environmental variance, population growth and evolution» (2010), J. Anim. Ecol.,
doi:10.1111/j.1365-2656.2009.01619.x.
**Ссылка.** https://www.sciencedirect.com/science/article/pii/S0169534720300501 ;
https://besjournals.onlinelibrary.wiley.com/doi/10.1111/j.1365-2656.2009.01619.x
**Проверено.** **аннотация/фрагмент.**
**Утверждение (пересказ).** При **малой вариации** и **отсутствии временной автокорреляции** долгосрочная стохастическая
скорость роста большой популяции приближается как `log λ_s ≈ log λ̄ − σ²/(2λ̄²)`.
**Что даёт нам.** Это **цена страховки в числах**, и её можно **предсказать до прогона** (`F-016`). Плюс гипотеза
демографического буферирования: отбор снижает чувствительность к изменчивости **самых важных** параметров.
**Что меняет.** `P-010`: измерить `log λ_s` для наших стратегий и сравнить с приближением.

---

### L-071 · Диверсификация стоит дорого, и её темп — не универсален

```json
{
 "L": "L-071",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4312886/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4312886/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Courting disaster: How diversification rate affects fitness under risk",
  "year": 2014,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Courting disaster: How diversification rate affects fitness under risk» (2014), PMC4312886.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC4312886/
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Bet-hedging через диверсификацию фенотипов; **темп диверсификации** меняется на порядки,
и выигрыш зависит от характеристик риска и организации.
**Что даёт нам.** Предупреждение: «полоса» не обязана быть одинаковой при разных **темпах** и **масштабах** риска —
значит и у нас ширина полосы должна зависеть от частоты катастроф (у нас она зависела, `FINDING-314`).
**Что меняет.** `FINDING-314`: назвать это согласием с литературой, а не отдельным выводом.

---

### L-072 · Зерно среды и число решений решают, **какой** bet-hedging работает

```json
{
 "L": "L-072",
 "locator": {
  "doi": "10.1098/rspb.2019.2070",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://royalsocietypublishing.org/doi/abs/10.1098/rspb.2019.2070",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://royalsocietypublishing.org/doi/abs/10.1098/rspb.2019.2070"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Bet-hedging across generations can affect the evolution of variance-sensitive strategies within generations",
  "year": 2019,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Bet-hedging across generations can affect the evolution of variance-sensitive strategies within generations»
(2019), Proc. R. Soc. B 286:20192070, doi:10.1098/rspb.2019.2070.
**Ссылка.** https://royalsocietypublishing.org/doi/abs/10.1098/rspb.2019.2070
**Проверено.** **аннотация.**
**Утверждение (пересказ).** **Мультипликативное** накопление приспособленности (крупное зерно среды, мало независимых
решений) благоприятствует **консервативному** bet-hedging; **аддитивное** (много независимых решений) — стратегиям,
чувствительным к дисперсии **внутри** поколения.
**Что даёт нам.** Это и есть **критерий различения**, которого не хватало `Q-019`: не «арифметика или геометрия», а
**зерно среды и число независимых решений**.
**Что меняет.** `Q-019`: дизайн эксперимента — общая катастрофа (крупное зерно) против идиосинкратической (мелкое
зерно) при **одинаковом среднем**.

---

### L-073 · Рост мембраны протоклетки: **скорость зависит от внешнего липида**

```json
{
 "L": "L-073",
 "locator": {
  "doi": "10.3390/life15050724",
  "arxiv": "1901.04406",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.mdpi.com/2075-1729/15/5/724",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.mdpi.com/2075-1729/15/5/724"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Protocell Dynamics: Modelling Growth and Division of Lipid Vesicles Driven by an Autocatalytic Reaction",
  "year": 2025,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Protocell Dynamics: Modelling Growth and Division of Lipid Vesicles Driven by an Autocatalytic Reaction»
(2025), Life 15(5):724, doi:10.3390/life15050724; «Dynamics of growth and form in prebiotic vesicles» (2019),
arXiv:1901.04406.
**Ссылка.** https://www.mdpi.com/2075-1729/15/5/724 ; https://arxiv.org/pdf/1901.04406
**Проверено.** **аннотация.**
**Утверждение (цитаты).** «The autocatalytic reaction drives volume growth **via osmosis**. Membrane area grows due to
addition of lipids from the environment. **The membrane growth rate depends on the external** [lipid]». В препринте:
динамика определяется **встраиванием амфифилов**, **потоком жидкости через мембрану** и **упругими деформациями**.
**Что даёт нам.** Это **цена границы в их языке**: рост площади лимитирован **внешним** липидом, а не внутренней
починкой. Наш `c·d·q_min` — цена **удержания** целости, их — цена **наращивания** площади. Разные величины, и это надо
различать.
**Что меняет.** `§4.7`: противопоставить «цена удержания» и «цена роста»; первая — наша.

---

### L-074 · Проницаемость как **движущая сила отбора**

```json
{
 "L": "L-074",
 "locator": {
  "doi": "10.1038/s41598-017-02799-6",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.nature.com/articles/s41598-017-02799-6",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.nature.com/articles/s41598-017-02799-6"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Permeability-driven selection in a semi-empirical protocell model: the roots of prebiotic systems evolution",
  "year": 2017,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Permeability-driven selection in a semi-empirical protocell model: the roots of prebiotic systems evolution»
(2017), Scientific Reports, doi:10.1038/s41598-017-02799-6.
**Ссылка.** https://www.nature.com/articles/s41598-017-02799-6
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Устойчивость везикулы зависит от **состава липидов**: есть **критическая концентрация
амфифила** для образования везикулы (`cvc`), и проницаемость связана с составом; отбор по проницаемости действует как
эволюционный фактор.
**Что даёт нам.** Наш `gate`/проницаемость — не свободный параметр: у него есть **физическая цена** и **порог**
(`cvc`). То есть проницаемость — компромисс: больше → больше питания, но меньше удержания.
**Что меняет.** `§4.10` (цена границы): добавить «проницаемость как компромисс», а не только «удержание».

---

### L-075 · Критерий «когда реакционная сеть — метаболизм», поддерживающий рост и деление

```json
{
 "L": "L-075",
 "locator": {
  "doi": "10.3390/life11090966",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.3390/life11090966",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.3390/life11090966"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Критерий «когда реакционная сеть — метаболизм», поддерживающий рост и деление",
  "year": 2021,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «When Is a Reaction Network a Metabolism? Criteria for Simple Metabolisms That Support Growth and Division of
Protocells» (2021), Life 11(9):966, doi:10.3390/life11090966.
**Ссылка.** https://doi.org/10.3390/life11090966
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Сформулированы **критерии**, при которых реакционная сеть является метаболизмом, способным
поддерживать **рост и деление** протоклетки; рост площади мембраны связан с синтезом липида.
**Что даёт нам.** Прямой конкурент нашему `F-022` (замыкание как граф): у них **критерий на сеть** с требованием роста
и деления. Сравнить: что у них требуется сверх замыкания (вероятно, **производство липида внутри**).
**Что меняет.** `Q-028`: сравнивать с этим критерием, а не с общим COT.

---

### L-076 · Эффект матрицы: размер потомков **наследуется** без генов

```json
{
 "L": "L-076",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://ncbi.nlm.nih.gov/pmc/articles/PMC2931742/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://ncbi.nlm.nih.gov/pmc/articles/PMC2931742/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Self-Reproduction of Fatty Acid Vesicles: A Combined Experimental and Simulation Study",
  "year": 2010,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Self-Reproduction of Fatty Acid Vesicles: A Combined Experimental and Simulation Study» (2010),
PMC2931742.
**Ссылка.** https://ncbi.nlm.nih.gov/pmc/articles/PMC2931742/
**Проверено.** **аннотация.**
**Утверждение (цитаты).** «the size distribution of the newly formed vesicles is strongly **biased toward that of the
seed vesicles**» — эффект **матрицы**.
**Что даёт нам.** Наследование **формы** (размера) без генетического носителя — аналог нашей линии «наследование
морфологии есть, но линия расходится» (§4.5). У них — **притяжение** к размеру затравки, у нас — дрейф.
**Что меняет.** §4.5: указать, что в эксперименте есть **стабилизация**, а у нас — дрейф; возможная причина — отсутствие
матричного механизма.

---

### L-077 · Прямая и обратная линия родства дают **разные средние**

```json
{
 "L": "L-077",
 "locator": {
  "doi": "10.3389/fphy.2018.00064",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2018.00064/full",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2018.00064/full"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Analysis of Cell Size Homeostasis at the Single-Cell and Population Level",
  "year": 2018,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «Analysis of Cell Size Homeostasis at the Single-Cell and Population Level» (2018), Frontiers in Physics,
doi:10.3389/fphy.2018.00064.
**Ссылка.** https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2018.00064/full
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитата).** «the mean cell size in a **forward lineage** is independent of the division error CV while it
**increases** with CV in **backward lineages**».
**Что даёт нам.** Это **методологическая ловушка**, ровно та же, что мы нашли у себя: измерять по траектории или по
случайной выборке — **разные средние**. У нас это была «калибровка на траектории против зондирующей выборки»
(`L-040`, `Q-012`).
**Что меняет.** `Q-012`: назвать это **forward/backward lineage bias** и явно указать, какую линию мы измеряем.

---

### L-078 · Adder: клетка добавляет **постоянную** величину, а не тянется к размеру

```json
{
 "L": "L-078",
 "locator": {
  "doi": "10.1038/s41540-024-00383-z",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5660915/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "pmc",
  "via_detail": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5660915/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "A mechanistic stochastic framework for regulating bacterial cell division",
  "year": 2016,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «A mechanistic stochastic framework for regulating bacterial cell division» (2016), PMC4960620; «Adder and a
coarse-grained approach to cell size homeostasis in bacteria» (2016), PMC5660915; «Mechanisms of cell size regulation in
slow-growing E. coli: discriminating models beyond the adder» (2024), npj Syst. Biol.,
doi:10.1038/s41540-024-00383-z.
**Ссылка.** https://pmc.ncbi.nlm.nih.gov/articles/PMC5660915/ ; https://www.nature.com/articles/s41540-024-00383-z
**Проверено.** **аннотация/фрагмент.**
**Утверждение (пересказ).** В устойчивом росте клетки добавляют между рождением и делением **почти постоянный**
размер, независимо от размера при рождении; механизм связывают с **числом стадий** и накоплением предшественников.
**Что даёт нам.** Adder — **третий механизм** рядом с нашим «сила ∝ ошибке» и «полоса»; и он **робастен** там, где
sizer накапливает ошибку.
**Что меняет.** `Q-013`: добавить adder как четвёртое плечо в сравнение распределений, а не только порогов.

---

### L-079 · Предсказание adder в числах: `CV² = ln 4 − 1`

```json
{
 "L": "L-079",
 "locator": {
  "doi": "10.31219/osf.io/ea6yx",
  "arxiv": "2411.08327",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.31219/osf.io/ea6yx",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.31219/osf.io/ea6yx"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Statistical properties of dynamical models underlying cell size homeostasis",
  "year": 2023,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «Statistical properties of dynamical models underlying cell size homeostasis» (2023),
doi:10.31219/osf.io/ea6yx; «Cell size distributions in lineages» (2024), arXiv:2411.08327.
**Ссылка.** https://doi.org/10.31219/osf.io/ea6yx ; https://arxiv.org/abs/2411.08327
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитаты).** При `β = 1/2` с вероятностью один «`CV²_s = log(4) − 1`»; в линиях измеряют
`CV_h ≈ 0.07–0.09` — «small amount of stochasticity at division».
**Что даёт нам.** **Готовое число для сверки:** `ln 4 − 1 = 0.386` — дисперсия, которую даёт чистый adder. Если наш
регулятор даёт другую — он **не** adder, и это измеримо.
**Что меняет.** `P-012`: сравнить с 0.386.

---

### L-080 · Нормальные формы трёх локальных бифуркаций

```json
{
 "L": "L-080",
 "locator": {
  "doi": "10.1142/S0218127417501450",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://ocw.mit.edu/courses/12-006j-nonlinear-dynamics-chaos-fall-2022/mit12_006jf22_lec2-3.pdf",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://ocw.mit.edu/courses/12-006j-nonlinear-dynamics-chaos-fall-2022/mit12_006jf22_lec2-3.pdf"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Нормальные формы трёх локальных бифуркаций",
  "year": 2017,
  "first_author": "MIT OCW"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** MIT OCW 12.006J, лекции 2–3; «KCC Analysis of the Normal Form of Typical Bifurcations in One-Dimensional
Dynamical Systems» (2017), Int. J. Bifurcation and Chaos, doi:10.1142/S0218127417501450.
**Ссылка.** https://ocw.mit.edu/courses/12-006j-nonlinear-dynamics-chaos-fall-2022/mit12_006jf22_lec2-3.pdf ;
https://doi.org/10.1142/S0218127417501450
**Проверено.** **аннотация/фрагмент** (лекция — полный конспект в фрагменте).
**Утверждение (цитаты).** «saddle-node: `ṅ = r + n²`; transcritical: `ṅ = rn − n²`; supercritical pitchfork:
`ṅ = rn − n³`». «The second term vanishes because… f(x) is tangent to the x-axis at `r = r_c`. Then
`ẋ = a(r − r_c) + b(x − x*)²`… Appropriate rescalings bring us back to `ẋ = r + x²`».
**Что даёт нам.** Точный **критерий**, чем наш случай **не** является: у нас нет касания и нет пары корней — значит
наша классификация «полюс, не бифуркация» (`FINDING-316`, `SYNTHESIS` §1.2) согласуется с каноном.
**Что меняет.** `Q-027`: закрыт терминологически; слова «складка/вилка» — только после проверки касания.

---

### L-081 · Классы универсальности и показатели для трёх бифуркаций

```json
{
 "L": "L-081",
 "locator": {
  "doi": "10.1016/j.cnsns.2016.04.008",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1016/j.cnsns.2016.04.008",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1016/j.cnsns.2016.04.008"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Defining universality classes for three different local bifurcations",
  "year": 2016,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Defining universality classes for three different local bifurcations» (2016), CNSNS,
doi:10.1016/j.cnsns.2016.04.008.
**Ссылка.** https://doi.org/10.1016/j.cnsns.2016.04.008
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Сходимость к неподвижной точке **у бифуркации и около неё** описывается скейлинг-формализмом
для трёх типов (складка, транскритическая, надкритическая вилка); у каждого свой набор показателей.
**Что даёт нам.** Показатель **не универсален по числу каналов** (`F-018`), он привязан к **типу** и порядку ведущего
члена. Это подтверждает опровержение нашего `1/(m+1)`.
**Что меняет.** `Q-026`: окончательно снят; в `QUESTIONS.md` формулировка «опровергнут контрпримером + литературой».

---

### L-082 · Несовершенная бифуркация: **шум сглаживает переход**

```json
{
 "L": "L-082",
 "locator": {
  "doi": "10.1002/cpa.3160320103",
  "arxiv": "2405.19947",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1002/cpa.3160320103",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1002/cpa.3160320103"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "A theory for imperfect bifurcation via singularity theory",
  "year": 1979,
  "first_author": "CPAM"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Golubitsky & Schaeffer (1979), «A theory for imperfect bifurcation via singularity theory», CPAM,
doi:10.1002/cpa.3160320103; «A Statistical Theory for Imperfect Bifurcation» (1982), SIAM J. Appl. Math.,
doi:10.1137/0142011; «Universal finite-time scaling in the transcritical, saddle-node, and pitchfork discrete and
continuous bifurcations» (2024), arXiv:2405.19947.
**Ссылка.** https://doi.org/10.1002/cpa.3160320103 ; https://arxiv.org/abs/2405.19947
**Проверено.** **аннотация.**
**Утверждение (пересказ).** У реальных систем есть **несовершенства** (шум, конечный размер, асимметрия); теория
несовершенных бифуркаций описывает, как они **сглаживают** переход. Для складки ширина переходной области растёт как
**`ε^(2/3)`** от величины несовершенства `ε` (классический результат), а не линейно.
**Что даёт нам.** Наш «порог» в конечной системе **не может** быть резким: шум и конечный `N` его размывают. Значит
**ширина размытия** — измеримая величина с **предсказанным показателем 2/3**.
**Что меняет.** `P-013`: измерить ширину перехода против амплитуды шума и проверить наклон в log-log.

---

### L-083 · Симуляция против реализации: что мы вправе утверждать

```json
{
 "L": "L-083",
 "locator": {
  "doi": "10.1162/106454600568375",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.13140/2.1.1871.8723",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.13140/2.1.1871.8723"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Simulations, Realizations, and Theories of Life",
  "year": 1987,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** Bedau (1987), «Simulations, Realizations, and Theories of Life»; «Artificial life: Discipline or method?»
(2000), doi:10.1162/106454600568375; «Simulation and Artificial Life» (2017), Springer.
**Ссылка.** https://doi.org/10.13140/2.1.1871.8723 ; https://doi.org/10.1162/106454600568375
**Проверено.** **аннотация/фрагмент.**
**Утверждение (пересказ).** Различаются **симуляция** (модель, описывающая жизнь) и **реализация** (система, которая
ею **является**). Главная методологическая трудность ALife — «**связать результаты симуляции с системой, которую
симулируют**».
**Что даёт нам.** Название для нашей дисциплины: мы делаем **симуляцию** и **не** заявляем реализацию. Значит все наши
утверждения — **о модели**, и это не скромность, а корректность.
**Что меняет.** `000-why.md`: добавить различение «симуляция/реализация» одной строкой.

---

### L-084 · Как **мерить** открытость: набор метрик и его критика

```json
{
 "L": "L-084",
 "locator": {
  "doi": null,
  "arxiv": "2006.03079",
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "http://workshops.alife.org/oee4/papers/stepney-oee4-camera-ready.pdf",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "http://workshops.alife.org/oee4/papers/stepney-oee4-camera-ready.pdf"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Modelling and measuring open-endedness",
  "year": 2019,
  "first_author": "OEE"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** Stepney, «Modelling and measuring open-endedness» (OEE4); «The MODES Toolbox: Measurements of Open-Ended
Dynamics in Evolving Systems» (2019), Artificial Life 25(1):50;
«The Importance of Open-Endedness (for the Sake of Open-Endedness)» (2020), arXiv:2006.03079.
**Ссылка.** http://workshops.alife.org/oee4/papers/stepney-oee4-camera-ready.pdf ;
https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox ;
https://arxiv.org/abs/2006.03079
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Открытость меряют **Levenshtein**, **энтропией Шеннона**, **колмогоровской сложностью** и
набором специальных метрик (MODES); единого определения нет, есть **спор**: открытость или сложность решений важнее
(Hintze).
**Что даёт нам.** Если мы захотим утверждать «модель открыта/не открыта», у нас есть **набор инструментов** и
предупреждение, что это **спорная** величина. Пока мы этого не утверждаем — и правильно.
**Что меняет.** `008-where-next.md`: если появится линия открытости — начинать с MODES, а не с определения.

---

### L-085 · Оценка открытости **субъективна**, и это признано

```json
{
 "L": "L-085",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "http://workshops.alife.org/oee2/abstracts/stanley-soros-oee2-submission.pdf",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "http://workshops.alife.org/oee2/abstracts/stanley-soros-oee2-submission.pdf"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "The Role of Subjectivity in the Evaluation of Open-Endedness",
  "year": null,
  "first_author": "OEE"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «The Role of Subjectivity in the Evaluation of Open-Endedness» (OEE2).
**Ссылка.** http://workshops.alife.org/oee2/abstracts/stanley-soros-oee2-submission.pdf
**Проверено.** **аннотация.**
**Утверждение (пересказ).** Определение открытости «удивительно трудно зафиксировать»; часть трудности — в том, что
**оценка** зависит от наблюдателя.
**Что даёт нам.** Прямое подтверждение нашей практики: **предрегистрация** и **число** вместо оценки. Если мера
субъективна, единственный выход — записать метрику и предсказание **до** прогона.
**Что меняет.** `WORK-LOOPS.md` §10 и `PREDICTIONS.md`: это не формальность, а ответ на известную проблему.

---

### L-086 · Ограничение выживания **выводится** из графа процессов — и это уже сделано

```json
{
 "L": "L-086",
 "locator": {
  "doi": "10.1162/isal_a_00739",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://doi.org/10.1162/isal_a_00739",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://doi.org/10.1162/isal_a_00739"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Deriving The Intrinsic Viability Constraint of an Emergent Individual from First Principles",
  "year": 2024,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** «Deriving The Intrinsic Viability Constraint of an Emergent Individual from First Principles» (2024),
ALIFE, doi:10.1162/isal_a_00739.
**Ссылка.** https://doi.org/10.1162/isal_a_00739
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитаты).** Граф включает «a total of **352 processes and 5 912 dependency links**»; «the same process may
appear multiple times but still have distinct identities because their dependencies differ». Работа **выводит
внутреннее ограничение выживания** (intrinsic viability constraint) индивида из первых принципов.
**Что даёт нам.** **Огромное:** направление 5.1 из `ZOOM-OUT-2` (совместимость ядра выживания и замыкания) **уже
занято**. Причём в масштабе, до которого мы не дотягиваем (352 процесса против наших ~10 частей).
**Что меняет.** `ZOOM-OUT-2` §5.1: переписать как «сверить», а не «сделать первыми». Наш шанс — **не** вывод
ограничения, а **измерение цены** этого ограничения (`F-023`).

---

### L-087 · Теория выживания на границе жизнь–смерть: заявка на недостающее

```json
{
 "L": "L-087",
 "locator": {
  "doi": "10.1038/s41540-026-00718-y",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://www.nature.com/articles/s41540-026-00718-y",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://www.nature.com/articles/s41540-026-00718-y"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Matters of life and death in computational cell biology",
  "year": 2026,
  "first_author": null
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": null
}
```



**Кто.** «Matters of life and death in computational cell biology» (2026), npj Systems Biology and Applications,
doi:10.1038/s41540-026-00718-y.
**Ссылка.** https://www.nature.com/articles/s41540-026-00718-y
**Проверено.** **аннотация.**
**Утверждение (пересказ).** «Many cell models deal with constraints for life's persistence, yet we lack **principles**
for how dynamics interact with them… **Computational biology needs a theory of viability** that confronts the life–death
boundary».
**Что даёт нам.** Прямое подтверждение, что **общая теория** пока не построена: модели есть, **принципов** нет. Это
наша ниша — не «ещё модель», а **свод принципов** с числами.
**Что меняет.** `ZOOM-OUT-2` §5.1: формулировка «свод принципов» вместо «теорема о совместимости».

---

### L-088 · Viability ≠ survival: различение, которого нам не хватало

```json
{
 "L": "L-088",
 "locator": {
  "doi": null,
  "arxiv": null,
  "arxiv_version": null,
  "openalex": null,
  "pmid": null,
  "url": "https://apsframework.org/articles/viability-the-organising-principle-of-biological-persistence/",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": null,
  "via": "publisher",
  "via_detail": "https://apsframework.org/articles/viability-the-organising-principle-of-biological-persistence/"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Viability — The Organising Principle of Biological Persistence",
  "year": 2010,
  "first_author": "Constraint — How"
 },
 "legacy": true,
 "legacy_reason": "запись написана до контракта 2026-11-21",
 "downgrade_reason": "копии текста нет в papers/"
}
```



**Кто.** APS Publishing Platform: «Viability — The Organising Principle of Biological Persistence»; «Constraint — How
Organisation Becomes Persistence»; «Constraint Closure — What It Does and What It Does Not Do».
**Ссылка.** https://apsframework.org/articles/viability-the-organising-principle-of-biological-persistence/ ;
https://apsframework.org/articles/constraint-how-organisation-becomes-persistence/
**Проверено.** **аннотация/фрагмент.**
**Утверждение (цитаты).** «**Survival** describes an **outcome** — the continued existence of a system — whereas
**viability** concerns the **organisational conditions** under which continued functioning remains possible». «Constraint
closure occurs when constraints form **networks of mutual dependence**».
**Что даёт нам.** Чистое различение, которого у нас не было: наша «жизнь» — это **outcome** (сколько шагов), а
«выживание» в их смысле — **условия** (набор состояний). Это ровно `F-024` (ядро) против нашей метрики шагов.
**Что меняет.** `POSITIVE.md`: развести «продолжительность» и «условия продолжения»; первое — измерено, второе —
вычислимо.

---

---

## B. Банк формул

Все формулы записаны **в наших символах**; столбец «как у них» — их обозначения, если известны.

### F-001 · Кумулятивная опасность и жизнь
**Линии.** smert

```
H(T) = ∫₀ᵀ μ(t) dt          смерть наступает при H(T) = 1   (63.2-й перцентиль, НЕ средняя)
μ(t) = μ₀ + λδt             при линейном росте повреждения
⇒ μ₀T + (λδ/2)T² = 1        наше уравнение жизни (FINDING-297)
средняя E[T] = ∫₀^∞ exp(−H(t)) dt
```
**Откуда.** надёжностная рамка: L-001, L-010.
**Что важно.** Форма распределения — **Вейбулл с k = 2 (Рэлей)** в пределе `μ₀ → 0`; при `μ₀ > 0` — не чистый Вейбулл.
**Наши числа.** `T(H=1)` = 348 / 261 / 129; **средние** = 332.7 / 253.8 / 127.8; измерено 339 / 258 / 128.

### F-002 · Порог доли удержания
**Линии.** porog

```
Dₙ₊₁ = h·Dₙ + δ·T          рекуррентность повреждения по поколениям
D* = δ·T / (1 − h)         конечное плато при h < 1
h ≥ 1                      плато нет (рост)
```
**Откуда.** L-005 (Chao 2010), L-014.
**Наши числа.** плато 2.02 / 3.28 / 5.80 / 8.68 для `h` = 0.90 / 0.95 / 0.98 / 0.99.

**Поправка 25.11.2026.** Эти числа — **не плато и не воспроизводимы**. Поиск по репозиторию не нашёл
ни скрипта, ни прогона, из которых они получены (единственное вхождение — эта строка). Проверка по
формуле: если бы это были неподвижные точки `δ·T/(1−h)`, произведение `δ·T` было бы общим, а оно
падает в 2,3 раза (0,202 / 0,164 / 0,116 / 0,0868). При `δ·T = 0,2` записанные значения совпадают с
`D_n = δ·T·(1 − h^n)/(1 − h)` при `n ≈ 33 / 43 / 57`, то есть это **снимки на конечном горизонте**.
Настоящие пределы при `δ·T = 0,2`: **2 / 4 / 10 / 20**. Горизонт в исходной записи не указан, поэтому
числа нельзя повторить; пользоваться следует пределами, а если нужен снимок — указывать `n` и `δ·T`.
Подробный разбор: `docs/UNITS-AUDIT.md` §4, `docs/FINDING-343.md`.

### F-003 · Самоограничение повреждения (корневой закон)
**Линии.** porog

```
λ·D² + μ₀·D = δ/(1 − h)                 равновесие: рост = смертность
D* = ( −μ₀ + √(μ₀² + 4λδ/(1−h)) ) / (2λ)
режимы:  h < 1 − δ/(μ₀D):  D* ≈ δ/(μ₀(1−h))      ЛИНЕЙНЫЙ
         иначе:            D* ≈ √( δ/(λ(1−h)) )   КОРНЕВОЙ  (показатель −1/2)
```
**Откуда.** наше (`FINDING-308`, `309`); в литературе формы не встречено (L-005, L-009 — проверить).
**Наши числа.** проверено на семи точках, ≤3 %; корневой режим — только с `h ≥ 0.97`.

### F-004 · Цена поддержания и замыкание
**Линии.** obmen

```
приход = c_y·σ·p·f̄            доход формы
расход = f₀ + μ·n + κ·n²/p     поддержание + починка + издержки
жива ⟺ приход ≥ расход
```
**Откуда.** L-012 (DEB), L-013 (Pirt).
**Наше.** §4.4 и §4.10 — та же схема с геометрией.

**Интерпретация (25.11.2026).** `n` — масса (г), `p` — безразмерная доля; иначе уравнение допускает
второе прочтение (`n` — число особей в шт), где `μ` и `κ` имеют другие единицы. Разбор и таблица двух
вариантов: `docs/UNITS-AUDIT.md` §5.

### F-005 · Доля ресурса в поддержание (правило κ)
**Линии.** obmen

```
энергия = κ·E   на поддержание сомы
        + (1−κ)·E  на рост и размножение
```
**Откуда.** L-012.
**Наше.** `income − maintenance` против `Σ u_i·cost_i` — та же схема без роста.


### F-006 · Складка Chao и её универсальный масштаб
**Линии.** porog

```
порог:            Πλ = 1/6            (Π — время повреждения, λ — темп)
асимметрия a:     сдвигает порог в [1/6, 1/2]
при h → h_c:      D*  конечно
                  dD*/dh ~ (h_c − h)^(−1/2)
                  T_senescence ~ (h_c − h)^(−1/2)
                  N(ε)·√ε → 1.706
```
**Откуда.** L-023 (реконструкция Chao 2010 по обзору).
**Что это значит для нас.** `√` — **не наше**: это универсальный масштаб складки (saddle-node, интермиттентность
I типа). Наш вклад может быть только в **типе перехода** (L-024).

### F-007 · Порог ошибок
**Линии.** proshloe

```
σ · q^ν = 1        граница удержания информации (общая форма по ревью)
L_max ≈ ln(σ) / (1 − q)        классическая оценка
```
**Откуда.** L-029.
**Наше.** `h = 1` **не** равно этому порогу; нужен перевод переменных (Q-024).

### F-008 · Viability kernel
**Линии.** vybor

```
Viab(K) = { x₀ ∈ K : ∃ траектория x(·), x(0) = x₀, x(t) ∈ K ∀t ≥ 0 }
```
**Откуда.** L-028.
**Наше.** `q_min` — проекция этого множества на ось `q`, а не само множество.

### F-009 · Замыкание ограничений (структурное)
**Линии.** svoi-usloviya
**Единицы.** вершины и степени — штуки; мера замыкания — доля вершин в наибольшей SCC, безразмерная (0…1).
**Проверка.** `EXP-CLOSURE-MEASURE` (`FINDING-319`): цепочка 0.25, частичный цикл 0.75, замкнутый цикл 1.0.

```
для каждого ограничения Cᵢ:  ∃ j ≠ i : Cᵢ зависит от Cⱼ
                             ∃ k ≠ i : Cₖ зависит от Cᵢ
```
**Откуда.** L-025.
**Наше.** §4.10 («части зависят друг от друга») — это условие **в графе**, а не неравенство в бюджете.

### F-010 · RAF
**Линии.** organizaciya

```
R' ⊆ R  есть RAF, если
  ∀ r ∈ R': катализатор r ∈ (молекулы, порождённые R' из food set F)
  все реагенты r строятся из F
```
**Откуда.** L-027.
**Наше.** Ни один из наших механизмов пока не проверен на это условие.

### F-011 · Ниша и её изменение
**Линии.** svoi-usloviya

```
ΔR = R_original − R_modified          эко-подпись (ecosystem signature)
НАБРОСОК, А НЕ ФОРМУЛА: R не определена (вектор откликов? набор признаков? индекс?), опоры в карте
нет (0 из 1125 ячеек), единицы «1» верны только для безразмерной R. Проверено и записано:
FORMULA-NICHE.md. До определения R формулу нельзя ни посчитать, ни опровергнуть.
```
**Откуда.** L-034.
**Наше.** `spent = 0` — вырожденный случай `ΔR = 0` при полном самообеспечении.

### F-012 · Многоуровневый отбор (Прайс)
**Линии.** organizaciya

```
Δz̄ = Cov(w, z)/w̄ + E[w·Δz]/w̄
```
**Откуда.** L-031 (Queller & Strassmann).
**Наше.** Пока не используется; нужен, если появится организация с разделением.

### F-013 · Цепь рождения–смерти и «честная вероятность» как медиана
**Линии.** individualnost

```
π(i) = π(0) · Π_{j<i} p_j / Π_{j≤i} q_j          стационарное распределение
±1 шаг, ρ = p/q < 1, стенка снизу:  π(n) = (1−ρ)ρⁿ
медиана m  ⇒  ρ ≈ 2^(−1/(m+1)),   p* = ρ/(1+ρ)

m = 4/10/16  →  p* = 0.4654 / 0.4843 / 0.4898
время релаксации ~ (√q − √p)^(−2) ≈ 5·10³ шагов при p ≈ 0.49
```
**Откуда.** `L-049`, `L-013`; внешний разбор 2026-11-20.
**Предсказание до прогона:** измеренная `p*` **зависит от `N`**; если поколений меньше релаксации — мерим транзиент.

### F-014 · Порог полосы без возвращающей силы
**Линии.** vybor, porog

```
δ_c ≈ σ_g · √(2 ln N)
σ_g ≈ 0.1, N ≈ 10³  →  δ_c ≈ 0.37   (середина нашего окна 0.2…0.5)
```
**Откуда.** `L-041`. **Различитель:** зависимость `δ_c` от `N`.
**Проверка различителя — провалена (2026-11-24, `FINDING-339`).** Измеренная нейтральная точка мутации
`p_grow*` (`FINDING-221`, 0.27) при смене числа мутаций `N` от 200 до 20 000 **не выросла**, как требовала
бы формула (предсказание +0.120), а **упала** на −0.028: 0.269 / 0.268 / 0.267 / 0.246 / 0.241.
Значит `p_grow*` — не `δ_c`: это точка баланса роста и удаления. Сама формула в своей области не проверена
и остаётся `hypothesis`.

### F-015 · Sizer / adder / timer
**Линии.** individualnost

```
s_d = a·s_b + b        a = 0 (sizer), 1 (adder), 2 (timer)
s_b' = (a/2)·s_b + b/2
устойчивость распределения  ⟺  |a| < 2
стационарная дисперсия      =  σ²/(1 − (a/2)²)
```
**Откуда.** `L-041`.

### F-016 · Цена страховки (Тулджапурак)
**Линии.** vybor

```
log λ_s ≈ log λ̄ − σ²/(2λ̄²)
```
**Откуда.** `L-038`. **Предрегистрируемое число** для Q-019.

### F-017 · Порог ошибок Эйгена
**Линии.** proshloe

```
σ·q^ν > 1        граница;   μ_c = ln σ / ν
```
**Откуда.** `L-048`. **Не равно** нашему `h = 1`.

### F-018 · Показатель и порядок нелинейности
**Линии.** porog

```
ε = a·x^k  ⇒  x ~ ε^(1/k)     показатель = 1/(порядок ведущего члена)
два линейных канала:  ε = (a+b)x  ⇒  показатель 1  (НЕ 1/2)
два квадратичных:     ε = (Σb)x²  ⇒  показатель 1/2
```
**Откуда.** `L-050`-контекст, внешний разбор; **опровергает** нашу гипотезу `1/(m+1)`.

### F-019 · Критерий равновесия Chao (подтверждён локатором)
**Линии.** porog

```
симметричное деление (a = 1):   Πλ ≤ 1/6      критерий существования равновесия
Πλ = 0.10  →  равновесие есть (пример из статьи)
Πλ > 1/6   →  уравнение не имеет вещественного решения
асимметрия a сдвигает границу
```
**Откуда.** `L-051` (PLOS figures + глава ASU).
**Наше.** `h = 1` — **другой параметр**; перевод через `a` (`L-054`) — открытая работа.

### F-020 · Надёжность: Гомпертц, Макегам и плато из избыточности
**Линии.** smert

```
Гомпертц:      μ(x) = R · e^(αx)          удвоение примерно каждые 8 лет взрослой жизни
Макегам:       μ(x) = μ₀ + R · e^(αx)     начальная смертность + возрастная компонента
Плато:         при исчерпании избыточности число работоспособных элементов падает,
               и μ выходит на уровень, заданный архитектурой (не экспонента)
```
**Откуда.** `L-055`, `L-056`.
**Наше.** Наш `μ = floor + rate·(1−q)^p + λ·damage` — **феноменологическая** версия: `floor` играет роль плато,
но он **взят извне**. Надёжностная рамка выводит и то и другое.

### F-021 · Правило κ и приоритет поддержания
**Линии.** obmen

```
поток ассимиляции J_A делится:  κ·J_A → поддержание сомы,  (1−κ)·J_A → рост и размножение
голодание:  κ·J_A < J_M   ⇒   поддержание платится из ветви (1−κ), рост останавливается
запас оплачивает поддержание, пока не исчерпан
```
**Откуда.** `L-059`.
**Наше.** Наш бюджет `income − maintenance ≥ Σ u_i·cost_i` — та же схема **без роста**; различие: у нас второе
назначение — **запас против засухи**, у них — потомство.
**Проверка различия — тождество, а не тест (2026-11-24, `FINDING-340`).** При эндогенной κ
(`κ = maintenance/income`) величины `ρ_s` и `ρ_s^κ` совпадают тождественно (разница 5·10⁻¹⁷), то есть две
«гипотезы» — одна формула. Различить записи можно только при **экзогенной** κ: тогда граница по доходу —
сдвиг `0.615` (абсолютная схема) против пропорции `0.03` (κ = 0.5).

### F-022 · Замыкание как свойство графа
**Линии.** svoi-usloviya

```
граф зависимостей ограничений:  вершины C = {c₁…cₙ},  ребро cᵢ → cⱼ  «cᵢ зависит от cⱼ»

условие отсутствия источников и стоков (формула из L-061, СЛАБЕЕ замыкания):
                                 ∀ c ∈ C:  indeg_C(c) ≥ 1  и  outdeg_C(c) ≥ 1
усиление (наша гипотеза):        подграф C сильно связен
мера (предложение):              доля вершин в наибольшей сильно связной компоненте
```
**Откуда.** `L-060`, `L-061`.
**Наше.** Это превращает «участие в формировании собственных условий» в **число**: 0 — цепочка, 1 — замыкание.
**Проверка на нашей модели:** построить граф «часть → часть, которую она поддерживает» и посчитать меру.

### F-023 · Двойственная задача и смысл цены
**Линии.** granica

```
прямая:   max  cᵀv      при  S·v = 0,  l ≤ v ≤ u          (S — стехиометрия, v — потоки)
двойственная:  min  uᵀy⁺ + lᵀy⁻   при  Sᵀ·y ≥ c,  y свободна
y — двойственные переменные (теневые цены);
    физический смысл — химические потенциалы (L-062)

инварианты: левое ядро S:  {w : wᵀS = 0}   →  wᵀv постоянно (L-064)
```
**Откуда.** `L-062`, `L-064`.
**Наше.** «Цена кожи» = компонента `y` ограничения на мембрану. **Предсказание:** `y` **кусочно-постоянна** и скачет
при смене базиса (изломы цены).

### F-024 · Ядро выживания и его граница
**Линии.** vybor

```
K — множество ограничений (например, q ≥ q_min, w ≥ 0)
V(K) = { x₀ ∈ K : ∃ траектория x(·), x(0)=x₀, x(t) ∈ K  ∀t ≥ 0 }        ядро выживания
дискретная аппроксимация:   K₀ = K,  K_{i+1} = K_i ∩ F⁻¹(K_i)          (убывающая последовательность)

граница выживания:   ∂V_α = ∂{ параметры : система остаётся в K навсегда }
наша «полоса»  →  проекция V(K) на ось alpha
ширина полосы  →  расстояние между границами ∂V по этой оси
```
**Единицы.** `K`, `V` — множества состояний (не числа); `F` — отображение шага (безразмерное); `alpha` и `band` — доля дохода, безразмерные.
**Проверка.** **не проведена.** Нужен прогон: построить `K` по бюджету, итерировать `K_{i+1} = K_i ∩ F⁻¹(K_i)` до сходимости, спроецировать `V(K)` на ось доли и сравнить ширину с измеренной полосой 3–10 %. Это и есть эксперимент 1.1 плана.
**Ограничение.** Алгоритм итерации взят из `L-065` (Aubin), но полный текст первоисточника в просмотренной выборке не найден (2026-11-24, OpenAlex `closed`), поэтому сама итерация пока не подтверждена по первоисточнику — только по нашей записи.
**Откуда.** `L-065`, `L-066`.
**Наше.** Наша полоса (3–10 %) — не «допуск», а **толщина** `V(K)` вдоль оси доли. Это проверяемо вычислением.

### F-025 · ITI: разложение временной информации
**Линии.** proshloe

```
временная целостность:   I(X_t ; X_{t+1})
разложение (схема):       I(X_t ; X_{t+1}) = I_env  + I_ind  + I_col
  I_env — вклад среды (детерминизм извне),
  I_ind — «индивидуальная» память/инерция (система предсказывает себя),
  I_col — коллективная компонента (части предсказывают целое)

индивидуальность  ~  доля I_ind + I_col  в общей временной информации
```
**Откуда.** `L-067`, `L-069`.
**Наше.** Измеримо на наших рядах: `q(t)`, `w(t)`, число живых, поле. **Нужен перестановочный нуль** (перемешать
время внутри окна) и, по `L-068`, **интервенция** (нок-аут части).

### F-026 · Зерно среды задаёт тип bet-hedging
**Линии.** vybor

```
крупное зерно (катастрофа общая для всех, мало независимых решений):
      приспособленность накапливается МУЛЬТИПЛИКАТИВНО  →  консервативный bet-hedging
      (жертва средним ради снижения дисперсии)
мелкое зерно (решения независимы, много событий):
      накопление АДДИТИВНО  →  дисперсия усредняется, «оптимизм» допустим
```

**Наш критерий (`Q-019`)**: переключать **общность катастрофы** при одинаковом среднем и смотреть, **сдвигается ли**
оптимум по среднему. Сдвиг в сторону меньшего среднего = bet-hedging; отсутствие сдвига = эффект Йенсена.

**Статус (25.11.2026).** Собственная конструкция, а не извлечение: критерий `Q-019` придуман нами (переключать общность катастрофы при одинаковом среднем и смотреть, сдвигается ли оптимум). «Откуда» поэтому пуст. Поиск источника 25.11.2026 (Europe PMC, `openAccess=Y`, запросы про bet-hedging и зерно среды) подходящей цитаты не дал — см. `docs/ANCHOR-AUDIT.md`.

### F-027 · Цена роста против цены удержания
**Линии.** obmen

```
рост площади:      dA/dt = k_inc · [липид]_вне − γ · A          (L-073)
рост объёма:       осмос, движим автокаталитической реакцией
деление:           при достижении соотношения A/V (или критического размера)
проницаемость:     P = P(состав),  есть порог cvc                 (L-074)

наше:   цена УДЕРЖАНИЯ целости  c·d·q_min   ≠   цена РОСТА площади k_inc·[липид]
```
**Откуда.** `L-073`, `L-074`.
**Наше.** Наш `c ≤ 1` — про **удержание**; у протоклеток вопрос про **рост**. Это разные бюджеты, и их нельзя путать.

### F-028 · Adder, sizer и линии родства
**Линии.** individualnost

```
правило:            s_d = a·s_b + b        (a = 0 sizer, 1 adder, 2 timer)
adder в числах:     CV²_s = ln 4 − 1 ≈ 0.386      (при beta = 1/2)
                    ВНИМАНИЕ: это свойство МОДЕЛИ С ШУМОМ добавки ≈ 0,5, а не правила s_d = a·s_b + b;
                    при нулевом шуме CV_s = 0, а наблюдаемое CV_h ≈ 0,07…0,09 в 4–5 раз ниже (FORMULA-ADDER.md)
наблюдаемое:        CV_h ≈ 0.07…0.09              (малая стохастика деления)

линия родства:      forward  — среднее НЕ зависит от CV ошибки деления
                    backward — среднее РАСТЁТ с CV
```
**Откуда.** `L-077`, `L-078`, `L-079`.
**Наше.** Измерять надо **явно названную** линию; иначе сравнение с 0.386 недействительно.

### F-029 · Нормальные формы и размытие перехода
**Линии.** porog

```
saddle-node:      ẋ = r + x²          (касание → пара корней)
transcritical:    ẋ = r·x − x²
pitchfork:        ẋ = r·x − x³        (нужна симметрия)

несовершенная складка с несовершенством ε:
      переход размыт на ширину  Δ ~ ε^(2/3)      (классический результат, L-082)
```
**Единицы.** `r` — 1/время; `x` — состояние, безразмерное; `eps` — параметр несовершенства, безразмерный; `Delta` — ширина перехода, в единицах `x`.
**Проверка.** **не проведена.** Закон `Delta ~ eps^(2/3)` взят из литературы (`L-082`), у нас своего измерения показателя нет. Что нужно: серия прогонов с разным `eps` и измерение ширины перехода; ожидаемый показатель 2/3.
**Ограничение.** Смешивать с нашим `h = 1` нельзя: у нас полюс, у Chao складка (`GAP-02`).
**Откуда.** `L-080`…`L-082`.
**Наше.** Наш «порог `h = 1`» — **полюс**, а не складка; но в конечной системе он всё равно **размыт**, и у размытия
есть **свой показатель**, который можно измерить.

### F-030 · Метрики открытости (если понадобятся)
**Линии.** organizaciya

```
изменение (novelty):     прирост числа ячеек за шаг (коммит);
                         Левенштейн между поколениями НЕ ИСПОЛЬЗУЕТСЯ — у карты нет поколений,
                         она растёт непрерывно (проверено: FORMULA-OPENNESS.md, раздел про операциональность)
разнообразие:            энтропия Шеннона по типам
сложность:               колмогоровская (аппроксимация сжатием)
MODES:                   набор из нескольких метрик динамики
```
**Откуда.** `L-084`, `L-085`.
**Наше.** Мы **не** заявляем открытость; если заявим — начинать с MODES и предрегистрации, потому что сама оценка
признана **субъективной**.

### F-031 · Внутреннее ограничение выживания из графа
**Линии.** granica

```
граф процессов:      вершины P (процессы), рёбра — зависимости; |P| = 352, рёбер 5912 (пример L-086)
внутреннее ограничение выживания:  множество конфигураций, при которых
      граф зависимостей остаётся самоподдерживающимся

наше:  q ≥ q_min, w ≥ 0 — грубая проекция этого множества на две оси
```
**Откуда.** `L-086`, `F-022`.
**Наше.** Мы считаем **outcome** (шаги), они — **условия** (`L-088`). Связка: наши пороги = **проекция** их
ограничения.

---

## C. Соответствия: наше ↔ литература

| наше | что это оказывается | записи |
|---|---|---|
| §4.7 цена кожи `c·d·q_min` | член поддержания (Pirt, DEB) + геометрия | L-012, L-013, F-004 |
| §4.9 «плательщики 1.00» | **следствие постановки** (u = 0 = не чинится) | — |
| §4.10 цена границы/глубины | бюджетное неравенство DEB | L-012, F-005 |
| §4.11 разделение через поток | автокаталитическое самоподдержание (Piedrafita) | L-021 |
| §4.12 «жизнь = 1/μ» | кумулятивная опасность; Вейбулл k = 2 | L-001, L-010, F-001 |
| §4.12 прошлое (339/258/128) | **frailty / vitality** | L-011 |
| §4.12 порог `h = 1` | порог доли удержания (Chao) | L-005, F-002 |
| §4.12 корневой закон | **снято:** `√` — универсальный масштаб складки (Chao) | L-023, F-006 |
| §4.13 выбор/полоса | **insurance / cliff-edge** | L-007, L-008 |
| §4.14 две опасности | статический вывод Tomasik в динамике | L-014 |
| §9.1 «нет организации с разделением» | **замкнутость ограничений** (Moreno–Mossio); химотон (Gánti); chemical organizations | L-015, L-016, L-025, L-026 |

---

## D. Чего в литературе, по нашим данным, **нет** (там наша модель может дать число)

> **Обновлено 2026-11-20 после второго обзора.** Прежний список начинался с «формы расходимости у порога» — **это
> снято**: `√` у порога — универсальный масштаб складки (L-023, F-006).

1. **Сшивка «повреждение + граница» в один бюджет** — **главный кандидат** (L-037): у моделей старения нет цены
   мембраны, у протоклеточных моделей нет наследования повреждения.
2. **Тип перехода**: смертность как канал удаления превращает складку в непрерывную расходимость (L-024) — это
   утверждение о механизме, а не о масштабе.
3. **Цена границы как функция её целости** (`c·d·q_min`) — в DEB цена постоянна, у протоклеток её нет (L-033).
4. **Полоса допуска как сечение viability kernel** (L-028) — проверяемо, и в литературе так не сформулировано.
5. **Числа для полосы** (3 %, 10 %) — у L-007 и L-035 качественно.

## E. Что читать первым (для следующего агента)

| порядок | запись | зачем |
|---|---|---|
| 1 | **L-009** Karin–Alon 2019 | решает судьбу единственного кандидата на новизну |
| 2 | **L-015** Moreno–Mossio | решает, наш ли критерий слона |
| 3 | **L-005** Chao 2010 полный текст | есть ли у них расходимость у порога |
| 4 | **L-014** Tomasik 2024 | предел `c ≤ 1` |
| 5 | **L-010, L-011** надёжность и frailty | язык и предшественники «прошлого» |

---

## F. Журнал файла

| дата | что сделано |
|---|---|
| 2026-11-20 | файл заведён; 22 записи, 5 формул; источники — два поисковых сеанса и три внешних отзыва. **Полный текст читался только у L-007**; остальное — аннотации и вторые руки |
| 2026-11-20 | **круг 013 (новое направление)**: `L-086`…`L-088`, `F-031` — внутреннее ограничение выживания **уже выведено** из графа процессов (352 процесса, 5912 связей); различение **viability ≠ survival** |
| 2026-11-20 | **круг кампании 012**: `L-083`…`L-085`, `F-030` — симуляция против реализации; метрики открытости и их субъективность. **Кампания 12 областей пройдена** |
| 2026-11-20 | **круг кампании 011**: `L-080`…`L-082`, `F-029` — нормальные формы трёх бифуркаций; **несовершенная бифуркация** размывает переход с показателем **2/3** |
| 2026-11-20 | **круг кампании 010**: `L-077`…`L-079`, `F-028` — forward/backward линии дают разные средние; adder предсказывает `CV² = ln 4 − 1 ≈ 0.386` |
| 2026-11-20 | **круг кампании 009**: `L-073`…`L-076`, `F-027` — рост мембраны лимитирован **внешним** липидом; проницаемость как компромисс с порогом; критерий метаболизма; эффект матрицы |
| 2026-11-20 | **круг кампании 008**: `L-070`…`L-072`, `F-026` — зерно среды и число независимых решений задают **тип** bet-hedging; приближение Тулджапурака даёт цену дисперсии числом |
| 2026-11-20 | **круг кампании 007**: `L-067`…`L-069`, `F-025` — ITI как **вычислимая мера** индивидуальности; причинная критика требует **интервенций**, а они у нас есть |
| 2026-11-20 | **круг кампании 006**: `L-065`, `L-066`, `F-024` — ядро выживания и его **граница**; наша «полоса» = проекция ядра, её ширина = расстояние между границами |
| 2026-11-20 | **круг кампании 005**: `L-062`…`L-064`, `F-023` — двойственные цены = **химические потенциалы**; COT как структурная рамка; инвариант из **левого ядра** стехиометрии |
| 2026-11-20 | **круг кампании 004**: `L-060`, `L-061`, `F-022` — замыкание ограничений как **свойство графа** (process-enablement graphs, 2025); появляется вычислимая мера третьего потолка |
| 2026-11-20 | **круг кампании 003**: `L-057`…`L-059`, `F-021` — баланс «асимметрия против починки» (PNAS 2023), кривые выживания из оптимального распределения, правило κ и приоритет поддержания |
| 2026-11-20 | **круг кампании 002**: `L-055`, `L-056`, `F-020` — надёжность объясняет **и Гомпертца, и плато**; плато подтверждено как феномен, а не артефакт |
| 2026-11-20 | **круг кампании 001**: `L-051`…`L-054`, `F-019`; порог `Πλ = 1/6` подтверждён локатором; найдены протоклетки с асимметричным делением (2024) и стохастическая модель старения (2019) |
| 2026-11-20 | **третий обзор (сетевой разбор очереди)**: добавлены `L-038`…`L-050`, `F-013`…`F-018`; опровергнут закон `1/(m+1)`, порог переклассифицирован в **полюс**; см. `docs/SYNTHESIS-2026-11-20.md` |
| 2026-11-20 | **второй обзор**: добавлены `L-023`…`L-037`, формулы `F-006`…`F-012`; снят кандидат на новизну `√`; §D переписан — главный пробел теперь **сшивка повреждения и границы** |

### L-089 · Minimal Conditions for Protocell Stationary Growth

```json
{
 "L": "L-089",
 "locator": {
  "doi": "10.1162/artl_a_00165",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W1941562954",
  "pmid": null,
  "url": "https://doi.org/10.1162/artl_a_00165",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-21T21:55:49Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1162/artl_a_00165"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "b73cd7168aa7f06fdaeaf53b2c2ca5a1fca6ef64294ca7a3e8a7a58f2077c29c",
 "bibliographic": {
  "title": "Minimal Conditions for Protocell Stationary Growth",
  "year": 2015,
  "first_author": "Erwan Bigan"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Minimal Conditions for Protocell Stationary Growth (2015). Erwan Bigan; Jean‐Marc Steyaert; Stéphane Douady
**Ссылка.** https://doi.org/10.1162/artl_a_00165
**Проверено.** **аннотация** OpenAlex, 2026-11-21T21:55:49Z, отпечаток есть; фрагмент не читался.
**Утверждение.** минимальные условия стационарного роста протоклетки: топологическое условие на химическую сеть, а не баланс энергии
**Что даёт нам.** — (суждение не сделано).

### L-090 · The “protocell”: A mathematical model of self-maintenance

```json
{
 "L": "L-090",
 "locator": {
  "doi": "10.1016/0303-2647(86)90008-0",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2004037730",
  "pmid": null,
  "url": "https://doi.org/10.1016/0303-2647(86)90008-0",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=3801605 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "8809a277f22f6cc9289f6257a8edfc8080e28cf2b2f0e137876e27b73da5aa0b",
 "bibliographic": {
  "title": "The “protocell”: A mathematical model of self-maintenance",
  "year": 1986,
  "first_author": "Helmut Schwegler"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** The “protocell”: A mathematical model of self-maintenance (1986). Helmut Schwegler; Kazuaki Tarumi
**Ссылка.** https://doi.org/10.1016/0303-2647(86)90008-0
**Проверено.** **аннотация** PubMed/efetch (PMID 3801605), 2026-11-27, sha256 8809a277f22f…; полный текст не читался.
**Утверждение.** самоподдержание протоклетки как динамика с подвижной границей и обратной связью, а не арифметическое условие
**Что даёт нам.** — (суждение не сделано).

### L-091 · Synergistic effects of repair, resilience and retention of damage determine the conditions for replicative ageing

```json
{
 "L": "L-091",
 "locator": {
  "doi": "10.1038/s41598-020-58444-2",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W3003628019",
  "pmid": null,
  "url": "https://doi.org/10.1038/s41598-020-58444-2",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-21T21:55:50Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1038/s41598-020-58444-2"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "c9aa631adffeebb8170948f9230784453c1b168f2a4e5d088b30febf3044ee1d",
 "bibliographic": {
  "title": "Synergistic effects of repair, resilience and retention of damage determine the conditions for replicative ageing",
  "year": 2020,
  "first_author": "Johannes Borgqvist"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Synergistic effects of repair, resilience and retention of damage determine the conditions for replicative ageing (2020). Johannes Borgqvist; Niek Welkenhuysen; Marija Cvijović
**Ссылка.** https://doi.org/10.1038/s41598-020-58444-2
**Проверено.** **аннотация** OpenAlex, 2026-11-21T21:55:50Z, отпечаток есть; фрагмент не читался.
**Утверждение.** ремонт, устойчивость и удержание повреждения одновременно определяют условия репликативного старения
**Что даёт нам.** — (суждение не сделано).

### L-092 · Balance between asymmetric allocation and repair of somatic damage in unicellular life forms as an ancient form of r/K selection

```json
{
 "L": "L-092",
 "locator": {
  "doi": "10.1073/pnas.2400008121",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W4398794048",
  "pmid": null,
  "url": "https://doi.org/10.1073/pnas.2400008121",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-21T21:55:51Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1073/pnas.2400008121"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "ebabcff3082d5b89ad953d89a0f66a54e364de056ba8b01e029cb7a08ff6c842",
 "bibliographic": {
  "title": "Balance between asymmetric allocation and repair of somatic damage in unicellular life forms as an ancient form of r/K selection",
  "year": 2024,
  "first_author": "Dmitry Biba"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Balance between asymmetric allocation and repair of somatic damage in unicellular life forms as an ancient form of r/K selection (2024). Dmitry Biba; Yuri I. Wolf; Eugene V. Koonin; Nash D. Rochman
**Ссылка.** https://doi.org/10.1073/pnas.2400008121
**Проверено.** **аннотация** OpenAlex, 2026-11-21T21:55:51Z, отпечаток есть; фрагмент не читался.
**Утверждение.** компромисс между асимметричным распределением повреждения и его ремонтом как стратегия популяции
**Что даёт нам.** — (суждение не сделано).

### L-093 · Autopoiesis: The organization of living systems, its characterization and a model

```json
{
 "L": "L-093",
 "locator": {
  "doi": "10.1016/0303-2647(74)90031-8",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2093020640",
  "pmid": null,
  "url": "https://doi.org/10.1016/0303-2647(74)90031-8",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/varela74.pdf",
  "bytes": 1195955,
  "sha256": "f5b8ae7ff67dd1cc95672455a86979d5c64e592b12941360d41b145f8946ac27",
  "retrieved_at": "2026-11-27T07:35:00Z",
  "via": "monoskop-pdf-scan-ocr",
  "via_detail": "Varela_Maturana_Uribe_1974_Autopoiesis.pdf (BioSystems 5:187-196), 10 стр., OCR rapidocr_onnxruntime по колонкам; цитаты верифицированы как подстроки OCR-текста"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "187", "to": "196", "note": "OCR"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Autopoiesis: The organization of living systems, its characterization and a model",
  "year": 1974,
  "first_author": "Francisco J. Varela"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Autopoiesis: The organization of living systems, its characterization and a model (1974). Francisco J. Varela; Humberto R. Maturana; R. Uribe
**Ссылка.** https://doi.org/10.1016/0303-2647(74)90031-8
**Проверено.** **полный текст** скан PDF (monoskop-зеркало), 2026-11-27, sha256 f5b8ae7f…; все 10 страниц OCR'нуты по колонкам, ключевые разделы прочитаны, цитаты верифицированы (батч s7zer).
**Утверждение.** Varela, Maturana & Uribe 1974 — автопоэтическая организация: единство производится сетью продукций компонентов, участвующих в той же сети; организация не воплощена в свойствах компонентов; граница производится самой динамикой и создаёт условия для неё; самоподдержание первично, воспроизведение — логически и операционально вторично; аллопоэтические системы неавтономны.
**Что даёт нам.** «Автономный барьер» слона — это в точности требование VMU-1974: граница, произведённая динамикой, создающая условия для себя; организация (отношения) важнее компонентов; кристалл-подобная фиксация границы без самовоспроизводства = единство, но не автопоэзис — наш damage=1 порог без самовосстанавливающейся границы был бы аллопоэтическим.

### L-094 · Biological organisation as closure of constraints

```json
{
 "L": "L-094",
 "locator": {
  "doi": "10.1016/j.jtbi.2015.02.029",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2107475155",
  "pmid": null,
  "url": "https://doi.org/10.1016/j.jtbi.2015.02.029",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=25752259 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "2875e9cc69fc532b616922ab01f3ee14eeb2b0e61bea88418d089064222d3c0f",
 "bibliographic": {
  "title": "Biological organisation as closure of constraints",
  "year": 2015,
  "first_author": "Maël Montévil"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Biological organisation as closure of constraints (2015). Maël Montévil; Matteo Mossio
**Ссылка.** https://doi.org/10.1016/j.jtbi.2015.02.029
**Проверено.** **аннотация** PubMed/efetch (PMID 25752259), 2026-11-27, sha256 2875e9cc69fc…; полный текст не читался.
**Утверждение.** Montévil & Mossio 2015 — организация как замыкание ограничений; словесная рамка «организация оплачивает свои ограничения»
**Что даёт нам.** — (суждение не сделано).

### L-095 · Detecting autocatalytic, self-sustaining sets in chemical reaction systems

```json
{
 "L": "L-095",
 "locator": {
  "doi": "10.1016/j.jtbi.2003.11.020",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W1995205814",
  "pmid": null,
  "url": "https://doi.org/10.1016/j.jtbi.2003.11.020",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=15038982 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "af58bbfccf244c5807f18ac1617c73c00c5e1099c7a6f7f2846a4fd8f2ae4a71",
 "bibliographic": {
  "title": "Detecting autocatalytic, self-sustaining sets in chemical reaction systems",
  "year": 2003,
  "first_author": "Wim Hordijk"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Detecting autocatalytic, self-sustaining sets in chemical reaction systems (2003). Wim Hordijk; Mike Steel
**Ссылка.** https://doi.org/10.1016/j.jtbi.2003.11.020
**Проверено.** **аннотация** PubMed/efetch (PMID 15038982), 2026-11-27, sha256 af58bbfccf24…; полный текст не читался.
**Утверждение.** Hordijk & Steel 2004 — детекция автокаталитических самоподдерживающихся множеств (RAF)
**Что даёт нам.** — (суждение не сделано).

### L-096 · Asymmetric segregation of protein aggregates is associated with cellular aging and rejuvenation

```json
{
 "L": "L-096",
 "locator": {
  "doi": "10.1073/pnas.0708931105",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W1984571004",
  "pmid": null,
  "url": "https://doi.org/10.1073/pnas.0708931105",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-22T00:51:02Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1073/pnas.0708931105"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "f40390e03121bbb204842d6b5c8b44d7bdea2c9aac77224eae0f362f2b24213f",
 "bibliographic": {
  "title": "Asymmetric segregation of protein aggregates is associated with cellular aging and rejuvenation",
  "year": 2008,
  "first_author": "Ariel B. Lindner"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Asymmetric segregation of protein aggregates is associated with cellular aging and rejuvenation (2008). Ariel B. Lindner; Richard Madden; Alice Démarez; Eric J. Stewart; François Taddéi
**Ссылка.** https://doi.org/10.1073/pnas.0708931105
**Проверено.** **аннотация** OpenAlex, 2026-11-22T00:51:02Z, отпечаток есть; фрагмент не читался.
**Утверждение.** Lindner et al. 2008 — асимметричная сегрегация агрегатов связана со старением и омоложением
**Что даёт нам.** — (суждение не сделано).

### L-097 · THE MAINTENANCE OF THE ACCURACY OF PROTEIN SYNTHESIS AND ITS RELEVANCE TO AGEING

```json
{
 "L": "L-097",
 "locator": {
  "doi": "10.1073/pnas.49.4.517",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2062776142",
  "pmid": null,
  "url": "https://doi.org/10.1073/pnas.49.4.517",
  "none": false
 },
 "access": {
  "level": "full_text_examined",
  "artifact": "papers/orgel63david.pdf",
  "bytes": 686846,
  "sha256": "69749f7761e7df721791c0d48d09058f45fae6acfc893b7614f5bd5bddbd1287",
  "retrieved_at": "2026-11-27T07:05:00Z",
  "via": "pmc-scanned-pdf",
  "via_detail": "PMC299893 PDF (pnas00171-0095.pdf) via davidson.edu course mirror; текстовый слой PDF, 5 стр. 517-521"
 },
 "inspection": {
  "scope": "full",
  "reviewed_ranges": [{"type": "page", "from": "517", "to": "521"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "THE MAINTENANCE OF THE ACCURACY OF PROTEIN SYNTHESIS AND ITS RELEVANCE TO AGEING",
  "year": 1963,
  "first_author": "Leslie Eleazer Orgel"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** THE MAINTENANCE OF THE ACCURACY OF PROTEIN SYNTHESIS AND ITS RELEVANCE TO AGEING (1963). Leslie Eleazer Orgel
**Ссылка.** https://doi.org/10.1073/pnas.49.4.517
**Проверено.** **полный текст** PMC299893 (PDF-скан с текстовым слоем, зеркало davidson.edu), 2026-11-27, sha256 69749f77…; все 5 страниц прочитаны, цитаты верифицированы посимвольно (батч s7zep).
**Утверждение.** Оргель 1963 — катастрофа ошибок: аппарат точности повреждает сам себя. Полный текст уточняет: уравнение (1) — непрерывное dp/dt = a·p (p = p₀·e^{at}), катастрофа = частота ошибок, при которой необходимый для жизни процесс становится критически неэффективным; спасает только клеточный отбор — в тканях без деления селекции нет и накопление ошибок особенно опасно; автор ограничивает претензию («один источник прогрессивного ухудшения», не «механизм старения»).
**Что даёт нам.** Q-021: первоисточник самоссылки прочитан напрямую — она НЕ самоподдерживающаяся без отбора; наш случай (один компартмент, нет популяции с селекцией) — уязвимейший режим Оргеля, но наша граница damage=1 играет роль внешнего ареста, которого у него не было.

### L-098 · Stochastic modeling of aging cells reveals how damage accumulation, repair, and cell-division asymmetry affect clonal senescence and population fitness

```json
{
 "L": "L-098",
 "locator": {
  "doi": "10.1186/s12859-019-2921-3",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2961272871",
  "pmid": null,
  "url": "https://doi.org/10.1186/s12859-019-2921-3",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-22T00:51:02Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1186/s12859-019-2921-3"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "5475aab1b456e5b6e17e3579f1cdff8bbecb56f89341888972428da424c6aa59",
 "bibliographic": {
  "title": "Stochastic modeling of aging cells reveals how damage accumulation, repair, and cell-division asymmetry affect clonal senescence and population fitness",
  "year": 2019,
  "first_author": "Ruijie Song"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Stochastic modeling of aging cells reveals how damage accumulation, repair, and cell-division asymmetry affect clonal senescence and population fitness (2019). Ruijie Song; Murat Açar
**Ссылка.** https://doi.org/10.1186/s12859-019-2921-3
**Проверено.** **аннотация** OpenAlex, 2026-11-22T00:51:02Z, отпечаток есть; фрагмент не читался.
**Утверждение.** Song & Acar 2019 — стохастическая модель старения: повреждение, ремонт, асимметрия деления
**Что даёт нам.** — (суждение не сделано).

### L-099 · Evolution of ageing

```json
{
 "L": "L-099",
 "locator": {
  "doi": "10.1038/270301a0",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W1993091967",
  "pmid": null,
  "url": "https://doi.org/10.1038/270301a0",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=593350 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "ce70a680cd1f6bd8d3855ff23d46dc75ba771d278ca82e483d7e8195652c71c7",
 "bibliographic": {
  "title": "Evolution of ageing",
  "year": 1977,
  "first_author": "Thomas B. L. Kirkwood"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Evolution of ageing (1977). Thomas B. L. Kirkwood
**Ссылка.** https://doi.org/10.1038/270301a0
**Проверено.** **аннотация** PubMed/efetch (PMID 593350), 2026-11-27, sha256 ce70a680cd1f…; полный текст не читался.
**Утверждение.** Kirkwood 1977 — эволюция старения: компромисс ремонта и размножения
**Что даёт нам.** — (суждение не сделано).

### L-100 · Selforganization of matter and the evolution of biological macromolecules

```json
{
 "L": "L-100",
 "locator": {
  "doi": "10.1007/bf00623322",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2087895317",
  "pmid": null,
  "url": "https://doi.org/10.1007/BF00623322",
  "none": false
 },
 "access": {
  "level": "fragment_read",
  "artifact": "papers/eigen71.pdf",
  "bytes": 7655752,
  "sha256": "f51e8a9954652dc5166daad53acab986b3c8836697ff5f5004d972a927086e53",
  "retrieved_at": "2026-11-27T07:40:00Z",
  "via": "evolocus-pdf",
  "via_detail": "Eigen1971.pdf (Naturwissenschaften 58:465-523, англ. перевод), 59 стр.; прочитаны фрагменты §I-II (предпосылки, отбор, quality factor, error copies, hypercycle), цитаты верифицированы"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": [{"type": "section", "from": "§I.1-1.2"}, {"type": "section", "from": "§II.1-II.6"}, {"type": "section", "from": "Fig.13"}]
 },
 "abstract_sha256": null,
 "bibliographic": {
  "title": "Selforganization of matter and the evolution of biological macromolecules",
  "year": 1971,
  "first_author": "Manfred Eigen"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Selforganization of matter and the evolution of biological macromolecules (1971). Manfred Eigen
**Ссылка.** https://doi.org/10.1007/BF00623322
**Проверено.** **фрагменты** полного текста (evolocus-зеркало PDF, 59 стр.), 2026-11-27, sha256 f51e8a99…; прочитаны §I–II и подписи рисунков, цитаты верифицированы (батч s7zer); §III–VI (стохастика, фазы) не читаны.
**Утверждение.** Eigen 1971 — самоорганизация требует замкнутого цикла реакций и каталитических связей; ошибка при репликации наследуема; master copy несёт «кометный хвост» error copies; точность держится отбором (член «repair of errors»/«back flow of information» пренебрежим для master copy); максимальная воспроизводимая информация Vmax·ln2 привязана к точности распознавания цифр; гиперцикл — связанные циклы стабилизируют, а не конкурируют.
**Что даёт нам.** Оргелю (L-097) не хватало механизма, удерживающего точность — у Эйгена это селекция по W_i со скользящим порогом; repair-поток в его уравнениях — «обратный поток информации», пренебрежимый для master copy, т.е. у Эйгена починка слабее отбора; наш контур имеет и то и другое — структурно богаче.

### L-101 · Statistical theory of asymmetric damage segregation in clonal cell populations

```json
{
 "L": "L-101",
 "locator": {
  "doi": "10.1016/j.mbs.2023.108980",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W4321202971",
  "pmid": null,
  "url": "https://doi.org/10.1016/j.mbs.2023.108980",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=36804386 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "19a77cd8f9276a19512126128eb9b1baecf3c5f8c7ea2fc3ce4dd927878f8078",
 "bibliographic": {
  "title": "Statistical theory of asymmetric damage segregation in clonal cell populations",
  "year": 2023,
  "first_author": "ARKADY S. PIKOVSKY"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Statistical theory of asymmetric damage segregation in clonal cell populations (2023). ARKADY S. PIKOVSKY; Lev S. Tsimring
**Ссылка.** https://doi.org/10.1016/j.mbs.2023.108980
**Проверено.** **аннотация** PubMed/efetch (PMID 36804386), 2026-11-27, sha256 19a77cd8f927…; полный текст не читался.
**Утверждение.** Найдено при починке чужого DOI (внешний ответ приписал работе Chao 2010 неверный DOI): статистическая теория асимметричной сегрегации повреждения в клональных популяциях, 2023. Сама работа Chao 2010 по-прежнему не подтверждена — её DOI в ответе был ложным.
**Что даёт нам.** — (суждение не сделано).

### L-102 · A network theory of ageing: the interactions of defective mitochondria, aberrant proteins, free radicals and scavengers in the ageing process

```json
{
 "L": "L-102",
 "locator": {
  "doi": "10.1016/s0921-8734(96)90005-3",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2041793728",
  "pmid": null,
  "url": "https://doi.org/10.1016/S0921-8734(96)90005-3",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=8649456 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "cffeb61ff0c90b423d29d0482871ef64730ae19cfae1b9555367d1ffa00a5a4c",
 "bibliographic": {
  "title": "A network theory of ageing: the interactions of defective mitochondria, aberrant proteins, free radicals and scavengers in the ageing process",
  "year": 1996,
  "first_author": "Axel Kowald"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** A network theory of ageing: the interactions of defective mitochondria, aberrant proteins, free radicals and scavengers in the ageing process (1996). Axel Kowald; Thomas B. L. Kirkwood
**Ссылка.** https://doi.org/10.1016/S0921-8734(96)90005-3
**Проверено.** **аннотация** PubMed/efetch (PMID 8649456), 2026-11-27, sha256 cffeb61ff0c9…; полный текст не читался.
**Утверждение.** Kowald & Kirkwood 1996 — сетевая теория старения: повреждение бьёт по системе удаления (scavengers), ремонт ремонтирует сам себя
**Что даёт нам.** — (суждение не сделано).

### L-103 · Self-maintenance and Self-reproduction in an Abstract Cell Model

```json
{
 "L": "L-103",
 "locator": {
  "doi": "10.1006/jtbi.2000.2121",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2010069344",
  "pmid": null,
  "url": "https://doi.org/10.1006/jtbi.2000.2121",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=10966762 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "86b9b5f7c811481c5a31d275c8dbb094d5a193ddde0e3c4830626369ed0e9daa",
 "bibliographic": {
  "title": "Self-maintenance and Self-reproduction in an Abstract Cell Model",
  "year": 2000,
  "first_author": "Naoaki Ono"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Self-maintenance and Self-reproduction in an Abstract Cell Model (2000). Naoaki Ono; Takashi Ikegami
**Ссылка.** https://doi.org/10.1006/jtbi.2000.2121
**Проверено.** **аннотация** PubMed/efetch (PMID 10966762), 2026-11-27, sha256 86b9b5f7c811…; полный текст не читался.
**Утверждение.** Ono & Ikegami 2000 — самоподдержание и граница в минимальной модели (проверить, что именно содержит)
**Что даёт нам.** — (суждение не сделано).

### L-104 · Thirty Years of Computational Autopoiesis: A Review

```json
{
 "L": "L-104",
 "locator": {
  "doi": "10.1162/1064546041255548",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2129280699",
  "pmid": null,
  "url": "https://doi.org/10.1162/1064546041255548",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-22T02:22:34Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1162/1064546041255548"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "298331aea217142570d50bfa39ae9f251e936c8ef818f07561665d6aec97646e",
 "bibliographic": {
  "title": "Thirty Years of Computational Autopoiesis: A Review",
  "year": 2004,
  "first_author": "Barry McMullin"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Thirty Years of Computational Autopoiesis: A Review (2004). Barry McMullin
**Ссылка.** https://doi.org/10.1162/1064546041255548
**Проверено.** **аннотация** OpenAlex, 2026-11-22T02:22:34Z, отпечаток есть; фрагмент не читался.
**Утверждение.** McMullin & Varela 2004 — реимплементация автопоэзиса: вторичный источник уравнений Varela 1974
**Что даёт нам.** — (суждение не сделано).

### L-105 · Closure to efficient causation, computability and artificial life

```json
{
 "L": "L-105",
 "locator": {
  "doi": "10.1016/j.jtbi.2009.11.010",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2158631600",
  "pmid": null,
  "url": "https://doi.org/10.1016/j.jtbi.2009.11.010",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=19962389 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "54410c5bf7ced90fa118d38659b635a0aec2b75445df995b2a0b3709594606f5",
 "bibliographic": {
  "title": "Closure to efficient causation, computability and artificial life",
  "year": 2009,
  "first_author": "María Luz Cárdenas"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Closure to efficient causation, computability and artificial life (2009). María Luz Cárdenas; Juan‐Carlos Letelier; Claudio Gutiérrez; Athel J. Cornish-Bowden; Jorge Antonio Soto-Andrade
**Ссылка.** https://doi.org/10.1016/j.jtbi.2009.11.010
**Проверено.** **аннотация** PubMed/efetch (PMID 19962389), 2026-11-27, sha256 54410c5bf7ce…; полный текст не читался.
**Утверждение.** Cárdenas et al. 2010 — замыкание организации в формальной модели (есть corrigendum 2011)
**Что даёт нам.** — (суждение не сделано).

### L-106 · Proteasome inhibition by lipofuscin/ceroid during postmitotic aging of fibroblasts

```json
{
 "L": "L-106",
 "locator": {
  "doi": "10.1096/fj.99-0843com",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W2012221118",
  "pmid": null,
  "url": "https://doi.org/10.1096/fj.99-0843com",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-22T02:22:34Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1096/fj.99-0843com"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "b5d9d6929ccee2e69aeb3b9ead1f97780de595b122f44a7094620cd765e1c090",
 "bibliographic": {
  "title": "Proteasome inhibition by lipofuscin/ceroid during postmitotic aging of fibroblasts",
  "year": 2000,
  "first_author": "Nicolle Sitte"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Proteasome inhibition by lipofuscin/ceroid during postmitotic aging of fibroblasts (2000). Nicolle Sitte; Michael Huber; Tilman Grune; Axel Ladhoff; Wolf‐Dietrich Doecke; Thomas Von Zglinicki
**Ссылка.** https://doi.org/10.1096/fj.99-0843com
**Проверено.** **аннотация** OpenAlex, 2026-11-22T02:22:34Z, отпечаток есть; фрагмент не читался.
**Утверждение.** Sitte et al. 2000 — липофусцин ингибирует протеасому: измеряемая связь груза повреждения и способности к удалению
**Что даёт нам.** — (суждение не сделано).

### L-107 · Lipofuscin inhibits the proteasome by binding to surface motifs

```json
{
 "L": "L-107",
 "locator": {
  "doi": "10.1016/j.freeradbiomed.2010.12.011",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W1980062352",
  "pmid": null,
  "url": "https://doi.org/10.1016/j.freeradbiomed.2010.12.011",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-27T07:20:00Z",
  "via": "pubmed-efetch",
  "via_detail": "eutils.ncbi.nlm.nih.gov efetch db=pubmed id=21167934 (abstract text)"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "3c0d328dab7fd7e404f10d2d4dfcbb14859cbee4ef45e575bc78697ef456cf8a",
 "bibliographic": {
  "title": "Lipofuscin inhibits the proteasome by binding to surface motifs",
  "year": 2010,
  "first_author": "Annika Höhn"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Lipofuscin inhibits the proteasome by binding to surface motifs (2010). Annika Höhn; Tobias Jung; Stefanie Grimm; Betül Catalgol; Daniela Weber; Tilman Grune
**Ссылка.** https://doi.org/10.1016/j.freeradbiomed.2010.12.011
**Проверено.** **аннотация** PubMed/efetch (PMID 21167934), 2026-11-27, sha256 3c0d328dab7f…; полный текст не читался.
**Утверждение.** Höhn et al. 2011 — титрование протеасомы липофусцином: константа ингибирования как кандидат на ι
**Что даёт нам.** — (суждение не сделано).

### L-108 · Damage dynamics and the role of chance in the timing of E. coli cell death

```json
{
 "L": "L-108",
 "locator": {
  "doi": "10.1038/s41467-023-37930-x",
  "arxiv": null,
  "arxiv_version": null,
  "openalex": "W4366278330",
  "pmid": null,
  "url": "https://doi.org/10.1038/s41467-023-37930-x",
  "none": false
 },
 "access": {
  "level": "abstract_read",
  "artifact": null,
  "bytes": null,
  "sha256": null,
  "retrieved_at": "2026-11-22T02:22:34Z",
  "via": "openalex",
  "via_detail": "api.openalex.org/works/https://doi.org/10.1038/s41467-023-37930-x"
 },
 "inspection": {
  "scope": "partial",
  "reviewed_ranges": []
 },
 "abstract_sha256": "4b5d86ce670c0d988861f731158c4d24d22408beb290dc52471c0ebea5e4bb6c",
 "bibliographic": {
  "title": "Damage dynamics and the role of chance in the timing of E. coli cell death",
  "year": 2023,
  "first_author": "Yifan Yang"
 },
 "legacy": false,
 "legacy_reason": null,
 "downgrade_reason": null
}
```

**Кто.** Damage dynamics and the role of chance in the timing of E. coli cell death (2023). Yifan Yang; Omer Karin; Avi Mayo; Alon Bar; Xiaohu Song; Peipei Chen
**Ссылка.** https://doi.org/10.1038/s41467-023-37930-x
**Проверено.** **аннотация** OpenAlex, 2026-11-22T02:22:34Z, отпечаток есть; фрагмент не читался.
**Утверждение.** Damage dynamics and the role of chance in the timing of E. coli cell death (2023) — измеряемая динамика повреждения и насыщаемый ремонт
**Что даёт нам.** — (суждение не сделано).
