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
# `all` — ровно 13 разделов, в этом порядке:
#   1 test, 2 lean, 3 reach, 4 dispatcher, 5 verus, 6 build, 7 exp,
#   8 kg, 9 claims, 10 audit, 11 export, 12 agents, 13 lab.
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

# Зафиксировать точный HEAD до preflight: pin обязан проверять этот commit,
# даже если другой агент успеет продвинуть branch ref во время preflight.
GATE_HEAD=$(git rev-parse HEAD 2>/dev/null || true)

WHAT="${1:-all}"
if [ "$WHAT" = all ]; then
  echo "all: 13 разделов — test, lean, reach, dispatcher, verus, build, exp, kg, claims, audit, export, agents, lab"
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
  # Default features do not enable lean-ffi; tests that touch the Lean runtime
  # are feature-gated and remain serialized in the dedicated CI step.
  # The ordinary default-feature suite can use Rust's parallel test runner.
  # --tests excludes doctests, which are not part of this gate.
  #
  # Раньше код возврата терялся: последним в конвейере стоял `awk`, который
  # возвращает 0 всегда. Провал компиляции давал `библиотек: 0, passed: 0` и
  # код 0 -- то есть ошибка сборки выглядела как успешный прогон нуля тестов.
  local out rc
  out=$(mktemp)
  ( cd core && cargo test --release --tests ) >"$out" 2>&1
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

