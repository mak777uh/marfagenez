"""Полнота записей формул в карте знаний: единицы, проверка прогоном, литературная опора.

Задача-повод: `P7` показал, что запись может обещать больше, чем содержит. Здесь то же самое, но по
всему слою формул: сколько записей вообще имеют единицы и на что опираются.

Запуск:
    python3 tools/formula_records.py           # сводка
    python3 tools/formula_records.py --write   # docs/FORMULA-RECORDS-AUDIT.md
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
OUT = ROOT / "docs" / "FORMULA-RECORDS-AUDIT.md"


def load_formulas() -> list[dict]:
    out = []
    for line in NODES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n = json.loads(line)
            if n.get("kind") == "formula":
                out.append(n)
    return out


def main(argv: list[str]) -> int:
    write = "--write" in argv
    fs = sorted(load_formulas(), key=lambda n: n["id"])

    rows = []
    for n in fs:
        math = n.get("math") or {}
        units = math.get("units") or {}
        checked = (math.get("checked") or {}).get("kind", "none")
        lit = (n.get("data") or {}).get("lit_ref") or []
        rows.append({
            "id": n["id"],
            "text": n.get("text", "")[:60],
            "units": len(units),
            "checked": checked,
            "lit": len(lit),
        })

    no_units = [r for r in rows if r["units"] == 0]
    unreviewed = [r for r in rows if r["checked"] == "none"]
    no_lit = [r for r in rows if r["lit"] == 0]

    lines: list[str] = []
    a = lines.append
    a("# Полнота записей формул (сгенерировано `tools/formula_records.py`)")
    a("")
    a("## Зачем")
    a("")
    a("После `P7` стало ясно: запись может обещать больше, чем содержит (там текст называл аналитическую")
    a("формулу «вычислением ядра»). Здесь проверяется базовое: есть ли у записи единицы, проверена ли она")
    a("прогоном и на что опирается в литературе.")
    a("")
    a("## Числа")
    a("")
    a(f"- формул в карте: **{len(rows)}**")
    a(f"- без объявленных единиц: **{len(no_units)}**")
    a(f"- без проверки прогоном (`checked.kind == none`): **{len(unreviewed)}**")
    a(f"- без литературной опоры (`lit_ref` пуст): **{len(no_lit)}**")
    a("")
    a("## Таблица")
    a("")
    a("| формула | о чём | величин с единицами | проверка | опора |")
    a("|---|---|---|---|---|")
    for r in rows:
        a(f"| `{r['id']}` | {r['text']} | {r['units']} | {r['checked']} | {r['lit']} |")
    a("")
    a("## Вывод")
    a("")
    a("Слой формул **не аудирован системно**: большинство записей не объявляют единицы и не имеют")
    a("проверки прогоном. Три записи (`F-001`, `F-003`, `F-029`) приведены в порядок в циклах 567 и 570 —")
    a("это исключение, а не правило.")
    a("")
    a("## Предложение (не применяю автоматически)")
    a("")
    a("1. Не добавлять новую формулу без `math.units` и хотя бы одного символа в `math.symbols`.")
    a("2. Записям без единиц присвоить `units: {}` и пометить `epistemic` ниже, чем `established`, —")
    a("   пока единицы не выписаны, «проверенность» ограничена.")
    a("3. Ввести проверку, но **с порогом**: она краснеет не на «есть 24 без единиц», а на «число выросло».")
    a("   Иначе гейт станет красным на историческом долге и его начнут обходить.")
    a("")
    a("## Чего это не доказывает")
    a("")
    a("- Что формулы без единиц неверны: часть безразмерна по построению, но это должно быть **сказано**,")
    a("  а не выведено читателем.")
    a("- Что отсутствие `lit_ref` означает отсутствие опоры: опора может быть в `evidence`.")
    text = "\n".join(lines) + "\n"

    if write:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано: {OUT}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
