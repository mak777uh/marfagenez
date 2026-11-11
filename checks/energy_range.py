"""Где на самом деле живёт энергия?

Три провала гейта в EXP-04 были из-за того, что порог не попадал в рабочий
диапазон энергии. Прежде чем ставить порог, надо узнать диапазон.

Запуск: python checks/energy_range.py
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


def run(damage_rate: float, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    energy = rng.uniform(1.0, 5.0, N)
    damage = np.zeros(N)
    alive = np.ones(N, dtype=bool)
    history = []

    for step in range(STEPS):
        energy = np.minimum(energy + INCOME, CAPACITY)
        energy = energy - MAINTENANCE
        damage = np.minimum(damage + damage_rate, 1.0)

        # Full repair.
        affordable = np.where(energy > 0, energy / REPAIR_COST, 0.0)
        repaired = np.minimum(affordable, damage)
        damage = damage - repaired
        energy = energy - repaired * REPAIR_COST

        structure = np.maximum(1.0 - damage, 0.0)
        died = alive & ((energy <= 0) | (structure <= 0) | (damage >= 1.0))
        alive = alive & ~died
        energy = np.maximum(energy, 0.0)

        if alive.any():
            history.append((float(energy[alive].min()), float(energy[alive].max()),
                            float(energy[alive].mean())))
        if not alive.any():
            break

    return {"history": history, "alive": int(alive.sum())}


print("# Где живёт энергия?")
print()
print(f"income = {INCOME}, maintenance = {MAINTENANCE}, repair_cost = {REPAIR_COST}")
print(f"чистый доход при полном ремонте: {INCOME - MAINTENANCE:.3f}")
print()

for dr in [0.02, 0.05, 0.08, 0.09]:
    r = run(dr)
    h = r["history"]
    if not h:
        print(f"damage_rate = {dr}: все погибли")
        continue
    # Sample at several points.
    print(f"damage_rate = {dr} (живых {r['alive']}):")
    for frac in [0.0, 0.25, 0.5, 0.75, 0.99]:
        idx = int(frac * (len(h) - 1))
        mn, mx, mean = h[idx]
        print(f"  шаг {idx:5}: энергия min={mn:.3f} max={mx:.3f} mean={mean:.3f}")
    print()

print("# Вывод")
print()
print("Если энергия растёт до capacity, порог надо ставить близко к capacity.")
print("Если колеблется — порог в середине диапазона.")
