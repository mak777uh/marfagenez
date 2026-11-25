# RESULT — S7-раунд 10 (очередь L-*): L-042, источник закрыт

## Цель
L-042 «Chemical organization theory: формальное замыкание» — у узла был DOI,
работы в карте не было.

## DOI
10.1007/s11538-006-9130-8 — Dittrich & Speroni di Fenizio — «Chemical
Organisation Theory», Bull Math Biol 2007. OA-версия: arXiv:q-bio/0501016
(PDF получен, 20 с., полный текст).

## Новые ячейки: FAST-S7J-01..05 (5 шт., домен bio.closure)
- 01 definition: organization = closed ∧ mass-maintaining (Def.7);
  Mv ≥ 0 покомпонентно; mass-maintaining ⟹ self-maintaining.
- 02 mechanism: замкнутые множества образуют решётку OCL; GCL(S) —
  наименьшее замкнутое, содержащее S.
- 03 mechanism: Theorem 1 — абстракция неподвижной точки φ(x′) (xi>Θ)
  является организацией: динамика ↔ статика.
- 04 mechanism: любой аттрактор A ⊆ X имеет организацию-генератор; траектория
  = движение по решётке организаций (E. coli sugar metabolism, 76 видов).
- 05 definition: иерархия closure ⊂ self-maintenance ⊂ semi-org ⊂ org.

## Рёбра: 8
Внутренние: 05→01, 03→01, 04→03, 02→01 supports.
К карте: 01→DIP3-0004 supports (канон COT-определения);
05→C-0004 supports (Mv≥0 = формализация взаимной зависимости);
03→C-0006 refines (шаг к количественной формуле организации);
04→DIP3-0002 analogous (решётка vs RAF).

## kg_ref
L-042 у всех пяти — один источник, узел про формальное замыкание COT.

## Что подтвердилось / что НЕВЕРНО в узле
- **Узел неточен**: «замкнутое по реакциям и самоподдерживающееся» — это
  определение SEMI-ORGANIZATION (Def.5: closed + self-maintaining).
  Настоящая ORGANIZATION (Def.7) требует closed + MASS-MAINTAINING
  (стехиометрический вектор Mv≥0), что строже и влечёт self-maintenance.
  Внесено в notes атомов 01 и 05 и здесь — это результат раунда.
- Подтвердилось: формальное замыкание существует и образует решётку;
  организации соответствуют аттракторам динамики.

## Проверки
map_contract merged: 0 нарушений; после отката 1130/784 чисто.
Сирот: 0. DOI проверен (arXiv q-bio/0501016, полный текст).
