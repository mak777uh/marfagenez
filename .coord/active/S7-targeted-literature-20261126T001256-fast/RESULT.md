# RESULT — S7-раунд 16 (очередь L-*): L-062, источник закрыт

## Цель
L-062 «Двойственные переменные LP — это химические потенциалы» — у узла был
DOI, работы в карте не было. Побочный выигрыш: прямая литература для C-002
(теневые цены измерены и интерпретированы).

## DOI
10.1103/physrevlett.99.108101 — Warren & Jones — «Duality, Thermodynamics,
and the Linear Programming Problem in Constraint-Based Models of Metabolism»,
PRL 2007. OA: arXiv:q-bio/0702021 (PDF, 4 с., полный текст).

## Новые ячейки: FAST-S7P-01..05 (5 шт., домен chem.dissipative)
- 01 mechanism: dual LP CBM → μ_i=−π_i·B* как химические потенциалы;
  shadow price = −μ_i/B*.
- 02 formula: правила B_α (0 reversible, ≤0 irreversible, ≤−B* growth) +
  цель min Σvmin·|B_α|.
- 03 formula: MEP-пинчинг z ≤ TṠ/B* ≤ w — выведен из дуальности.
- 04 measurement: E. coli genome-scale — μ_i>0, распределение по декадам,
  рост с молекулярной сложностью.
- 05 condition: B_α ≠ A_α — LP-семантика, не кинетическая термодинамика;
  вырождение primal↔dual.

## Рёбра: 8
Внутренние: 02→01, 03→02, 04→01 supports; 05→01, 05→03 condition.
К карте: 01→DIP28-0001 analogous (потенциалы vs DEB-аллокация);
04→B7-05-0001 analogous (цена потока в рост);
03→DIP22B-0006 analogous (MEP: LP vs σ-правило).

## kg_ref
L-062 у всех пяти — один источник, узел про двойственные переменные LP.

## Что подтвердилось / что неверно
- Подтверждено полностью: dual variables LP в CBM = химические потенциалы
  (analogue), теневые цены = −μ_i/B*; есть формулы и измеренный пример
  (E. coli).
- Для C-002: теневые цены здесь ИЗМЕРЕНЫ (genome-scale E. coli) — первый
  кандидат на «измеренный shadow price»; прыжки при связывании ограничений
  = вырождение dual (обсуждается в тексте).
- Ошибок в узле не найдено.

## Проверки
map_contract merged: 0 нарушений. Сирот: 0. DOI проверен (arXiv полный текст).
