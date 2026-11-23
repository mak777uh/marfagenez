"""Сводная таблица цен: приводим все к паре «поток × сила» и считаем произведение.

Все входные числа — из принятых ячеек карты. Скрипт только пересчитывает единицы и умножает,
ничего не измеряет и не моделирует. Результат пишется в docs/PRICE-TABLE.md.

Usage: python3 tools/price_table.py [--write]
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PRICE-TABLE.md"

F = 96485.0          # Кл/моль
V_MOL_WATER = 18e-6   # м3/моль

# (подпись, поток массовый в моль/(м2*с) или None, сила в Дж/моль, цена Вт/м2 или None, ячейка)
ROWS = [
    ("мембрана данио, ATPase", 1.7e-8, 50_000.0, 8e-4, "B7-03-0001"),
    ("мембрана данио, ATPase (верх)", 1.7e-7, 50_000.0, 8e-3, "B7-03-0001"),
    ("нейронный компартмент, Na/K", 6.0e-6, 50_000.0, 0.3, "B7-03-0003"),
    ("эпителий молочной железы", 24.6e-6 / 1e-4 / F, 12.8e-3 * F, 3.15e-3, "DIP24-0001"),
    ("корневой волосок Arabidopsis", 250e-6 / 1e-4 / F, 200e-3 * F, 0.5, "DIP24-0002"),
    ("кожа Necturus (зажим)", 227e-12 / 1e-4, 8e-3 * F, 0.83e-3, "DIP24-0003"),
    ("обратный осмос (промышленный)", 8.7e-6 / V_MOL_WATER, 153e3 * V_MOL_WATER, 1.33, "B11-08-0002"),
    ("гидравлическая мембрана", None, 5.9e3 * V_MOL_WATER, 0.14e-3, "DIP24-0005"),
    ("кисты MDCK", None, 248e3 * V_MOL_WATER, 3.0e-3, "DIP24-0007"),
]


def main(argv: list[str]) -> int:
    rows = []
    for name, flux, force, price, atom in ROWS:
        calc = flux * force if flux is not None else None
        rows.append((name, flux, force, price, calc, atom))

    lines: list[str] = []
    add = lines.append
    add("# Цены в одной таблице: поток, сила, произведение")
    add("")
    add("Сгенерировано `tools/price_table.py` из принятых ячеек. Скрипт только пересчитывает единицы:")
    add("поток приводится к моль/(м²·с), сила — к Дж/моль, произведение — к Вт/м².")
    add("")
    add("| система | поток, моль/(м²·с) | сила, Дж/моль | цена, Вт/м² | поток×сила | ячейка |")
    add("|---|---|---|---|---|---|")
    for name, flux, force, price, calc, atom in rows:
        fs = "—" if flux is None else f"{flux:.2e}"
        cs = "—" if calc is None else f"{calc:.2e}"
        add(f"| {name} | {fs} | {force:.3g} | {price:.2e} | {cs} | `{atom}` |")
    add("")
    known = [r for r in rows if r[4] is not None]
    add("## Проверка")
    add("")
    mism = [(n, p, c) for n, _, _, p, c, _ in known if p > 0 and not (0.2 * p <= c <= 5 * p)]
    if mism:
        add("Есть расхождения больше чем в 5 раз (значит числа из ячеек описывают разные условия):")
        for n, p, c in mism:
            add(f"- {n}: цена {p:.2e}, произведение {c:.2e}")
    else:
        add("Для всех строк, где известны оба члена, произведение совпадает с ценой в пределах 5 раз.")
    add("")
    add("## Что видно")
    add("")
    add("Силы различаются на пять порядков (от десятых долей Дж/моль у воды под давлением до десятков")
    add("килоджоулей на моль у ATP), а потоки — на семь порядков (от единиц наномоль у ATP до десятых")
    add("долей моля у воды). Произведение укладывается в четыре порядка. Это и есть наша формула:")
    add("")
    add("    цена = поток * сила")
    add("")
    add("Малые силы компенсируются большими потоками, и наоборот. Поэтому сравнение «по ткани» или")
    add("«по царству» ничего не даёт, а сравнение по паре даёт порядок.")
    add("")
    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"записано {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