do_build() {
  section "Rust: bins и examples"
  # Эксперименты вызывают release-бинарники из target/release. Собираем их
  # внутри pinned HEAD, иначе свежий клон может использовать старые бинарники.
  ( cd core && cargo build --release --bins --examples )
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

# Таймер отдельной проверки внутри exp-lane. Длительность секции измеряется
# диспетчером отдельно; этот таймер показывает фактическую цену каждого чека.
run_timed() {
  local label="$1"; shift
  local started ended rc
  started=$(date +%s)
  "$@"
  rc=$?
  ended=$(date +%s)
  echo "    [$label: $((ended-started))с, rc=$rc]"
  return "$rc"
}

exp_lane1() {
  # Тяжёлые симуляции, лана 1. bad несёт код; имена провалов печатает LANE1_FAIL.
  local bad=0
  echo "--- cli_refuses_bad_numbers.sh ---"
  run_timed "cli_refuses_bad_numbers.sh" bash checks/cli_refuses_bad_numbers.sh || { echo "LANE1_FAIL cli_refuses_bad_numbers.sh"; bad=1; }
  echo "--- cli_refuses_bad_numbers_occupancy.sh ---"
  run_timed "cli_refuses_bad_numbers_occupancy.sh" bash checks/cli_refuses_bad_numbers_occupancy.sh || { echo "LANE1_FAIL cli_refuses_bad_numbers_occupancy.sh"; bad=1; }
  echo "--- exp_memory_cost.py ---"
  run_timed "exp_memory_cost.py" python3 checks/exp_memory_cost.py || { echo "LANE1_FAIL exp_memory_cost.py"; bad=1; }
  echo "--- exp_memory_sampling.py ---"
  run_timed "exp_memory_sampling.py" python3 checks/exp_memory_sampling.py || { echo "LANE1_FAIL exp_memory_sampling.py"; bad=1; }
  echo "--- exp_division_threshold.py ---"
  run_timed "exp_division_threshold.py" python3 checks/exp_division_threshold.py || { echo "LANE1_FAIL exp_division_threshold.py"; bad=1; }
  echo "--- exp_shape_regulator.py ---"
  run_timed "exp_shape_regulator.py" python3 checks/exp_shape_regulator.py || { echo "LANE1_FAIL exp_shape_regulator.py"; bad=1; }
  return $bad
}
exp_lane2() {
  # Тяжёлые симуляции, лана 2.
  local bad=0 out
  echo "--- exp05_frozen.py ---"
  out=$(mktemp)
  if run_timed "exp05_frozen.py" python3 checks/exp05_frozen.py >"$out" 2>&1; then tail -12 "$out"; else tail -12 "$out"; echo "LANE2_FAIL exp05_frozen.py"; bad=1; fi
  rm -f "$out"
  echo "--- exp99_protocol_capacity.py ---"
  run_timed "exp99_protocol_capacity.py" python3 checks/exp99_protocol_capacity.py || { echo "LANE2_FAIL exp99_protocol_capacity.py"; bad=1; }
  echo "--- exp_look_order.py ---"
  run_timed "exp_look_order.py" python3 checks/exp_look_order.py || { echo "LANE2_FAIL exp_look_order.py"; bad=1; }
  echo "--- life_calibration.py ---"
  run_timed "life_calibration.py" python3 checks/life_calibration.py || { echo "LANE2_FAIL life_calibration.py"; bad=1; }
  echo "--- env_prior_tails.py ---"
  run_timed "env_prior_tails.py" python3 checks/env_prior_tails.py || { echo "LANE2_FAIL env_prior_tails.py"; bad=1; }
  echo "--- exp_memory_question.py ---"
  run_timed "exp_memory_question.py" python3 checks/exp_memory_question.py || { echo "LANE2_FAIL exp_memory_question.py"; bad=1; }
  echo "--- damage_clock.py ---"
  run_timed "damage_clock.py" python3 checks/damage_clock.py || { echo "LANE2_FAIL damage_clock.py"; bad=1; }
  echo "--- rng_seed_noise.py ---"
  run_timed "rng_seed_noise.py" python3 checks/rng_seed_noise.py || { echo "LANE2_FAIL rng_seed_noise.py"; bad=1; }
  return $bad
}
exp_lane3() {
  # Аудиты дерева и контрактов, лана 3.
  local bad=0
  echo "--- stub_covers_bridge.py ---"
  run_timed "stub_covers_bridge.py" python3 checks/stub_covers_bridge.py || { echo "LANE3_FAIL stub_covers_bridge.py"; bad=1; }
  echo "--- stub_links.sh ---"
  run_timed "stub_links.sh" bash checks/stub_links.sh || { echo "LANE3_FAIL stub_links.sh"; bad=1; }
  echo "--- contract.py ---"
  run_timed "contract.py" python3 checks/contract.py || { echo "LANE3_FAIL contract.py"; bad=1; }
  echo "--- mde.py ---"
  run_timed "mde.py" python3 checks/mde.py --selftest || { echo "LANE3_FAIL mde.py"; bad=1; }
  echo "--- lean_ffi_feature.py ---"
  run_timed "lean_ffi_feature.py" python3 checks/lean_ffi_feature.py || { echo "LANE3_FAIL lean_ffi_feature.py"; bad=1; }
  echo "--- rng_result_audit.py ---"
  run_timed "rng_result_audit.py" python3 tools/rng_result_audit.py || { echo "LANE3_FAIL rng_result_audit.py"; bad=1; }
  echo "--- test_result_design.py ---"
  run_timed "test_result_design.py" python3 checks/test_result_design.py || { echo "LANE3_FAIL test_result_design.py"; bad=1; }
  echo "--- test_kg_reach.py ---"
  run_timed "test_kg_reach.py" python3 checks/test_kg_reach.py || { echo "LANE3_FAIL test_kg_reach.py"; bad=1; }
  echo "--- test_kg_edges.py ---"
  run_timed "test_kg_edges.py" python3 checks/test_kg_edges.py || { echo "LANE3_FAIL test_kg_edges.py"; bad=1; }
  echo "--- paper_claims.py ---"
  run_timed "paper_claims.py" python3 checks/paper_claims.py || { echo "LANE3_FAIL paper_claims.py"; bad=1; }
  echo "--- paper_format.py ---"
  run_timed "paper_format.py" python3 checks/paper_format.py || { echo "LANE3_FAIL paper_format.py"; bad=1; }
  echo "--- paper_prose.py ---"
  run_timed "paper_prose.py" python3 checks/paper_prose.py || { echo "LANE3_FAIL paper_prose.py"; bad=1; }
  echo "--- readme_features.py ---"
  run_timed "readme_features.py" python3 checks/readme_features.py || { echo "LANE3_FAIL readme_features.py"; bad=1; }
  echo "--- stitch_coverage_floor.py ---"
  run_timed "stitch_coverage_floor.py" python3 checks/stitch_coverage_floor.py || { echo "LANE3_FAIL stitch_coverage_floor.py"; bad=1; }
  echo "--- formula_units_ceiling.py ---"
  run_timed "formula_units_ceiling.py" python3 checks/formula_units_ceiling.py || { echo "LANE3_FAIL formula_units_ceiling.py"; bad=1; }
  echo "--- units_symbol_audit.py ---"
  run_timed "units_symbol_audit.py" python3 tools/units_symbol_audit.py --strict || { echo "LANE3_FAIL units_symbol_audit.py"; bad=1; }
  echo "--- map_duplicates.py ---"
  run_timed "map_duplicates.py" python3 tools/map_duplicates.py --strict || { echo "LANE3_FAIL map_duplicates.py"; bad=1; }
  echo "--- map_orphans.py ---"
  run_timed "map_orphans.py" python3 tools/map_orphans.py --strict || { echo "LANE3_FAIL map_orphans.py"; bad=1; }
  echo "--- wiring_audit.py ---"
  run_timed "wiring_audit.py" python3 tools/wiring_audit.py --strict || { echo "LANE3_FAIL wiring_audit.py"; bad=1; }
  echo "--- unanchored_nodes.py ---"
  run_timed "unanchored_nodes.py" python3 tools/unanchored_nodes.py --strict || { echo "LANE3_FAIL unanchored_nodes.py"; bad=1; }
  echo "--- support_sources.py ---"
  run_timed "support_sources.py" python3 checks/support_sources.py || { echo "LANE3_FAIL support_sources.py"; bad=1; }
  echo "--- cli_refuses.py ---"
  run_timed "cli_refuses.py" python3 checks/cli_refuses.py || { echo "LANE3_FAIL cli_refuses.py"; bad=1; }
  echo "--- no_unseeded_random.py ---"
  run_timed "no_unseeded_random.py" python3 checks/no_unseeded_random.py || { echo "LANE3_FAIL no_unseeded_random.py"; bad=1; }
  echo "--- goal_features.py ---"
  run_timed "goal_features.py" python3 checks/goal_features.py || { echo "LANE3_FAIL goal_features.py"; bad=1; }
  echo "--- finding_elephant_line.py ---"
  run_timed "finding_elephant_line.py" python3 checks/finding_elephant_line.py || { echo "LANE3_FAIL finding_elephant_line.py"; bad=1; }
  echo "--- embeddings_fresh.py ---"
  run_timed "embeddings_fresh.py" python3 checks/embeddings_fresh.py || { echo "LANE3_FAIL embeddings_fresh.py"; bad=1; }
  echo "--- tree_contract.py ---"
  run_timed "tree_contract.py" python3 checks/tree_contract.py || { echo "LANE3_FAIL tree_contract.py"; bad=1; }
  echo "--- insights_contract.py ---"
  run_timed "insights_contract.py" python3 checks/insights_contract.py || { echo "LANE3_FAIL insights_contract.py"; bad=1; }
  echo "--- dip_reports.py ---"
  run_timed "dip_reports.py" python3 checks/dip_reports.py || { echo "LANE3_FAIL dip_reports.py"; bad=1; }
  echo "--- map_contract.py ---"
  run_timed "map_contract.py" python3 checks/map_contract.py || { echo "LANE3_FAIL map_contract.py"; bad=1; }
  echo "--- budget_ledger.py ---"
  run_timed "budget_ledger.py" python3 checks/budget_ledger.py || { echo "LANE3_FAIL budget_ledger.py"; bad=1; }
  echo "--- capacity_two_answers.py ---"
  run_timed "capacity_two_answers.py" python3 checks/capacity_two_answers.py || { echo "LANE3_FAIL capacity_two_answers.py"; bad=1; }
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
  # Целочисленные законы обязаны совпадать с их Rust-копиями (аналитик, ветка C):
  # нормализация пробелов и комментариев, только пары с общим исполняемым телом.
  python3 checks/verus_copies_match.py || rc=1
  return $rc
}

do_kg() {
  section "Граф знаний (инварианты и ссылки)"
  local out rc_check=0 rc_regress=0 rc_edges=0 rc_price=0 rc_selftest=0 rc=0

  # Проверка самой fail-closed обёртки на искусственных rc.
  if [ "${KG_GATE_SELFTEST:-0}" != 1 ]; then
    python3 checks/gate_kg_fail_closed.py --selftest || rc_selftest=$?
  fi

  out=$(mktemp) || {
    echo "KG_SECTION_RED rc=1 (check=125 regress=125 edges=125 price=125 selftest=$rc_selftest)"
    return 1
  }

  python3 kg/kg.py check --refs >"$out" 2>&1
  rc_check=$?
  tail -20 "$out"
  if [ "$rc_check" -eq 0 ] && grep -qE '^[[:space:]]*FAIL:' "$out"; then
    rc_check=1
  fi

  : >"$out"
  python3 kg/regress.py >"$out" 2>&1
  rc_regress=$?
  cat "$out"
  if [ "$rc_regress" -eq 0 ] && grep -qE '^[[:space:]]*FAIL:' "$out"; then
    rc_regress=1
  fi

  echo "--- kg_edges.py ---"
  python3 checks/kg_edges.py
  rc_edges=$?

  # F2: цена обязана быть производной функции значения, а не правилом по флагу.
  python3 checks/bridge_price_derivative.py
  rc_price=$?

  rm -f "$out"
  [ "$rc_check" -eq 0 ] || rc=1
  [ "$rc_regress" -eq 0 ] || rc=1
  [ "$rc_edges" -eq 0 ] || rc=1
  [ "$rc_price" -eq 0 ] || rc=1
  [ "$rc_selftest" -eq 0 ] || rc=1

  if [ "$rc" -ne 0 ]; then
    echo "KG_SECTION_RED rc=$rc (check=$rc_check regress=$rc_regress edges=$rc_edges price=$rc_price selftest=$rc_selftest)"
    return 1
  fi
  echo "KG_SECTION_GREEN (check=0 regress=0 edges=0 price=0 selftest=0)"
  return 0
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

  if ! command -v shellcheck >/dev/null 2>&1; then
    echo "    FAIL: shellcheck не найден в PATH"
    [ "$rc" -ne 0 ] || rc=1
  else
    local sc_out
    sc_out=$(shellcheck -f gcc -S warning run.sh 2>&1 || true)
    if printf '%s\n' "$sc_out" | grep -E 'SC2034|SC2154'; then
      echo "    FAIL: shellcheck обнаружил неиспользуемую или неинициализированную переменную"
      [ "$rc" -ne 0 ] || rc=1
    fi
    shellcheck -S error run.sh || { code=$?; [ "$rc" -ne 0 ] || rc=$code; }
  fi
  return "$rc"
}


# Дешёвые детерминированные проверки до сборок и тяжёлых экспериментов.
# --no-test-count не запускает ещё один cargo test в холодном окружении.
PREFLIGHT_FAILED=""
preflight_check() {
  local label="$1"; shift
  local started ended rc
  started=$(date +%s)
  "$@"
  rc=$?
  ended=$(date +%s)
  echo "    [preflight $label: $((ended-started))с, rc=$rc]"
  if [ "$rc" -ne 0 ]; then
    echo "PREFLIGHT_FAIL $label (rc=$rc)"
    PREFLIGHT_FAILED="$PREFLIGHT_FAILED $label"
  fi
  return 0
}
run_preflight() {
  if [ "${MARFAGENEZ_SKIP_PREFLIGHT:-0}" = 1 ]; then
    echo "PREFLIGHT_SKIPPED: dispatcher fixture"
    return 0
  fi
  PREFLIGHT_FAILED=""
  section "Preflight: дешёвые проверки до тяжёлого гейта"
  preflight_check log_check python3 checks/log_check.py --no-test-count
  preflight_check doc_numbers python3 checks/doc_numbers.py
  preflight_check paper_numbers python3 checks/paper_numbers.py
  preflight_check protocol_checks python3 checks/protocol_checks.py
  preflight_check doc_links python3 checks/doc_links.py
  preflight_check literature_contract python3 checks/literature_contract.py
  preflight_check litsearch_contract python3 checks/litsearch_contract.py
  preflight_check results_allowlist python3 checks/results_allowlist.py
  preflight_check hash_version python3 checks/hash_version.py
  preflight_check candidates_quarantine python3 checks/candidates_quarantine.py
  preflight_check guard_self_test python3 checks/guard_self_test.py
  preflight_check ci_workflow python3 checks/ci_workflow.py
  if [ -n "$PREFLIGHT_FAILED" ]; then
    echo "PREFLIGHT_RED: провалились:$PREFLIGHT_FAILED"
    return 1
  fi
  echo "PREFLIGHT_GREEN: 12 проверок"
  return 0
}


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Параллельный планировщик `all`: зависимости выражены как DAG, а не барьер.
# `reach` стартует сразу после `lean`, `exp` — после release build bins/examples.
# Каждая секция пишет собственные log/trace/rc/dur; отчёт идёт в каноническом
# порядке независимо от времени завершения.
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
PINNED_SECTIONS="test lean reach dispatcher verus build exp kg claims audit export agents lab"
GATE_PIN=""

pin_cd() {
  case " $PINNED_SECTIONS " in *" $1 "*)
    [ -n "$GATE_PIN" ] || { echo "GATE_RED: нет pin для секции $1"; return 1; }
    cd "$GATE_PIN" || { echo "GATE_RED: не перейти в pin для секции $1"; return 1; };;
  esac
}

