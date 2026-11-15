#!/usr/bin/env python3
"""Диагностика диспетчера `run.sh`: провал одной проверки не теряется.

Дефект, ради которого это написано: `all` вызывал `do_*` подряд через
`|| RC=$?`. Код возврата присваивался заново на каждой проверке, поэтому
провал `exp` затирался успехом `agents` -- и прогон печатал «ВСЁ ЗЕЛЁНОЕ»
с кодом 0. Это тот же класс, что уже чинили в `do_lean` (потерянный статус
`lake build`) и в `do_exp` (потерянный статус `exp05_frozen.py`): провал
выглядит как успех.

Проверка смотрит на поведение, а не на текст: `run.sh` копируется, `do_*`
подменяются заглушками с заданным кодом, и проверяется пара
(баннер, код возврата). Переписанный диспетчер обязан пройти её заново --
иначе это не проверка, а снимок одной реализации.

Запуск: `python3 checks/dispatcher.py` (или `bash run.sh dispatcher`).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "run.sh"

#: С чего начинается диспетчер. Всё выше -- заголовок и функции, всё ниже --
#: `case`. Заглушки вставляются в стык, поэтому подменяются только `do_*`,
#: а сам `case` остаётся тем, что лежит в дереве.
#:
#: Маркер обязан стоять ПОСЛЕ всех определений `do_*`: bash берёт последнее
#: определение, поэтому заглушка, вставленная раньше настоящей функции, будет
#: перекрыта ею -- и проверка станет тавтологией. Раньше здесь стоял
#: комментарий над `keep` (то есть выше функций), и инъекция старого
#: `|| RC=$?` в `case` проходила незамеченной: 6/6 при любом поведении.
MARKER = "\nRC=0\ncase \"$WHAT\" in"

STUBS = """do_test(){{ :; }}; do_lean(){{ :; }}; do_reach(){{ :; }}
do_dispatcher(){{ :; }}; do_verus(){{ :; }}
do_exp(){{ return {exp_rc}; }}
do_claims(){{ return {claims_rc}; }}; do_export(){{ :; }}; do_models(){{ :; }}
do_agents(){{ return {agents_rc}; }}
"""


def build(directory: Path, exp_rc: int, agents_rc: int, claims_rc: int = 0) -> Path:
    """A copy of run.sh whose do_* are stubs with the given exit codes."""
    text = RUN.read_text(encoding="utf-8")
    if MARKER not in text:
        raise SystemExit(f"нет маркера «{MARKER}» в run.sh -- проверка устарела")
    head, tail = text.split(MARKER, 1)
    path = directory / f"run-{exp_rc}-{agents_rc}-{claims_rc}.sh"
    path.write_text(
        head
        + STUBS.format(exp_rc=exp_rc, agents_rc=agents_rc, claims_rc=claims_rc)
        + MARKER
        + tail,
        encoding="utf-8",
    )
    # Заглушки обязаны перекрыть настоящие do_*: проверяем это, а не надеемся.
    body = path.read_text(encoding="utf-8")
    for fn in ("do_exp", "do_agents", "do_claims"):
        last = body.rfind(f"\n{fn}()")
        stub = body.rfind(f"\n{fn}(){{ return")
        if stub < last or stub < 0:
            raise SystemExit(
                f"заглушка {fn} перекрыта настоящей функцией -- проверка тавтологична"
            )
    return path


def run(script: Path, target: str) -> tuple[int, str]:
    # `cd` не нужен: run.sh сам делает `cd /root/marfagenez`, а заглушки
    # ничего не читают. Код возврата берётся от процесса, не от конвейера.
    p = subprocess.run(
        ["bash", str(script), target],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return p.returncode, p.stdout + p.stderr


CASES = [
    # (имя, exp_rc, agents_rc, claims_rc, цель, ожидаемый код, ожидаемый баннер)
    #
    # Баннер сверяется ЦЕЛИКОМ, вместе с кодом. Раньше проверялось только
    # вхождение подстроки «ЕСТЬ ПРОВАЛЫ», и `(код 1)` от `(код 2)` было
    # неотличимо: диспетчер, затирающий первый провал вторым, печатал
    # «ЕСТЬ ПРОВАЛЫ (код 2)» и проходил проверку -- хотя именно потеря
    # исходной причины и есть дефект.
    ("exp падает, agents проходит", 1, 0, 0, "all", 1, "ЕСТЬ ПРОВАЛЫ (код 1)"),
    ("agents падает последним", 0, 1, 0, "all", 1, "ЕСТЬ ПРОВАЛЫ (код 1)"),
    ("оба падают", 1, 1, 0, "all", 1, "ЕСТЬ ПРОВАЛЫ (код 1)"),
    ("всё проходит", 0, 0, 0, "all", 0, "ВСЁ ЗЕЛЁНОЕ"),
    ("одиночная цель падает", 1, 0, 0, "exp", 1, "ЕСТЬ ПРОВАЛЫ (код 1)"),
    ("одиночная цель проходит", 0, 0, 0, "agents", 0, "ВСЁ ЗЕЛЁНОЕ"),
    # Провал `exp` (код 1) и более поздний провал `claims` (код 2): диспетчер
    # обязан сохранить ПЕРВЫЙ код. `do_exp || RC=$?` в этой паре даёт 2,
    # `do_exp; keep $?` -- 1, и различие видно только по коду в баннере.
    ("первый провал не затирается вторым", 1, 0, 2, "all", 1, "ЕСТЬ ПРОВАЛЫ (код 1)"),
]


def main() -> int:
    if not RUN.exists():
        print(f"нет {RUN}", file=sys.stderr)
        return 1

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        built: dict[tuple[int, int, int], Path] = {}
        for name, exp_rc, agents_rc, claims_rc, target, want_rc, want_banner in CASES:
            key = (exp_rc, agents_rc, claims_rc)
            if key not in built:
                built[key] = build(Path(tmp), exp_rc, agents_rc, claims_rc)
            rc, out = run(built[key], target)
            problems = []
            if rc != want_rc:
                problems.append(f"код {rc}, ожидался {want_rc}")
            lines = out.splitlines()
            banner = [l for l in lines if l.startswith(want_banner)]
            if not banner:
                problems.append(f"нет строки «{want_banner}»")
            elif want_rc != 0:
                # Баннер обязан назвать раздел: без имени провал неотличим
                # от «упало что-то». Проверка стоит ДО развилки, иначе она
                # не может провалить тест -- это замер, который не может
                # провалиться, ровно та болезнь, которую ловит `keep`.
                tail = banner[0].split("провалились разделы:")
                named = tail[-1].split() if len(tail) > 1 else []
                if not named:
                    problems.append(
                        f"баннер не называет раздел: «{banner[0]}»")
            if problems:
                failures += 1
                print(f"  FAIL {name}: {'; '.join(problems)}")
                print("       " + "\n       ".join(out.strip().splitlines()[-3:]))
            else:
                print(f"  ok   {name} (код {rc}, «{banner[0]}»)")

    if failures:
        print(f"    FAIL: диспетчер теряет провал в {failures} из {len(CASES)} случаев")
        return 1
    print(f"    диспетчер сохраняет провал: {len(CASES)}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
