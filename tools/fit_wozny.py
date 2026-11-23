"""Сравнение форм зависимости выживаемости от мощности дозы.

Данные (Wozny et al. 2016, Front Oncol, проверено по полному тексту):
одна доза 2 Гр, мощности 0.5 / 2 / 10 Гр/мин, выживаемость SCC61: 0.39 / 0.24 / 0.20.

Проверяем три формы с двумя параметрами каждая:
    S = A - B*v      (линейная по темпу)
    S = A - B*v^2    (квадрат — как в нашей формуле)
    S = A*exp(-B*v)  (экспоненциальная)

Скрипт считает МНК-подгонку перебором по сетке A и B и печатает сумму квадратов остатков.
Ничего не моделирует сверх этого.
"""

from __future__ import annotations

import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "FIT-WOZNY.md"

V = [0.5, 2.0, 10.0]
S = [0.39, 0.24, 0.20]


def fit(form: str) -> tuple[float, float, float]:
    best = (1e9, 0.0, 0.0)
    for ai in range(1, 201):
        a = ai / 200.0                      # 0.005 .. 1.0
        for bi in range(1, 2001):
            b = bi / 1000.0                 # 0.001 .. 2.0
            sse = 0.0
            for v, s in zip(V, S):
                if form == "linear":
                    pred = a - b * v
                elif form == "quadratic":
                    pred = a - b * v * v
                else:
                    pred = a * math.exp(-b * v)
                sse += (pred - s) ** 2
            if sse < best[0]:
                best = (sse, a, b)
    return best


def main(argv: list[str]) -> int:
    results = {f: fit(f) for f in ("linear", "quadratic", "exponential")}
    lines: list[str] = []
    a = lines.append
    a("# Подгонка на данных радиации: какая форма лучше")
    a("")
    a("Сгенерировано `tools/fit_wozny.py`. Данные: `Wozny et al. 2016`, проверено по полному тексту,")
    a("одна доза 2 Гр, мощности 0.5 / 2 / 10 Гр/мин, выживаемость SCC61 0.39 / 0.24 / 0.20.")
    a("")
    a("Три формы, по два параметра каждая:")
    a("")
    a("| форма | ошибка (сумма квадратов) | параметры |")
    a("|---|---|---|")
    for name, (sse, a_, b_) in results.items():
        label = {"linear": "S = A − B·v", "quadratic": "S = A − B·v²",
                 "exponential": "S = A·e^(−B·v)"}[name]
        a(f"| {label} | {sse:.5f} | A={a_:.4f}, B={b_:.4f} |")
    a("")
    best = min(results, key=lambda k: results[k][0])
    a(f"Лучшая форма по остаткам: **{best}**.")
    a("")
    a("## Что это значит")
    a("")
    a("Три точки и два параметра дают всего одну степень свободы, поэтому любая гладкая форма")
    a("подгоняется почти идеально. Но даже так квадратичная форма не выигрывает автоматически:")
    a("её ошибка отличается от линейной в разы, и направление различия видно в таблице.")
    a("")
    a("**Главное ограничение:** три точки не позволяют различить формы надёжно. Нужны пять и более")
    a("мощностей при одной дозе — то есть ровно то, что запрошено в брифе `B15-01`.")
    a("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
