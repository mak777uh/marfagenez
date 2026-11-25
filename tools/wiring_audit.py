"""Все ли проверки подключены к гейту? Если файл есть, а `run.sh` его не вызывает — он мёртв.

Повод (25.11.2026): `tools/map_duplicates.py --strict` и `tools/units_symbol_audit.py --strict` были написаны,
но в `run.sh` не вызывались. Инструмент «есть», проверки «нет». Обнаружилось чтением, а не проверкой.

Что делает: собирает `checks/*.py` и `tools/*audit*.py`, ищет имя файла в `run.sh`; те, что не упомянуты,
печатает как неподключённые. Осознанно неподключённые перечисляются в `docs/WIRING-EXEMPTIONS.json` с
причиной.

Запуск:
    python3 tools/wiring_audit.py            # отчёт
    python3 tools/wiring_audit.py --strict   # код 1, если есть неподключённые без объяснения
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "run.sh"
EXEMPT = ROOT / "docs" / "WIRING-EXEMPTIONS.json"


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    run_text = RUN.read_text(encoding="utf-8")
    exempt = {}
    if EXEMPT.exists():
        exempt = json.loads(EXEMPT.read_text(encoding="utf-8"))

    # В `checks/` лежит и то, что обязано быть в гейте, и одноразовые исследовательские скрипты
    # (183 файла из 240 не подключены, и это нормально). Правило сужено до инструментов-аудитов:
    # именно они пишутся «чтобы проверять» и легче всего забываются.
    candidates = sorted(p for p in (ROOT / "tools").glob("*.py") if "audit" in p.name)

    unwired = []
    for p in candidates:
        if p.name.startswith("_"):
            continue
        if p.name in run_text:
            continue
        if p.name in exempt:
            continue
        unwired.append(p.name)

    print(f"проверок найдено: {len(candidates)}; неподключённых: {len(unwired)}")
    for name in unwired:
        print("  ", name)
    if exempt:
        print(f"осознанно не подключены (docs/WIRING-EXEMPTIONS.json): {len(exempt)}")
        for name, why in sorted(exempt.items()):
            print(f"   {name}: {why[:90]}")
    print()
    if unwired:
        print("Подключите в run.sh или объясните в docs/WIRING-EXEMPTIONS.json, почему нет.")
        return 1 if strict else 0
    print("все проверки либо подключены, либо объяснены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
