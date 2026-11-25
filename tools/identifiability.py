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
# разбор кандидатов вручную: пара -> (вердикт, объяснение)
# "product" — действительно произведение, данные различают только комбинацию
# "terms"   — два независимых слагаемых/множителя в разных членах, различимы
# "junk"    — не произведение: обрывок слова, префикс, имя величины
CURATED = {
    "F-001|λ·δ": ("product", "alpha = lambda*delta — это и есть определение alpha"),
    "F-003|λ·δ": ("product", "та же комбинация, что в F-001"),
    "F-003|λ·D": ("product", "скорость потери мощности: темп умножается на повреждение"),
    "F-001|F·I": ("junk", "обрывок: 'F' и 'I' из разных обозначений, не произведение"),
    "F-001|N·D": ("junk", "обрывок: 'N' и 'D' стоят рядом в тексте формулы"),
    "F-001|I·N": ("junk", "обрывок"),
    "F-002|h·D": ("terms", "слагаемое рекуррентности: h*D_n — произведение внутри одного члена, "
                           "но h и D различимы (h — параметр, D — состояние)"),
    "F-002|δ·T": ("product", "различимо только повреждение за поколение (FINDING-343)"),
    "F-004|c_y·σ": ("product", "доход формы: c_y*sigma — множители входят только вместе"),
    "F-005|κ·E": ("terms", "kappa и E различимы: kappa — доля, E — запас"),
    "F-006|Π·λ": ("product", "порог задан произведением (F-019, §7)"),
    "F-019|Π·λ": ("product", "то же"),
    "F-010|R·A": ("junk", "обрывок: 'R' и 'A' из RAF-обозначений, не произведение"),
    "F-010|f·o": ("junk", "обрывок слова"),
    "F-011|Δ·R": ("junk", "Delta — префикс приращения, а не множитель"),
    "F-012|Δ·z": ("junk", "Delta — префикс приращения"),
    "F-012|w·Δ": ("junk", "обрывок"),
    "F-012|C·o": ("junk", "обрывок слова"),
    "F-016|g·λ": ("junk", "обрывок: 'g' и 'lambda' из логарифма, не произведение"),
    "F-021|κ·J_A": ("terms", "kappa — доля, J_A — поток: различимы"),
    "F-022|o·u": ("junk", "обрывок слова"),
    "F-025|I_col·I_env": ("junk", "совместная информация — не произведение величин"),
    "F-027|γ·A": ("terms", "gamma — темп (1/время), A — площадь; входят в разные члены"),
    "F-028|C·V": ("junk", "'CV' — коэффициент вариации, имя величины"),
    "F-028|C·V_h": ("junk", "то же"),
    "F-028|f·o": ("junk", "обрывок слова"),
    "F-029|h·f": ("junk", "обрывок"),
    "F-030|M·O": ("junk", "обрывок слова"),
    "F-030|D·E": ("junk", "обрывок слова"),
}

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
    lines.append("## Кандидаты из латекса (с разбором)")
    lines.append("")
    lines.append("| формула | кандидат | вердикт | почему |")
    lines.append("|---|---|---|---|")
    counts = {"product": 0, "terms": 0, "junk": 0, "unchecked": 0}
    for fid in sorted(found):
        for pair in found[fid][:6]:
            v, why = CURATED.get(f"{fid}|{pair}", ("unchecked", "не проверялся"))
            counts[v] += 1
            lines.append(f"| `{fid}` | `{pair}` | {v} | {why} |")
    lines.append("")
    lines.append(f"Итог: **product** {counts['product']}, **terms** {counts['terms']}, "
                 f"**junk** {counts['junk']}, не проверено {counts['unchecked']}.")
    lines.append("")
    lines.append("«Не проверено» — не приговор: это список того, что ещё не читали глазами.")
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
