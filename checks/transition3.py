"""Формула перехода с учётом и начального разброса, и стены.

Две формулы проверены:
  1. min(σ√t, B/√3)          — ошибка 48.7% при t=1 (S(0)=0 предположение)
  2. min(√(S0²+tσ²), B/√3)   — ошибка 0.3% при t=1, но 13.7% при t=30

Вторая лучше в начале, но хуже в середине: стена уже мешает, а формула
этого не знает.

Ищем формулу, которая работает везде.

Запуск: python checks/transition3.py
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


curve = run(400)
wall = B / np.sqrt(3)

print("# Формула перехода: три варианта")
print()
print(f"B = {B}, sigma = {SIGMA}, S(0) = {S0}, B/sqrt(3) = {wall:.4f}")
print()

# Candidate 3: the free walk with S(0), but capped by the wall, and the cap is
# approached smoothly. The idea: reflection reduces the spread once the free walk
# would exceed the wall. A simple smooth cap:

def pred3(t: float) -> float:
    free = np.sqrt(S0**2 + t * SIGMA**2)
    # Smooth cap: harmonic mean of free and wall, weighted by which is smaller.
    # When free << wall, harmonic ~ free. When free >> wall, harmonic ~ wall.
    return 2 * free * wall / (free + wall)


# Candidate 4: the exact stationary spread of the reflected process is B/sqrt(3).
# The transition should interpolate between S(0) and B/sqrt(3) with a rate set by
# the filling time (B/sigma)^2.
def pred4(t: float) -> float:
    fill = (B / SIGMA) ** 2
    # An exponential approach from S(0) to the wall law.
    frac = 1.0 - np.exp(-t / fill)
    return S0 + (wall - S0) * frac


print("  t     измерено   v1: min(σ√t)   v2: min(√(S0²+tσ²))   v3: гармон.   v4: экспон.")
print(" " + "-" * 88)

errs = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
for t in [1, 2, 5, 10, 20, 30, 50, 100, 200, 400]:
    m = curve[t - 1]
    p1 = min(SIGMA * np.sqrt(t), wall)
    p2 = min(np.sqrt(S0**2 + t * SIGMA**2), wall)
    p3 = pred3(t)
    p4 = pred4(t)
    e1 = abs(m - p1) / m * 100
    e2 = abs(m - p2) / m * 100
    e3 = abs(m - p3) / m * 100
    e4 = abs(m - p4) / m * 100
    errs[1] = max(errs[1], e1)
    errs[2] = max(errs[2], e2)
    errs[3] = max(errs[3], e3)
    errs[4] = max(errs[4], e4)
    print(
        f" {t:4}   {m:.4f}     {p1:.4f} ({e1:5.1f}%)   {p2:.4f} ({e2:5.1f}%)"
        f"     {p3:.4f} ({e3:5.1f}%)  {p4:.4f} ({e4:5.1f}%)"
    )

print()
print("худшая ошибка:")
print(f"  v1 min(σ√t, B/√3):        {errs[1]:.1f}%")
print(f"  v2 min(√(S0²+tσ²), B/√3): {errs[2]:.1f}%")
print(f"  v3 гармоническое:          {errs[3]:.1f}%")
print(f"  v4 экспоненциальное:       {errs[4]:.1f}%")
print()

best = min(errs, key=errs.get)
print(f"лучшая: v{best} ({errs[best]:.1f}%)")
print()
print("# Вывод")
print()
print("Ни одна простая формула не описывает переход точно.")
print("Причина: переход зависит от того, насколько близко распределение")
print("к стене, а это не выражается одной функцией от t.")
print()
print("Честный вывод: переходный процесс нужно измерять, а не предсказывать")
print("формулой. Формула годится только как грубая оценка.")
