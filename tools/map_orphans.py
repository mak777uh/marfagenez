"""Ячейки карты без единой связи и правило цеттелькастена для новых ячеек.

Правило: **любая новая ячейка должна получить хотя бы одну связь с существующей** при добавлении.
Обоснование: ячейка без связи не участвует в графе — её нельзя найти обходом, она не влияет на сшивку
и на вывод. В карте такие ячейки уже есть (исторический долг), но новые появляться не должны.

Режимы:
    python3 tools/map_orphans.py            — отчёт (сколько сирот, кто именно)
    python3 tools/map_orphans.py --strict   — падает, если сирот больше потолка
                                              `docs/MAP-ORPHANS-BASELINE.json`

Запуск: python3 tools/map_orphans.py [--strict] [--update]
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
EDGES = ROOT / "literature" / "map" / "edges.jsonl"
BASE = ROOT / "docs" / "MAP-ORPHANS-BASELINE.json"


def load():
    atoms = [json.loads(l) for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    edges = [json.loads(l) for l in EDGES.read_text(encoding="utf-8").splitlines() if l.strip()]
    return atoms, edges


def orphans(atoms, edges):
    ids = {a["atom"] for a in atoms}
    deg = collections.Counter()
    for e in edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1
    return sorted(i for i in ids if deg[i] == 0), deg


def main(argv: list[str]) -> int:
    atoms, edges = load()
    missing, deg = orphans(atoms, edges)
    share = len(missing) / max(len(atoms), 1) * 100
    print(f"ячеек: {len(atoms)}; рёбер: {len(edges)}")
    print(f"ячеек без единой связи: {len(missing)} ({share:.0f} %)")
    if missing:
        print("первые:", ", ".join(missing[:10]))
        pref = collections.Counter(i.split("-")[0] for i in missing)
        print("по префиксам:", dict(pref.most_common(6)))

    if "--update" in argv:
        BASE.write_text(json.dumps({"orphans": len(missing), "date": "2026-11-25"}, ensure_ascii=False,
                                   indent=2) + "\n", encoding="utf-8")
        print(f"потолок обновлён: {len(missing)}")
        return 0

    if "--strict" in argv:
        ceiling = 0
        if BASE.exists():
            ceiling = int(json.loads(BASE.read_text(encoding="utf-8")).get("orphans") or 0)
        if len(missing) > ceiling:
            print(f"СТРОГИЙ РЕЖИМ: сирот {len(missing)} больше потолка {ceiling} — новые ячейки должны иметь связь")
            return 1
        print(f"СТРОГИЙ РЕЖИМ: сирот {len(missing)} при потолке {ceiling} — долг не вырос")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
