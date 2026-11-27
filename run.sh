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
# `all` — ровно 11 разделов, в этом порядке:
#   1 test, 2 lean, 3 reach, 4 dispatcher, 5 verus, 6 exp,
#   7 kg, 8 claims, 9 audit, 10 export, 11 agents.
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
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit 1
cd "$ROOT" || { echo "нет каталога скрипта: $ROOT"; exit 1; }

WHAT="${1:-all}"
if [ "$WHAT" = all ]; then
  echo "all: 12 разделов — test, lean, reach, dispatcher, verus, exp, kg, claims, audit, export, agents, lab"
fi

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

exp_lane1() {
  # Тяжёлые симуляции, лана 1. bad несёт код; имена провалов печатает LANE1_FAIL.
  local bad=0
  echo "--- cli_refuses_bad_numbers.sh ---"
  bash checks/cli_refuses_bad_numbers.sh || { echo "LANE1_FAIL cli_refuses_bad_numbers.sh"; bad=1; }
  echo "--- cli_refuses_bad_numbers_occupancy.sh ---"
  bash checks/cli_refuses_bad_numbers_occupancy.sh || { echo "LANE1_FAIL cli_refuses_bad_numbers_occupancy.sh"; bad=1; }
  echo "--- exp_memory_cost.py ---"
  python3 checks/exp_memory_cost.py || { echo "LANE1_FAIL exp_memory_cost.py"; bad=1; }
  echo "--- exp_memory_sampling.py ---"
  python3 checks/exp_memory_sampling.py || { echo "LANE1_FAIL exp_memory_sampling.py"; bad=1; }
  echo "--- exp_division_threshold.py ---"
  python3 checks/exp_division_threshold.py || { echo "LANE1_FAIL exp_division_threshold.py"; bad=1; }
  echo "--- exp_shape_regulator.py ---"
  python3 checks/exp_shape_regulator.py || { echo "LANE1_FAIL exp_shape_regulator.py"; bad=1; }
  return $bad
}
exp_lane2() {
  # Тяжёлые симуляции, лана 2.
  local bad=0 out
  echo "--- exp05_frozen.py ---"
  out=$(mktemp)
  if python3 checks/exp05_frozen.py >"$out" 2>&1; then tail -12 "$out"; else tail -12 "$out"; echo "LANE2_FAIL exp05_frozen.py"; bad=1; fi
  rm -f "$out"
  echo "--- exp99_protocol_capacity.py ---"
  python3 checks/exp99_protocol_capacity.py || { echo "LANE2_FAIL exp99_protocol_capacity.py"; bad=1; }
  echo "--- exp_look_order.py ---"
  python3 checks/exp_look_order.py || { echo "LANE2_FAIL exp_look_order.py"; bad=1; }
  echo "--- life_calibration.py ---"
  python3 checks/life_calibration.py || { echo "LANE2_FAIL life_calibration.py"; bad=1; }
  echo "--- env_prior_tails.py ---"
  python3 checks/env_prior_tails.py || { echo "LANE2_FAIL env_prior_tails.py"; bad=1; }
  echo "--- exp_memory_question.py ---"
  python3 checks/exp_memory_question.py || { echo "LANE2_FAIL exp_memory_question.py"; bad=1; }
  echo "--- damage_clock.py ---"
  python3 checks/damage_clock.py || { echo "LANE2_FAIL damage_clock.py"; bad=1; }
  echo "--- rng_seed_noise.py ---"
  python3 checks/rng_seed_noise.py || { echo "LANE2_FAIL rng_seed_noise.py"; bad=1; }
  return $bad
}
exp_lane3() {
  # Аудиты дерева и контрактов, лана 3.
  local bad=0
  echo "--- stub_covers_bridge.py ---"
  python3 checks/stub_covers_bridge.py || { echo "LANE3_FAIL stub_covers_bridge.py"; bad=1; }
  echo "--- stub_links.sh ---"
  bash checks/stub_links.sh || { echo "LANE3_FAIL stub_links.sh"; bad=1; }
  echo "--- contract.py ---"
  python3 checks/contract.py || { echo "LANE3_FAIL contract.py"; bad=1; }
  echo "--- mde.py ---"
  python3 checks/mde.py --selftest || { echo "LANE3_FAIL mde.py"; bad=1; }
  echo "--- paper_numbers.py ---"
  python3 checks/paper_numbers.py || { echo "LANE3_FAIL paper_numbers.py"; bad=1; }
  echo "--- paper_claims.py ---"
  python3 checks/paper_claims.py || { echo "LANE3_FAIL paper_claims.py"; bad=1; }
  echo "--- paper_format.py ---"
  python3 checks/paper_format.py || { echo "LANE3_FAIL paper_format.py"; bad=1; }
  echo "--- paper_prose.py ---"
  python3 checks/paper_prose.py || { echo "LANE3_FAIL paper_prose.py"; bad=1; }
  echo "--- readme_features.py ---"
  python3 checks/readme_features.py || { echo "LANE3_FAIL readme_features.py"; bad=1; }
  echo "--- protocol_checks.py ---"
  python3 checks/protocol_checks.py || { echo "LANE3_FAIL protocol_checks.py"; bad=1; }
  echo "--- doc_numbers.py ---"
  python3 checks/doc_numbers.py || { echo "LANE3_FAIL doc_numbers.py"; bad=1; }
  echo "--- stitch_coverage_floor.py ---"
  python3 checks/stitch_coverage_floor.py || { echo "LANE3_FAIL stitch_coverage_floor.py"; bad=1; }
  echo "--- formula_units_ceiling.py ---"
  python3 checks/formula_units_ceiling.py || { echo "LANE3_FAIL formula_units_ceiling.py"; bad=1; }
  echo "--- units_symbol_audit.py ---"
  python3 tools/units_symbol_audit.py --strict || { echo "LANE3_FAIL units_symbol_audit.py"; bad=1; }
  echo "--- map_duplicates.py ---"
  python3 tools/map_duplicates.py --strict || { echo "LANE3_FAIL map_duplicates.py"; bad=1; }
  echo "--- map_orphans.py ---"
  python3 tools/map_orphans.py --strict || { echo "LANE3_FAIL map_orphans.py"; bad=1; }
  echo "--- wiring_audit.py ---"
  python3 tools/wiring_audit.py --strict || { echo "LANE3_FAIL wiring_audit.py"; bad=1; }
  echo "--- unanchored_nodes.py ---"
  python3 tools/unanchored_nodes.py --strict || { echo "LANE3_FAIL unanchored_nodes.py"; bad=1; }
  echo "--- support_sources.py ---"
  python3 checks/support_sources.py || { echo "LANE3_FAIL support_sources.py"; bad=1; }
  echo "--- cli_refuses.py ---"
  python3 checks/cli_refuses.py || { echo "LANE3_FAIL cli_refuses.py"; bad=1; }
  echo "--- no_unseeded_random.py ---"
  python3 checks/no_unseeded_random.py || { echo "LANE3_FAIL no_unseeded_random.py"; bad=1; }
  echo "--- ci_workflow.py ---"
  python3 checks/ci_workflow.py || { echo "LANE3_FAIL ci_workflow.py"; bad=1; }
  echo "--- goal_features.py ---"
  python3 checks/goal_features.py || { echo "LANE3_FAIL goal_features.py"; bad=1; }
  echo "--- finding_elephant_line.py ---"
  python3 checks/finding_elephant_line.py || { echo "LANE3_FAIL finding_elephant_line.py"; bad=1; }
  echo "--- embeddings_fresh.py ---"
  python3 checks/embeddings_fresh.py || { echo "LANE3_FAIL embeddings_fresh.py"; bad=1; }
  echo "--- tree_contract.py ---"
  python3 checks/tree_contract.py || { echo "LANE3_FAIL tree_contract.py"; bad=1; }
  echo "--- insights_contract.py ---"
  python3 checks/insights_contract.py || { echo "LANE3_FAIL insights_contract.py"; bad=1; }
  echo "--- dip_reports.py ---"
  python3 checks/dip_reports.py || { echo "LANE3_FAIL dip_reports.py"; bad=1; }
  echo "--- map_contract.py ---"
  python3 checks/map_contract.py || { echo "LANE3_FAIL map_contract.py"; bad=1; }
  echo "--- candidates_quarantine.py ---"
  python3 checks/candidates_quarantine.py || { echo "LANE3_FAIL candidates_quarantine.py"; bad=1; }
  echo "--- budget_ledger.py ---"
  python3 checks/budget_ledger.py || { echo "LANE3_FAIL budget_ledger.py"; bad=1; }
  echo "--- litsearch_contract.py ---"
  python3 checks/litsearch_contract.py || { echo "LANE3_FAIL litsearch_contract.py"; bad=1; }
  echo "--- results_allowlist.py ---"
  python3 checks/results_allowlist.py || { echo "LANE3_FAIL results_allowlist.py"; bad=1; }
  echo "--- literature_contract.py ---"
  python3 checks/literature_contract.py || { echo "LANE3_FAIL literature_contract.py"; bad=1; }
  echo "--- guard_self_test.py ---"
  python3 checks/guard_self_test.py || { echo "LANE3_FAIL guard_self_test.py"; bad=1; }
  echo "--- log_check.py ---"
  python3 checks/log_check.py || { echo "LANE3_FAIL log_check.py"; bad=1; }
  echo "--- hash_version.py ---"
  python3 checks/hash_version.py || { echo "LANE3_FAIL hash_version.py"; bad=1; }
  echo "--- capacity_two_answers.py ---"
  python3 checks/capacity_two_answers.py || { echo "LANE3_FAIL capacity_two_answers.py"; bad=1; }
  return $bad
}

