"""EXP-02: помогает ли действие?

## История провалов

Пять раз гейт проваливался: все гибнут. Причина — мир нежизнеспособен.

`checks/viability.py` показал: одному организму нужно 0.630 ресурса за шаг,
а поле давало 0.100. Не хватает в 6 раз.

## Исправление

Расчёт: ресурс/организм = rich_cells * RICH * REGROW / n_org

Выбрано: 40 клеток (20 богатых), 40 организмов, RICH=2.0, REGROW=0.8
  -> 20 * 2.0 * 0.8 / 40 = 0.8 ресурса на организм
  -> нужно 0.63, есть 0.8. Запас 27%.

## Три условия

  A. не двигается
  B. движется к богатому соседу
  C. движется случайно

Запуск: python checks/exp02_action.py
"""

from __future__ import annotations

import numpy as np

CELLS = 40
RICH = 2.0
POOR = 0.2
REGROW = 0.8
STEPS = 2000
SEED = 11
N = 40

INCOME = 0.8
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02
CAPACITY = 10.0
MOVE_COST = 0.1

# Viability check.
need = MAINTENANCE + DAMAGE_RATE * REPAIR_COST
rich_cells = CELLS // 2
supply = rich_cells * RICH * REGROW / N
print("# Проверка жизнеспособности")
print()
print(f"нужно на организм: {need:.3f} за шаг")
print(f"поле даёт:         {supply:.3f} за шаг")
print(f"запас:             {(supply/need - 1)*100:+.0f}%")
print()
if supply < need:
    print("МИР НЕЖИЗНЕСПОСОБЕН. Эксперимент не запускаем.")
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
    lifetime = np.zeros(N)

    for step in range(STEPS):
        for i in range(N):
            if not alive[i]:
                continue

            if condition == "B":
                here = field[cells[i]]
                best = None
                best_val = here
                for nb in (cells[i] - 1, cells[i] + 1):
                    if 0 <= nb < CELLS and field[nb] > best_val:
                        best = nb
                        best_val = field[nb]
                if best is not None and energy[i] >= MOVE_COST:
                    cells[i] = best
                    energy[i] -= MOVE_COST
                    moves[i] += 1
            elif condition == "C":
                if energy[i] >= MOVE_COST:
                    nc = cells[i] + int(rng.integers(-1, 2))
                    if 0 <= nc < CELLS:
                        cells[i] = nc
                        energy[i] -= MOVE_COST
                        moves[i] += 1

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
        "mean_energy": float(energy[alive].mean()) if alive.any() else 0.0,
    }


print("# Гейт: срабатывает ли условие?")
print()
results = {}
for cond, name in [("A", "не двигается"), ("B", "к соседу"), ("C", "случайно")]:
    r = run(cond)
    results[cond] = r
    print(f"  {cond} ({name:14}): ходов {r['total_moves']:8}, выжив. {r['survival']*100:5.1f}%")

print()

moves_B = results["B"]["total_moves"]
moves_C = results["C"]["total_moves"]
sA = results["A"]["survival"]

gate_ok = True
if moves_B == 0:
    print("ГЕЙТ ПРОВАЛЕН: B не двигался.")
    gate_ok = False
elif sA == 0.0 and results["B"]["survival"] == 0.0:
    print("ГЕЙТ ПРОВАЛЕН: все гибнут.")
    gate_ok = False
else:
    print(f"Гейт пройден: B {moves_B} ходов, C {moves_C} ходов, A выжил {sA*100:.1f}%.")

print()
print("# Результат")
print()
print("  условие   выживаемость   время жизни   энергия")
print(" " + "-" * 54)
for cond, name in [("A", "не двигается"), ("B", "к соседу"), ("C", "случайно")]:
    r = results[cond]
    print(f"  {cond} {name:14} {r['survival']*100:8.1f}%   {r['mean_lifetime']:8.1f}   {r['mean_energy']:7.3f}")
print()

sB = results["B"]["survival"]
sC = results["C"]["survival"]

print("# Сравнение")
print()
print(f"  B против A: {(sB-sA)*100:+.1f}%")
print(f"  B против C: {(sB-sC)*100:+.1f}%")
print()

print("# Вывод")
print()
if not gate_ok:
    print("Эксперимент НЕДЕЙСТВИТЕЛЕН.")
else:
    if sB > sA + 0.05:
        print("Действие ПОМОГАЕТ.")
    elif sB < sA - 0.05:
        print("Действие ВРЕДИТ: стоимость хода больше выгоды.")
    else:
        print("Действие не влияет существенно.")
    print()
    if sB > sC + 0.05:
        print("Умное правило ЛУЧШЕ случайного.")
    elif sB < sC - 0.05:
        print("Умное правило ХУЖЕ случайного.")
    else:
        print("Умное и случайное неразличимы.")
