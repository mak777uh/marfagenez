"""Независимая проверка чисел `docs/RD-VS-V3.md` (агент `fast`): остаток DSB при 2400 Гр через 72 ч.

Модель RD (PMC4711806, Table 1, разрежённое излучение):
    dD1/dt = k1·R − (v1 + q1·R)·D1
    dD2/dt = k2·R − (v2 + q2·R)·D2 + q1·R·D1
    dD3/dt = k3·R + q2·R·D2
Параметры из документа: k1 = 6,08·10⁻², k2 = 7,83·10⁻³, k3 = 0,
v1 = 1,07 ч⁻¹, v2 = 4,44·10⁻² ч⁻¹, q1 = 1,22·10⁻³ Гр⁻¹, q2 = 2,67·10⁻⁴ Гр⁻¹, R = 7800 Гр/ч.

После облучения R = 0, классы спадают со своими v (DSB3 не репарируется).
Документ утверждает: при 2400 Гр остаток через 72 ч = 28,4 (измерено 30,2).

Запуск: python3 tools/verify_rd_numbers.py
"""

from __future__ import annotations

K1, K2, K3 = 6.08e-2, 7.83e-3, 0.0
V1, V2 = 1.07, 4.44e-2
Q1, Q2 = 1.22e-3, 2.67e-4
RATE = 7800.0


def run(dose: float, hours_after: float, dt: float = 1e-5) -> tuple[float, float, float]:
    t_irr = dose / RATE
    d1 = d2 = d3 = 0.0
    t = 0.0
    while t < t_irr:
        h = min(dt, t_irr - t)
        a1 = K1 * RATE - (V1 + Q1 * RATE) * d1
        a2 = K2 * RATE - (V2 + Q2 * RATE) * d2 + Q1 * RATE * d1
        a3 = K3 * RATE + Q2 * RATE * d2
        d1, d2, d3 = d1 + h * a1, d2 + h * a2, d3 + h * a3
        t += h
    d1 *= pow(2.718281828459045, -V1 * hours_after)
    d2 *= pow(2.718281828459045, -V2 * hours_after)
    return d1, d2, d3


def main() -> int:
    print("== проверка чисел RD-VS-V3 (2400 Гр, 72 ч)")
    d1, d2, d3 = run(2400.0, 72.0)
    total = d1 + d2 + d3
    print(f"  DSB1 = {d1:.2f}, DSB2 = {d2:.2f}, DSB3 = {d3:.2f}")
    print(f"  остаток всего = {total:.2f} (в документе 28,4; измерено 30,2)")
    print(f"  расхождение с документом: {abs(total - 28.4):.2f}")

    print()
    print("== тот же прогон при 22 ч (документ: 57,2)")
    d1b, d2b, d3b = run(2400.0, 22.0)
    print(f"  остаток = {d1b + d2b + d3b:.2f}")

    print()
    print("== состав классов при 2400 Гр (документ: 28/56/16 %)")
    d1c, d2c, d3c = run(2400.0, 0.0)
    s = d1c + d2c + d3c
    if s:
        print(f"  {100*d1c/s:.0f} / {100*d2c/s:.0f} / {100*d3c/s:.0f} %")

    ok = abs(total - 28.4) < 1.5
    print()
    print("ВЫВОД:", "числа документа воспроизводятся" if ok else "числа документа НЕ воспроизводятся")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