make_pin() {
  [ -n "$GATE_HEAD" ] || {
    echo "GATE_RED: не удалось зафиксировать HEAD до preflight"
    return 1
  }
  GATE_PIN=$(mktemp -d /tmp/marfagenez-gatepin-XXXXXX) || {
    GATE_PIN=""; echo "GATE_RED: не создать каталог worktree"; return 1;
  }
  rmdir "$GATE_PIN" || {
    rm -rf "$GATE_PIN"; GATE_PIN=""; echo "GATE_RED: не подготовить путь worktree"; return 1;
  }
  mkdir -p "$ROOT/core/target" "$ROOT/laws/.lake" || {
    GATE_PIN=""; echo "GATE_RED: не подготовить общие каталоги target/.lake"; return 1;
  }
  if ! git worktree add --detach "$GATE_PIN" "$GATE_HEAD" >/dev/null 2>&1; then
    rm -rf "$GATE_PIN"; GATE_PIN=""
    echo "GATE_RED: git worktree add не создал pin; запуск по живому дереву запрещён"
    return 1
  fi
  if ! ln -s "$ROOT/core/target" "$GATE_PIN/core/target"; then
    echo "GATE_RED: не создать core/target symlink"
    drop_pin; return 1
  fi
  if ! ln -s "$ROOT/laws/.lake" "$GATE_PIN/laws/.lake"; then
    echo "GATE_RED: не создать laws/.lake symlink"
    drop_pin; return 1
  fi
  [ -L "$GATE_PIN/core/target" ] && [ -L "$GATE_PIN/laws/.lake" ] || {
    echo "GATE_RED: отсутствует обязательный symlink в pin"
    drop_pin; return 1;
  }
  echo "гейт: pin HEAD $GATE_HEAD -> $GATE_PIN (секции: $PINNED_SECTIONS)"
}
drop_pin() {
  [ -n "$GATE_PIN" ] || return 0
  git worktree remove --force "$GATE_PIN" 2>/dev/null
  GATE_PIN=""
}