do_exp() {
  section "Эксперименты (3 параллельных ланы; отчёт в порядке 1-2-3)"
  # Аудит №4/№3 + владелец: серийный do_exp тянул гейт. Ланы независимы:
  # каждая проверка — отдельный процесс; тяжёлые симуляции разложены по ланам
  # 1-2, аудиты дерева — лана 3. Отчёт печатается в фиксированном порядке
  # 1-2-3, не по времени завершения: имена провалов явные (LANE*_FAIL),
  # первый провал по порядку сохраняется rc-агрегацией.
  local rc=0 p1 p2 p3 l1 l2 l3
  l1=$(mktemp); l2=$(mktemp); l3=$(mktemp)
  exp_lane1 >"$l1" 2>&1 & p1=$!
  exp_lane2 >"$l2" 2>&1 & p2=$!
  exp_lane3 >"$l3" 2>&1 & p3=$!
  wait "$p1" || rc=1
  wait "$p2" || rc=1
  wait "$p3" || rc=1
  echo "== лана 1 =="; cat "$l1"
  echo "== лана 2 =="; cat "$l2"
  echo "== лана 3 =="; cat "$l3"
  rm -f "$l1" "$l2" "$l3"
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

do_lab() {
  section "Lab: тесты control plane (lab/tests)"
  # Аудит №3 P0-6: lab/tests не входили в обязательную регрессию — гейт мог
  # быть зелёным при сломанном control plane (claim/submit/migration).
  # Секция независима, идёт в группе 1 параллельно остальным.
  python3 -m unittest discover -s lab/tests -t . 2>&1 | tail -15
  return "${PIPESTATUS[0]}"
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
  echo "=== диспетчер и integrity: первый провал не теряется ==="
  local rc=0 code
  python3 checks/dispatcher.py || rc=$?
  python3 checks/ingest_integrity.py || { code=$?; [ "$rc" -ne 0 ] || rc=$code; }
  python3 checks/runtime_integrity.py || { code=$?; [ "$rc" -ne 0 ] || rc=$code; }
  python3 checks/kg_transaction_integrity.py || { code=$?; [ "$rc" -ne 0 ] || rc=$code; }
  python3 checks/bridge_integrity.py || { code=$?; [ "$rc" -ne 0 ] || rc=$code; }
  return "$rc"
}

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Параллельный планировщик `all` (цикл 822). Секции независимы, кроме двух
# зависимостей сборки: `reach` ждёт olean от do_lean, `exp` — trace-бинарник
# от do_test. Группа 1 (сборки + проверки без зависимостей) идёт параллельно,
# группа 2 — после полного завершения группы 1. Лог каждой секции — свой файл,
# печатается после её ожидания: вывод не перемешивается, первый провал
# сохраняется `keep`, имя провалившейся секции видно сразу.
# Параллельные группы пишут каждую секцию в её собственный файл общего
# временного каталога; итоговый отчёт по всем группам печатает gate_report.
# Порядок ВЫЗОВОВ групп разрешает зависимости сборки (reach после lean,
# exp после test) и на отчёт не влияет.
gate_logs() {
  if [ -z "${GATE_LOG_DIR:-}" ]; then
    GATE_LOG_DIR=$(mktemp -d /tmp/marfagenez-gate-XXXXXX) || { echo "нет tmp для гейта"; exit 1; }
  fi
}

# Пин состояния гейта (цикл 860). Параллельный поток коммитит в master
# каждые ~5-10 минут; чеки, читающие git-историю и лит/kg/docs-состояние,
# видели переходные пары и неописанные коммиты (4 красных гейта 859b-859d).
# Гейт обязан проверять состояние на момент старта, а не живое дерево:
# worktree-пин HEAD замораживает историю и файлы; mid-gate коммиты
# проверяет следующий гейт. Симлинк core/target делит сборку с живым деревом.
PINNED_SECTIONS="exp kg claims audit"
GATE_PIN=""

pin_cd() {
  case " $PINNED_SECTIONS " in *" $1 "*)
    [ -n "$GATE_PIN" ] && cd "$GATE_PIN" || true;;
  esac
}

