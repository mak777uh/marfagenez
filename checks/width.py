"""Есть ли оптимум ширины комнаты?

Тест `optimal_width` не нашёл оптимум: измеренный всегда на краю.
Значит формула `B* = sigma*sqrt(T)` неверна.

Проверяем, что реально происходит.

Запуск: python checks/width.py
"""

from __future__ import annotations

import math

import numpy as np

SIGMA = 0.3
N = 600


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def final_spread(b: float, steps: int, seed: int = 9501) -> float:
    rng = np.random.default_rng(seed)
    pop = rng.normal(0.0, 0.5, N)
    for _ in range(steps):
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), b)
    return float(pop.std())


print("# Есть ли оптимум ширины?")
print()
print(f"sigma = {SIGMA}, N = {N}")
print()

for steps in [1000, 4000]:
    print(f"=== steps = {steps} ===")
    print("   B     law     spread   spread/law   fill_time")
    for b in [1, 2, 4, 8, 16, 32, 64, 128]:
        s = final_spread(b, steps)
        law = b / math.sqrt(3)
        fill = (b / SIGMA) ** 2
        print(f" {b:4d}  {law:6.2f}  {s:7.3f}   {s/law:8.3f}   {fill:10.0f}")
    print()

print("# Что видно")
print()
print("spread РАСТЁТ с B всё время, до B=128 и дальше.")
print("spread/law ПАДАЕТ, но абсолютный разброс растёт.")
print()
print("# Почему нет оптимума")
print()
print("Разброс растёт как sqrt(t) при отсутствии стены:")
print("  spread ~ sigma*sqrt(t)")
print("Стена только ОГРАНИЧИВАЕТ его сверху величиной B/sqrt(3).")
print()
print("Значит:")
print("  spread(t, B) = min( sigma*sqrt(t), B/sqrt(3) )")
print()
print("Это монотонно растёт с B. Оптимума НЕТ — есть насыщение.")
print()
print("# Где насыщение")
print()
print("  sigma*sqrt(t) = B/sqrt(3)")
print("  => B_sat = sqrt(3)*sigma*sqrt(t)")
print()
for steps in [1000, 4000]:
    b_sat = math.sqrt(3) * SIGMA * math.sqrt(steps)
    print(f"  steps={steps}: B_sat = {b_sat:.1f}")
print()
print("Выше B_sat комната не мешает — ребёнок до неё не доходит.")
print("Ниже B_sat комната ограничивает.")
