#!/usr/bin/env bash
# Всё в WSL. Один скрипт — всё проверки.
#
# Запуск:
#   wsl -e bash /root/marfagenez/run.sh          # всё
#   wsl -e bash /root/marfagenez/run.sh test     # только тесты
#   wsl -e bash /root/marfagenez/run.sh exp      # только эксперименты
#   wsl -e bash /root/marfagenez/run.sh lean     # только Lean
#   wsl -e bash /root/marfagenez/run.sh reach    # только достижимость файлов
#
# Почему только WSL: Windows-линковка Rust сломана
# (`undefined reference to GetHostNameW`), поэтому `cargo build` на Windows
# падает. Всё собирается и запускается здесь.
#
# Правило всего файла: **вывод фильтруется для человека, код возврата берётся
# от проверки.** Каждый do_* возвращает код своей проверки. Конвейер не может
# стоять последним, если его хвост (`head`, `tail`, `awk`, `grep`) возвращает 0
# независимо от результата: тогда провал выглядит как успех. Вывод пишется во
# временный файл, хвост печатается, код возвращается сохранённым.

set -uo pipefail

export PATH=/root/.elan/bin:/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH
cd /root/marfagenez || { echo "нет /root/marfagenez"; exit 1; }

WHAT="${1:-all}"

# `FAILED` и функция `run()` удалены: `FAILED=1` присваивался, но нигде не
# читался, а `run()` не вызывалась ни разу. Проверка, которая не может
# провалиться, -- не проверка; мёртвая переменная -- не проверка тем более.
# Диспетчер ниже использует `RC`, и только его.

section() {
  echo
  echo "================================================================"
  echo "  $1"
  echo "================================================================"
}

# ---------------------------------------------------------------------------

do_test() {
  section "Rust: тесты"
  # --test-threads=1 обязателен: Lean runtime не потокобезопасен.
  # --tests обязателен: без него cargo запускает ещё и doctest, а rustdoc
  # не установлен, и в выводе появляется ложный `error:`.
  #
  # Раньше код возврата терялся: последним в конвейере стоял `awk`, который
  # возвращает 0 всегда. Провал компиляции давал `библиотек: 0, passed: 0` и
  # код 0 -- то есть ошибка сборки выглядела как успешный прогон нуля тестов.
  local out rc
  out=$(mktemp)
  ( cd core && cargo test --release --tests -- --test-threads=1 ) >"$out" 2>&1
  rc=$?
  grep -E '^test result' "$out" \
    | awk '{p+=$4; f+=$6; n++} END {print "библиотек: " n ", passed: " p ", failed: " f}'
  if [ "$rc" -ne 0 ]; then
    echo "    FAIL: cargo test вернул $rc"
    grep -E '^error' "$out" | head -10
  fi
  rm -f "$out"
  return $rc
}

