"""Поиск связей, которые «рядом»: пары ячеек, похожих по величинам, тегам и области, но без ребра.

Задача не в том, чтобы угадать смысл, а в том, чтобы не пропустить очевидное: если две ячейки говорят
об одном и том же числе, объекте или механизме и стоят в соседних областях, между ними должно быть
ребро или явное объяснение, почему его нет.

Usage:
    python3 tools/link_scan.py [--top 40] [--min 2]
"""

from __future__ import annotations

import itertools
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAP = ROOT / "literature" / "map" / "atoms.jsonl"
EDGES = ROOT / "literature" / "map" / "edges.jsonl"


def tokens(atom: dict) -> set[str]:
    out: set[str] = set()
    for t in atom.get("tags") or []:
        out.add("tag:" + str(t).lower())
    for k in (atom.get("symbols") or {}):
        out.add("sym:" + str(k).lower())
    for w in ("полужизн", "оборот", "мощност", "цена", "поток", "ремонт", "репарац", "наследуем",
              "границ", "мембран", "ATP", "накоплен", "дефицит", "энтроп", "замыка", "эмерджент"):
        if w.lower() in (atom.get("statement") or "").lower():
            out.add("word:" + w.lower())
    return out


def main(argv: list[str]) -> int:
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 40
    min_score = int(argv[argv.index("--min") + 1]) if "--min" in argv else 2

    atoms = [json.loads(l) for l in MAP.read_text(encoding="utf-8").splitlines() if l.strip()]
    edges = [json.loads(l) for l in EDGES.read_text(encoding="utf-8").splitlines() if l.strip()]
    linked = {frozenset((e["from"], e["to"])) for e in edges}
    by_id = {a["atom"]: a for a in atoms}
    toks = {a["atom"]: tokens(a) for a in atoms}

    # кандидаты: только те, у кого есть общий «сильный» токен (символ или слово), не только область
    cands = []
    for a, b in itertools.combinations(atoms, 2):
        if frozenset((a["atom"], b["atom"])) in linked:
            continue
        shared = toks[a["atom"]] & toks[b["atom"]]
        strong = {t for t in shared if t.startswith(("sym:", "word:"))}
        if len(strong) < min_score:
            continue
        dom_bonus = 1 if a.get("domain") == b.get("domain") else 0
        score = len(strong) * 2 + dom_bonus
        cands.append((score, a, b, sorted(strong), dom_bonus))

    cands.sort(key=lambda x: -x[0])
    print(f"ячеек: {len(atoms)}, рёбер: {len(edges)}, кандидатов без ребра: {len(cands)}")
    print(f"показано: {min(top, len(cands))}\n")
    for score, a, b, shared, dom in cands[:top]:
        same = "та же область" if dom else "разные области"
        print(f"[{score}] {a['atom']} ({a.get('domain')}) <-> {b['atom']} ({b.get('domain')}), {same}")
        print(f"     общее: {', '.join(shared[:6])}")
        print(f"     A: {a['statement'][:110]}")
        print(f"     B: {b['statement'][:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
