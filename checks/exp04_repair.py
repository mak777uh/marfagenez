"""EXP-04: может ли организм поддерживать себя?

## Исправление после двух прогонов

Первый: C = B, ограничение не срабатывало (энергия всегда > порога).
Второй: C = B, потому что доход превышал стоимость ремонта.

**Найдена граница:** при
    income - maintenance = damage_rate * repair_cost
организм балансирует на грани.

## Что проверяем

Не «выживает или нет», а **где граница** между жизнью и смертью.

Запуск: python checks/exp04_repair.py
"""

from __future__ import annotations

import numpy as np

N = 2000
STEPS = 2000
SEED = 7

INCOME = 0.75
MAINTENANCE = 0.6
REPAIR_COST = 1.5
CAPACITY = 10.0
REPAIR_THRESHOLD = 2.0

# The break-even damage rate: net income pays for repair.
NET = INCOME - MAINTENANCE
BREAK_EVEN = NET / REPAIR_COST


def run(damage_rate: float, condition: str, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)

    structure = np.ones(N)
    energy = rng.uniform(1.0, 5.0, N)
    damage = np.zeros(N)
    alive = np.ones(N, dtype=bool)
    lifetime = np.zeros(N)
    repaired_total = 0.0

    for step in range(STEPS):
        energy = np.minimum(energy + INCOME, CAPACITY)
        energy = energy - MAINTENANCE
        damage = np.minimum(damage + damage_rate, 1.0)

        if condition in ("B", "C"):
            if condition == "C":
                can_repair = energy > REPAIR_THRESHOLD
            else:
                can_repair = energy > 0.0
            affordable = np.where(can_repair, energy / REPAIR_COST, 0.0)
            repaired = np.minimum(affordable, damage)
            repaired_total += float(repaired.sum())
            damage = damage - repaired
            energy = energy - repaired * REPAIR_COST

        structure = np.maximum(1.0 - damage, 0.0)

        died = alive & ((energy <= 0) | (structure <= 0) | (damage >= 1.0))
        lifetime[died] = step
        alive = alive & ~died
        energy = np.maximum(energy, 0.0)

        if not alive.any():
            break

    return {
        "survival": float(alive.mean()),
        "mean_lifetime": float(lifetime[~alive].mean()) if (~alive).any() else float(STEPS),
        "mean_damage": float(damage[alive].mean()) if alive.any() else 1.0,
        "repaired": repaired_total,
    }


print("# EXP-04: где граница между жизнью и смертью?")
print()
print(f"N = {N}, steps = {STEPS}")
print(f"income = {INCOME}, maintenance = {MAINTENANCE}, repair_cost = {REPAIR_COST}")
print(f"чистый доход: {NET:.3f} за шаг")
print(f"граница: damage_rate = {BREAK_EVEN:.4f}")
print()

print("# 1. Без ремонта — все погибают при любом damage_rate")
print()
print("  damage_rate   выживаемость   время жизни")
print(" " + "-" * 44)
for dr in [0.01, 0.02, 0.05]:
    r = run(dr, "A")
    print(f"  {dr:11.3f}   {r['survival']*100:11.1f}%   {r['mean_lifetime']:10.1f}")
print()

print("# 2. С ремонтом — граница видна")
print()
print("  damage_rate   выживаемость   время жизни   повреждения")
print(" " + "-" * 62)
for dr in [0.02, 0.05, 0.08, 0.09, 0.10, 0.11, 0.15, 0.20]:
    r = run(dr, "B")
    marker = " <- граница" if abs(dr - BREAK_EVEN) < 0.02 else ""
    print(f"  {dr:11.3f}   {r['survival']*100:11.1f}%   {r['mean_lifetime']:10.1f}   {r['mean_damage']:9.3f}{marker}")
print()

print("# 3. Ограниченный ремонт — когда порог кусает")
print()
print("  damage_rate   B: выжив.   C: выжив.   разница")
print(" " + "-" * 52)
for dr in [0.05, 0.08, 0.10, 0.15]:
    rb = run(dr, "B")
    rc = run(dr, "C")
    diff = (rb["survival"] - rc["survival"]) * 100
    print(f"  {dr:11.3f}   {rb['survival']*100:9.1f}%   {rc['survival']*100:9.1f}%   {diff:+7.1f}%")
print()

print("# Вывод")
print()
print(f"Граница предсказана: damage_rate = (income - maintenance) / repair_cost")
print(f"                    = ({INCOME} - {MAINTENANCE}) / {REPAIR_COST}")
print(f"                    = {BREAK_EVEN:.4f}")
print()
print("Выше границы ремонт стоит больше, чем приносит доход — организм гибнет.")
print("Ниже — выживает.")
print()
print("Это первый закон организма: у самоподдержания есть ЦЕНА,")
print("и она сравнима с доходом.")