record_section_status() {
  local name="$1" started="$2" rc="$3" finished
  finished=$(date +%s)
  printf '%s\n' "$rc" >"$GATE_LOG_DIR/$name.rc.tmp.$$" &&
    mv -f "$GATE_LOG_DIR/$name.rc.tmp.$$" "$GATE_LOG_DIR/$name.rc"
  printf '%s\n' "$((finished-started))" >"$GATE_LOG_DIR/$name.dur.tmp.$$" &&
    mv -f "$GATE_LOG_DIR/$name.dur.tmp.$$" "$GATE_LOG_DIR/$name.dur"
}

gate_start() {
  gate_logs
  local n
  for n in "$@"; do
    : "gate: запуск секции do_$n"
    (
      _section_started=$(date +%s)
      trap '_section_rc=$?; record_section_status "$n" "$_section_started" "$_section_rc"; exit "$_section_rc"' EXIT
      exec 9>"$GATE_LOG_DIR/$n.trace"
      BASH_XTRACEFD=9
      set -x
      pin_cd "$n" || exit 125
      "do_$n"
    ) >"$GATE_LOG_DIR/$n.log" 2>&1 &
    GATE_PID[$n]=$!
  done
}

gate_wait() {
  local n="$1" pid wait_rc=0 rc_file dur_file recorded_rc recorded_dur
  pid="${GATE_PID[$n]:-}"
  [ -n "$pid" ] || return 0
  wait "$pid" || wait_rc=$?
  rc_file="$GATE_LOG_DIR/$n.rc"
  dur_file="$GATE_LOG_DIR/$n.dur"
  if [ ! -s "$rc_file" ] || [ ! -s "$dur_file" ]; then
    echo "GATE_RED: секция $n завершилась без rc/duration marker (wait_rc=$wait_rc)"
    GATE_RC[$n]=125
    GATE_T[$n]="missing"
  else
    recorded_rc=$(cat "$rc_file")
    recorded_dur=$(cat "$dur_file")
    if ! [[ "$recorded_rc" =~ ^[0-9]+$ ]] || ! [[ "$recorded_dur" =~ ^[0-9]+$ ]]; then
      echo "GATE_RED: некорректный rc/duration marker секции $n"
      GATE_RC[$n]=125
      GATE_T[$n]="invalid"
    elif [ "$recorded_rc" -ne "$wait_rc" ]; then
      echo "GATE_RED: rc marker секции $n ($recorded_rc) != wait rc ($wait_rc)"
      GATE_RC[$n]=125
      GATE_T[$n]="$recorded_dur"
    else
      GATE_RC[$n]="$recorded_rc"
      GATE_T[$n]="$recorded_dur"
    fi
  fi
  unset "GATE_PID[$n]"
}

