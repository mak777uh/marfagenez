"""Сшивка по ТОЖДЕСТВУ ИСТОЧНИКА: узел kg/ и ячейка карты ссылаются на одну работу (DOI).

Это самый сильный класс пар: сравнивать не «формулировки», а одну и ту же публикацию.
Добавляет такие пары в `kg/lit-refs.json` (через манифест), чтобы `kg/migrate.py` их подхватил.

Запуск: python3 tools/stitch_identity.py [--write]
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
NODES = ROOT / "kg" / "nodes.jsonl"
LITREFS = ROOT / "kg" / "lit-refs.json"


def main(argv: list[str]) -> int:
    atoms = [json.loads(l) for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]

    by_doi: dict[str, list[str]] = collections.defaultdict(list)
    for a in atoms:
        for w in a.get("works") or []:
            doi = (w.get("doi") or "").lower().strip()
            if doi:
                by_doi[doi].append(a["atom"])

    pairs: list[tuple[str, str, str]] = []
    for n in nodes:
        loc = (n.get("data") or {}).get("locator") or {}
        doi = (loc.get("doi") or "").lower().strip() if isinstance(loc, dict) else ""
        if doi and doi in by_doi:
            for cell in by_doi[doi]:
                pairs.append((cell, n["id"], doi))

    print(f"пар по тождеству источника: {len(pairs)}")
    for cell, node, doi in pairs:
        print(f"  {cell} ↔ {node}  ({doi})")

    if "--write" not in argv:
        return 0

    # 1) kg_ref в ячейках
    by_cell: dict[str, list[str]] = collections.defaultdict(list)
    for cell, node, _ in pairs:
        by_cell[cell].append(node)
    for a in atoms:
        if a["atom"] in by_cell:
            a["kg_ref"] = sorted(set((a.get("kg_ref") or []) + by_cell[a["atom"]]))
    ATOMS.write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in atoms), encoding="utf-8")

    # 2) обратное отображение с дедупликацией
    data = json.loads(LITREFS.read_text(encoding="utf-8"))
    m = data.setdefault("map", {})
    for cell, node, _ in pairs:
        m.setdefault(node, [])
        if cell not in m[node]:
            m[node].append(cell)
    for k in list(m):
        m[k] = sorted(set(m[k]))
    LITREFS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(v) for v in m.values())
    print(f"\nзаписано: kg_ref в {len(by_cell)} ячейках; линков {total}, уникальных пар {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
