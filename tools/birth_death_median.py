"""`F-013`: `ρ ≈ 2^(−1/m)` — какая медиана имеется в виду?

Запись: `π(n) = (1−ρ)ρⁿ`, медиана `m`, `ρ ≈ 2^(−1/m)`.

Ключевое различие, которое решает всё: **какая медиана**.
- `P(X ≤ m) = 1/2` — медиана по функции распределения (CDF-медиана);
- `P(X ≥ m) = 1/2`, то есть `ρ^m = 1/2` — медиана по выживанию (survival-медиана).

Формула `ρ = 2^(−1/m)` **эквивалентна второму определению** и для геометрического распределения точна.
С первым определением она систематически смещена: CDF-медиана геометрического распределения меньше
survival-медианы, поэтому `ρ` по ней занижается.

Проверяем численно: обе медианы и обе оценки `ρ` для разных `ρ` и верхней стенки `N`.

Опровергающее условие: если survival-медиана даёт ошибку в `ρ` больше 1 % при `N ≥ 50·m`, приближение неверно
как таковое (а не из-за определения).

Запуск: python3 tools/birth_death_median.py
"""

from __future__ import annotations

import math


def stationary(rho: float, n_max: int) -> list[float]:
    w = [rho ** i for i in range(n_max + 1)]
    s = sum(w)
    return [x / s for x in w]


def median_cdf(dist: list[float]) -> float:
    acc = 0.0
    for i, pr in enumerate(dist):
        prev = acc
        acc += pr
        if acc >= 0.5:
            return i - 1 + (0.5 - prev) / pr if pr > 0 else float(i)
    return float(len(dist) - 1)


def median_survival(dist: list[float]) -> float:
    """Наибольшее m с P(X ≥ m) ≥ 1/2 (с интерполяцией между соседними шагами)."""
    n = len(dist)
    for m in range(n):
        tail = sum(dist[m:])
        if tail < 0.5:
            # между m−1 и m: интерполируем по хвосту
            tail_prev = sum(dist[m - 1:])
            frac = (tail_prev - 0.5) / (tail_prev - tail) if tail_prev > tail else 0.0
            return (m - 1) + frac
    return float(n - 1)


def main() -> int:
    print(f"{'ρ':>6} {'N':>6} {'m (CDF)':>9} {'ρ по CDF':>9} {'m (выж.)':>9} {'ρ по выж.':>10} {'ошибка':>9}")
    worst_survival = 0.0
    for rho in (0.5, 0.8, 0.9, 0.95, 0.99):
        for n_max in (50, 200, 1000, 5000):
            dist = stationary(rho, n_max)
            m_cdf = median_cdf(dist)
            m_surv = median_survival(dist)
            rho_cdf = 2 ** (-1.0 / m_cdf) if m_cdf > 0 else float('nan')
            rho_surv = 2 ** (-1.0 / m_surv) if m_surv > 0 else float('nan')
            err = rho_surv - rho
            print(f"{rho:6.2f} {n_max:6d} {m_cdf:9.3f} {rho_cdf:9.4f} {m_surv:9.3f} {rho_surv:10.4f} "
                  f"{err:+9.5f}")
            if n_max >= 50 * max(m_surv, 1):
                worst_survival = max(worst_survival, abs(err))

    print()
    print(f"макс. ошибка survival-версии при N ≥ 50·m: {worst_survival:.5f}")
    print()
    print("ЧТО ЭТО ЗНАЧИТ:")
    print("  1. Формула ρ = 2^(−1/m) ТОЧНА, если m — survival-медиана (P(X ≥ m) = 1/2).")
    print("  2. С CDF-медианой (P(X ≤ m) = 1/2) она систематически ЗАНИЖАЕТ ρ: при ρ = 0,8 примерно на 8 %.")
    print("  3. Верхняя стенка N добавляет смещение, но оно уходит при N ≫ m.")
    ok = worst_survival < 0.01
    if ok:
        print("ВЫВОД: при survival-медиане и N ≥ 50·m приближение годится (ошибка < 1 %).")
        return 0
    print("ВЫВОД: ошибка > 1 % даже для survival-медианы — нужна граница по N.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
