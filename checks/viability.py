"""Проверка жизнеспособности мира ДО эксперимента.

Пять провалов гейта в EXP-02 научили: сначала проверь, что мир вообще
позволяет жить, и только потом меряй эффект действия.

## Что проверяем

1. Сколько ресурса доступно на организм за шаг?
2. Сколько нужно для поддержания?
3. Есть ли запас?

Запуск: python checks/viability.py
"""

from __future__ import annotations

import numpy as np

RICH = 1.0
POOR = 0.1
REGROW = 0.2
INCOME = 0.8
MAINTENANCE = 0.6
REPAIR_COST = 1.5
DAMAGE_RATE = 0.02

print("# Жизнеспособность мира")
print()
print(f"богатая клетка {RICH}, бедная {POOR}, regrow {REGROW}")
print(f"income {INCOME}, maintenance {MAINTENANCE}")
print(f"repair_cost {REPAIR_COST}, damage_rate {DAMAGE_RATE}")
print()

# What one organism needs per step.
need_maintenance = MAINTENANCE
need_repair = DAMAGE_RATE * REPAIR_COST
need_total = need_maintenance + need_repair

print(f"# Что нужно одному организму за шаг")
print(f"  поддержание: {need_maintenance:.3f}")
print(f"  ремонт:      {need_repair:.3f}")
print(f"  всего:       {need_total:.3f}")
print()

# What the field can give.
print("# Что может дать поле")
print()
print("  организмов   клеток   на клетку   ресурс/организм   хватает?")
print(" " + "-" * 68)

for n_org in [20, 40, 100, 200]:
    for cells in [20, 40]:
        per_cell = n_org / cells
        # Each rich cell regrows toward RICH. At equilibrium, the regrowth per step
        # equals what is taken. Rich cells are half the field.
        rich_cells = cells // 2
        # Regrowth per rich cell per step at level L: (RICH - L) * REGROW.
        # If all organisms crowd the rich cells, the total regrowth is
        # rich_cells * (RICH - L) * REGROW. At L=0 it is maximal.
        max_regrow_per_step = rich_cells * RICH * REGROW
        per_org = max_regrow_per_step / n_org
        ok = "ДА" if per_org >= need_total else "НЕТ"
        print(f"  {n_org:11}   {cells:6}   {per_cell:9.1f}   {per_org:15.3f}   {ok:8}")

print()
print("# Вывод")
print()
print(f"Одному организму нужно {need_total:.3f} ресурса за шаг.")
print()
print("Если поле даёт меньше — организмы гибнут, и эксперимент недействителен.")
print()

# Find a viable configuration.
print("# Подбор жизнеспособной конфигурации")
print()
print("  организмов   клеток   ресурс/организм   хватает?")
print(" " + "-" * 56)

best = None
for n_org in [10, 20, 40, 100]:
    for cells in [20, 40, 80]:
        if n_org > cells:
            continue
        rich_cells = cells // 2
        max_regrow = rich_cells * RICH * REGROW
        per_org = max_regrow / n_org
        ok = per_org >= need_total
        if ok and best is None:
            best = (n_org, cells, per_org)
        print(f"  {n_org:11}   {cells:6}   {per_org:15.3f}   {'ДА' if ok else 'нет':8}")

print()
if best:
    print(f"Первая жизнеспособная: {best[0]} организмов на {best[1]} клеток")
    print(f"ресурс/организм = {best[2]:.3f}, нужно {need_total:.3f}")
