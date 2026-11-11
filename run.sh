#!/usr/bin/env bash
# Всё в WSL. Один скрипт — всё проверки.
#
# Запуск:
#   wsl -e bash /root/marfagenez/run.sh          # всё
#   wsl -e bash /root/marfagenez/run.sh test     # только тесты
#   wsl -e bash /root/marfagenez/run.sh exp      # только эксперименты
#   wsl -e bash /root/marfagenez/run.sh lean     # только Lean
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
  ( cd core && cargo test --release -- --test-threads=1 2>&1 | grep -E '^test result' )
}

do_lean() {
  section "Lean: сборка"
  ( cd laws && lake build 2>&1 | grep -E 'Build completed|error' | head -5 )
  echo
  echo "файлов:  $(ls laws/Medium/*.lean | wc -l)"
  echo "теорем:  $(grep -rhcE '^theorem ' laws/Medium/*.lean | paste -sd+ | bc)"
  echo "olean:   $(ls laws/.lake/build/lib/lean/Medium/*.olean 2>/dev/null | wc -l)"
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

do_export() {
  section "Экспорт в визуализатор"
  python3 checks/export.py
}

# ---------------------------------------------------------------------------

case "$WHAT" in
  test)   do_test ;;
  lean)   do_lean ;;
  exp)    do_exp ;;
  export) do_export ;;
  all)
    do_test
    do_lean
    do_exp
    do_export
    ;;
  *)
    echo "usage: run.sh [all|test|lean|exp|export]"
    exit 2
    ;;
esac

echo
if [ "$FAILED" -ne 0 ]; then
  echo "ЕСТЬ ПРОВАЛЫ"
  exit 1
fi
echo "ВСЁ ЗЕЛЁНОЕ"
