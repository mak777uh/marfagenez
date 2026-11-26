# Проверка 10 предложенных `check`-строк

**Дата:** 26.11.2026. **Источник:** `docs/KG-CHECKS.jsonl` (внешний агент, ночная смена).
**Инструмент:** `tools/kg_check_verify.py` — тянет аннотацию (OpenAlex inverted index, резерв EuropePMC)
и проверяет, что `quote` — подстрока после нормализации.

## Результат

| узел | уровень | вердикт | цитата |
|---|---|---|---|
| `F-012` | `abstract_read` | подтверждено в аннотации | The Price equation partitions total evolutionary change into two compo |
| `F-026` | `abstract_read` | подтверждено в аннотации | variance proneness evolves in fine-grained environments (lower correla |
| `F-016` | `abstract_read` | подтверждено в аннотации | In (st)age-structured populations, the long-run population growth rate |
| `F-005` | `full_text_examined` | нужен полный текст (цитата не из аннотации) | in accordance to the kappa rule: a proportion κ (−) is used for somati |
| `F-021` | `full_text_examined` | нужен полный текст (цитата не из аннотации) | This implies that somatic processes have priority over allocation to r |
| `F-013` | `full_text_examined` | нужен полный текст (цитата не из аннотации) | For birth–death processes, the stationary distribution can be calculat |
| `F-007` | `abstract_read` | подтверждено в аннотации | We also show that for long genomes and/or highly dynamic fitness lands |
| `F-008` | `abstract_read` | подтверждено в аннотации | we identify the viability kernel—the largest state-space region where  |
| `F-025` | `abstract_read` | подтверждено в аннотации | This mathematical formulation yields three principled and distinct for |
| `F-028` | `full_text_examined` | нужен полный текст (цитата не из аннотации) | the mean cell size in a forward lineage is independent of the division |

**Подтверждено в аннотации: 6 из 10.** Нужен полный текст: 4.

## Почему не все подтверждены

Четыре строки (`F-005`, `F-021`, `F-013`, `F-028`) помечены `full_text_examined` — цитата взята из
**полного текста**, а я проверял по аннотации. Отсутствие цитаты в аннотации **не отменяет** её:
это значит «нужна проверка по полному тексту».

## Что это меняет для фронтира

Шесть узлов (`F-012`, `F-026`, `F-016`, `F-007`, `F-008`, `F-025`) получили подтверждённую цитату из
аннотации источника. Это **готовый материал для сдвига фронтира**, но повышение `epistemic` я делаю
отдельным шагом: цитата из аннотации подтверждает упоминание, а не саму формулу.

## Правило на будущее (передать агенту)

Если цитата из полного текста — помечай `level: full_text_examined` **и** приводи короткий фрагмент,
который есть в аннотации, если такой существует. Тогда проверка автоматическая.
