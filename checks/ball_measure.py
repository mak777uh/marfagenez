"""Сохраняет ли радиальный fold равномерное распределение в шаре?

Разбор утверждает: нет, потому что объём оболочки растёт как r^(d-1),
и простое складывание радиуса не сохраняет меру.

Проверяем численно.

Запуск: python checks/ball_measure.py
"""

from __future__ import annotations

import math

import numpy as np

D = 4
R = 3.0
N = 200000


def fold_radial(points: np.ndarray, r_max: float) -> np.ndarray:
    """The implementation in room.rs: fold the radius, keep the direction."""
    radii = np.linalg.norm(points, axis=1)
    period = 2.0 * r_max
    u = np.mod(radii, period)
    folded = np.where(u <= r_max, u, period - u)
    scale = np.where(radii > 0, folded / np.maximum(radii, 1e-300), 1.0)
    return points * scale[:, None]


print("# Сохраняет ли радиальный fold равномерное распределение в шаре?")
print()
print(f"d = {D}, R = {R}, N = {N}")
print()

rng = np.random.default_rng(42)

# A uniform sample inside the ball: direction uniform on the sphere,
# radius with density ~ r^(d-1).
def uniform_ball(n: int, d: int, r: float) -> np.ndarray:
    direction = rng.normal(size=(n, d))
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    radius = r * rng.random(n) ** (1.0 / d)
    return direction * radius[:, None]


before = uniform_ball(N, D, R)
after = fold_radial(before.copy(), R)

# Check 1: is the folded sample still uniform? Compare the radius distribution.
# For a uniform ball, P(r < x) = (x/R)^d.
def radius_cdf(sample: np.ndarray, x: float, r: float, d: int) -> float:
    radii = np.linalg.norm(sample, axis=1)
    return float(np.mean(radii < x))

print("радиус   ожидаемо (x/R)^d   до fold   после fold")
print("-" * 52)
for frac in [0.25, 0.5, 0.75, 0.9]:
    x = frac * R
    expected = frac ** D
    b = radius_cdf(before, x, R, D)
    a = radius_cdf(after, x, R, D)
    print(f"  {x:.2f}     {expected:.4f}          {b:.4f}    {a:.4f}")

print()

# Check 2: the mean of r^2. For a uniform ball it is d*R^2/(d+2).
def mean_r2(sample: np.ndarray) -> float:
    return float(np.mean(np.sum(sample ** 2, axis=1)))

expected_r2 = D * R * R / (D + 2)
print(f"E[r^2] ожидаемо: {expected_r2:.4f}")
print(f"E[r^2] до fold:  {mean_r2(before):.4f}")
print(f"E[r^2] после:    {mean_r2(after):.4f}")
print()

# Check 3: the per-coordinate variance. For a uniform ball it is R^2/(d+2).
def coord_var(sample: np.ndarray) -> float:
    return float(np.mean(np.var(sample, axis=0)))

expected_var = R * R / (D + 2)
print(f"Var(X_i) ожидаемо: {expected_var:.4f}")
print(f"Var(X_i) до fold:  {coord_var(before):.4f}")
print(f"Var(X_i) после:    {coord_var(after):.4f}")
print()

# Check 4: the crucial test. Take a uniform sample, fold it, and see whether the
# folded sample is still uniform. A measure-preserving map would leave it uniform.
# Measure the chi-square of the radius distribution.
bins = 10
edges = np.linspace(0, R, bins + 1)
radii_after = np.linalg.norm(after, axis=1)
counts, _ = np.histogram(radii_after, bins=edges)
# Expected counts for a uniform ball: proportional to (r_{i+1}^d - r_i^d)
expected_counts = N * (edges[1:] ** D - edges[:-1] ** D) / R ** D
chi2 = float(np.sum((counts - expected_counts) ** 2 / expected_counts))
print(f"chi^2 радиального распределения после fold: {chi2:.1f}")
print(f"  (для {bins - 1} степеней свободы ожидается около {bins - 1})")
print()

if chi2 > 3 * (bins - 1):
    print("ВЫВОД: радиальный fold НЕ сохраняет равномерное распределение.")
    print("Разбор прав: геометрия шара требует учёта объёма оболочки r^(d-1).")
else:
    print("ВЫВОД: радиальный fold сохраняет равномерное распределение.")
