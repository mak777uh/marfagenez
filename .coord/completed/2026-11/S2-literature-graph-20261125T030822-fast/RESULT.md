# Раунд S2 — 2026-11-25 (агент fast)

## Вопрос

Измерено ли в литературе, как мощность/скорость репарации (протеасомного и
ДНК-клеточного) зависит от накопленной нагрузки повреждения/агрегатов — и есть
ли работы, дающие числа для оценки `D_cap`?

## Запросы (дословно) и каналы

Канал 1 — OpenAlex API (`api.openalex.org/works?search=...`, api_key из
`~/.dsh/secrets/openalex.key`), 25.11.2026:

- `proteasome activity aggregate substrate concentration dose response`
- `lipofuscin ceroid proteasome dose response inhibition`
- `aggrephagy capacity aggregate burden decline`
- `double-strand break repair rate dose dependence kinetics foci`
- `DNA repair capacity saturation lesion load quantitative`
- `replicative senescence homologous recombination decline fold`
- `Indirect inhibition of 26S proteasome activity in a cellular model of
  Huntington's disease` (точный поиск)

Канал 2 — Europe PMC `fullTextXML` (полные тексты):
- `PMC3307690` → JCB 2012, DOI 10.1083/jcb.201110093 (успех, 168 КБ);
- `PMC3616853` → Genome Integrity 2013, DOI 10.1186/2041-9414-4-1 (успех, 97 КБ);
- `PMC5270681` → Aging 2016, DOI 10.18632/aging.101141 (успех, 123 КБ);
- `PMC4813294` → J Cell Sci 2016, DOI 10.1242/jcs.179978 (**500 Internal
  Server Error** — канал сменён, статья не в OA-подмножества EPMC, пропущена).

## Что найдено

| ячейка | работа (DOI) | число | локатор | цитата |
|---|---|---|---|---|
| FAST-S2-01 | 10.1083/jcb.201110093 | Ki N-htt 150–215 нМ ≈ Ki MPC 150 нМ; задержка UPS 22,8±4 ч; 24 % клеток | Results, Figs. 3,4,6 | «the Ki for N-htt fragments is independent of polyglutamine length and aggregation state and is similar to the Ki of an unrelated polyubiquitinated protein, MPC» |
| FAST-S2-02 | 10.1083/jcb.201110093 | Km 46,9±3,5 нМ; Ki 150 нМ / 150–215 нМ | Results, Fig. 3B–3F | «Michaelis–Menten analysis of 35S–PY-Sic1(Ub n) degradation yielded a Michaelis constant (Km) of 46.9 ± 3.5 nM» |
| FAST-S2-03 | 10.1186/2041-9414-4-1 | t½ 10–30 мин/часы (PFGE); 1,5 ч и 1,5 сут (foci) | обзор, разделы о кинетике DSB | «reported slower foci loss at higher doses, in line with the hypothesis that multiple DSB may congregate into one shared» |
| FAST-S2-04 | 10.1186/2041-9414-4-1 | ~30 % PFGE-DSB — лизис-конвертируемые; late S/G2 ≈2× фокусов | обзор, абзацы о методах | «can be converted into DSB during cell lysis and may contribute ~30% of all DSB measured using PFGE» |
| FAST-S2-05 | 10.18632/aging.101141 | >2× агрегатов у пожилых; −25–30 %/−70 % массы мышц C. elegans | Results/Discussion, Figs. 2–3 | «which otherwise lose 25–30% of muscle mass by day 3, and >70% by day 9 of adult life» |

**Для `D_cap` итог:** прямого измерения «уровень повреждения, при котором мощность
ремонта падает в e раз» не найдено; но получены два опорных факта — (а) падение
*видимой* кинетики фокусов с дозой объясняется консолидацией DSB в repair
centers, а не потерей мощности (FAST-S2-03); (б) протеасомная ёмкость
ограничена конкуренцией субстратов с измеримыми Km/Ki (FAST-S2-02) — это
готовые числа для оценки насыщения клиренса.

## Что НЕ найдено (с запросами и датой)

- Титрование «доза/агрегат → остаточная активность репарации» с рядом точек
  для извлечения D_cap: запросы `proteasome IC50 aggregate substrate
  concentration`, `lipofuscin ceroid proteasome dose response`,
  `aggrephagy capacity aggregate burden` (OpenAlex, 25.11.2026) — подходящих
  первичных работ с кривой «нагрузка → остаточная активность» не выявлено;
  имеющиеся в карте (B8-01-0001-b, DIP59-0009) — точечные, не ряды.
- `PMC4813294` (JCS 2016, анализы формирования/клиренса агрегатов): fullTextXML
  вернул 500; OA-версии в EPMC нет — не читано, в ячейки не пошло.

## Предложенные связи

| пара | тип | что совпадает |
|---|---|---|
| FAST-S2-02 → FAST-S2-01 | measures | одна работа, один блок экспериментов: числа → механизм |
| FAST-S2-03 → DIP59-0005 | refines | одна измеряемая величина: полувремя репарации DSB при разных дозах; обзор добавляет исключение через repair centers |
| FAST-S2-01 → DIP59-0009 | analogous | только механизм ёмкости протеасомы; величины разные (Ki нМ vs % подавления) |

Доля analogous среди новых связей: 1/3 — на границе, остальные типы строже.

## Файлы, которые я создал

- `literature/map/inbox/fast-s2-atoms-20261125.jsonl` — 5 ячеек;
- `literature/map/inbox/fast-s2-edges-20261125.jsonl` — 3 связи.

## Проверки

- `python3 checks/map_contract.py` — зелёный (999 ячеек, 584 ребра; inbox
  проверяется при приёме `tools/ingest_safe.py` — за main).
- Все DOI проверены через OpenAlex/Europe PMC; все цитаты дословные из
  fullTextXML, 10–30 слов; `locator_status: verified` только для прочитанных
  полных текстов.

## Следующий вопрос

Повторить поиск титрования «нагрузка → остаточная активность» по другим
доменам: (а) автолизосомальный/агрефагический клиренс vs размер агрегатной
нагрузки (есть JCS-2016 и CNS-2026 кандидаты, нужен полный текст); (б) ряды
«доза → скорость удаления фокусов» в первичных работах, на которые ссылается
обзор (Neumaier и др.) — для пар `(D, R(D))` формулы v2.
