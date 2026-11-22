"""Инсайты: то, что карта уже позволяет утверждать, и как это проверить.

Ячейка — факт с локатором. Инсайт — утверждение, собранное из нескольких ячеек, вместе с тем, **что его
опровергнет** и **каким опытом это можно различить**. Инсайт без опровержения — это вера; инсайт без
дизайна — это лозунг. Поэтому оба поля обязательны.

Usage:
    python3 tools/insights.py list
    python3 tools/insights.py show I-004
    python3 tools/insights.py write          # пересобрать docs/INSIGHTS.md
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSIGHTS = ROOT / "literature" / "map" / "insights.jsonl"
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"
OUT = ROOT / "docs" / "INSIGHTS.md"


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render() -> str:
    rows = load(INSIGHTS)
    atoms = {a["atom"]: a for a in load(ATOMS)}
    lines = [
        "# INSIGHTS — что карта уже позволяет утверждать",
        "",
        "Сгенерировано `python3 tools/insights.py write`. **Не редактировать руками.**",
        "",
        "Ячейка — факт. Инсайт — утверждение из нескольких ячеек, вместе с тем, что его опровергнет, и",
        "дизайном опыта, который различит объяснения. Статусы: `supported` (есть ячейки и нет противоречия),",
        "`open` (собрано, но проверка не сделана), `contested` (есть противоречащие ячейки).",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['id']} — {row['status']}")
        lines.append("")
        lines.append(row["statement"])
        lines.append("")
        if row.get("supports"):
            lines.append("**Опирается на:** " + ", ".join(f"`{a}`" for a in row["supports"]))
            shown = [atoms[a]["statement"][:120] for a in row["supports"] if a in atoms]
            for a, text in zip(row["supports"], shown):
                lines.append(f"- `{a}`: {text}")
            lines.append("")
        if row.get("contradicts"):
            lines.append("**Противоречит:** " + ", ".join(f"`{c}`" for c in row["contradicts"]))
            lines.append("")
        lines.append(f"**Опровергнет:** {row.get('refuted_by') or '—'}")
        lines.append("")
        design = row.get("design") or {}
        lines.append("**Опыт:**")
        lines.append(f"- вопрос: {design.get('question', '—')}")
        lines.append(f"- метод: {design.get('method', '—')}")
        lines.append(f"- предсказание: {design.get('prediction', '—')}")
        lines.append(f"- если не подтвердится: {design.get('if_false', '—')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    rows = load(INSIGHTS)
    if not argv or argv[0] == "list":
        for row in rows:
            print(f"{row['id']:<6} {row['status']:<10} {row['statement'][:100]}")
        print(f"всего: {len(rows)}")
        return 0
    if argv[0] == "show":
        for row in rows:
            if row["id"] == argv[1]:
                print(json.dumps(row, ensure_ascii=False, indent=1))
                return 0
        print("нет такого инсайта")
        return 1
    if argv[0] == "write":
        OUT.write_text(render(), encoding="utf-8")
        print(f"записано {OUT.relative_to(ROOT)}")
        return 0
    print("глаголы: list, show <id>, write")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
