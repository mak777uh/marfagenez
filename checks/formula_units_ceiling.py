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


def current() -> tuple[int, int, list[str], list[str]]:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    fs = [n for n in nodes if n.get("kind") == "formula"]
    no_units = sorted(n["id"] for n in fs if not ((n.get("math") or {}).get("units") or {}))
    with_units = sorted(n["id"] for n in fs if ((n.get("math") or {}).get("units") or {}))
    return len(fs), len(no_units), no_units, with_units


def main(argv: list[str]) -> int:
    total, without, ids, with_units = current()
    if "--update" in argv:
        # --update НЕ должен стирать объявленный структурный список: иначе причина «почему без единиц»
        # пропадает при первом же обновлении порога (это случилось сразу после добавления списка).
        prev = {}
        if BASELINE_FILE.exists():
            try:
                prev = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
        data = {"without_units": without, "total": total, "with_units": with_units,
                "date": "2026-11-25"}
        for k in ("structural", "structural_reason"):
            if k in prev:
                data[k] = prev[k]
        BASELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        print(f"порог обновлён: без единиц {without} из {total}; с единицами записано {len(with_units)}")
        return 0

    if not BASELINE_FILE.exists():
        print(f"нет файла порога {BASELINE_FILE}; создайте базовую запись через --update")
        return 1
    base = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    limit = int(base.get("without_units", 0))

    # Формулы без единиц должны быть перечислены как СТРУКТУРНЫЕ, иначе долг растёт незаметно: новая
    # формула без единиц просто увеличит счётчик, а он уже на пороге.
    structural = sorted(base.get("structural") or [])
    if structural and sorted(ids) != structural:
        missing = sorted(set(ids) - set(structural))
        extra = sorted(set(structural) - set(ids))
        print("ЕДИНИЦЫ: список структурных формул разошёлся с деревом")
        if missing:
            print(f"  без единиц, но не объявлены структурными: {', '.join(missing)}")
        if extra:
            print(f"  объявлены структурными, но единицы есть: {', '.join(extra)}")
        print("  объявите формулу структурной в docs/FORMULA-UNITS-BASELINE.json с причиной")
        return 1

    # Список важнее числа: раньше запись F-005 «потеряла» единицы, и это прошло как сокращение долга.
    recorded = base.get("with_units") or []
    lost = [fid for fid in recorded if fid in ids]
    if lost:
        print(f"ЕДИНИЦЫ: формулы потеряли единицы, хотя они были записаны: {', '.join(lost)}")
        print("Это не сокращение долга, а исчезновение записи. Восстановите math.units или объясните")
        print("в docs/UNITS-AUDIT.md и пересоберите порог с --update.")
        return 1

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