make_pin() {
  GATE_PIN=$(mktemp -d /tmp/marfagenez-gatepin-XXXXXX) || { GATE_PIN=""; return 0; }
  rmdir "$GATE_PIN"
  if git worktree add --detach "$GATE_PIN" HEAD >/dev/null 2>&1; then
    ln -s "$ROOT/core/target" "$GATE_PIN/core/target" 2>/dev/null
    echo "гейт: пин состояния HEAD -> $GATE_PIN (секции: $PINNED_SECTIONS)"
  else
    echo "гейт: worktree-пин недоступен, секции идут по живому дереву"
    GATE_PIN=""
  fi
}

drop_pin() {
  [ -n "$GATE_PIN" ] || return 0
  git worktree remove --force "$GATE_PIN" 2>/dev/null
  GATE_PIN=""
}

gate_group() {
  gate_logs
  local n
  local -A pidx=()
  local _t0=$SECONDS
  for n in "$@"; do
    # Родительская трасса обязана называть каждую секцию (вложенные копии
    # run.sh и проверки трасс читают её именно так), но внутренности секции
    # идут в её собственную трассу: иначе параллельные выводы перемешиваются
    # и «первый провалившийся шаг» зависит от порядка завершения.
    : "gate: запуск секции do_$n"
    ( exec 9>"$GATE_LOG_DIR/$n.trace"; BASH_XTRACEFD=9; set -x; pin_cd "$n"; "do_$n" ) \
      >"$GATE_LOG_DIR/$n.log" 2>&1 &
    pidx[$n]=$!
  done
  for n in "$@"; do
    wait "${pidx[$n]}"
    GATE_RC[$n]=$?
    GATE_T[$n]=$((SECONDS-_t0))
  done
}

