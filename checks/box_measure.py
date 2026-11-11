"""Проверка: сохраняет ли Box равномерное распределение?

Шар опровергнут (chi^2 = 3e7). Нужно проверить куб, прежде чем на него опираться.

Запуск: python checks/box_measure.py
"""

from __future__ import annotations

import numpy as np

D = 4
B = 3.0
N = 200000

rng = np.random.default_rng(11)


def fold_box(points: np.ndarray, b: float) -> np.ndarray:
    """The implementation in room.rs: reflect each coordinate independently."""
    period = 4.0 * b
    u = np.mod(points + b, period)
    return b - np.abs(u - 2.0 * b)


print("# Сохраняет ли Box равномерное распределение?")
print()
print(f"d = {D}, B = {B}, N = {N}")
print()

# Points uniform in a big box of half-width 4B, so most are outside B.
outside = rng.uniform(-4 * B, 4 * B, size=(N, D))
inside_mask = np.all(np.abs(outside) <= B, axis=1)
print(f"точек внутри B: {np.sum(inside_mask)} из {N}")
print()

folded = fold_box(outside, B)

# All folded points must be inside.
print(f"максимальный |x| после fold: {np.abs(folded).max():.4f} (должно быть <= {B})")
print()

# The key question: is the folded distribution uniform in the box?
# For a uniform box, each coordinate is uniform on [-B, B].
bins = 10
edges = np.linspace(-B, B, bins + 1)
chi2_total = 0.0
for k in range(D):
    counts, _ = np.histogram(folded[:, k], bins=edges)
    expected = N / bins
    chi2 = float(np.sum((counts - expected) ** 2 / expected))
    chi2_total += chi2

dof = D * (bins - 1)
print(f"chi^2 (сумма по {D} координатам): {chi2_total:.1f}")
print(f"  для {dof} степеней свободы ожидается около {dof}")
print()

# Per-coordinate mean and variance.
print("координата   mean      var       ожидаемо var = B^2/3 = %.3f" % (B * B / 3))
for k in range(D):
    print(f"  {k}          {folded[:, k].mean():+.4f}   {folded[:, k].var():.4f}")

print()

if chi2_total > 3 * dof:
    print("ВЫВОД: Box НЕ сохраняет равномерное распределение.")
else:
    print("ВЫВОД: Box сохраняет равномерное распределение.")
    print("Это подтверждает, что на куб можно опираться.")
