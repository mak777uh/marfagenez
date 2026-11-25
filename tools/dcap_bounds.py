"""Границы `D_cap` по опубликованным измерениям: одна экспонента не покрывает все данные.

Формула v2 (`docs/FORMULA-DCRITICAL.md`) постулирует `R(D) = min(C0·exp(−D/D_cap), k·D)`. Если
`D_cap` — свойство системы, то из любой пары `(D, R(D))` он должен получаться одинаково. Здесь он
считается из трёх наборов данных, уже лежащих в карте, и сравнивается.

Что берём:
  DIP59-0001  RIF-фокусы: разрешение при 2 Гр примерно в 5 раз медленнее, чем при 0,1 Гр;
  DIP59-0006  53BP1-фокусы: t½ = 2,7 ± 0,8 ч при 500 мГр против 3,1 ± 0,5 ч при 5–10 мГр;
  DIP59-0005  DSB по PFGE: t½ = 168 ± 10 мин, не зависит от дозы в диапазоне 3–90 Гр.

Запуск: python3 tools/dcap_bounds.py
"""

from __future__ import annotations

import math


def dcap_from_two(d1: float, r1: float, d2: float, r2: float) -> float:
    """R(D) = C0·exp(−D/D_cap) ⇒ ln(r1/r2) = (d2−d1)/D_cap."""
    if r1 <= 0 or r2 <= 0 or r1 == r2:
        raise ValueError("отношение скоростей должно быть положительным и не равным 1")
    return (d2 - d1) / math.log(r1 / r2)


def main() -> int:
    print("== D_cap из RIF-фокусов (DIP59-0001)")
    # R ∝ 1/t½; при 2 Гр в 5 раз медленнее, чем при 0,1 Гр ⇒ R(0.1)/R(2) = 5
    d1 = dcap_from_two(0.1, 5.0, 2.0, 1.0)
    print(f"   D_cap ≈ {d1:.2f} Гр (отношение 5 на интервале 0,1–2 Гр)")

    print("== D_cap из 53BP1-фокусов (DIP59-0006)")
    t_half_low, t_half_high = 3.1, 2.7      # 5–10 мГр против 500 мГр
    d2 = dcap_from_two(0.0075, 1.0 / t_half_low, 0.5, 1.0 / t_half_high)
    print(f"   D_cap ≈ {d2:.2f} Гр (t½ {t_half_low} ч при 7,5 мГр против {t_half_high} ч при 500 мГр)")

    print("== нижняя граница из DSB по PFGE (DIP59-0005)")
    # изменение t½ в пределах погрешности на интервале 3–90 Гр: считаем, что R упала не более чем на 6 %
    t_half, err = 168.0, 10.0
    max_drop = err / t_half                # ~6 %
    d3 = (90.0 - 3.0) / -math.log(1.0 - max_drop)
    print(f"   D_cap > {d3:.0f} Гр (t½ = {t_half:.0f} ± {err:.0f} мин на 3–90 Гр, допустимое падение {max_drop:.1%})")

    print()
    print(f"разброс оценок: {d3 / d1:.0f} раз между нижней границей (PFGE) и оценкой по фокусам")

    print()
    print("== что предсказывает v2 при D_cap = %.2f Гр" % d1)
    for dose in (2, 5, 10, 30, 90):
        print(f"   R({dose:>2} Гр)/R(0) = {math.exp(-dose / d1):.2e}")
    print("   При этом PFGE-данные дают постоянную скорость до 90 Гр — это противоречие, а не разброс.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
