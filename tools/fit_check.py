"""Можно ли различить форму члена скорости на имеющихся данных?

Проверяем три формы:
    p = 1:  (dX/dX*) + (w/w*)   <= 1
    p = 2:  (dX/dX*) + (w/w*)^2 <= 1
    p = 3:  (dX/dX*) + (w/w*)^3 <= 1

Данные (все бинарные: «держится» / «срывается»):
  осмос, клетки почки:  50/ч держится; скачок срывается
  осмос, глиома C6:     180/ч держится; 360 и 540 срываются
  осмос, Jurkat:        30/ч даёт 40%; скачок — 15%

Скрипт не подгоняет модель, а показывает: для каждой формы существует ли набор (X, w*),
совместимый со всеми точками. Если да — форма не различается данными.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "FIT-CHECK.md"

SYSTEMS = {
    "почка мыши": {"holds": [50.0], "fails": [1e12]},          # скачок как бесконечная скорость
    "глиома C6": {"holds": [180.0], "fails": [360.0, 540.0]},
    "Jurkat": {"holds": [30.0], "fails": [1e12]},
}


def compatible(p: float, x_frac: float, w_star: float, sys_data: dict) -> bool:
    """Проверяет форму с показателем p при данном X и w*."""
    for v in sys_data["holds"]:
        if x_frac + (v / w_star) ** p > 1.0:
            return False
    for v in sys_data["fails"]:
        if x_frac + (v / w_star) ** p <= 1.0:
            return False
    return True


def main(argv: list[str]) -> int:
    lines: list[str] = []
    a = lines.append
    a("# Можно ли различить форму члена скорости")
    a("")
    a("Сгенерировано `tools/fit_check.py`. Проверяются три формы при сетке параметров.")
    a("")
    a("## Данные")
    a("")
    a("| система | держится при | срывается при |")
    a("|---|---|---|")
    a("| почка мыши | 50 в час | мгновенно |")
    a("| глиома C6 | 180 в час | 360 и 540 в час |")
    a("| Jurkat | 30 в час | мгновенно |")
    a("")
    a("## Перебор")
    a("")
    a("Для каждой формы ищем, существует ли пара `(X, w*)`, при которой все три системы объясняются")
    a("одной и той же формой (с общим `X` и своим `w*` на систему).")
    a("")
    results = {}
    for p in (1.0, 2.0, 3.0):
        found = {}
        for name, data in SYSTEMS.items():
            ok_any = False
            for w_star in [10 * 1.15 ** k for k in range(60)]:
                for xi in range(0, 21):
                    if compatible(p, xi / 20.0, w_star, data):
                        ok_any = True
                        break
                if ok_any:
                    break
            found[name] = ok_any
        results[p] = found
        a(f"### показатель p = {p:.0f}")
        a("")
        for name, ok in found.items():
            a(f"- {name}: {'объясняется' if ok else 'НЕ объясняется'}")
        a("")
    all_ok = all(all(v.values()) for v in results.values())
    a("## Вывод")
    a("")
    if all_ok:
        a("**Все три формы объясняют данные.** Это значит, что по имеющимся точкам показатель `p`")
        a("определить нельзя: бинарные исходы («держится/срывается») не различают степень.")
    else:
        a("Часть форм исключается — см. таблицы выше.")
    a("")
    a("## Что нужно, чтобы различить")
    a("")
    a("Нужны не бинарные исходы, а **градуированные**: доля выживших или скорость роста при 3-4 скоростях")
    a("в одной системе. Такие данные у нас есть только у дрожжей (`B18-02-0001`), но числа там в рисунках,")
    a("а не в тексте.")
    a("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
