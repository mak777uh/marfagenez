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
FAILED=0

section() {
  echo
  echo "================================================================"
  echo "  $1"
  echo "================================================================"
}

run() {
  echo "--- $1 ---"
  shift
  if "$@"; then
    echo "    OK"
  else
    echo "    FAIL"
    FAILED=1
  fi
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
  echo "файлов:  $(ls laws/Medium/*.lean | wc -l) Medium + $(ls laws/Legacy/*.lean | wc -l) Legacy"
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
  echo "--- contract.py ---"
  python3 checks/contract.py || rc=$?
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

do_claims() {
  section "Проверки утверждений (verify_all.js)"
  # Без seed проверка была разным экспериментом при каждом запуске:
  # одно и то же утверждение проходило и падало без изменения кода.
  # Теперь seed фиксирован, повтор прогона обязан дать тот же результат.
  # node есть и в Windows, и в WSL; вызываем через powershell.exe, потому что
  # так исторически работает и это проверено.
  local win out rc
  win=$(wslpath -w "$PWD/checks/verify_all.js")
  # `| tail` вернул бы код tail, а не node -- провал проверки стал бы
  # невидимым. Поэтому сначала пишем в файл, потом печатаем хвост.
  out=$(mktemp)
  powershell.exe -NoProfile -Command "node '$win'" >"$out" 2>&1
  rc=$?
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
    local head state
    head=$(git rev-parse HEAD)
    state=$(git log -1 --format=%H -- docs/agent/AGENT_STATE.md)
    if [ -z "$state" ]; then
      echo "    FAIL: docs/agent/AGENT_STATE.md не закоммичен"
      rc=1
    elif [ "$head" != "$state" ]; then
      echo "    FAIL: состояние не отражает последний коммит"
      echo "          HEAD:  $head"
      echo "          state: $state"
      echo "          обнови docs/agent/AGENT_STATE.md и закоммить вместе с изменением"
      rc=1
    fi
  fi
  return $rc
}

# ---------------------------------------------------------------------------

RC=0
case "$WHAT" in
  test)   do_test || RC=$? ;;
  lean)   do_lean || RC=$? ;;
  reach)  do_reach || RC=$? ;;
  exp)    do_exp || RC=$? ;;
  models) do_models || RC=$? ;;
  verus)  do_verus || RC=$? ;;
  claims) do_claims || RC=$? ;;
  export) do_export || RC=$? ;;
  agents) do_agents || RC=$? ;;
  all)
    do_test   || RC=$?
    do_lean   || RC=$?
    do_reach  || RC=$?
    do_verus  || RC=$?
    do_exp    || RC=$?
    do_claims || RC=$?
    do_export || RC=$?
    do_agents || RC=$?
    ;;
  *)
    echo "usage: run.sh [all|test|lean|reach|verus|exp|models|claims|export|agents]"
    exit 2
    ;;
esac

echo
if [ "$RC" -ne 0 ]; then
  echo "ЕСТЬ ПРОВАЛЫ"
  exit 1
fi
echo "ВСЁ ЗЕЛЁНОЕ"
