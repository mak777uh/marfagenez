"""Порог полосы `δ_c ≈ σ_g·√(2 ln N)`: единицы, пределы и вероятность превышения.

Что в записи `F-014`: `δ_c ≈ σ_g·√(2 ln N)`, при `σ_g ≈ 0,1` и `N ≈ 10³` получается `0,37`
(«середина нашего окна 0,2…0,5»).

Что проверяется:
  1) арифметика — сходится ли `0,37`;
  2) единицы — `σ_g` в единицах `δ_c` (доля), `N` — счёт;
  3) **смысл** — это не порог редкого события, а ТИПИЧНЫЙ максимум `N` гауссовых шумов: вероятность
     превышения ≈ 0,63 по построению, а не 0,05;
  4) как выглядит настоящий порог заданной редкости: `δ_p = σ_g·√(2 ln(N/p))`.

Запуск: python3 tools/noise_threshold.py
"""

from __future__ import annotations

import math


def delta_typical(sigma: float, n: float) -> float:
    return sigma * math.sqrt(2 * math.log(n))


def delta_for_fail_prob(sigma: float, n: float, p: float) -> float:
    """δ, которое максимум из N гауссовых шумов превышает с вероятностью p."""
    return sigma * math.sqrt(2 * math.log(n / p))


def main() -> int:
    sigma, n = 0.1, 1e3

    print("== арифметика записи")
    got = delta_typical(sigma, n)
    print(f"  sigma_g = {sigma}, N = {n:.0f} -> delta_c = {got:.4f} (в записи 0,37)")

    print()
    print("== единицы")
    print("  sigma_g — стандартное отклонение шума, доля (безразмерна), 1")
    print("  N       — число независимых шумов, счёт, 1")
    print("  ln N    — безразмерен (аргумент логарифма — счёт)")
    print("  delta_c — та же размерность, что sigma_g, 1")

    print()
    print("== смысл: это типичный максимум, а не редкий порог")
    print(f"  ожидаемый максимум N = {n:.0f} гауссовых шумов: {got:.4f}")
    print("  вероятность, что максимум его превысит: ≈ 1 - exp(-1) = 0,63")
    print("  то есть «порог 0,37» срабатывает чаще, чем в половине случаев")

    print()
    print("== порог заданной редкости: delta_p = sigma*sqrt(2 ln(N/p))")
    print(f"{'p':>6} {'delta_p':>9} {'во сколько раз выше 0,37':>26}")
    for p in (0.5, 0.1, 0.05, 0.01, 0.001):
        d = delta_for_fail_prob(sigma, n, p)
        print(f"{p:>6} {d:>9.4f} {d/got:>26.2f}")

    print()
    print("== пределы")
    print("  N → 1     => delta_c → 0   (шум один, «максимум» — он сам, нулевого среднего)")
    print("  N → ∞     => delta_c → ∞   но как sqrt(2 ln N): 10^6 дают всего 0,53 при sigma = 0,1")
    for n in (10, 1e3, 1e6):
        print(f"  N = {n:>8.0f}: delta_c = {delta_typical(sigma, n):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
