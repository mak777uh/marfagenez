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
import sys

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
    "set", "all", "any", "one", "two", "six", "for", "min", "max", "sup", "inf", "lim", "log", "exp",
    # индексные буквы и служебные обозначения (не величины): i, j в π(i), p_j; e — число Эйлера;
    # E — оператор математического ожидания E[...]
    "i", "j", "e", "E",
    "and", "not", "but", "the", "see", "use", "via", "per", "её", "их", "это", "шаг", "ось", "оси",
}

LATIN = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{0,11})\b")
CYR = re.compile(r"\b([а-яА-ЯёЁ]{3,})")


def main(argv: list[str]) -> int:
    nodes = [json.loads(l) for l in NODES.read_text(encoding="utf-8").splitlines()]
    formulas = [n for n in nodes if n.get("kind") == "formula"]
    total_gaps = 0
    for n in formulas:
        latex = str((n.get("math") or {}).get("latex") or "")
        units = (n.get("math") or {}).get("units") or {}
        if not latex:
            continue
        # Формулы без таблицы единиц — структурные (множества, логические условия): у них единиц нет по
        # смыслу, и сообщать про их символы значит выдавать структурность за дырку.
        if not units:
            continue
        # Дифференциалы: `dA`, `dt`, `dD` — это `d` + переменная, а не новые имена. Иначе каждый
        # дифференциал попадает в кандидаты и шум растёт (33 кандидата на 3 дырки при первом прогоне).
        # Ссылки на клетки карты (`L-061`, `F-029`) — не символы величины. Без этого `L` попадал в кандидаты
        # у каждой формулы, которая цитирует клетку.
        cleaned = re.sub(r"\b[A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+\b", " ", latex)
        cleaned = re.sub(r"\bd([A-Za-z])", r"\1", cleaned)
        cleaned = re.sub(r"\bdt\b", " ", cleaned)
        tokens = set(LATIN.findall(cleaned)) | set(CYR.findall(cleaned))
        covered = set(units)
        # символ считаем «в записи», если он встречается как отдельное слово или как имя переменной
        def covered_by_prefix(t: str) -> bool:
            """`h` покрыт, если в таблице есть `h_c`: буква — сокращение того же символа с подписью."""
            if len(t) != 1:
                return False
            return any(str(c).startswith(t) for c in covered)

        def covered_by_base(t: str) -> bool:
            """`p_j` покрыт, если покрыт `p`; `indeg_C` — если `indeg`; `X_t` — если `X`."""
            if t in covered or covered_by_prefix(t):
                return True
            base = t.split("_")[0]
            if base in covered:
                return True
            for c in covered:
                if t.startswith(c) and len(c) >= 2:
                    return True
            return False

        # Однобуквенные символы — самые частые переменные (`d`, `x`, `p`). Фильтр `len(t) > 1` их выбрасывал,
        # и проверка не видела, например, что `d` в `c·d·q_min` (F-027) вообще отсутствует в таблице единиц.
        gaps = sorted(t for t in tokens
                      if not covered_by_base(t) and t not in NOISE and len(t) >= 1
                      and (t[0].islower() or t[0].isupper()))
        # оставим только те, что реально похожи на переменные: одна-две буквы или с подчёркиванием
        def looks_like_symbol(t: str) -> bool:
            if "_" in t and t[0].isascii():
                return True
            # `cvc`, `scc`, `RAF`, `CV` — настоящие символы, их длина 2–3. Раньше отсекались трёхбуквенные,
            # и самопроверка не покраснела, когда я убрал `cvc` из единиц: фильтр его выбрасывал.
            if t.isascii() and len(t) <= 3:
                return True
            return False

        suspicious = [g for g in gaps if looks_like_symbol(g)]
        if suspicious:
            total_gaps += len(suspicious)
            print(f"{n['id']}: не в таблице единиц -> {', '.join(suspicious[:12])}")
            if units:
                print(f"    покрыто: {', '.join(sorted(units))}")
    print()
    print(f"кандидатов на проверку: {total_gaps}")
    strict = "--strict" in argv
    if strict:
        base_file = ROOT / "docs" / "UNITS-SYMBOLS-BASELINE.json"
        ceiling = 0
        if base_file.exists():
            try:
                ceiling = int(json.loads(base_file.read_text(encoding="utf-8")).get("gaps") or 0)
            except Exception:
                ceiling = 0
        if total_gaps > ceiling:
            print(f"СТРОГИЙ РЕЖИМ: кандидатов {total_gaps} больше потолка {ceiling} — объявите единицы")
            return 1
        if ceiling:
            print(f"СТРОГИЙ РЕЖИМ: {total_gaps} кандидатов при потолке {ceiling} — долг не вырос")
            return 0
        print("СТРОГИЙ РЕЖИМ: все символы формул с единицами покрыты")
        return 0
    print("Список для чтения: имена команд latex и слова прозы сюда тоже попадают.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