gate_report() {
  # Отчёт — строго в каноническом порядке `all` (шапка: 11 разделов), не по
  # времени завершения и не по группам запуска: RC и «первый провалившийся
  # шаг» даёт первый провал по порядку, как в последовательном диспетчере;
  # поздний код его не затирает.
  gate_logs
  local n
  for n in test lean reach dispatcher verus exp kg claims audit export agents lab; do
    [ -n "${GATE_RC[$n]:-}" ] || continue
    keep "${GATE_RC[$n]}" "$n"
    echo "    [секция $n: ${GATE_T[$n]}с]"
    cat "$GATE_LOG_DIR/$n.log"
    if [ "${GATE_RC[$n]}" -ne 0 ] && [ -z "${FIRST_FAIL_STEP:-}" ]; then
      FIRST_FAIL_STEP=$(first_failed_step "$GATE_LOG_DIR/$n.trace")
    fi
  done
  rm -rf "$GATE_LOG_DIR"
}

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
declare -A GATE_RC=()
declare -A GATE_T=()
GATE_LOG_DIR=""
# «первый провалившийся шаг» параллельного `all`: шаг первой по порядку
# провалившейся секции; ищет gate_report по трассе этой секции.
FIRST_FAIL_STEP=""
# Виновник провала должен быть назван, а не выведен из лога.
#
# `keep` копит код, но не говорит, ЧЕЙ он: раздел `exp` состоит из сорока
# шагов, и красный прогон показывает только «провалился exp». Один раз это
# стоило часа догадок (`FINDING-197`), а ответ дала одна трассировка.
#
# У каждого запуска своя трасса (включая вложенные копии run.sh): родительский
# файл никогда не обрезается дочерним диспетчером.
TRACE="/tmp/marfagenez-run-trace-$(date -u +%Y%m%dT%H%M%S.%NZ)-$$.log"
: > "$TRACE" || { echo "не создать трассировку: $TRACE"; exit 1; }
echo ">>> трассировка: $TRACE"

