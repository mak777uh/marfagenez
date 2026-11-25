"""Насколько оставшийся долг сирот вообще связуем — и сколько из него требует аналогий.

Вопрос: из 305 ячеек без связей сколько имеют «опору» — связную ячейку в том же домене — и сколько
связуемы только через другой домен (то есть почти наверняка через `analogous`, доля которых ограничена M9).

Метод (грубый, но проверяемый):
1. Считаем степени и домены.
2. Для каждой сироты смотрим, есть ли связная ячейка в её домене.
3. Если есть — долг «связуем без аналогий» (кандидат на refines/requires).
4. Если нет, но есть связные ячейки с тем же префиксом группы — долг «связуем внутри кластера».
5. Иначе — «связуем только аналогией» (риск для M9).

Запуск: python3 tools/orphan_reach.py
"""

from __future__ import annotations

import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
EDGES = ROOT / "literature" / "map" / "edges.jsonl"


def main() -> int:
    atoms = [json.loads(l) for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    edges = [json.loads(l) for l in EDGES.read_text(encoding="utf-8").splitlines() if l.strip()]
    deg = collections.Counter()
    for e in edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1

    domain_of = {a["atom"]: (a.get("domain") or "") for a in atoms}
    prefix_of = {a["atom"]: a["atom"].split("-")[0] for a in atoms}

    connected_by_domain = collections.Counter(
        d for i, d in domain_of.items() if deg[i] > 0)
    connected_by_prefix = collections.Counter(
        p for i, p in prefix_of.items() if deg[i] > 0)

    orphans = [a["atom"] for a in atoms if deg[a["atom"]] == 0]
    same_domain, same_prefix, only_analogous = [], [], []
    for o in orphans:
        d = domain_of[o]
        p = prefix_of[o]
        if connected_by_domain[d] >= 2:
            same_domain.append(o)
        elif connected_by_prefix[p] >= 1:
            same_prefix.append(o)
        else:
            only_analogous.append(o)

    total = len(orphans)
    print(f"ячеек: {len(atoms)}; рёбер: {len(edges)}; сирот: {total}")
    print()
    print(f"1) в домене есть ≥2 связных опоры (refines/requires реальны): {len(same_domain)} "
          f"({len(same_domain) / max(total, 1) * 100:.0f} %)")
    print(f"2) опора только по префиксу группы:                          {len(same_prefix)} "
          f"({len(same_prefix) / max(total, 1) * 100:.0f} %)")
    print(f"3) опоры нет ни в домене, ни в группе (только аналогия):     {len(only_analogous)} "
          f"({len(only_analogous) / max(total, 1) * 100:.0f} %)")
    print()
    print("домены сирот, где опор меньше двух:")
    small = collections.Counter(domain_of[o] for o in orphans if connected_by_domain[domain_of[o]] < 2)
    for d, n in small.most_common(8):
        print(f"  {d or '(без домена)':32} {n:3} сирот, связных в домене: {connected_by_domain[d]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
