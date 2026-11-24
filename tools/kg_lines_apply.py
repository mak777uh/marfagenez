"""Проставить линии формулам в их корпусе (docs/ELEPHANT-LITERATURE.md).

`kg/nodes.jsonl` — производный файл: он пересобирается из корпуса командой
`python3 kg/migrate.py`. Поэтому линии записываются в сам корпус строкой
`**Линии.** smert, porog`, а `migrate.py` их читает и переносит в узел.

Запуск: python3 tools/kg_assign_lines.py [--write]
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "ELEPHANT-LITERATURE.md"

ASSIGN = {
    "F-001": ["smert"],
    "F-020": ["smert"],
    "F-002": ["porog"],
    "F-003": ["porog"],
    "F-006": ["porog"],
    "F-018": ["porog"],
    "F-019": ["porog"],
    "F-029": ["porog"],
    "F-023": ["granica"],
    "F-031": ["granica"],
    "F-008": ["vybor"],
    "F-024": ["vybor"],
    "F-014": ["vybor", "porog"],
    "F-016": ["vybor"],
    "F-026": ["vybor"],
    "F-009": ["svoi-usloviya"],
    "F-011": ["svoi-usloviya"],
    "F-022": ["svoi-usloviya"],
    "F-004": ["obmen"],
    "F-005": ["obmen"],
    "F-021": ["obmen"],
    "F-027": ["obmen"],
    "F-010": ["organizaciya"],
    "F-012": ["organizaciya"],
    "F-030": ["organizaciya"],
    "F-013": ["individualnost"],
    "F-015": ["individualnost"],
    "F-028": ["individualnost"],
    "F-007": ["proshloe"],
    "F-017": ["proshloe"],
    "F-025": ["proshloe"],
}


def main(argv: list[str]) -> int:
    text = DOC.read_text(encoding="utf-8")
    changed, already = 0, 0
    for fid, lines in ASSIGN.items():
        head = re.search(r"^### " + re.escape(fid) + r" · .+$", text, re.M)
        if not head:
            print("нет раздела", fid)
            return 1
        start = head.end()
        nxt = re.search(r"^### F-\d{3} · ", text[start:], re.M)
        end = start + (nxt.start() if nxt else len(text) - start)
        body = text[start:end]
        want = "**Линии.** " + ", ".join(lines)
        if "**Линии.**" in body:
            body2 = re.sub(r"^\*\*Линии\.\*\*.*$", want, body, count=1, flags=re.M)
            if body2 == body:
                already += 1
                continue
        else:
            body2 = "\n" + want + body
        text = text[:start] + body2 + text[end:]
        changed += 1

    print(f"разделов изменено: {changed}, уже размечено: {already}")
    if "--write" in argv:
        DOC.write_text(text, encoding="utf-8")
        print("записано", DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
