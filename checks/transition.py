"""Проверка: описывает ли `min(σ√t, B/√3)` переходный процесс?

Формула используется как «закон насыщения». Но она — минимум двух пределов:

  σ√t   — свободный случайный ход
  B/√3  — разброс равномерного на [-B, B]

Вопрос: совпадает ли реальный переход с этим минимумом?

Запуск: python checks/transition.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
SIGMA = 0.3
N = 20000


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(steps: int, seed: int = 42) -> list[float]:
    """Spread at every step, from a narrow start."""
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    out = []
    for _ in range(steps):
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), B)
        out.append(float(pop.std()))
    return out


print("# Описывает ли min(sigma*sqrt(t), B/sqrt(3)) переход?")
print()
print(f"B = {B}, sigma = {SIGMA}, N = {N}")
print(f"свободный ход: sigma*sqrt(t)")
print(f"закон стены:   B/sqrt(3) = {B / np.sqrt(3):.4f}")
print()

steps = 400
curve = run(steps)

print("  t     измерено   σ√t      B/√3     min      ошибка min")
print(" " + "-" * 62)

worst = 0.0
worst_t = 0
for t in [1, 2, 5, 10, 20, 50, 100, 200, 400]:
    measured = curve[t - 1]
    free = SIGMA * np.sqrt(t)
    wall = B / np.sqrt(3)
    pred = min(free, wall)
    err = abs(measured - pred) / pred * 100
    if err > worst:
        worst = err
        worst_t = t
    print(f" {t:4}   {measured:.4f}     {free:.4f}   {wall:.4f}   {pred:.4f}   {err:6.1f}%")

print()
print(f"худшая ошибка: {worst:.1f}% при t = {worst_t}")
print()

# Where does the formula do worst? Check the transition region.
print("# Где формула ошибается сильнее всего?")
print()
print("  t     измерено   min      ошибка")
print(" " + "-" * 40)
for t in range(10, 210, 20):
    measured = curve[t - 1]
    free = SIGMA * np.sqrt(t)
    wall = B / np.sqrt(3)
    pred = min(free, wall)
    err = abs(measured - pred) / pred * 100
    print(f" {t:4}   {measured:.4f}     {pred:.4f}   {err:6.1f}%")

print()
print("# Вывод")
print()

# The formula is exact only when the free walk is far from the wall, or when the
# wall is fully reached. In between it is an approximation.
free_at_100 = SIGMA * np.sqrt(100)
wall = B / np.sqrt(3)
print(f"при t=100: σ√t = {free_at_100:.2f}, B/√3 = {wall:.2f}")
print(f"  σ√t < B/√3, значит min = σ√t")
print(f"  измерено: {curve[99]:.3f}, σ√t = {free_at_100:.3f}")
print(f"  разница: {abs(curve[99] - free_at_100) / free_at_100 * 100:.1f}%")
print()
print("Формула — приближение: она не учитывает, что отражение уже начало")
print("работать до того, как σ√t достигло B/√3.")
