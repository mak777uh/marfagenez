"""Собрать математику карты в один файл: формулы, их смысл и пустые места.

Usage: python3 tools/math_core.py [--write]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAP = ROOT / "literature" / "map" / "atoms.jsonl"
OUT = ROOT / "docs" / "MATH-CORE.md"

GROUPS = [
    ("Скорость процесса", r"d[A-Za-z]|/dt|r\(D\)|lambda|λ|скорост", "как быстро что-то прибывает или убывает"),
    ("Цена и мощность", r"P/A|Вт|Дж|ATP|цена|стоимост|cost", "сколько стоит поддержание"),
    ("Порог и критерий", r">=|<=|порог|критич|μ\*|порогов", "при каком условии режим меняется"),
    ("Вероятность и информация", r"Q_|вероятн|энтроп|бит|информац", "границы на точность и на энтропию"),
    ("Пространство и форма", r"q\b|волнов|диффузи|Тьюринг|мод", "как возникает пространственный паттерн"),
    ("Надёжность и смертность", r"hazard|интенсивност|Гомперц|Gompertz|виртуальн", "как растёт риск отказа"),
]


def has_formula(atom: dict) -> bool:
    if atom.get("formula"):
        return True
    st = atom.get("statement") or ""
    return bool(re.search(r"[=<>≤≥~]", st))


def main(argv: list[str]) -> int:
    atoms = [json.loads(l) for l in MAP.read_text(encoding="utf-8").splitlines() if l.strip()]
    formulas = [a for a in atoms if has_formula(a)]
    gaps = [a for a in atoms if a.get("kind") == "gap"]

    lines: list[str] = []
    add = lines.append
    add("# Математика карты")
    add("")
    add(f"Сгенерировано `tools/math_core.py`: ячеек с формулой или отношением — {len(formulas)},")
    add(f"пустот — {len(gaps)}. Группировка по типу закона, внутри — по областям.")
    add("")
    for name, pat, why in GROUPS:
        group = [a for a in formulas if re.search(pat, " ".join([
            str(a.get("formula") or ""), str(a.get("statement") or ""), str(a.get("mechanism") or "")]))]
        if not group:
            continue
        add(f"## {name} — {len(group)}")
        add("")
        add(f"*Зачем:* {why}.")
        add("")
        for a in sorted(group, key=lambda x: (x.get("domain") or "", x["atom"])):
            f = a.get("formula") or "—"
            add(f"- `{a['atom']}` ({a.get('domain')}): `{f}`")
            add(f"  {a['statement'][:190]}")
        add("")

    add("## Чего в математике нет")
    add("")
    add("Пустоты, где нужная формула отсутствует по результатам поиска:")
    add("")
    for a in sorted(gaps, key=lambda x: (x.get("domain") or "", x["atom"]))[:40]:
        add(f"- `{a['atom']}` ({a.get('domain')}): {a['statement'][:170]}")
    add("")
    add("## Что это значит")
    add("")
    add("Формул много, но они про разные вещи: скорость, цена, порог, вероятность, форма. Общей")
    add("математики, которая связывает цену поддержания с деградацией ремонта и наследованием, в карте")
    add("нет — и это не пробел поиска, а отсутствие самой конструкции.")
    add("")
    text = "\n".join(lines) + "\n"
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}: формул {len(formulas)}, пустот {len(gaps)}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
