"""Список для чтения: ячейки, где в одном утверждении несколько разных знаменателей.

Повод: агент `probe` нашёл `DIP39-0008`, где 4,3·10³ частиц/мг и 11·10¹⁰ частиц/г печени несовместимы
(отношение даёт 25,6 кг белка на грамм печени). Это класс «внутреннее противоречие», который дешевле
искать самому, чем ждать ревью.

Инструмент НЕ выносит вердиктов: он показывает ячейки, где есть ≥2 разных знаменателя, и числа рядом,
чтобы человек (или агент) проверил совместимость.

Запуск: python3 tools/cell_denominator_audit.py [--min 2] [--json]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATOMS = ROOT / "literature" / "map" / "atoms.jsonl"

# знаменатели: русские и английские формы записи «на единицу»
DENOMS = [
    (r"на\s+(?:1\s+)?мг(?:\s+белка)?", "мг"),
    (r"на\s+(?:1\s+)?г(?:рамм)?(?:\s+ткани)?", "г"),
    (r"на\s+грамм", "г"),
    (r"на\s+(?:1\s+)?кг", "кг"),
    (r"на\s+(?:1\s+)?клетку", "клетка"),
    (r"на\s+(?:1\s+)?частицу", "частица"),
    (r"/\s*мг", "мг"),
    (r"/\s*г(?![а-я])", "г"),
    (r"per\s+mg", "mg"),
    (r"per\s+g(?:ram)?(?![a-z])", "g"),
    (r"per\s+cell", "cell"),
    (r"мкмоль/\(?г", "г"),
    (r"нмоль/\(?г", "г"),
    # площади и объёмы — самые частые знаменатели в этой карте
    (r"на\s+(?:1\s+)?м²", "м²"),
    (r"на\s+(?:1\s+)?см²", "см²"),
    (r"на\s+(?:1\s+)?мкм²", "мкм²"),
    (r"/\s*м²", "м²"),
    (r"/\s*см²", "см²"),
    (r"/\s*мкм²", "мкм²"),
    (r"на\s+(?:1\s+)?мл", "мл"),
    (r"на\s+(?:1\s+)?литр", "л"),
    (r"/\s*л(?![а-я])", "л"),
    (r"на\s+(?:1\s+)?моль", "моль"),
    (r"/\s*моль", "моль"),
    (r"на\s+(?:1\s+)?секунду", "с"),
]
NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:[·×]\s*10\s*[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?")


def denominators(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    low = (text or "").lower()
    for pattern, name in DENOMS:
        for m in re.finditer(pattern, low):
            found[name] = found.get(name, 0) + 1
    return found


def nearby_number(text: str, pos: int, window: int = 40) -> str:
    seg = text[max(0, pos - window):pos + window]
    m = NUM.search(seg)
    return m.group(0) if m else "?"


def main(argv: list[str]) -> int:
    min_denoms = 2
    for i, a in enumerate(argv):
        if a == "--min" and i + 1 < len(argv):
            min_denoms = int(argv[i + 1])

    atoms = [json.loads(l) for l in ATOMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for a in atoms:
        text = " ".join(str(a.get(k) or "") for k in ("statement", "notes", "formula"))
        d = denominators(text)
        if len(d) >= min_denoms:
            rows.append((len(d), a["atom"], d, text))

    rows.sort(key=lambda r: -r[0])
    print(f"ячеек с ≥{min_denoms} разными знаменателями: {len(rows)}")
    print()
    if "--json" in argv:
        print(json.dumps([{"atom": r[1], "denoms": r[2]} for r in rows], ensure_ascii=False, indent=2))
        return 0

    for n, atom, d, text in rows[:15]:
        print("=" * 78)
        print(f"{atom}: {', '.join(f'{k}×{v}' for k, v in sorted(d.items()))}")
        # числа рядом с каждым знаменателем — то, что надо сверить
        low = text.lower()
        for pattern, name in DENOMS:
            for m in re.finditer(pattern, low):
                num = nearby_number(text, m.start())
                if num != "?":
                    print(f"   {name:8} ← {num}")
                    break
    print()
    print("Проверять так: перемножить/поделить числа по соседним знаменателям; если отношение даёт")
    print("физически невозможную величину (>10⁴ или <10⁻⁴ по порядку) — это внутреннее противоречие.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
