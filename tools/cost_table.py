"""Сводная таблица цен: собирает из карты все ячейки, где есть величина с единицами.

Зачем: центральный тезис проекта — «цену границы можно измерить и сравнить». Пока это набор отдельных
чисел в разных валютах. Этот инструмент вытаскивает их в одну таблицу с единицами и условиями, чтобы
видно было, где величины действительно сопоставимы, а где только выглядят похоже.

Usage:
    python3 tools/cost_table.py            # markdown в stdout
    python3 tools/cost_table.py --write    # записать docs/COST-TABLE.md
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

MAP = pathlib.Path(__file__).resolve().parents[1] / "literature" / "map" / "atoms.jsonl"
OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "COST-TABLE.md"

# валюты, которые нас интересуют: (метка, регулярка по statement/notes/symbols)
CURRENCIES = [
    ("Вт/м² (мощность на площадь)", r"Вт/м|W/m|фДж/\(с|пДж/мкм"),
    ("Дж/м² (энергия на площадь)", r"Дж/м2|Дж/м²|J/m2|Дж/мг|кДж/г|kJ"),
    ("доля бюджета", r"%|дол[яию]|трети|процент"),
    ("энергия на массу/объём", r"мг глюкозы|мкВ/ч|мВт|мДж|нэкв"),
    ("время оборота", r"полужизн|t1/2|t½|врем[яи] полужизни|часов|суток"),
]


def collect() -> list[dict]:
    rows = []
    for line in MAP.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        hay = " ".join([
            str(a.get("statement") or ""),
            json.dumps(a.get("symbols") or {}, ensure_ascii=False),
            str(a.get("mechanism") or ""),
            " ".join(a.get("tags") or []),
        ])
        for label, pat in CURRENCIES:
            if re.search(pat, hay):
                rows.append({"label": label, "atom": a["atom"], "domain": a.get("domain"),
                             "kind": a.get("kind"), "confidence": a.get("confidence"),
                             "statement": (a.get("statement") or "")[:150]})
                break
    return rows


def render(rows: list[dict]) -> str:
    out = ["# Цены в одной таблице", "",
           "Собрано из карты автоматически: ячейки, в которых есть величина с единицами.",
           "Порядок — по валюте; внутри валюты сначала `high`, потом `medium`.", ""]
    for label, _ in CURRENCIES:
        group = [r for r in rows if r["label"] == label]
        if not group:
            continue
        group.sort(key=lambda r: ({"high": 0, "medium": 1, "low": 2}.get(r["confidence"], 3), r["atom"]))
        out.append(f"## {label} — {len(group)} ячеек")
        out.append("")
        out.append("| атом | область | уверенность | что именно |")
        out.append("|---|---|---|---|")
        for r in group:
            st = r["statement"].replace("|", "/")
            out.append(f"| `{r['atom']}` | {r['domain']} | {r['confidence']} | {st} |")
        out.append("")
    out.append("## Чего в таблице нет")
    out.append("")
    out.append("Ячейки без единиц (определения, условия, пустоты) сюда не попадают — это не ошибка,")
    out.append("но означает, что их нельзя сравнивать по величине, только по смыслу.")
    out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    rows = collect()
    text = render(rows)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT} ({len(rows)} ячеек с единицами)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
