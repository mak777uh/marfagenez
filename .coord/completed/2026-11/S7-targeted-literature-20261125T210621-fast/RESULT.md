# RESULT — S7-раунд 1: F-031 (порог выживания из графа зависимостей)

## Цель
F-031 — «внутреннее ограничение выживания из графа процессов»: порог выживания,
вычисленный из структуры графа зависимостей.

## Каналы
EPMC search → abstracts → MDPI PDF через mdpi-res.com (PMC/EPMC флаки).

## Новые ячейки: FAST-S7A-01..05 (5 шт., домен bio.protocell)
Источник: Villani, Serra, Villani? — «Template-Based Catalysis and the Emergence
of Collectively Autocatalytic Systems», Entropy 2026, 28, 184. DOI 10.3390/e28020184.

- 01 measurement: K-BPM — RAF-индексы = 0 до порога 1500–1600 реакций, затем скачок к максимуму.
- 02 measurement: P(RAF) фазовый переход по p_r: ~0 → ~1, |RAF| → N_species.
- 03 measurement: >60% малых RAF синхронизируются; большие RAF при той же связности — нет.
- 04 measurement: крупные RAF синхронизируются при ≥40 катализаторах (60%→>80%).
- 05 mechanism: RAF необходим, но недостаточен — starvation при рассинхронизации.

## Рёбра: 5
01→02 supports; 02→P-0009 supports; 03→01 refines; 04→03 supports; 05→P-0010 supports.

## kg_ref
F-031 у всех пяти (порог выживания из структуры графа — измерен в реакциях/катализаторах);
F-010 дополнительно у 02 (определение RAF — та же величина).

## Проверки
map_contract merged: 0 ошибок. Сирот: 0. DOI чист.
