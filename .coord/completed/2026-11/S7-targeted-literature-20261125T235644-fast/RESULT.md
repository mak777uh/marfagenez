# RESULT — S7-раунд 8 (очередь L-*): L-040, источник закрыт

## Цель
L-040 «Калибровка и sharpness — стандартные метрики» — у узла был DOI,
работы в карте не было.

## DOI
10.1198/016214506000001437 — Gneiting & Raftery — «Strictly Proper Scoring
Rules, Prediction, and Estimation», JASA 2007, 20 с. (PDF с авторской
страницы stat.washington.edu — green OA, полный текст получен).
Канал: OpenAlex → sites.stat.washington.edu PDF → pypdf.

## Новые ячейки: FAST-S7H-01..05 (5 шт., домен complex.systems)
- 01 definition: proper/strictly proper scoring rule — максимум ожидания
  при честном прогнозе F, единственность максимума.
- 02 definition: цель прогноза = max sharpness при условии калибровки;
  калибровка и sharpness — раздельные требования.
- 03 formula: Brier score S(p,i)=2pi−Σpj²−1; дивергенция = квадрат
  евклидова расстояния; Brier 1950, Selten 1998.
- 04 formula: CRPS(F,x)=−∫(F(y)−1{y≥x})²dy = ½E|X−X′|−E|X−x|;
  «интеграл Brier-скоров по всем порогам»; строго proper при конечном
  первом моменте; в единицах наблюдений, сводится к |ошибке|.
- 05 formula: Energy score ES=½E‖X−X′‖^β−E‖X−x‖^β, β∈(0,2), R^m;
  CRPS = частный случай (β=1,m=1); β=2 → −квадратичная ошибка.

## Рёбра: 7
Внутренние: 04→03 refines (CRPS=интеграл Brier), 05→04 refines
(energy score ⊃ CRPS), 03→01, 04→01, 02→01, 03→02, 05→W4-0020 analogous.

## kg_ref
L-040 у всех пяти — один источник, узел про метрики калибровки/sharpness.

## Что подтвердилось / что неверно
- Подтвердилось полностью: Brier для бинарного, CRPS для непрерывного,
  калибровка и sharpness — раздельные требования, strictly proper —
  всё в узле и в статье.
- Уточнение: статья даёт иерархию обобщений — Brier ⊂ CRPS ⊂ energy
  score (β,m) — это можно использовать для выбора метрики под тип
  прогноза.
- Ошибок в узле не найдено.

## Проверки
map_contract merged: 0 нарушений; после отката 1130/784 чисто.
Сирот: 0. DOI проверен (полный текст, 20 с., JASA 102:359–378).
