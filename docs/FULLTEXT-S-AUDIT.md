# FULLTEXT-S-AUDIT — сверка S-пар по полным текстам работ (партия 1)

Дата: 2026-11-25. Агент: fast. Задача: `P90-fulltext-s-audit`.
Метод: для каждой пары взят полный текст работы (Europe PMC `fullTextXML` → PMC HTML с browser-UA → DOI-редирект), утверждение атома сверено с тем, что реально сказано в работе. Вердикты: `подтверждено` / `расхождение` / `недоступно`.

## Таблица партии 1 (8 пар)

| # | пара | что в атоме | что в полном тексте | локатор | вердикт |
|---|---|---|---|---|---|
| 1 | `FT-0003 \| L-091` | способность удерживать повреждение ухудшается с возрастом; асимметричное деление удерживает повреждение в материнской клетке | Abstract: «the capacity to retain damage deteriorates with high age, that asymmetric division allows for retention of damage» — дословно | Abstract, PMC6994596 | **подтверждено** |
| 2 | `B7-05-0001 \| L-092` | цена ремонта входит в рост напрямую: на рост остаётся доля `1 − r/E` | Eq. (3A): `u˙ = A(1 − r/E)ϕu − …`; `r ≡ R/E` «represents repair» — множитель `(1 − r/E)` стоит именно при члене роста | Eq. (3A) и определения констант, PMC11145259 | **подтверждено** |
| 3 | `B7-05-0002 \| L-092` | безразмерный индекс `I`; при малом `I` сочетание ремонта и асимметрии глобально оптимально | `I` — «relative impact, 0 < I ≤ 1, of the linear component of somatic damage»; «When I ≪ 1 … the combination of strategies is globally optimal» | Results + Eq. (D2), PMC11145259 | **подтверждено** |
| 4 | `A-0004 \| L-108` | в популяции E. coli смерть объясняется динамикой накопления и удаления повреждений с насыщением, а не только возрастом | «lifespan variation comes not from initial conditions but from stochastic accumulation of damage that saturates repair systems»; «removal processes saturate at high damage levels» | Abstract + модель, PMC10113371 | **подтверждено** |
| 5 | `A-0003 \| L-096` | асимметричное распределение агрегатов связано со старением и омоложением клеток | Накопление IbpA-фокусов на старых полюсах «associated with >30% of the loss of reproductive ability»; new-pole progeny «devoid of parental inclusion bodies … exhibit rejuvenation» | Abstract + Results, PMC2268587 | **подтверждено** |
| 6 | `W2-0001 \| L-100` | сохранение мастер-последовательности в quasispecies-модели требует ошибки ниже порога | «beyond a threshold error rate the master sequence» исчезает; порог по error rate воспроизведён в Swetina–Schuster | Main text + Appendix, PMC1317512 (JVI 2006) | **подтверждено** (с оговоркой: обзор критичен к «error catastrophe» как механизму вымирания, но пороговое утверждение подтверждает) |
| 7 | `A-0005 \| L-094` | организация = замыкание ограничений (Montévil & Mossio 2015) | JTB (Elsevier) — полный текст за пейволом; EPMC без fullTextXML; linkinghub → ScienceDirect | — | **недоступно** (пробовал: EPMC fullTextXML, doi.org→linkinghub, PII-страница) |
| 8 | `A-0001 \| L-106` | липофусцин/цероид снижает каталитическую активность протеасомы (Sitte 2000) | FASEB J (Wiley) — 403 на doi.org; в EPMC записи нет | — | **недоступно** (пробовал: doi.org→Wiley 403, EPMC search — записи нет) |

## Сводка

| вердикт | количество |
|---|---|
| подтверждено | **6** |
| недоступно | **2** |
| расхождение | 0 |

## Замечания

- Обе «недоступно»-пары опираются на работы 1999–2015 гг. в закрытых журналах (FASEB J, JTB). Это тот же
  класс, что в `docs/ARTIFACTS-ACCESS.md`.
- Пары 2–3 — **одна работа** (Biba et al. 2024, PNAS, «Balance between asymmetric allocation and repair»):
  проверены вместе, обе подтверждены по разным местам текста (уравнение 3A и показатель I).
- Пара 6: источник — обзор (Bull et al. 2006, JVI), а не первичная работа Eigen 1971; в атоме
  `W2-0001` второй работой стоит `10.1007/BF00623322` (Springer, тоже закрыт). Полный текст Eigen
  не проверялся — верифицирована только обзорная формулировка порога.
- Методические наблюдения для следующих партий: EPMC `fullTextXML` даёт 500 на части старых PMC
  (`PMC1317512`); рабочий обход — `?report=xml` или обычная PMC-страница с browser-UA. PNAS-статьи
  после эмбарго открыты на PMC, хотя `isOpenAccess=N` в EPMC (`PMC2268587`).
