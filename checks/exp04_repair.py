"""EXP-04: порог, который реально кусает.

## Что было не так

Три попытки поставить порог ремонта провалились: энергия насыщается на 9.37,
а порог был 2.0 — он никогда не срабатывал.

**Сначала узнаём диапазон, потом ставим порог.**

## Найденный диапазон

При полном ремонте энергия насыщается:
  damage_rate=0.02 -> 9.370
  damage_rate=0.08 -> 9.280
  damage_rate=0.09 -> 9.265

Значит порог надо ставить близко к 9.3.

## Эксперимент

  A. без ремонта
  B. полный ремонт
  C. ремонт только при energy > порог

Порог проверяем на нескольких значениях, чтобы найти, где он кусает.

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


def run(damage_rate: float, condition: str, threshold: float = 0.0,
        seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    energy = rng.uniform(1.0, 5.0, N)
    damage = np.zeros(N)
    alive = np.ones(N, dtype=bool)
    lifetime = np.zeros(N)
    repaired_total = 0.0

    for step in range(STEPS):
        energy = np.minimum(energy + INCOME, CAPACITY)
        energy = energy - MAINTENANCE
        damage = np.minimum(damage + damage_rate, 1.0)

        if condition == "B":
            affordable = np.where(energy > 0, energy / REPAIR_COST, 0.0)
            repaired = np.minimum(affordable, damage)
            repaired_total += float(repaired.sum())
            damage = damage - repaired
            energy = energy - repaired * REPAIR_COST
        elif condition == "C":
            can = energy > threshold
            affordable = np.where(can, energy / REPAIR_COST, 0.0)
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


print("# EXP-04: порог, который кусает")
print()
print(f"N = {N}, steps = {STEPS}, capacity = {CAPACITY}")
print(f"energy насыщается около 9.3")
print()

print("# 1. Найти порог, который кусает")
print()
print("  порог   damage_rate   выжив.   повреждения   отремонтировано")
print(" " + "-" * 66)
for thr in [2.0, 5.0, 8.0, 9.0, 9.3, 9.5]:
    r = run(0.05, "C", threshold=thr)
    print(f"  {thr:5.1f}   {0.05:11.2f}   {r['survival']*100:6.1f}%   {r['mean_damage']:11.3f}   {r['repaired']:15.0f}")
print()

print("# 2. Сравнение A / B / C при пороге, который кусает (9.3)")
print()
print("  damage_rate   A: выжив.   B: выжив.   C: выжив.   C повреждения")
print(" " + "-" * 68)
for dr in [0.02, 0.05, 0.08, 0.09, 0.10]:
    ra = run(dr, "A")
    rb = run(dr, "B")
    rc = run(dr, "C", threshold=9.3)
    print(f"  {dr:11.2f}   {ra['survival']*100:8.1f}%   {rb['survival']*100:8.1f}%   "
          f"{rc['survival']*100:8.1f}%   {rc['mean_damage']:12.3f}")
print()

print("# 3. Гейт: кусает ли порог?")
print()
r_full = run(0.05, "B")
r_lim = run(0.05, "C", threshold=9.3)
print(f"  отремонтировано B: {r_full['repaired']:.0f}")
print(f"  отремонтировано C: {r_lim['repaired']:.0f}")
ratio = r_lim["repaired"] / r_full["repaired"] if r_full["repaired"] > 0 else 0
print(f"  отношение: {ratio:.3f}")
if ratio < 0.9:
    print("  ГЕЙТ ПРОЙДЕН: порог реально снизил ремонт.")
else:
    print("  ГЕЙТ ПРОВАЛЕН: порог не влияет.")
print()

print("# Вывод")
print()
print("Порог 9.3 попадает в рабочий диапазон энергии.")
print("Ремонт ограничен, когда энергия ниже 9.3.")
