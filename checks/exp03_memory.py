"""EXP-03: помогает ли память?

## Провал гейта в первой версии

C сделал 0 ходов. Причина: память инициализировалась уровнем СВОЕЙ клетки.
Организм в богатой клетке имел best_level=2.0 и не двигался.

**Без исследования память пуста.**

## Исправление

Память начинается ПУСТОЙ (best_level=0). Организм:
  - если память пуста или стара — двигается случайно (исследование)
  - если память есть — двигается к ней

Это не чистая память, а память + исследование. Но без исследования
память бесполезна: организм не может узнать о других клетках.

## Три условия

  A. не двигается
  B. двигается случайно (без памяти)
  C. память + исследование

Запуск: python checks/exp03_memory.py
"""

from __future__ import annotations

import numpy as np

CELLS = 40
RICH = 2.0
POOR = 0.2
REGROW = 0.8
STEPS = 2000
SEED = 13
N = 40

INCOME = 0.8
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
CAPACITY = 10.0
MOVE_COST = 0.1
MEMORY_LIFE = 300

need = MAINTENANCE + DAMAGE_RATE * REPAIR_COST
rich_cells = CELLS // 2
supply = rich_cells * RICH * REGROW / N

print("# Проверка жизнеспособности")
print()
print(f"нужно: {need:.3f}, поле даёт: {supply:.3f}, запас {(supply/need-1)*100:+.0f}%")
if supply < need:
    print("МИР НЕЖИЗНЕСПОСОБЕН.")
    raise SystemExit(1)
print("Мир жизнеспособен.")
print()


def run(condition: str, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    field = np.array([RICH if i % 2 == 0 else POOR for i in range(CELLS)], dtype=float)

    cells = rng.integers(0, CELLS, N)
    energy = rng.uniform(3.0, 6.0, N)
    damage = np.zeros(N)
    alive = np.ones(N, dtype=bool)
    moves = np.zeros(N, dtype=int)
    explore_moves = np.zeros(N, dtype=int)
    exploit_moves = np.zeros(N, dtype=int)
    lifetime = np.zeros(N)

    # Memory starts EMPTY: the organism knows nothing.
    best_cell = cells.copy()
    best_level = np.zeros(N)
    best_age = np.zeros(N, dtype=int)

    for step in range(STEPS):
        for i in range(N):
            if not alive[i]:
                continue

            here = field[cells[i]]

            if condition == "C":
                best_age[i] += 1
                if here > best_level[i]:
                    best_cell[i] = cells[i]
                    best_level[i] = here
                    best_age[i] = 0
                if best_age[i] > MEMORY_LIFE:
                    best_level[i] = 0.0

            if condition == "B":
                if energy[i] >= MOVE_COST:
                    nc = cells[i] + int(rng.integers(-1, 2))
                    if 0 <= nc < CELLS:
                        cells[i] = nc
                        energy[i] -= MOVE_COST
                        moves[i] += 1
            elif condition == "C":
                if energy[i] >= MOVE_COST:
                    if best_level[i] <= 0 or best_cell[i] == cells[i]:
                        # Explore: move randomly.
                        nc = cells[i] + int(rng.integers(-1, 2))
                        if 0 <= nc < CELLS:
                            cells[i] = nc
                            energy[i] -= MOVE_COST
                            moves[i] += 1
                            explore_moves[i] += 1
                    else:
                        # Exploit: move toward the memory.
                        d = 1 if best_cell[i] > cells[i] else -1
                        nc = cells[i] + d
                        if 0 <= nc < CELLS:
                            cells[i] = nc
                            energy[i] -= MOVE_COST
                            moves[i] += 1
                            exploit_moves[i] += 1

            taken = min(field[cells[i]], INCOME)
            field[cells[i]] -= taken

            energy[i] = min(energy[i] + taken, CAPACITY)
            energy[i] -= MAINTENANCE
            damage[i] = min(damage[i] + DAMAGE_RATE, 1.0)

            if energy[i] > 0:
                affordable = energy[i] / REPAIR_COST
                repaired = min(affordable, damage[i])
                damage[i] -= repaired
                energy[i] -= repaired * REPAIR_COST

            structure = max(1.0 - damage[i], 0.0)
            if energy[i] <= 0 or structure <= 0 or damage[i] >= 1.0:
                alive[i] = False
                lifetime[i] = step
                energy[i] = max(energy[i], 0.0)

        field += (RICH - field) * REGROW
        if not alive.any():
            break

    return {
        "survival": float(alive.mean()),
        "mean_lifetime": float(lifetime[~alive].mean()) if (~alive).any() else float(STEPS),
        "total_moves": int(moves.sum()),
        "explore": int(explore_moves.sum()),
        "exploit": int(exploit_moves.sum()),
        "mean_energy": float(energy[alive].mean()) if alive.any() else 0.0,
    }


print("# Гейт: срабатывает ли условие?")
print()
results = {}
for cond, name in [("A", "не двигается"), ("B", "случайно"), ("C", "память+исслед.")]:
    r = run(cond)
    results[cond] = r
    extra = ""
    if cond == "C":
        extra = f" (исслед. {r['explore']}, использ. {r['exploit']})"
    print(f"  {cond} ({name:16}): ходов {r['total_moves']:8}, выжив. {r['survival']*100:5.1f}%{extra}")

print()

rC = results["C"]
sA = results["A"]["survival"]

gate_ok = True
if rC["total_moves"] == 0:
    print("ГЕЙТ ПРОВАЛЕН: C не двигался.")
    gate_ok = False
elif rC["exploit"] == 0:
    print("ГЕЙТ ПРОВАЛЕН: C не использовал память (только исследовал).")
    gate_ok = False
elif sA == 0.0 and rC["survival"] == 0.0:
    print("ГЕЙТ ПРОВАЛЕН: все гибнут.")
    gate_ok = False
else:
    print(f"Гейт пройден: C сделал {rC['total_moves']} ходов "
          f"({rC['explore']} исслед., {rC['exploit']} использ.).")

print()
print("# Результат")
print()
print("  условие   выживаемость   время жизни   энергия")
print(" " + "-" * 54)
for cond, name in [("A", "не двигается"), ("B", "случайно"), ("C", "память+исслед.")]:
    r = results[cond]
    print(f"  {cond} {name:16} {r['survival']*100:8.1f}%   {r['mean_lifetime']:8.1f}   {r['mean_energy']:7.3f}")
print()

sB = results["B"]["survival"]
sC = results["C"]["survival"]

print("# Сравнение")
print()
print(f"  C против A: {(sC-sA)*100:+.1f}%")
print(f"  C против B: {(sC-sB)*100:+.1f}%")
print()

print("# Вывод")
print()
if not gate_ok:
    print("Эксперимент НЕДЕЙСТВИТЕЛЕН.")
else:
    if sC > sA + 0.05:
        print("Память+исследование ПОМОГАЕТ.")
    elif sC < sA - 0.05:
        print("Память ВРЕДИТ.")
    else:
        print("Память не влияет существенно.")
    print()
    if sC > sB + 0.05:
        print("Память ЛУЧШЕ чистого случая.")
    elif sC < sB - 0.05:
        print("Память ХУЖЕ чистого случая.")
    else:
        print("Память и случай неразличимы.")