# Два `all` не идут одновременно. Внутри all маркер наследуется копиями
# run.sh, поэтому вложенный диспетчер не пытается повторно взять тот же lock.
if [ "$WHAT" = all ] && [ "${MARFAGENEZ_GATE_LOCK_HELD:-0}" != 1 ]; then
  # lock — runtime-состояние лаборатории, а не старой очереди: .coord/
  # заморожена как read-only архив (cutover, журнал 821)
  mkdir -p "$ROOT/lab/state/locks"
  exec 8>"$ROOT/lab/state/locks/run-all.lock"
  if ! flock -n 8; then
    echo "FAIL: другой run.sh all уже держит gate lock"
    exit 1
  fi
  export MARFAGENEZ_GATE_LOCK_HELD=1
fi

exec 9>"$TRACE"
BASH_XTRACEFD=9
set -x

first_failed_step() {
  # Первый ненулевой числовой rc= в трассе, а не последний. Строка перед ним
  # называет команду, которая этот код вернула. Аргумент — трасса секции
  # (параллельный `all`), без аргумента — трасса запуска (одиночная цель).
  awk '
    /^\+ (local )?rc=[1-9][0-9]*([ ]|$)/ { print previous; exit }
    { previous = $0 }
  ' "${1:-$TRACE}"
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
  kg)     do_kg;     keep $? kg ;;
  models) do_models; keep $? models ;;
  lab)    do_lab;    keep $? lab ;;
  verus)  do_verus;  keep $? verus ;;
  claims) do_claims; keep $? claims ;;
  audit)  do_audit;  keep $? audit ;;
  export) do_export; keep $? export ;;
  agents) do_agents; keep $? agents ;;
  all)
    make_pin
    trap 'drop_pin' EXIT
    gate_group test lean dispatcher verus claims audit kg export agents lab
    gate_group reach exp
    gate_report
    ;;
  *)
    echo "usage: run.sh [all|test|lean|reach|dispatcher|verus|exp|models|kg|claims|audit|export|agents|lab]"
    exit 2
    ;;
esac

echo
set +x
if [ "$RC" -ne 0 ]; then
  echo "ЕСТЬ ПРОВАЛЫ (код $RC): провалились разделы:$FAILED"
  step=$(first_failed_step)
  if [ -n "${FIRST_FAIL_STEP:-}" ]; then
    step="$FIRST_FAIL_STEP"
  fi
  if [ -n "$step" ]; then
    echo ">>> первый провалившийся шаг: $step"
  fi
  echo ">>> трассировка: $TRACE"
  exit 1
fi
set +x
echo "ВСЁ ЗЕЛЁНОЕ"
