# FINDING-236. Пункт D-3 (CI) упирается в права токена, а не в код

**Дата:** 2026-11-18. **Статус:** **заблокирован извне**. **Цикл:** 177.

## Что произошло

Пункт D-3 плана — CI в `.github/workflows`. Файл написан, проверен локально и **не может быть
доставлен**:

```
! [remote rejected] master -> master
  (refusing to allow an OAuth App to create or update workflow
   `.github/workflows/gate.yml` without `workflow` scope)
```

GitHub **отказывается** принимать файлы workflow от OAuth-приложения без области `workflow`. Это
**не** ошибка содержимого: тот же коммит без файла workflow прошёл раньше и пройдёт снова.

## Почему это не «сделано»

Соблазн записать D-3 выполненным был, и это было бы ложью: файла в репозитории нет, CI не запустится
никогда. Соблазн оставить красный гейт тоже был — но тогда **постоянная краснота** скрыла бы настоящие
падения за правом, которое может дать только владелец. Поэтому:

- `.github/workflows/gate.yml` **не добавлен в репозиторий**;
- `checks/ci_workflow.py` печатает **`OPEN`**, а не `FAIL`, и называет причину;
- пункт D-3 в плане остаётся **открытым** с этой причиной.

## Что нужно от владельца

Одно действие, и оно не техническое: **выдать токену область `workflow`** (в настройках GitHub —
fine-grained token с правом Workflows: write, либо classic token со scope `workflow`), после чего
файл добавляется одним коммитом без правок.

## Содержимое, готовое к добавлению

```yaml
name: gate
on:
  push:
    branches: [master]
  pull_request:
  workflow_dispatch:
jobs:
  gate:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - name: Rust toolchain
        uses: dtolnay/rust-toolchain@stable
      - name: Cache cargo
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            core/target
          key: cargo-${{ hashFiles('core/Cargo.lock') }}
      - name: Rust tests
        working-directory: core
        run: cargo test --release -- --test-threads=1
      - name: Lean toolchain
        uses: leanprover/lean-action@v1
        with:
          auto-config: false
          build: false
          use-github-cache: true
      - name: Lean build
        working-directory: laws
        run: lake build
      - name: Python checks
        run: |
          python3 -m pip install --upgrade pip
          bash run.sh all
```

## Что проверено локально

Сам файл проверялся, пока лежал в дереве (`checks/ci_workflow.py`, `pyyaml`): валидный YAML, три
стадии (`cargo test`, `lake build`, `run.sh all`), триггер на `push`, все пути существуют, и в файле
стояла оговорка «NOT RUN ON A RUNNER». **На раннере он не запускался и сейчас** — первое исполнение
останется опытом.

## Что это доказывает

- **Код готов, доставка — нет.** Это первый случай за сессию, когда ограничение пришло **извне**, а не
  из модели или документа.
- **«Сделано» и «доставлено» — разные вещи**, и записывать первое вместо второго нельзя.

## Что это не доказывает

- Не доказывает, что workflow **правильный**: он не исполнялся.
- Не доказывает, что в репозитории нет других путей поставки (например, добавление файла вручную через
  веб-интерфейс).
