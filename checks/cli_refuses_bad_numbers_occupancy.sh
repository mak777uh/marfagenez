#!/bin/bash
# CLI `occupancy` обязан отказывать на неверном числе, а не молча брать дефолт.
#
# Тот же дефект, что в `trace` (см. checks/cli_refuses_bad_numbers.sh), но в
# позиционных аргументах: `args.get(i).and_then(|s| s.parse().ok())
# .unwrap_or(default)` превращал опечатку в другой эксперимент. `occupancy 50O`
# (буква O) молча прогонял 160 организмов, и вывод об этом молчал.
#
# Контроль по контракту §2: fires (плохой вход -- код 2), silent (хороший вход --
# 0, аргументов нет -- 0 и дефолты), specific (ломается именно разбор числа:
# лишние аргументы игнорировались и до правки и должны игнорироваться после).
cd "$(dirname "$0")/.." || exit 1
BIN=./core/target/release/occupancy
fail=0

check() {
  local want="$1"; shift
  "$BIN" "$@" >/dev/null 2>&1
  local got=$?
  if [ "$want" = "nonzero" ]; then
    if [ "$got" -eq 0 ]; then
      echo "FAIL fires: $* вернул 0, ожидался ненулевой"
      fail=1
    else
      echo "OK   fires: $* -> $got"
    fi
  else
    if [ "$got" -ne 0 ]; then
      echo "FAIL silent: $* вернул $got, ожидался 0"
      fail=1
    else
      echo "OK   silent: $* -> 0"
    fi
  fi
}

if [ ! -x "$BIN" ]; then
  echo "FAIL: нет $BIN -- сначала cargo build --release --bin occupancy"
  exit 1
fi

# fires: опечатка в каждом из четырёх позиционных аргументов
check nonzero 50O 3 2 1
check nonzero 4 4O 2 1
check nonzero 4 3 2O 1
check nonzero 4 3 2 x
check nonzero -1 3 2 1
# silent: правильный вход молчит
check zero 4 3 2 1
check zero
# specific: лишний аргумент игнорировался и до правки -- не должен сломаться
check zero 4 3 2 1 extra

if [ "$fail" -eq 0 ]; then
  echo "Вердикт: passed"
else
  echo "Вердикт: failed"
fi
exit $fail
