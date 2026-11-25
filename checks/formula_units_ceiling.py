"""Порог исторического долга: число формул без единиц не должно расти.

Почему порог, а не «должно быть ноль». В карте 31 формула, у 22 единицы не объявлены. Если проверка
потребует ноль, гейт станет красным на историческом долге — и его начнут обходить. Правильная проверка:

    число формул без `math.units` не больше, чем записано в BASELINE

Уменьшение — хорошо и разрешено (число понижается только вручную вместе с записью). Рост — красный.
Так долг нельзя увеличить молча, но и нельзя требовать его погасить одним коммитом.

Запуск: python3 checks/formula_units_ceiling.py [--update]
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
BASELINE_FILE = ROOT / "docs" / "FORMULA-UNITS-BASELINE.json"


def current() -> tuple[int, int, list[str]]:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    fs = [n for n in nodes if n.get("kind") == "formula"]
    no_units = [n["id"] for n in fs if not ((n.get("math") or {}).get("units") or {})]
    return len(fs), len(no_units), sorted(no_units)


def main(argv: list[str]) -> int:
    total, without, ids = current()
    if "--update" in argv:
        BASELINE_FILE.write_text(json.dumps({"without_units": without, "total": total,
                                             "date": "2026-11-25"}, ensure_ascii=False,
                                            indent=2) + "\n", encoding="utf-8")
        print(f"порог обновлён: без единиц {without} из {total}")
        return 0

    if not BASELINE_FILE.exists():
        print(f"нет файла порога {BASELINE_FILE}; создайте базовую запись через --update")
        return 1
    base = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    limit = int(base.get("without_units", 0))

    if without > limit:
        print(f"ЕДИНИЦЫ: формул без единиц стало {without} против порога {limit} — долг вырос.")
        print(f"Всего формул: {total}. Список без единиц: {', '.join(ids)}")
        print("Правило: новая формула без math.units не принимается. Погасить долг можно, но не молча —")
        print("см. notices: docs/FORMULA-RECORDS-AUDIT.md.")
        return 1

    print(f"ЕДИНИЦЫ: без единиц {without} из {total} (порог {limit}) — долг не вырос")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
