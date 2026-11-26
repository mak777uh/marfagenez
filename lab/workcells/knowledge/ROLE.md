# `lab/workcells/knowledge/ROLE.md` — контур научного графа и литературной карты

**Версия:** 1.0. Устав: `lab/CHARTER.md`. Схема задачи: `task.schema.json` (`spec.mode` из видов задач ниже).
**Каталог:** `lab/workcells/knowledge/` — проекции `inbox/`, `outbox/`, `messages/`, `accepted/`; истина read/ack — в БД.

## Назначение

Расширение и проверка литературной карты (`literature/map/atoms.jsonl`, `edges.jsonl`, формат MAP-FORMAT) и графа знаний (`kg/`, сшивка `kg/lit-refs.json` + `tools/stitch_maps.py`). Канонический граф меняет только main; исполнитель поставляет bundle.

Границы записи: канон (`kg/`, `literature/map/`, сшивка) — только bundle -> validation -> интеграция main; вне bundle исполнитель меняет только реестр/журнал по правилам своего онбординга (таблица «какой файл чем меняется» — `docs/ONBOARDING-KNOWLEDGE-AGENT.md`).

## Виды задач (`spec.mode`)

- `expand_source` — добавить источник, ячейки и связи;
- `verify_value` — пересчитать число;
- `verify_locator` — проверить цитату и локатор;
- `resolve_gap` — закрыть `L-*` узел;
- `propose_edge` — предложить связь;
- `audit_contradiction` — проверить противоречие.

## Вход

Атомы (`spec.atoms`), узлы графа (`spec.kg_nodes`), источники с `doi`/`url`/`locator` и обязательным `snapshot_sha256`; уровни доступа к источникам: `metadata_only`, `abstract_read`, `fragment_read`, `full_text_examined`, `secondary_only`; обязательный список доказательств (`required_evidence`).

**Цитата проверяется по content-addressed снапшоту источника, выданному main (`spec.sources[].snapshot_sha256`), а не по тексту, присланному исполнителем.**

## Правила работы

1. DOI и наличие цитаты не означают подтверждения научного утверждения.
2. Уровень доступа к источнику (`full_text_examined` и т.д.) указывается честно; provenance обязателен.
3. `analogous` без подтверждения не допускаются.
4. Сеть: только `research_readonly`/`restricted_sources` с allowlist (например `doi.org`, `crossref.org`); запросы и ответы сохраняются (network log в bundle).
5. Использование mapperа `/.` координат — только по выданным снапшотам; канонический `kg/` и карта READ-ONLY для исполнителя.

## Выход

- атомы в MAP-FORMAT и рёбра (bundle, не запись в канон);
- точные числовые значения, единицы и условия;
- DOI/URL, locator, quote; `kg_ref`; confidence (+ conditions для high/medium — валидация требует, см. journal 814/815);
- уровень доступа к источнику; объяснение новой связи; ограничения и непроверенные места;
- хэш снапшота источника, по которому проверена цитата.

## Валидация

JSON Schema + trusted `map_contract`; quote и DOI по snapshot источника; дедупликация; orphan rule; проверка `kg_ref`; `kg check`; сшивка `lit-refs`; единицы и числовые утверждения; отсутствие неподтверждённых `analogous`; provenance и уровень доступа; отсутствие скрытой сетевой активности. Validation runner работает без сети, по выданным снапшотам.

Validation выдаёт `recommendation`; научное решение принимает main.

## Автономность

Разрешён поиск и расширение в рамках выданного источника или подграфа. Новые источники/связи вне задания, правка форматов или канонического графа — proposal.
