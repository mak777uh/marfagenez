"""Честное покрытие сшивки: считать не «есть пара», а «величина совпадает».

Повод: `P11` (внешний Red Team, агент `fast`) проверил все 111 пар и дал вердикты
`S` (величина совпадает) / `Ch` (частично) / `N` (несравнимо). Прежняя метрика «30 из 152»
считала пары независимо от вердикта, поэтому завышала опору.

Запуск:
    python3 tools/stitch_audit.py           # сводка
    python3 tools/stitch_audit.py --write   # docs/STITCH-AUDIT.md
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
VERDICTS = ROOT / "docs" / "REDTEAM-STITCH-VERDICTS.json"
OUT = ROOT / "docs" / "STITCH-AUDIT.md"

NAMES = {"S": "величина совпадает", "Ch": "частично", "N": "несравнимо"}


def load_nodes() -> list[dict]:
    return [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv: list[str]) -> int:
    write = "--write" in argv
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    nodes = load_nodes()

    by_node: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for key, v in verdicts.items():
        if "|" not in key:
            continue
        atom, node = key.split("|", 1)
        by_node[node].append((atom, v))

    best: dict[str, str] = {}
    for node, pairs in by_node.items():
        vs = [v for _, v in pairs]
        best[node] = "S" if "S" in vs else ("Ch" if "Ch" in vs else "N")

    with_ref = {n["id"]: n for n in nodes if ((n.get("data") or {}).get("lit_ref") or [])}
    pairs_total = len(verdicts)
    pair_counts = collections.Counter(verdicts.values())

    supported_s = sorted(n for n in with_ref if best.get(n) == "S")
    supported_ch = sorted(n for n in with_ref if best.get(n) == "Ch")
    unsupported = sorted(n for n in with_ref if best.get(n) == "N")
    unaudited = sorted(n for n in with_ref if n not in best)

    lines: list[str] = []
    a = lines.append
    a("# Покрытие сшивки: считать по величине, а не по факту пары")
    a("")
    a("Сгенерировано `tools/stitch_audit.py` по вердиктам Red Team (`docs/REDTEAM-STITCH-VERDICTS.json`).")
    a("")
    a("## Почему прежняя метрика завышена")
    a("")
    a("`docs/STITCH-COVERAGE.md` считал утверждение «опёртым», если у него есть хоть одна пара")
    a("«ячейка ↔ узел». Red Team показал, что **20 из 111 пар** держатся на совпадении слова, числа или")
    a("размерности, а не измеряемой величины. Значит пара — не то же самое, что опора.")
    a("")
    a("## Числа")
    a("")
    a(f"- пар проверено: **{pairs_total}**")
    for k in ("S", "Ch", "N"):
        a(f"  - `{k}` ({NAMES[k]}): **{pair_counts.get(k, 0)}**")
    a(f"- узлов с `lit_ref`: **{len(with_ref)}**")
    a(f"- узлов, у которых есть хотя бы одна пара: **{len(best)}**")
    a(f"- **опора «величина совпадает» (`S`): {len(supported_s)}**")
    a(f"- только частичная (`Ch`): {len(supported_ch)}")
    a(f"- **только несравнимые пары (`N`): {len(unsupported)}**")
    a(f"- узлов с `lit_ref`, которых Red Team не покрыл: {len(unaudited)}")
    a("")
    a("## Что это делает с покрытием")
    a("")
    a("| метрика | значение | что значит |")
    a("|---|---|---|")
    a(f"| прежняя | `{len(with_ref)} / 152` | есть хоть одна пара |")
    a(f"| строгая | `{len(supported_s)} / 152` | есть пара, где измеряемая величина совпадает |")
    a(f"| промежуточная | `{len(supported_s) + len(supported_ch)} / 152` | считая частичные |")
    a("")
    a("Для работы следует пользоваться **строгой** метрикой: только она означает, что литература")
    a("действительно измеряет ту же величину.")
    a("")
    if unsupported:
        a("## Узлы, которые считались опёртыми, но опоры не имеют")
        a("")
        for nid in unsupported:
            atom = by_node[nid][0][0]
            a(f"- `{nid}` (пара с `{atom}`, вердикт `N`): {with_ref[nid].get('text', '')[:80]}")
        a("")
    if unaudited:
        a("## Не проверено Red Team")
        a("")
        for nid in unaudited:
            a(f"- `{nid}`")
        a("")
    a("## Ограничение")
    a("")
    a("Вердикты — суждение Red Team по тексту и переменным, а не измерение. Спорную пару можно")
    a("переклассифицировать, но только с объяснением, какая величина на самом деле общая.")
    text = "\n".join(lines) + "\n"

    if write:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано: {OUT}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
