"""Равновесный разброс при постоянном толчке: формула `alpha = 2*mu/sigma^2`.

В проекте `medium` было найдено: при постоянном толчке `mu` и шуме `sigma` в
отражающей комнате `[-B, B]` стационарная плотность

    rho(x) ~ exp(alpha * x),   alpha = 2*mu/sigma^2

Проверяем, держится ли это в новом коде (`marfagenez`).

Запуск: python checks/tilt.py

## Замечание о реализации

Первая версия этой проверки считала моменты вручную и давала бессмыслицу:
sd = 3.72 при комнате шириной 6, и sd = 0 при большом alpha. Ошибка была в
ручной формуле, не в физике. Здесь моменты считает SymPy — символьно, без
ручной арифметики.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import sympy as sp

B = 3.0
N = 20000
STEPS = 25000

# The exact moments of exp(alpha*x) on [-b, b], computed symbolically once.
_x, _a, _b = sp.symbols("x alpha b", real=True)
_dens = sp.exp(_a * _x)
_Z = sp.integrate(_dens, (_x, -_b, _b))
_M1 = sp.integrate(_x * _dens, (_x, -_b, _b)) / _Z
_M2 = sp.integrate(_x**2 * _dens, (_x, -_b, _b)) / _Z
_VAR = sp.simplify(_M2 - _M1**2)


def theory(alpha: float, b: float) -> tuple[float, float]:
    """Mean and sd of the density exp(alpha*x) on [-b, b], from SymPy."""
    if abs(alpha) < 1e-9:
        return 0.0, b / math.sqrt(3)
    subs = {_a: alpha, _b: b}
    m = float(sp.N(_M1.subs(subs)))
    v = float(sp.N(_VAR.subs(subs)))
    return m, math.sqrt(max(v, 0.0))


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def simulate(mu: float, sigma: float, steps: int = STEPS, seed: int = 5001) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    for _ in range(steps):
        pop = reflect(pop + mu + sigma * rng.normal(0.0, 1.0, N), B)
    return float(pop.mean()), float(pop.std())


print("# Равновесный разброс при толчке")
print()
print(f"B = {B}, N = {N}, steps = {STEPS}")
print()
print(" mu    sigma   alpha    mean(sim)  mean(th)   sd(sim)   sd(th)")
print(" " + "-" * 66)

cases = [
    (0.0, 0.3),
    (0.01, 0.3),
    (0.03, 0.3),
    (0.05, 0.3),
    (0.1, 0.3),
    (0.05, 0.5),
    (0.05, 0.8),
]
rows = []
for mu, sigma in cases:
    alpha = 2 * mu / (sigma * sigma)
    m_sim, s_sim = simulate(mu, sigma)
    m_th, s_th = theory(alpha, B)
    rows.append((mu, sigma, alpha, m_sim, m_th, s_sim, s_th))
    print(
        f" {mu:4.2f}  {sigma:5.2f}  {alpha:6.2f}   {m_sim:+.4f}   {m_th:+.4f}   "
        f"{s_sim:.4f}   {s_th:.4f}"
    )

print()

mean_ok = all(abs(r[3] - r[4]) / max(abs(r[4]), 1e-9) < 0.15 for r in rows if abs(r[4]) > 0.05)
print(f"{'PASS' if mean_ok else 'FAIL'}  mean matches exp(alpha*x)")

sd_ok = all(abs(r[5] - r[6]) / r[6] < 0.15 for r in rows)
print(f"{'PASS' if sd_ok else 'FAIL'}  sd matches exp(alpha*x)")

no_push = rows[0]
law = B / math.sqrt(3)
law_ok = abs(no_push[5] - law) / law < 0.05
print(f"{'PASS' if law_ok else 'FAIL'}  no push gives B/sqrt(3)  ({no_push[5]:.3f} vs {law:.3f})")

print()
if not (mean_ok and sd_ok and law_ok):
    print("Формула не подтвердилась в новом коде.")
    sys.exit(1)

print("# Что это доказывает")
print("Формула alpha = 2*mu/sigma^2 из проекта `medium` держится в новом коде:")
print("и среднее, и разброс совпадают с экспоненциальной плотностью.")
print()
print("# Что это НЕ доказывает")
print("- Что формула выведена: проверена численно, не доказана.")
print("- Что она верна вне этой модели: одна комната, один набор шумов.")
