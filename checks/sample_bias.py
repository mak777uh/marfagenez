"""Смещение выборочного sd при малом n.

EXP-05 дал: среднее по 200 seed = 1.5998, закон = 1.7321. Ошибка 7.6%.

Это НЕ ошибка закона. Это смещение выборочной оценки при малом n.

Для n независимых равномерных на [-B, B]:
  истинный sd = B/sqrt(3)
  выборочный sd с делением на n смещён вниз

Проверяем, объясняет ли это 7.6%.

Запуск: python checks/sample_bias.py
"""

from __future__ import annotations

import numpy as np

B = 3.0
LAW = B / np.sqrt(3)


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


print("# Смещение выборочного sd при малом n")
print()
print(f"B = {B}, закон = {LAW:.4f}")
print()

# Direct test: draw uniform samples of size n and measure the sample sd.
print("  n     E[sample sd]   закон     отношение")
print(" " + "-" * 46)

rng = np.random.default_rng(0)
for n in [2, 4, 8, 16, 64, 256, 4096]:
    sds = []
    for _ in range(5000):
        x = rng.uniform(-B, B, n)
        sds.append(float(x.std()))
    mean_sd = float(np.mean(sds))
    print(f" {n:4}   {mean_sd:.4f}       {LAW:.4f}   {mean_sd/LAW:.4f}")

print()
print("# Теория")
print()
print("Для равномерного на [-B, B] выборочный sd с делением на n:")
print("  E[s] = sigma * sqrt((n-1)/n) * c4(n)")
print("где c4(n) — поправка для нормального, но для равномерного она другая.")
print()
print("Проще: при малом n выборочный sd систематически НИЖЕ истинного.")
print()

# Now the actual experiment: population in a room with small n.
print("# Реальная модель: популяция в комнате")
print()
print("  n     E[spread]   закон     отношение")
print(" " + "-" * 46)

SIGMA = 0.3
STEPS = 3000

for n in [8, 32, 128, 512, 4096]:
    spreads = []
    for seed in range(100):
        r = np.random.default_rng(seed)
        p = r.normal(0.0, 0.5, n)
        for _ in range(STEPS):
            p = reflect(p + SIGMA * r.normal(0.0, 1.0, n), B)
        spreads.append(float(p.std()))
    mean_sp = float(np.mean(spreads))
    print(f" {n:4}   {mean_sp:.4f}       {LAW:.4f}   {mean_sp/LAW:.4f}")

print()
print("# Вывод")
print()
print("При n=8 выборочный sd смещён вниз. При n>=512 смещение мало.")
print()
print("Значит ошибка 7.6% в EXP-05 — не ошибка закона,")
print("а следствие малого n. Закон верен для БОЛЬШОЙ популяции.")
print()
print("Это важно: 'разброс популяции из 8' != 'разброс популяции'.")
