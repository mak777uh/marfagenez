"""Правильная формула перехода: учёт начального разброса.

Формула `min(σ√t, B/√3)` даёт 95% ошибки при t=1, потому что начальный
разброс не ноль.

Правильно для свободного хода:

    S(t) = sqrt(S(0)^2 + t*σ^2)

Проверяем.

Запуск: python checks/transition2.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
SIGMA = 0.3
N = 20000
S0 = 0.5


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def run(steps: int, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, S0, N)
    out = []
    for _ in range(steps):
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), B)
        out.append(float(pop.std()))
    return out


print("# Правильная формула перехода")
print()
print(f"B = {B}, sigma = {SIGMA}, N = {N}, S(0) = {S0}")
print()
print("  свободный ход: S(t) = sqrt(S(0)^2 + t*sigma^2)")
print("  закон стены:   B/sqrt(3) = %.4f" % (B / np.sqrt(3)))
print()

steps = 400
curve = run(steps)
wall = B / np.sqrt(3)

print("  t     измерено   старый min   новый min   ошибка старая   ошибка новая")
print(" " + "-" * 76)

worst_old = 0.0
worst_new = 0.0
for t in [1, 2, 5, 10, 20, 30, 50, 100, 200, 400]:
    measured = curve[t - 1]
    free_old = SIGMA * np.sqrt(t)
    free_new = np.sqrt(S0**2 + t * SIGMA**2)
    pred_old = min(free_old, wall)
    pred_new = min(free_new, wall)
    err_old = abs(measured - pred_old) / measured * 100
    err_new = abs(measured - pred_new) / measured * 100
    worst_old = max(worst_old, err_old)
    worst_new = max(worst_new, err_new)
    print(
        f" {t:4}   {measured:.4f}     {pred_old:.4f}       {pred_new:.4f}"
        f"      {err_old:6.1f}%        {err_new:6.1f}%"
    )

print()
print(f"худшая ошибка старая: {worst_old:.1f}%")
print(f"худшая ошибка новая:  {worst_new:.1f}%")
print()

# Compare the free-walk part alone, before the wall matters.
print("# Только свободный ход (t <= 20, стена ещё не мешает)")
print()
print("  t     измерено   σ√t      sqrt(S0²+tσ²)   ошибка σ√t   ошибка sqrt")
print(" " + "-" * 72)
for t in [1, 2, 5, 10, 20]:
    measured = curve[t - 1]
    old = SIGMA * np.sqrt(t)
    new = np.sqrt(S0**2 + t * SIGMA**2)
    print(
        f" {t:4}   {measured:.4f}     {old:.4f}   {new:.4f}"
        f"          {abs(measured-old)/measured*100:5.1f}%      {abs(measured-new)/measured*100:5.1f}%"
    )

print()
print("# Вывод")
print()
print("Формула min(σ√t, B/√3) предполагает S(0)=0.")
print("При S(0)>0 правильный свободный ход: S(t) = sqrt(S(0)^2 + t*σ^2).")
print("Это объясняет 95% ошибки при t=1.")
