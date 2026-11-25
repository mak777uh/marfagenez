"""Полнота таблицы единиц: есть ли в записи формулы символ, для которого нет единицы.

Повод (25.11.2026): в `F-030` была четвёртая строка `MODES` («набор из нескольких метрик»), которой не было
в таблице единиц. Таблица покрывала три метрики из четырёх. Найти такое глазами на 31 формуле трудно.

Скрипт берёт `math.latex` каждой формулы, вытаскивает латинские/греческие имена (после `\\`-команд), ищет те,
что встречаются как отдельные символы в записи, и печатает те, для которых в `math.units` нет ключа.

Это **список для чтения**, а не гейт: в latex попадают имена команд (`frac`, `exp`), и часть
«непокрытых» — просто служебные слова.

Запуск: python3 tools/units_symbol_audit.py
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODES = ROOT / "kg" / "nodes.jsonl"

# служебные слова latex и естественного языка, которые не являются величинами
NOISE = {
    "frac", "exp", "log", "ln", "sqrt", "sum", "int", "min", "max", "cdot", "times", "pm", "approx",
    "le", "ge", "ll", "gg", "to", "in", "forall", "exists", "quad", "text", "mathrm", "left", "right",
    "prod", "partial", "nabla", "infty", "Rightarrow", "iff", "sim", "propto", "alpha", "beta", "gamma",
    "delta", "varepsilon", "epsilon", "kappa", "lambda", "mu", "nu", "pi", "rho", "sigma", "tau", "phi",
    "psi", "omega", "theta", "Delta", "Pi", "Sigma", "Phi", "Psi", "Omega", "Theta", "Lambda", "Xi",
    "и", "в", "на", "при", "для", "это", "если", "то", "как", "или", "не", "из", "с", "по", "к", "о",
    "the", "of", "is", "for", "when", "and", "or", "with", "md", "shell", "state", "true", "false",
}

LATIN = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{0,11})\b")
CYR = re.compile(r"\b([а-яА-ЯёЁ]{3,})")


def main() -> int:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines()]
    formulas = [n for n in nodes if n.get("kind") == "formula"]
    total_gaps = 0
    for n in formulas:
        latex = str((n.get("math") or {}).get("latex") or "")
        units = (n.get("math") or {}).get("units") or {}
        if not latex:
            continue
        tokens = set(LATIN.findall(latex)) | set(CYR.findall(latex))
        covered = set(units)
        # символ считаем «в записи», если он встречается как отдельное слово или как имя переменной
        gaps = sorted(t for t in tokens
                      if t not in covered and t not in NOISE and len(t) > 1
                      and (t[0].islower() or t[0].isupper()))
        # оставим только те, что реально похожи на переменные: одна-две буквы или с подчёркиванием
        suspicious = [g for g in gaps if len(g) <= 3 or "_" in g]
        if suspicious:
            total_gaps += len(suspicious)
            print(f"{n['id']}: не в таблице единиц -> {', '.join(suspicious[:12])}")
            if units:
                print(f"    покрыто: {', '.join(sorted(units))}")
    print()
    print(f"кандидатов на проверку: {total_gaps}")
    print("Список для чтения: имена команд latex и слова прозы сюда тоже попадают.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