do_lean() {
  section "Lean: сборка"
  # `lake build` собирается успешно и с `sorry` -- это предупреждение, а не
  # ошибка. Поэтому сборка не ловит дыру в доказательстве, и счётчик `sorry`
  # ниже -- отдельный критерий провала, а не украшение.
  local out rc=0
  out=$(mktemp)
  ( cd laws && lake build ) >"$out" 2>&1 || rc=$?
  grep -E 'Build completed|error' "$out" | head -5
  ( cd laws && lake build Legacy ) >>"$out" 2>&1 || rc=$?
  grep -E 'Build completed|error' "$out" | tail -5
  rm -f "$out"
  echo
  _lean_files=$(ls laws/Medium/*.lean laws/Legacy/*.lean | wc -l)
  _lean_with=$(grep -lE '^(theorem|lemma) ' laws/Medium/*.lean laws/Legacy/*.lean | wc -l)
  echo "файлов:  $(ls laws/Medium/*.lean | wc -l) Medium + $(ls laws/Legacy/*.lean | wc -l) Legacy, из них с теоремами $_lean_with"
  echo "теорем:  $(grep -rhE '^(theorem|lemma) ' laws/Medium/*.lean | wc -l) Medium + $(grep -rhE '^(theorem|lemma) ' laws/Legacy/*.lean | wc -l) Legacy"
  # `sorry` в комментарии — не дыра в доказательстве. Считаем только код:
  # убираем строчные комментарии и блоки /- -/, затем ищем `sorry`.
  local sorry
  sorry=$(python3 - <<'PY'
import glob, re
n = 0
for f in glob.glob('laws/Medium/*.lean') + glob.glob('laws/Legacy/*.lean'):
    t = open(f, encoding='utf-8').read()
    t = re.sub(r'/-.*?-/', '', t, flags=re.S)
    t = re.sub(r'--[^\n]*', '', t)
    n += len(re.findall(r'\bsorry\b', t))
print(n)
PY
)
  echo "sorry:   $sorry"
  if [ "$sorry" -ne 0 ]; then
    echo "    FAIL: $sorry незакрытых sorry -- сборка зелёная, доказательство дырявое"
    rc=1
  fi
  return $rc
}

do_reach() {
  section "Lean: достижимость файлов"
  # LESSONS #1: файл в репозитории не обязательно компилируется.
  # Проверка «.olean = .lean» это не ловит — старые olean-файлы дают равенство,
  # хотя сборка их не читает. Ловит только обход графа импортов.
  python3 checks/reach.py --strict
}

do_exp() {
  section "Эксперименты"
  # Раньше `rc` брался только от contract.py, а код exp05_frozen.py
  # отбрасывался целиком: провал второй проверки был невидим, и прогон с
  # вердиктом `failed` печатал «ВСЁ ЗЕЛЁНОЕ».
  local rc=0
  echo "--- cli_refuses_bad_numbers.sh ---"
  # Бинарник `trace` должен быть собран: скрипт гоняет
  # core/target/release/trace. Его собирает do_test, который в `all`
  # идёт раньше; в `run.sh exp` отдельно -- сначала cargo build.
  bash checks/cli_refuses_bad_numbers.sh || rc=$?
  echo
  echo "--- cli_refuses_bad_numbers_occupancy.sh ---"
  # Тот же дефект, что у `trace`, но в позиционных аргументах `occupancy`:
  # `occupancy 50O` молча прогонял 160 организмов. Бинарник собирает do_test.
  bash checks/cli_refuses_bad_numbers_occupancy.sh || rc=$?
  echo
  echo "--- stub_covers_bridge.py ---"
  python3 checks/stub_covers_bridge.py || rc=$?
  echo
  echo "--- stub_links.sh ---"
  # Список символов и линковка — разные дефекты. stub_covers_bridge.py
  # сравнивает имена; он не заметит, что архив не собрался, а write_stub
  # игнорирует код возврата `ar`. Здесь crate собирается без lean, и
  # отвечает линкер.
  bash checks/stub_links.sh || rc=$?
  echo
  echo "--- contract.py ---"
  python3 checks/contract.py || rc=$?
  echo
  echo "--- mde.py ---"
  # Минимально детектируемый эффект: протокол (п. 3) требует поле `mde` рядом
  # с `arithmetic`. Таблица 3 сигмы × 3 эффекта сверяется с числами разбора
  # (393/16/4, 6280/252/63, 39245/1570/393); --selftest — это и есть проверка,
  # что формула в checks/result.py не разошлась с записанным требованием.
  python3 checks/mde.py --selftest || rc=$?
  echo
  echo "--- damage_clock.py ---"
  # K -- часы урона -- это накопление, а не ceil(1/dr): десять сложений 0.1
  # не дают 1.0, поэтому при dr = 0.1 K = 11. Три контроля: расхождения на
  # десятичной сетке (ровно обратные 1/n), тишина на случайных даблах и то,
  # что причина -- последовательное сложение (fsum и другая ассоциация
  # расхождение снимают). Скрипт дешёвый, поэтому в `exp`.
  python3 checks/damage_clock.py || rc=$?
  echo "--- exp_memory_question.py ---"
  python3 checks/exp_memory_question.py || rc=$?
  echo "--- env_prior_tails.py ---"
  python3 checks/env_prior_tails.py || rc=$?
  echo "--- paper_numbers.py ---"
  python3 checks/paper_numbers.py || rc=$?
  echo "--- life_calibration.py ---"
  python3 checks/life_calibration.py || rc=$?
  echo "--- paper_claims.py ---"
  python3 checks/paper_claims.py || rc=$?
  echo "--- paper_format.py ---"
  python3 checks/paper_format.py || rc=$?
  echo "--- paper_prose.py ---"
  python3 checks/paper_prose.py || rc=$?
  echo "--- readme_features.py ---"
  python3 checks/readme_features.py || rc=$?
  echo "--- protocol_checks.py ---"
  python3 checks/protocol_checks.py || rc=$?
  echo "--- doc_numbers.py ---"
  python3 checks/doc_numbers.py || rc=$?
  echo "--- rng_seed_noise.py ---"
  python3 checks/rng_seed_noise.py || rc=$?
  echo "--- cli_refuses.py ---"
  python3 checks/cli_refuses.py || rc=$?
  echo "--- no_unseeded_random.py ---"
  python3 checks/no_unseeded_random.py || rc=$?
  echo "--- ci_workflow.py ---"
  python3 checks/ci_workflow.py || rc=$?
  echo "--- exp_shape_regulator.py ---"
  python3 checks/exp_shape_regulator.py || rc=$?
  echo "--- exp_division_threshold.py ---"
  # Порог разделения через поток: пять плеч, три контроля, два объявленных совпадения хэшей
  # (`FINDING-290`, `FINDING-292`). Совпадения — часть результата: выше порога починка упирается в предел,
  # а потолок запаса не связывает.
  python3 checks/exp_division_threshold.py || rc=$?
  echo "--- goal_features.py ---"
  python3 checks/goal_features.py || rc=$?
  echo "--- finding_elephant_line.py ---"
  python3 checks/finding_elephant_line.py || rc=$?
  echo "--- embeddings_fresh.py ---"
  # Индекс эмбеддингов обязан быть собран из текущего графа, иначе similar врёт уверенно.
  python3 checks/embeddings_fresh.py || rc=$?
  echo "--- tree_contract.py ---"
  # checks/ не растёт без вызова или записи в LEGACY.txt; probes/ — не гейт.
  python3 checks/tree_contract.py || rc=$?
  echo "--- dip_reports.py ---"
  # Отчёты дипа: партия без отчёта о покрытии — не работа.
  python3 checks/dip_reports.py || rc=$?
  echo "--- map_contract.py ---"
  # Карта: ячейка без доказательства — не ячейка.
  python3 checks/map_contract.py || rc=$?
  echo "--- candidates_quarantine.py ---"
  # Карантин кандидатов: граф не растёт случайно, допуск идёт через журнал.
  python3 checks/candidates_quarantine.py || rc=$?
  echo "--- budget_ledger.py ---"
  # Леджер бюджета: офлайн, без сети; ключ не должен попасть в коммит.
  python3 checks/budget_ledger.py || rc=$?
  echo "--- litsearch_contract.py ---"
  # Снимок поиска: ранги — истина, дедуп и RRF пересчитываются офлайн.
  python3 checks/litsearch_contract.py || rc=$?
  echo "--- results_allowlist.py ---"
  # results/ восстанавливается `git checkout`, поэтому только артефакты прогонов модели.
  python3 checks/results_allowlist.py || rc=$?
  echo "--- literature_contract.py ---"
  # Литературный контракт: машинный уровень записи не может превышать артефакт. Офлайн, секунды.
  python3 checks/literature_contract.py || rc=$?
  echo "--- guard_self_test.py ---"
  python3 checks/guard_self_test.py || rc=$?
  echo
  echo "--- exp_memory_cost.py ---"
  # Цена чтения и поле с пиками: 216 прогонов, 15 с, поэтому в `exp`.
  # Проверяет не только числа, но и то, что цена действительно давит на
  # читающего: контроль `specific` держится на том, что при `read_budget=1`
  # сосед не читается и цена инертна.
  python3 checks/exp_memory_cost.py || rc=$?
  echo
  echo "--- exp_memory_sampling.py ---"
  # Память, которая может не смотреть: read_period > 1 у Memory. 384 прогона,
  # 26 с. Ось обязана трогать только память: `sighted` не меняет хеш при смене
  # периода, а при read_cost = 0 контроль silent молчит. Вердикт записи —
  # void: +33/+37 шагов ниже mde = 250, механизм измерен, размер не подтверждён.
  python3 checks/exp_memory_sampling.py || rc=$?
  echo
  echo "--- exp05_frozen.py ---"
  local out
  out=$(mktemp)
  python3 checks/exp05_frozen.py >"$out" 2>&1
  local rc_exp=$?
  tail -12 "$out"
  rm -f "$out"
  if [ "$rc_exp" -ne 0 ]; then
    echo "    FAIL: exp05_frozen.py вернул $rc_exp"
    rc=1
  fi
  echo
  echo "--- exp99_protocol_capacity.py ---"
  # В отличие от exp05_frozen.py, здесь печатается весь вывод: таблица
  # лестницы и есть результат, а не только вердикт.
  python3 checks/exp99_protocol_capacity.py || rc=$?
  echo
  echo "--- exp_look_order.py ---"
  # Какой порядок несёт информацию: число выживших или соответствие памяти
  # факту. Решающее плечо -- однородное поле, где памяти нечего запоминать:
  # если различие там сохраняется, оно не про точность памяти.
  python3 checks/exp_look_order.py || rc=$?
  echo
  echo "--- log_check.py ---"
  # Числа теорем в живой документации против дерева. Датированные записи
  # (FINDING-*, LESSONS, VISION) не трогаются: это история, а не заявка.
  python3 checks/log_check.py || rc=$?
  echo
  echo "--- hash_version.py ---"
  # Хеш динамики -- это определение «одно плечо» (AGENTS.md §5), и оно
  # верно только внутри одной версии функции. `prev_cell` вошёл в хеш
  # после того, как часть записей была сделана, поэтому старый хеш
  # `40bd71fa379e135a` и новый `f94d3b830971a9e8` -- разные величины под
  # одним именем. Скрипт раскладывает записи на ok/stale/unversioned и
  # падает, если появляется НОВАЯ запись без версии (иначе дефект растёт
  # молча) или если путь из замороженного списка исчез из дерева.
  python3 checks/hash_version.py || rc=$?
  echo
  echo "--- capacity_two_answers.py ---"
  # Две формулы ёмкости в одном репозитории: LAW-capacity.md (жёсткая
  # граница) и capacity_law.py (среднее по ансамблю). Скрипт печатает
  # обе и падает, если порядок нарушится.
  # Скрипт печатает NOTE, когда файлы расходятся, но это не провал:
  # расхождение уже записано в docs/UNREPRODUCIBLE.md. Красным он станет,
  # только если порядок нарушится или точка с bill не найдётся.
  python3 checks/capacity_two_answers.py || rc=$?
  return $rc
}

# Not part of `all`: the three simulations take ~25 minutes each.
# Run explicitly when the tables in laws/Medium/{Budget,Corrected,Child}.lean change.
do_models() {
  section "Модели из laws/Medium (Budget, Corrected, Child)"
  # Таблицы в Budget.lean и Corrected.lean были помечены [UNVERIFIED]: числа не
  # воспроизводились ни одним скриптом. Здесь они воспроизводятся.
  local rc=0
  echo "--- budget_model.py ---"
  python3 checks/budget_model.py 2>&1 | tail -8 || rc=$?
  echo
  echo "--- corrected_model.py ---"
  python3 checks/corrected_model.py 2>&1 | tail -8 || rc=$?
  echo
  echo "--- room_model.py ---"
  python3 checks/room_model.py 2>&1 | tail -8 || rc=$?
  return $rc
}

do_verus() {
  section "Verus: целочисленные законы"
  # docs/CLAIMS.md:90 заявляет «Verus — 41 verified», :110 даёт команду
  # `verus verus/integer_laws.rs`. Заявление было без проверки: в этом файле
  # слово verus не встречалось ни разу, и провал Verus был невидим.
  #
  # Отсутствие verus в PATH -- провал, а не пропуск: заявление без проверки
  # и есть дефект (GOAL.md §4: формулировка сильнее статуса -- дефект).
  if ! command -v verus >/dev/null 2>&1; then
    echo "    FAIL: verus не найден в PATH"
    return 1
  fi
  local out rc
  out=$(mktemp)
  verus verus/integer_laws.rs >"$out" 2>&1
  rc=$?
  grep -E 'verification results|error' "$out" | tail -5
  rm -f "$out"
  return $rc
}

do_kg() {
  section "Граф знаний (инварианты и ссылки)"
  # Своя обёртка: у run.sh нет общего do_py, а терять код возврата нельзя --
  # иначе раздел печатает отчёт и «проходит» при любой ошибке.
  local out rc
  out=$(mktemp)
  python3 kg/kg.py check --refs >"$out" 2>&1
  rc=$?
  tail -20 "$out"
  rm -f "$out"
  # Second gate: the corpus, not the generated file, is the source of truth,
  # and import must not move a status by itself (D-07).
  python3 kg/regress.py
  local rrc=$?
  # F2: цена обязана быть производной функции значения, а не правилом по флагу.
  python3 checks/bridge_price_derivative.py || rrc=1
  if [ "$rrc" -ne 0 ] && [ "$rc" -eq 0 ]; then
    rc=$rrc
  fi
  return $rc
}

do_claims() {
  section "Проверки утверждений (verify_all.js)"
  # Без seed проверка была разным экспериментом при каждом запуске:
  # одно и то же утверждение проходило и падало без изменения кода.
  # Теперь seed фиксирован, повтор прогона обязан дать тот же результат.
  # node есть и в Windows, и в WSL; вызываем через powershell.exe, потому что
  # так исторически работает и это проверено.
  local out rc
  # `| tail` вернул бы код tail, а не node -- провал проверки стал бы
  # невидимым. Поэтому сначала пишем в файл, потом печатаем хвост.
  out=$(mktemp)
  # Node есть и в WSL, и в Windows. Раньше вызов шёл только через
  # powershell.exe: без него (или из окружения без Windows в PATH) проверка
  # не запускалась вовсе, а код возврата терялся. Теперь сначала пробуем
  # node из самого WSL и только потом powershell.exe.
  if command -v node >/dev/null 2>&1; then
    node "$PWD/checks/verify_all.js" >"$out" 2>&1
    rc=$?
  else
    local win
    win=$(wslpath -w "$PWD/checks/verify_all.js")
    powershell.exe -NoProfile -Command "node '$win'" >"$out" 2>&1
    rc=$?
  fi
  tail -4 "$out"
  # Код возврата powershell.exe ничего не значит: он 0 и когда node упал.
  # Единственный признак успеха -- строка вердикта в выводе.
  if grep -q 'ALL CLAIMS VERIFIED' "$out"; then
    rc=0
  else
    rc=1
  fi
  rm -f "$out"
  return $rc
}

do_audit() {
  section "Аудит численных утверждений (audit.js)"
  # audit.js проверял те же численные утверждения, что и verify_all.js, но
  # не запускался ниоткуда: проверка была, а гейта не было. Красный аудит
  # ничего не останавливал.
  #
  # Заодно закрыт seed: до этого в файле стоял Math.random, и одно и то же
  # утверждение проходило и падало без изменения кода, а провал нельзя было
  # воспроизвести. Теперь seed печатается и принимается через --seed N.
  local out rc
  out=$(mktemp)
  if command -v node >/dev/null 2>&1; then
    node "$PWD/checks/audit.js" >"$out" 2>&1
    rc=$?
  else
    local win
    win=$(wslpath -w "$PWD/checks/audit.js")
    powershell.exe -NoProfile -Command "node '$win'" >"$out" 2>&1
    rc=$?
  fi
  tail -4 "$out"
  # Код возврата powershell.exe ничего не значит, а `| tail` вернул бы код
  # tail. Единственный признак успеха -- строка вердикта в выводе.
  if grep -q 'claims verified' "$out" && ! grep -q '^FAIL' "$out"; then
    rc=0
  else
    rc=1
  fi
  rm -f "$out"
  return $rc
}

do_export() {
  section "Экспорт в визуализатор"
  python3 checks/export.py
}

check_doc_links() {
  echo "    проверка ссылок в документации"
  python3 checks/doc_links.py || return 1
}

do_agents() {
  section "Контракт агента"
  # Состояние агента -- часть контракта, а не дневник. AGENT_STATE.md обязан
  # отражать последний коммит: иначе следующий агент читает память, которая
  # врёт о том, где проект.
  #
  # Сравнение по истории Git, а не по времени файла: после clone/checkout/
  # переноса workspace mtime врёт. Оба файла в одном коммите -- зелёный.
  local rc=0
  if [ ! -f AGENTS.md ]; then
    echo "    FAIL: нет AGENTS.md (на него ссылаются checks/contract.py,"
    echo "          checks/experiment.py, checks/result.py)"
    rc=1
  else
    local s
    for s in 1 2 3 4 5 6; do
      if ! grep -qE "^## §${s}[ .]" AGENTS.md; then
        echo "    FAIL: в AGENTS.md нет раздела §$s"
        rc=1
      fi
    done
  fi
  if [ ! -f docs/agent/AGENT_STATE.md ]; then
    echo "    FAIL: нет docs/agent/AGENT_STATE.md"
    rc=1
  else
    # Состояние обязано быть не старше последнего содержательного коммита.
    # Раньше требовалось точное равенство с HEAD, и это было невыполнимо:
    # любой коммит, который не трогает AGENT_STATE.md (запись прогона,
    # правка журнала), делал гейт красным, и обойти это можно было только
    # подмешивая пустую правку состояния в каждый коммит. Гейт, который
    # требует врать в файле состояния, защищает не правду, а ритуал.
    #
    # Теперь: состояние должно быть предком HEAD (или самим HEAD), а
    # коммиты между ними не должны трогать код модели, законы и проверки.
    # Запись прогона в results/ состояние не меняет - прогон ничего не
    # говорит о том, где проект.
    local head state
    head=$(git rev-parse HEAD)
    state=$(git log -1 --format=%H -- docs/agent/AGENT_STATE.md)
    if [ -z "$state" ]; then
      echo "    FAIL: docs/agent/AGENT_STATE.md не закоммичен"
      rc=1
    elif ! git merge-base --is-ancestor "$state" HEAD 2>/dev/null; then
      echo "    FAIL: docs/agent/AGENT_STATE.md не является предком HEAD"
      echo "          HEAD:  $head"
      echo "          state: $state"
      rc=1
    elif [ "$head" != "$state" ]; then
      local drift
      drift=$(git diff --name-only "$state"..HEAD -- \
        core laws verus checks run.sh AGENTS.md 2>/dev/null)
      if [ -n "$drift" ]; then
        echo "    FAIL: состояние отстало от изменения модели, законов или проверок"
        echo "          state: $state"
        echo "          изменилось после него:"
        echo "$drift" | sed 's/^/            /'
        echo "          обнови docs/agent/AGENT_STATE.md и закоммить вместе с изменением"
        rc=1
      fi
    fi
  fi
  # Ссылки в документации -- часть контракта: битая ссылка стоит круга догадок.
  check_doc_links || rc=1
  return $rc
}

# ---------------------------------------------------------------------------

# Диспетчер `all` обязан сохранять первый провал: голый `|| RC=$?` затирал
# его следующим успехом. Проверка подменяет `do_*` заглушками и смотрит на
# пару (баннер, код), поэтому ловит регрессию в самом `case`, а не только
# в функциях.
do_dispatcher() {
  echo "=== диспетчер: провал не теряется ==="
  python3 checks/dispatcher.py
}

# ---------------------------------------------------------------------------

# Каждая проверка записывается в RC, если он ещё ноль. Голый `|| RC=$?`
# затирал предыдущий провал следующим успехом: `exp` падал, `agents`
# проходил, и `all` печатал «ВСЁ ЗЕЛЁНОЕ» с кодом 0. Тот же дефект, что уже
# чинили в do_lean и do_exp, только на уровне диспетчера: провал выглядел
# как успех, потому что последним в списке стоял тот, кто прошёл.
#
# `keep` не маскирует код: первый провал и есть причина, остальные --
# следствия того же прогона.
# Имя провалившегося раздела печатается сразу, а не теряется в выводе:
# `all` кончался на «ЕСТЬ ПРОВАЛЫ (код 1)» без единой подсказки, какой из
# девяти разделов дал код. `FAILED` копится, чтобы итог назвал все.
FAILED=""
# Виновник провала должен быть назван, а не выведен из лога.
#
# `keep` копит код, но не говорит, ЧЕЙ он: раздел `exp` состоит из сорока
# шагов, и красный прогон показывает только «провалился exp». Один раз это
# стоило часа догадок (`FINDING-197`), а ответ дала одна трассировка.
#
# Трассировка пишется в файл всегда — на экран её никто не выводит, — и при
# ненулевом коде последняя строка `+ rc=` называет шаг.
TRACE=/tmp/marfagenez-run-trace.log
: > "$TRACE"
exec 9>"$TRACE"
BASH_XTRACEFD=9
set -x

last_failed_step() {
  # Строка трассы перед присваиванием `rc=` и есть провалившийся шаг.
  grep -B1 '^+ rc=' "$TRACE" 2>/dev/null | grep -v '^+ rc=' | grep -v '^--$' | tail -1
}
keep_q() {
  # exit code of the previous command, captured in a function body
  local rc
  rc=$?
  keep "$rc" kg
}
keep() {
  local rc=$1 name=$2
  if [ "$rc" -ne 0 ]; then
    echo ">>> РАЗДЕЛ ПРОВАЛЕН: $name (код $rc)"
    FAILED="$FAILED $name"
    if [ "$RC" -eq 0 ]; then RC=$rc; fi
  fi
  return 0
}

RC=0
case "$WHAT" in
  test)   do_test;   keep $? test ;;
  lean)   do_lean;   keep $? lean ;;
  reach)  do_reach;  keep $? reach ;;
  dispatcher) do_dispatcher; keep $? dispatcher ;;
  exp)    do_exp;    keep $? exp ;;
  kg)     do_kg;     keep_q kg ;;
  models) do_models; keep $? models ;;
  verus)  do_verus;  keep $? verus ;;
  claims) do_claims; keep $? claims ;;
  audit)  do_audit;  keep $? audit ;;
  export) do_export; keep $? export ;;
  agents) do_agents; keep $? agents ;;
  all)
    do_test;   keep $? test
    do_lean;   keep $? lean
    do_reach;  keep $? reach
    do_dispatcher; keep $? dispatcher
    do_verus;  keep $? verus
    do_exp;    keep $? exp
    do_kg;     keep $? kg
    do_claims; keep $? claims
    do_audit;  keep $? audit
    do_export; keep $? export
    do_agents; keep $? agents
    ;;
  *)
    echo "usage: run.sh [all|test|lean|reach|dispatcher|verus|exp|models|kg|claims|audit|export|agents]"
    exit 2
    ;;
esac

echo
set +x
if [ "$RC" -ne 0 ]; then
  echo "ЕСТЬ ПРОВАЛЫ (код $RC): провалились разделы:$FAILED"
  step=$(last_failed_step)
  if [ -n "$step" ]; then
    echo ">>> последний провалившийся шаг: $step"
  fi
  echo ">>> трассировка: $TRACE"
  exit 1
fi
set +x
echo "ВСЁ ЗЕЛЁНОЕ"
