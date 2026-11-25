"""Различимость параметров: если они входят только произведением, по данным различима лишь комбинация.

Зачем. Три раза подряд в этой линии обнаруживалось одно и то же:
  * `F-001`: `alpha = lambda*delta` — наблюдаемо только произведение (`FINDING-297`);
  * `F-002`: `delta*T` — различимо только повреждение за поколение (`FINDING-343`);
  * `F-017`: `q^nu` — различима только комбинация «точность на основание в степени длины»;
  * `F-006/F-019`: `Pi*lambda` — порог задан произведением.

Проверка механическая: ищем в `math.latex` формулы произведения двух/трёх символов и печатаем их как
кандидатов на неразличимость. Это эвристика (регексп по латексу), поэтому вывод — список для чтения
глазами, а не приговор.

Запуск: python3 tools/identifiability.py [--write]
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"
OUT = ROOT / "docs" / "IDENTIFIABILITY.md"

# символ: одна греческая буква или латинская с индексом, не команда и не число
SYM = r"(?:[A-Za-zα-ωΑ-Ω]|\\[a-zA-Z]+)(?:_\{?[A-Za-z0-9]+\}?)?"

# известные случаи: проверены вручную и записаны в docs/UNITS-AUDIT.md
KNOWN = {
    "F-001": ("alpha = lambda·delta", "наблюдаемо только alpha; множители не разделяются"),
    "F-002": ("delta·T", "различимо только повреждение за поколение"),
    "F-017": ("q^nu", "различима только точность в степени длины генома"),
    "F-006": ("Pi·lambda", "порог задан произведением; отдельные Pi и lambda не наблюдаются"),
    "F-019": ("Pi·lambda", "то же, симметричный случай"),
}


def main(argv: list[str]) -> int:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    formulas = [n for n in nodes if n.get("kind") == "formula"]

    found: dict[str, list[str]] = collections.defaultdict(list)
    for n in formulas:
        latex = ((n.get("math") or {}).get("latex") or "")
        # произведения вида a·b, ab, a b
        for m in re.finditer(rf"({SYM})\s*[·\\*]?\s*({SYM})", latex):
            a, b = m.group(1), m.group(2)
            if a == b or a.isdigit() or b.isdigit():
                continue
            pair = f"{a}·{b}"
            # отсекаем мусор из слов: 'ln', 'max', 'min', одиночные строчные латинские без индекса
            junk = {"l", "n", "e", "d", "x", "t", "s", "i", "m", "a", "b", "c", "p", "q", "r", "v"}
            if a in junk or b in junk:
                continue
            if pair not in found[n["id"]]:
                found[n["id"]].append(pair)

    lines = ["# Различимость параметров: что наблюдается, а что нет", ""]
    lines.append("Сгенерировано `tools/identifiability.py`. Эвристика по латексу: список кандидатов на")
    lines.append("чтение глазами, а не приговор. Смысл правила: если параметры входят только")
    lines.append("произведением, данные различают **комбинацию**, а не множители.")
    lines.append("")
    lines.append("## Подтверждено вручную")
    lines.append("")
    lines.append("| формула | комбинация | что это значит |")
    lines.append("|---|---|---|")
    for fid, (combo, why) in KNOWN.items():
        lines.append(f"| `{fid}` | `{combo}` | {why} |")
    lines.append("")
    lines.append("## Кандидаты из латекса")
    lines.append("")
    for fid in sorted(found):
        pairs = found[fid][:4]
        lines.append(f"- `{fid}`: " + ", ".join(f"`{p}`" for p in pairs))
    lines.append("")
    lines.append("## Как пользоваться")
    lines.append("")
    lines.append("1. Кандидат — не приговор: проверьте, входит ли пара как произведение или как два")
    lines.append("   независимых слагаемых.")
    lines.append("2. Если произведение — данные различают только его. Записывайте комбинацию как")
    lines.append("   наблюдаемую величину, а множители — как параметры модели.")
    lines.append("3. Проверка не заменяет оценку: она говорит, что **нельзя** оценить, а не что можно.")
    text = "\n".join(lines) + "\n"

    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано: {OUT}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
