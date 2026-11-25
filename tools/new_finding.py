"""Выдать агенту свободный номер FINDING и создать файл эксклюзивно.

Зачем: 25.11.2026 второй агент записал свой отчёт как `FINDING-344`, но этот номер принадлежит `main`
и уже был занят — файл перезаписался, и содержимое чужой находки попало в коммит вместо своей.
Конвенция «main 300–349, fast 350–399» в README от этого не спасает: её надо ещё прочитать.

Этот скрипт делает номер **атомарно**: берёт первый свободный в диапазоне агента и создаёт файл через
`O_EXCL`, поэтому перезапись невозможна. Если файл уже есть — отказ, а не тихая замена.

Диапазоны:
    main  300–349
    fast  350–399
    third 400–449

Использование:
    python3 tools/new_finding.py --agent fast --title "D_cap: титровки нет" [--dry-run]
    # напечатает путь и создаст файл с заголовком; текст вписывает агент
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
# 300–349 для main исчерпан 25.11.2026 (см. AGENT_LOG, цикл 628): диапазон продлён блоком
# 450–549. Диапазоны fast (350–399) и third (400–449) не тронуты.
RANGES = {"main": (300, 349), "main-2": (450, 549), "fast": (350, 399), "third": (400, 449)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="new_finding")
    ap.add_argument("--agent", required=True, choices=sorted(RANGES))
    ap.add_argument("--title", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    lo, hi = RANGES[a.agent]
    used = set()
    for p in DOCS.glob("FINDING-*.md"):
        tail = p.stem.split("FINDING-", 1)[-1]
        num = tail.split("-", 1)[0]
        if num.isdigit():
            used.add(int(num))

    free = [n for n in range(lo, hi + 1) if n not in used]
    if not free:
        print(f"ошибка: диапазон {lo}–{hi} для агента {a.agent} исчерпан")
        return 1
    num = free[0]
    path = DOCS / f"FINDING-{num}.md"
    title = a.title.strip().rstrip(".")
    body = (f"# FINDING-{num}: {title}\n\n"
            f"**Дата:** {time.strftime('%d.%m.%Y')}. **Агент:** `{a.agent}`.\n\n"
            "## Что установлено\n\n_(заполнить)_\n\n"
            "## На каком основании\n\n_(числа, команда, локатор)_\n\n"
            "## Что это НЕ доказывает\n\n_(обязательно)_\n\n"
            "## Следующая проверка\n\n_(обязательно)_\n")

    if a.dry_run:
        print(f"свободный номер: {num} -> {path.relative_to(ROOT).as_posix()}")
        return 0

    try:
        with open(path, "x", encoding="utf-8") as f:   # O_EXCL: перезапись невозможна
            f.write(body)
    except FileExistsError:
        print(f"ошибка: {path.name} уже существует — номер не выдан")
        return 1

    print(f"создан: {path.relative_to(ROOT).as_posix()}")
    print(f"номер {num} занят за агентом {a.agent}; следующий свободный в диапазоне — "
          f"{free[1] if len(free) > 1 else 'нет'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
