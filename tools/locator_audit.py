"""Проверка: числа с локатором в формулах-обобщениях должны встречаться в атоме.

Повод (`FINDING-355`, аудит `fast`): в `docs/FORMULA-GENERAL.md` два «якорных» числа ссылались не на те
атомы — «5 %» стояло при `DIP42-0008` (где его нет), «1 мМ» при `DIP42-0009` (где его нет). Контракт карты
и проверки документации такое не видят: оба атома существуют, ссылки синтаксически корректны.

Что делает скрипт: ищет в документах пары «число … (`АТОМ`)» в пределах одной строки или соседних строк
(абзаца), и проверяет, есть ли это число в `statement`/`formula` атома. Печатает расхождения.

Это **не** гейт: ложные срабатывания возможны (единицы, округления, пересказ). Задача — список для чтения.

Запуск:
    python3 tools/locator_audit.py            # по всем .md в docs/
    python3 tools/locator_audit.py FORMULA-GENERAL.md
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"

ATOM_REF = re.compile(r"`([A-Z][A-Z0-9]*-[0-9A-Za-z-]+)`")
NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*(%|мМ|мг|мкм|Гр|ч|мин|с\b|мОсм)")


def load_atoms() -> dict[str, str]:
    out = {}
    for line in ATOMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        out[a["atom"]] = (a.get("statement") or "") + " " + str(a.get("formula") or "")
    return out


def norm_number(s: str) -> str:
    return s.replace(",", ".")


def main(argv: list[str]) -> int:
    atoms = load_atoms()
    files = ([DOCS / argv[0]] if argv else sorted(DOCS.glob("*.md")))
    total, bad = 0, []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        # абзацы: проверяем окрестность каждого упоминания атома
        for m in ATOM_REF.finditer(text):
            atom = m.group(1)
            if atom not in atoms:
                continue
            # окно — только та же строка и только числа ПЕРЕД ссылкой (типичный вид: «**5 %** (`X`)»)
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start: m.end()]
            # строки, которые ЦИТИРУЮТ ошибку (таблицы поправок), не проверяем: там пара «ошибочное
            # число ↔ ошибочная ссылка» стоит намеренно.
            if "|" in line or "было указано" in line or "на самом деле" in line or "было:" in line:
                continue
            window = text[line_start: m.start()]
            matches = list(NUM.finditer(window))
            if not matches:
                continue
            for n in matches[-2:]:
                number, unit = n.group(1), n.group(2)
                total += 1
                needle = norm_number(number)
                if needle not in atoms[atom].replace(",", "."):
                    bad.append((path.name, atom, f"{number} {unit}", atoms[atom][:110]))
    print(f"проверено пар «число ↔ атом»: {total}; расхождений: {len(bad)}")
    for name, atom, num, stmt in bad[:20]:
        print(f"\n  {name}: число **{num}** при `{atom}`, но в атоме его нет")
        print(f"    атом: {stmt}…")
    if len(bad) > 20:
        print(f"\n  … и ещё {len(bad) - 20}")
    print()
    print("Это список для чтения, а не приговор: единицы и округления дают ложные срабатывания.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
