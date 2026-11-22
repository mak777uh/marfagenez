# Четвёртая волна — термодинамика открытых систем и теория надёжности

**Дата поиска:** 2026-11-22  
**Партия:** область 6 (термодинамика открытых систем) и углубление области 3 (теория надёжности / несовершенный ремонт).  
**Новые атомы:** 30.  

## 1. Главный результат

В термодинамике открытых систем найдено формальное разделение релаксационной диссипации и мощности, необходимой для поддержания неравновесного стационарного состояния (housekeeping heat). Это наиболее строгий язык для «цены поддержания состояния», но он не равен автоматически затратам на ремонт конкретной структуры. Биологические модели обслуживания (Pirt) выделяют substrate/energy maintenance отдельно от роста; экспериментальные коэффициенты заметно зависят от системы и условий.

В инженерной надёжности несовершенный ремонт чаще описывается через виртуальный возраст, обновление интенсивности отказов, shock/wear states или ограниченную мощность repair facility. Найден также конкретный модельный случай, где repair effect может быть отрицательным; этот результат зависит от относительных интенсивностей в виртуальной series-system и не означает, что любой ремонт вреден.

## 2. Сильные атомы термодинамики

- `W4-0001`: баланс энтропии `dS/dt = e_p - h_d/T`.
- `W4-0002`–`W4-0003`: открытая система `T e_p = f_d + Q_hk`, где `Q_hk` — необратимая поддерживающая работа/подача энергии, удерживающая систему вдали от равновесия.
- `W4-0004`–`W4-0005`: локальный entropy balance и сумма потоков на сопряжённые термодинамические силы.
- `W4-0006`–`W4-0008`: химический master equation, производство энтропии и диссипация циклического потока.
- `W4-0009`–`W4-0011`: Pirt maintenance terms: отдельная доля субстрата для обслуживания; постоянный и рост-зависимый компоненты; эмпирические коэффициенты для анаэробных реакторов.
- `W4-0012`: осторожность с принципом минимума производства энтропии — он относится к окрестности равновесия и линейному отклику, а не ко всем far-from-equilibrium структурам.

### Интерпретационное ограничение

`Q_hk`, `m`, ATP maintenance demand и расход на ремонт мембраны — не взаимозаменяемые параметры. Первый — термодинамическая мощность поддержания NESS; второй — коэффициент обслуживания в модели микробного роста; ATP maintenance demand — метаболическая оценка в конкретной модели; membrane-repair ATP cost требует отдельного измерения.

## 3. Сильные атомы надёжности

- `W4-0015` — ремонт снижает либо интенсивность отказов, либо виртуальный возраст.
- `W4-0016` / `W4-0017` — формулы Kijima I и II различаются тем, к какому возрастному отрезку применяется доля ремонта.
- `W4-0018` — hazard определяется базовой функцией от виртуального возраста.
- `W4-0019` — формальное определение conditional intensity point process.
- `W4-0020` — хорошее соответствие прошлым данным не гарантирует хорошего прогноза будущих отказов; нужна prequential проверка.
- `W4-0022` — shock/wear модель различает три варианта постремонтного состояния.
- `W4-0023` / `W4-0024` — virtual series-system: renewal + minimal repair; в специальном условии repair effect может оказаться отрицательным.
- `W4-0025` / `W4-0026` — ограниченное число ремонтников / бригад создаёт очередь и ограничивает доступность.
- `W4-0027` — maintenance interventions могут включать human-error risk в оптимизацию расписания и operational costs.
- `W4-0028` — виртуальный возраст и интенсивность отказов можно обновлять отдельными факторами.

## 4. Новые кандидаты пробелов

`W4-0013`–`W4-0014` ограничены поиском по неравновесной термодинамике, cellular damage/repair и биологическим границам. Они спрашивают о совместной формализации housekeeping power, degradation of repair capacity, boundary repair and inheritance. Это не заявление, что такого нет во всей биофизике или системной биологии.

`W4-0029`–`W4-0030` ограничены выборкой imperfect-repair, virtual-age, repair queueing, team constraints и maintenance-induced human error. Очереди, несовершенный/отрицательный эффект ремонта и human error уже изучаются по отдельности; пробел — в их совместной эндогенной динамике.

## 5. Поисковые запросы

**Термодинамика:**
- `housekeeping heat open systems free energy dissipation entropy production`
- `nonequilibrium biochemical systems chemical master equation cyclic flux thermodynamic force`
- `biological cells local entropy balance entropy flux thermodynamic forces`
- `Pirt maintenance energy coefficient anaerobic acetogenesis methanogenesis 37 C`
- `minimum entropy production principle near equilibrium linear response limitations`
- `cell membrane resealing ATP thermodynamic cost boundary repair entropy balance`

**Надёжность:**
- `imperfect repair virtual age failure intensity Kijima I Kijima II`
- `classes of imperfect repair reduction of failure intensity virtual age`
- `virtual series-system models imperfect repair negative repair effect`
- `shock and wear degrading systems three types of repair`
- `N parallel queueing systems server breakdown limited repair capacity repairmen`
- `maintenance grouping multi-component systems limited maintenance teams availability constraints`
- `aircraft maintenance scheduling impact of human errors operational costs`
- `hybrid failure rate update model imperfect maintenance virtual age failure intensity update factors`

**Каналы:** APS publisher abstract; PMC full text; Frontiers full text; Wiley full text; Elsevier publisher abstracts; Cardiff ORCA repository; RePEc/IDEAS; PubMed; Inderscience publisher record; targeted web search.

## 6. Проверки и ограничения

- Новые идентификаторы `W4-0001`…`W4-0030` не дублируют ID волн 1–3.
- Все формульные утверждения привязаны к локаторам уравнений/разделов.
- `high` используется только там, где формула показана в открытом тексте или абстракте источника; abstract-only классификации остаются `medium`.
- Все четыре gap атома имеют `searched` и `scope`, уверенность `low`.
- Ни один новый DOI не повторяет DOI из старых reliability-атомов, которые уже находились в карте.
- DOI/title ownership новой партии проверен по доступным publisher / PubMed / repository records; автоматическая пакетная сверка Crossref не проводилась.
- Карта не является systematic review и пока не достигает цели 1000+ работ.

## 7. Сопоставление двух областей

Сходство: обе области изучают поддержание работоспособного режима при потере/расходовании ресурсов. Различие: термодинамика описывает поток энергии, энтропии и термодинамических сил; reliability обычно описывает условную интенсивность отказов, виртуальный возраст и ресурс ремонтников. Их можно сопоставлять по структуре «поддержание требует ресурса», но нельзя подставлять виртуальный возраст вместо энергии или housekeeping heat вместо бюджета персонала.
