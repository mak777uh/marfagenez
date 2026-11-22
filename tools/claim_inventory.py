"""What the graph actually claims, versus what we intend to claim.

Two external reviews disagreed about the three elements of the intended model, and both were partly right:
some parts exist as established static claims, others exist only as literature or as intent. This tool makes
that difference mechanical instead of rhetorical — it searches `kg/nodes.jsonl` for each element, prints node
ids with their kind and provenance, and refuses to label anything "implemented" without an experiment node.

Usage:
    python3 tools/claim_inventory.py
    python3 tools/claim_inventory.py --write      # rewrite docs/CLAIM-INVENTORY.md
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODES = ROOT / "kg" / "nodes.jsonl"
OUT = ROOT / "docs" / "CLAIM-INVENTORY.md"

ELEMENTS = [
    ("E1. Граница как состояние, за которое платят",
     ["границ", "boundary", "целостност", "integrity", "упkeep", "upkeep"]),
    ("E2. Повреждение бьёт по способности ремонтировать",
     ["ремонтоспособ", "repair capacity", "ремонт второго", "second-order repair", "ι", "iota"]),
    ("E3. Повреждение наследуется через воспроизводство",
     ["наследован", "inheritance", "inherited", "сегрегац", "segregation", "потомк"]),
]

IGNORE = {"the", "and", "для", "как", "что"}


def load_nodes() -> list[dict]:
    return [json.loads(line) for line in NODES.read_text(encoding="utf-8").splitlines() if line.strip()]


def hits(nodes: list[dict], needles: list[str]) -> list[dict]:
    out = []
    for node in nodes:
        text = (node.get("text") or "").lower()
        context = json.dumps(node.get("context") or {}, ensure_ascii=False).lower()
        if any(n in text or n in context for n in needles if n not in IGNORE):
            out.append(node)
    return out


def render() -> str:
    nodes = load_nodes()
    lines = [
        "# CLAIM-INVENTORY — что граф утверждает на самом деле",
        "",
        "Сгенерировано `python3 tools/claim_inventory.py --write`. **Не редактировать руками.**",
        "",
        "Три элемента — это формулировка *замысла*, а не описание реализованного. Здесь показано, что из них",
        "есть в графе, в каком виде и с каким происхождением.",
        "",
        "Правило вердикта: элемент считается `implemented` только если найдён узел `kind: experiment` с",
        "`provenance: verified_agent` или `human_confirmed`, в тексте которого элемент назван. Иначе — `claim`, `literature` или `absent`.",
        "",
    ]
    for title, needles in ELEMENTS:
        found = hits(nodes, needles)
        kinds = collections.Counter(n.get("kind") for n in found)
        provs = collections.Counter(n.get("provenance") for n in found)
        experiments = [n for n in found if n.get("kind") == "experiment"
                       and n.get("provenance") in ("verified_agent", "human_confirmed")]
        if experiments:
            verdict = "implemented"
        elif any(n.get("kind") == "claim" for n in found):
            verdict = "claim"
        elif found:
            verdict = "literature"
        else:
            verdict = "absent"
        lines += [f"## {title}", "", f"**Вердикт:** `{verdict}`", "",
                  f"узлов: {len(found)}; по видам: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())),
                  f"по происхождению: " + ", ".join(f"{k}={v}" for k, v in sorted(provs.items())), ""]
        if found:
            lines.append("| id | вид | происхождение | текст |")
            lines.append("|---|---|---|---|")
            for node in found[:12]:
                text = (node.get("text") or "").replace("|", "\\|")[:110]
                lines.append(f"| `{node.get('id')}` | {node.get('kind')} | {node.get('provenance')} | {text} |")
            if len(found) > 12:
                lines.append(f"| … | | | ещё {len(found) - 12} |")
            lines.append("")
        else:
            lines += ["Узлов нет ни одного вида — элемент отсутствует в графе.", ""]

    lines += [
        "## Чем это отличается от намерения",
        "",
        "Формулировка «в модели есть цена границы, повреждение бьёт по ремонтоспособности и это наследуется»",
        "описывает **замысел**. В графе на сегодня: цена границы существует как статическое утверждение,",
        "ремонтоспособность как переменная не названа ни разу, наследование присутствует только в",
        "литературных узлах и гипотезах. Поэтому любые внешние тексты, написанные так, будто модель уже это",
        "делает, описывают не модель, а план.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    text = render()
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT.relative_to(ROOT)}")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
