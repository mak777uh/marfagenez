# `lab/workcells/experiments/ROLE.md` — контур экспериментов

**Версия:** 1.0. Устав: `lab/CHARTER.md`. Схема задачи: `task.schema.json` (`spec.mode=experiment`).
**Каталог:** `lab/workcells/experiments/` — проекции `inbox/`, `outbox/`, `messages/`, `accepted/`; истина read/ack — в БД.

## Назначение

Воспроизводимые эксперименты над Rust-движком (`core/`): проверка гипотез, измерение эффектов, контроли и регрессии. Результат — данные и выводы, не правки научного ядра.

## Вход: что исполнитель получает в задаче

- гипотезу и точную целевую постановку (`spec.hypothesis`, `target_setup`);
- арифметику и ожидаемый масштаб эффекта (`expected_effect`);
- параметры, оси и seed (`parameters`, `axes`, `seeds`);
- контроли `fires` / `silent` / `specific` — все три обязательны;
- ссылки на прежние результаты и узлы графа;
- content-addressed снапшот входов (`inputs` с хэшами);
- `base_commit`, `write_scope`, budget, validator profiles;
- pins: `rust-toolchain`, `Cargo.lock`, `RUSTFLAGS`, target, образ песочницы.

## Правила работы

1. Воспроизвести базовый прогон на выданном снапшоте до любых изменений.
2. Реализовать эксперимент или патч только в `write_scope`.
3. Зафиксировать seed, toolchain и окружение; никаких незадекларированных случайностей (`no_unseeded_random`).
4. Выполнить все три контроля; сохранить полные результаты, а не только красивые.
5. Не менять гипотезу, определения и gates. Новая гипотеза — proposal, не самовольная работа.
6. `network_profile` по умолчанию `none`; heartbeat живого lease не блокируется сообщениями.
7. Claim/heartbeat/submit — через сервис, с `lease_id`/`lease_epoch` и `Idempotency-Key`.

## Выход (bundle в `submission/v1`)

- `design.md` или JSON-дизайн;
- код/патч;
- параметры и seed;
- сырые результаты (полностью) и агрегированные таблицы;
- хэши динамики (`hash_version`);
- `scientific_outcome`: `passed`, `failed`, `void`, `not_applicable`, `insensitive_by_construction`;
- `limitations` — что результат не доказывает (обязательное поле);
- описание воспроизведения в `reproduce` (для аудита; исполняет валидатор по профилям, не сам исполнитель);
- предлагаемые связи с формулами и графом в `links`.

## Валидация (профиль экспериментов)

- сборка Rust в зафиксированном toolchain и чистой candidate tree;
- запуск experiment profile с точным argv, без shell;
- `cargo test --test-threads=1` там, где общий Lean/runtime небезопасен при потоках;
- сверка seed, параметров, toolchain и хэшей; проверка контролей;
- существующие trusted `checks/` и golden-тесты;
- absence незадекларированной сети;
- floating-point reductions: детерминированный порядок, однопоточный режим либо tolerance-сравнение агрегатов.

Если bundle меняет `checks/`, `tools/`, `run.sh` или build-конфигурацию — результат эскалируется main и авто-зелёный невозможен.

## Автономность

Всё внутри выданной гипотезы и `write_scope`. Новая гипотеза, правка определений, ворот или порогов — proposal с revision/CAS.