gate_wait_all() {
  local n
  for n in test lean reach dispatcher verus build exp kg claims audit export agents lab; do
    [ -n "${GATE_PID[$n]:-}" ] && gate_wait "$n"
  done
}

gate_group() {
  gate_start "$@"
  local n
  for n in "$@"; do gate_wait "$n"; done
}

gate_report() {
  # Отчёт — строго в каноническом порядке `all` (шапка: 13 разделов), не по
  # времени завершения и не по группам запуска: RC и «первый провалившийся
  # шаг» даёт первый провал по порядку, как в последовательном диспетчере;
  # поздний код его не затирает.
  gate_logs
  local n
  for n in test lean reach dispatcher verus build exp kg claims audit export agents lab; do
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
declare -A GATE_PID=()
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
  preflight) run_preflight; keep $? preflight ;;
  build)  do_build;  keep $? build ;;
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
    run_preflight
    preflight_rc=$?
    if [ "$preflight_rc" -ne 0 ]; then
      echo "ЕСТЬ ПРОВАЛЫ (код 1): провалились разделы: preflight"
      exit 1
    fi
    make_pin || {
      echo "ЕСТЬ ПРОВАЛЫ (код 1): провалился pin"
      exit 1
    }
    trap 'drop_pin' EXIT

    # DAG: reach начинается сразу после lean, exp после build.
    # Другие независимые секции не ждут завершения этих зависимостей.
    gate_start test lean dispatcher verus claims audit kg export agents lab build
    gate_wait lean
    gate_start reach
    gate_wait build
    gate_start exp
    gate_wait_all
    gate_report
    ;;
  *)
    echo "usage: run.sh [all|preflight|build|test|lean|reach|dispatcher|verus|exp|models|kg|claims|audit|export|agents|lab]"
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
