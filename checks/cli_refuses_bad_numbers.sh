#!/bin/bash
# CLI `trace` обязан отказывать на неверном числе, а не молча брать дефолт.
#
# Дефект, ради которого написан этот файл: `args.get(i).and_then(|s|
# s.parse().ok()).unwrap_or(default)` превращает опечатку в другой эксперимент.
# `--steps 50O` (буква O) молча прогонял 500 шагов, и трасса об этом молчала.
# Теперь флаг, который дали, но не смогли разобрать, -- ошибка; дефолт остаётся
# только для флага, которого не было вовсе.
#
# Контроль по контракту §2: fires (плохой вход -- ненулевой код), silent
# (хороший вход -- ноль), specific (ломается именно разбор числа, а не любой
# аргумент: `--bogus` падал и до правки, `--steps 50O` -- только после).
cd "$(dirname "$0")/.." || exit 1
BIN=./core/target/release/trace
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
  echo "FAIL: нет $BIN -- сначала cargo build --release --bin trace"
  exit 1
fi

# fires: опечатка в числе не должна доезжать до симуляции
check nonzero --steps 50O
check nonzero --n abc
check nonzero --capacity 1,5
check nonzero --maintenance 0.6.1
# fires: флаг без значения -- тоже ошибка, а не дефолт
check nonzero --steps
check nonzero --seed
# silent: правильный вход молчит
check zero --steps 20
check zero
# specific: неизвестный аргумент падал и до правки -- он не должен был сломаться
check nonzero --bogus

if [ "$fail" -eq 0 ]; then
  echo "Вердикт: passed"
else
  echo "Вердикт: failed"
fi
exit $fail
