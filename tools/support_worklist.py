"""Список работы: утверждения без литературной опоры, сгруппированные по линиям.

Помогает выбрать, что искать дальше: показывает, у каких утверждений опоры нет и какие из них
формулы (у формул выше шанс найти измеряемые величины).

Запуск: python3 tools/support_worklist.py [--write]
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SUPPORT-WORKLIST.md"
LINES = ROOT / "kg" / "lines-map.json"


def main(argv: list[str]) -> int:
    nodes = [json.loads(l) for l in (ROOT / "kg" / "nodes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    lines_map = json.loads(LINES.read_text(encoding="utf-8")) if LINES.exists() else {}

    target = [n for n in nodes if n.get("kind") in ("claim", "formula", "gap", "correspondence")]
    without = [n for n in target if not (n.get("data") or {}).get("lit_ref")]

    # Группировка по статусу и виду: линия через рёбра получается неполной (у большинства утверждений
    # нет ребра к литературному узлу), поэтому режем по тому, что известно точно.
    groups = collections.defaultdict(list)
    for n in without:
        key = (n.get("kind"), n.get("epistemic") or "—")
        groups[key].append(n)

    def order(key):
        kind, ep = key
        prio = {"formula": 0, "claim": 1, "gap": 2, "correspondence": 3}.get(kind, 4)
        ep_prio = {"established": 0, "hypothesis": 1, "bounded": 2, "refuted": 3}.get(ep, 4)
        return (prio, ep_prio)

    lines: list[str] = []
    a = lines.append
    a("# Что искать: утверждения без литературной опоры")
    a("")
    a("Сгенерировано `tools/support_worklist.py`. Список отсортирован так, чтобы начинать с того, где")
    a("литература вероятнее: сначала **формулы** (у них есть измеримые величины), затем утверждения, затем")
    a("дыры.")
    a("")
    a(f"Всего утверждений, формул, дыр и соответствий: **{len(target)}**; без опоры: **{len(without)}**.")
    a("")
    for key in sorted(groups, key=order):
        items = groups[key]
        kind, ep = key
        a(f"## {kind} / {ep}: {len(items)} без опоры")
        a("")
        for n in sorted(items, key=lambda x: x["id"])[:40]:
            a(f"- `{n['id']}` — {(n.get('text') or '')[:150]}")
        if len(items) > 40:
            a(f"- … и ещё {len(items) - 40}")
        a("")

    a("## Как этим пользоваться")
    a("")
    a("1. Берём линию, где больше всего **формул** — там есть что измерять.")
    a("2. Для каждой формулы выписываем её величины (например, `D_cap`, `C0`, `P`) и ищем работы с числами.")
    a("3. Утверждения без формулы ищутся хуже: у них нет величины, только качественное содержание.")
    a("4. Дыры (`gap`) не ищем — они уже фиксируют, что не нашли.")

    text = "\n".join(lines) + "\n"
    print(text[:1500])
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"\nзаписано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
