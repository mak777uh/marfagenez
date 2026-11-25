# RESULT — S2-раунд: information.error_threshold (десятый)

## Вопрос
Каков измеренный порог элиминации вируса мутатagenезом и что его сдвигает?
(домен information.error_threshold имел 1 ячейку — только формула μ_c=1−f1/f0)

## Каналы
EPMC search → PMC12799177 fullTextXML (PNAS 2026, OA) — полный текст, числа из Results/Fig.3B.

## Новые ячейки: FAST-S2P-01..05 (5 шт.)
- 01 measurement: IAV mutation counts надисперсированы, индекс дисперсии D=var/mean=1.16 — Poisson-эквивалент Лурия–Дельбрюка нарушен.
- 02 mechanism: γ-Poisson порог экстинкции f(Ū,D); ∂threshold/∂D>0 — Poisson-модели занижают нужный темп мутаций.
- 03 measurement: 1–2 nonsynonymous мутации на полимеразный комплекс на геном (источник вариабельности).
- 04 condition: подпороговый мутатогенез → резистентность/антительный уход (molnupiravir, SARS-CoV-2 клиника).
- 05 definition: lethal mutagenesis ≠ error catastrophe (экстинкция vs перестройка ландшафта).

## Рёбра: 4
- S2P-02 → MAIN-P122-01 refines (порог при D>1 выше классического μ_c)
- S2P-01 → S2P-02 supports; S2P-04 → S2P-02 condition
- S2P-05 → MAIN-P122-01 analogous (порог ошибок vs порог экстинкции — разные объекты)

## Примечание по kg_ref
kg_ref→F-017 у 01,02,04,05 — та же величина (темп мутаций vs порог), не родственная.
Узел MAIN-P122-01 уже имеет S-пару; новые связи — уточнение условия применимости.

## Проверки
map_contract merged (атомы+все 10 ожидающих раундов): 0 ошибок. DOI 10.1073/pnas.2523734123 проверен.
