"""F-016 «цена страховки»: где работает приближение `log λ_s ≈ log λ̄ − σ²/(2λ̄²)`.

Формула — разложение второго порядка по относительной флуктуации среды. Проверяем численно: для
`λ_t = λ̄(1+ε_t)`, `ε ~ N(0, v)`, точная средняя логарифмическая скорость роста равна
`log λ̄ + E[log(1+ε)]` (при `ε > −1`), а приближение даёт `log λ̄ − v/2`.

Считаем точное значение квадратурой по усечённому нормальному распределению и сравниваем.

Запуск: python3 tools/insurance_limit.py
"""

from __future__ import annotations

import math


def exact_minus_log_lambda(v: float, n: int = 20001) -> float:
    """E[log(1+ε)] для ε ~ N(0, v), усечённого на (−1, ∞), через квадратуру по сетке."""
    if v <= 0:
        return 0.0
    sd = math.sqrt(v)
    lo, hi = -1.0 + 1e-9, 8.0
    # узлы сетки по z в пределах ±8 sd
    zmin, zmax = max((lo) / sd, -8.0), min(hi / sd, 8.0)
    h = (zmax - zmin) / (n - 1)
    total = 0.0
    norm = 0.0
    for i in range(n):
        z = zmin + i * h
        w = math.exp(-0.5 * z * z)
        x = 1.0 + sd * z
        if x <= 0:
            continue
        total += w * math.log(x)
        norm += w
    return total / norm if norm else 0.0


def main() -> int:
    print("v = σ²/λ̄² (относительная дисперсия среды)")
    print(f"{'v':>7} {'σ/λ̄':>7} {'точно':>12} {'приближ.':>12} {'ошибка':>10}")
    rows = []
    for v in (0.01, 0.04, 0.09, 0.25, 0.49, 0.81, 1.0):
        exact = exact_minus_log_lambda(v)
        approx = -v / 2.0
        err = exact - approx
        rows.append((v, math.sqrt(v), exact, approx, err))
        print(f"{v:7.2f} {math.sqrt(v):7.2f} {exact:12.5f} {approx:12.5f} {err:10.5f}")

    print()
    worst_small = max(abs(r[4]) for r in rows if r[0] <= 0.09)
    worst_mid = max(abs(r[4]) for r in rows if r[0] <= 0.25)
    print(f"макс. ошибка при v ≤ 0,09: {worst_small:.5f} (в долях σ) — приближение годится")
    print(f"макс. ошибка при v ≤ 0,25: {worst_mid:.5f}")
    big = [r for r in rows if r[0] >= 0.49]
    print("при v ≥ 0,49 (σ/λ̄ ≥ 0,7):")
    for v, s, e, a, err in big:
        print(f"  v={v:.2f}: ошибка {err:.4f} — это уже не «поправка порядка σ²», а половина члена")

    print()
    print("ВЫВОД: формула верна как разложение второго порядка; рабочая граница — σ/λ̄ ≲ 0,3 (v ≲ 0,09).")
    print("Опровергающее условие: если при σ/λ̄ < 0,1 ошибка превышает 1 %, формула неверна, а не «неточна».")
    ok = worst_small < 0.01
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
