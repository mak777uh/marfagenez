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
  ( cd core && cargo test --release --tests -- --test-threads=1 2>&1 \
      | grep -E '^test result' \
      | awk '{p+=$4; f+=$6; n++} END {print "библиотек: " n ", passed: " p ", failed: " f}' )
}

do_lean() {
  section "Lean: сборка"
  ( cd laws && lake build 2>&1 | grep -E 'Build completed|error' | head -5 )
  ( cd laws && lake build Legacy 2>&1 | grep -E 'Build completed|error' | head -5 )
  echo
  echo "файлов:  $(ls laws/Medium/*.lean | wc -l) Medium + $(ls laws/Legacy/*.lean | wc -l) Legacy"
  echo "теорем:  $(grep -rhE '^(theorem|lemma) ' laws/Medium/*.lean | wc -l) Medium + $(grep -rhE '^(theorem|lemma) ' laws/Legacy/*.lean | wc -l) Legacy"
  # `sorry` в комментарии — не дыра в доказательстве. Считаем только код:
  # убираем строчные комментарии и блоки /- -/, затем ищем `sorry`.
  echo "sorry:   $(python3 - <<'PY'
import glob, re
n = 0
for f in glob.glob('laws/Medium/*.lean') + glob.glob('laws/Legacy/*.lean'):
    t = open(f, encoding='utf-8').read()
    t = re.sub(r'/-.*?-/', '', t, flags=re.S)
    t = re.sub(r'--[^\n]*', '', t)
    n += len(re.findall(r'\bsorry\b', t))
print(n)
PY
)"
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
  echo "--- contract.py ---"
  python3 checks/contract.py
  local rc=$?
  echo
  echo "--- exp05_frozen.py ---"
  python3 checks/exp05_frozen.py 2>&1 | tail -12
  return $rc
}

do_claims() {
  section "Проверки утверждений (verify_all.js)"
  # Без seed проверка была разным экспериментом при каждом запуске:
  # одно и то же утверждение проходило и падало без изменения кода.
  # Теперь seed фиксирован, повтор прогона обязан дать тот же результат.
  # node есть только в Windows, в WSL его нет -- вызываем через powershell.exe.
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

# ---------------------------------------------------------------------------

RC=0
case "$WHAT" in
  test)   do_test || RC=$? ;;
  lean)   do_lean || RC=$? ;;
  reach)  do_reach || RC=$? ;;
  exp)    do_exp || RC=$? ;;
  claims) do_claims || RC=$? ;;
  export) do_export || RC=$? ;;
  all)
    do_test   || RC=$?
    do_lean   || RC=$?
    do_reach  || RC=$?
    do_exp    || RC=$?
    do_claims || RC=$?
    do_export || RC=$?
    ;;
  *)
    echo "usage: run.sh [all|test|lean|reach|exp|claims|export]"
    exit 2
    ;;
esac

echo
if [ "$RC" -ne 0 ]; then
  echo "ЕСТЬ ПРОВАЛЫ"
  exit 1
fi
echo "ВСЁ ЗЕЛЁНОЕ"
