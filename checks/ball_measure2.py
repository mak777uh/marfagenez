"""Правильный тест: точки СНАРУЖИ шара.

Первый тест складывал уже равномерную выборку внутри шара — это ничего не
проверяет. Нужно взять точки снаружи и посмотреть, куда их переносит fold.

Запуск: python checks/ball_measure2.py
"""

from __future__ import annotations

import numpy as np

D = 4
R = 3.0
N = 200000

rng = np.random.default_rng(7)


def fold_radial(points: np.ndarray, r_max: float) -> np.ndarray:
    radii = np.linalg.norm(points, axis=1)
    period = 2.0 * r_max
    u = np.mod(radii, period)
    folded = np.where(u <= r_max, u, period - u)
    scale = np.where(radii > 0, folded / np.maximum(radii, 1e-300), 1.0)
    return points * scale[:, None]


print("# Точки снаружи шара: куда их переносит fold?")
print()
print(f"d = {D}, R = {R}, N = {N}")
print()

# Points uniform in a big ball of radius 4R, so most are outside R.
direction = rng.normal(size=(N, D))
direction /= np.linalg.norm(direction, axis=1)[:, None]
radius = 4 * R * rng.random(N) ** (1.0 / D)
outside = direction * radius[:, None]

inside_mask = radius <= R
print(f"точек внутри R: {np.sum(inside_mask)} из {N}")
print()

folded = fold_radial(outside.copy(), R)
folded_radii = np.linalg.norm(folded, axis=1)

# All folded points must be inside.
print(f"максимальный радиус после fold: {folded_radii.max():.4f} (должно быть <= {R})")
print()

# The key question: is the folded distribution uniform inside the ball?
# For a uniform ball, P(r < x) = (x/R)^d.
print("радиус   ожидаемо (x/R)^d   получено")
print("-" * 42)
for frac in [0.25, 0.5, 0.75, 0.9]:
    x = frac * R
    expected = frac ** D
    got = float(np.mean(folded_radii < x))
    print(f"  {x:.2f}     {expected:.4f}          {got:.4f}")

print()

# chi-square of the radial distribution
bins = 10
edges = np.linspace(0, R, bins + 1)
counts, _ = np.histogram(folded_radii, bins=edges)
expected_counts = N * (edges[1:] ** D - edges[:-1] ** D) / R ** D
chi2 = float(np.sum((counts - expected_counts) ** 2 / expected_counts))
print(f"chi^2: {chi2:.1f} (для {bins - 1} степеней свободы ожидается около {bins - 1})")
print()

print("counts:  ", counts)
print("expected:", np.round(expected_counts).astype(int))
print()

if chi2 > 3 * (bins - 1):
    print("ВЫВОД: fold НЕ даёт равномерного распределения из внешних точек.")
    print("Разбор прав: радиальное складывание не сохраняет меру шара.")
else:
    print("ВЫВОД: fold даёт равномерное распределение.")
