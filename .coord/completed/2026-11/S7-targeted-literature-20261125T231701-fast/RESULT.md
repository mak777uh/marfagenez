# RESULT — S7-раунд 3: F-001 (кумулятивная опасность и жизнь)

## Цель
F-001 — H(T)=∫μ(t)dt, смерть при H(T)=1: нужна литература, где смерть наступает
после кумулятивного накопления повреждений/опасности.

## Каналы
EPMC → NCBI efetch full JATS (PMC11541399, J Math Biol 2024).

## Новые ячейки: FAST-S7C-01..05 (5 шт., домен aging.mortality_law)
Источник: Shimoyama & Hosonuma — «Application of the first exit time stochastic
model with self-repair mechanism to human mortality rates», J Math Biol 2024.
DOI 10.1007/s00285-024-02150-4.

- 01 measurement: U_t = u + ct − S_t; S_t — кумулятивная сумма шоков; отказ при
  первом проходе ниже 0; фит к life tables Japan/UK 2019.
- 02 measurement: ~8000 внешних шоков за жизнь (λ=1, n=100, удар 1/100).
- 03 measurement: явная μ_h(t); max плотности 0.0424 @ 88 (Japan) / 0.0393 @ 87 (UK).
- 04 measurement: λ ∈ [0.2,1.2]/год; λ>1.2 — резкое падение точности подгонки.
- 05 mechanism: неидентифицируемость — множество наборов параметров фитят одинаково.

## Рёбра: 5
01→02, 01→03, 04→01 supports; 05→04 qualifies; 03→S7B-05 analogous.

## kg_ref
F-001 у всех пяти: кумулятивная величина S_t (сумма шоков) — прямой аналог
кумулятивной опасности H(T); смерть = first exit после накопления.

## Проверки
map_contract merged: 0 ошибок. Сирот: 0. DOI чист.
