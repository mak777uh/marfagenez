"""PROTOCOL-0 п.3 — ТОЧНАЯ модель core/src/organism.rs::step (строки 420-460).

Расхождение с моим первым скриптом: в core ремонт — ВСЁ-ИЛИ-НИЧЕГО
по цене `damage * repair_cost`, а не `damage_rate * repair_cost`.
Условие: `price < energy` (строго).

Порядок шага:
  1. energy += min(resource, income)
  2. energy -= maintenance_cost
  3. damage = min(damage + damage_rate, 1.0)
  4. если damage > 0 и damage*repair_cost < energy:
       energy -= damage*repair_cost; damage = 0
  5. energy = clamp(energy, 0, capacity)
  6. смерть: energy <= 0 или damage >= 1
"""
import itertools

MAINT, REPAIR, CAP, STEPS = 0.6, 1.5, 10.0, 5000

def step(energy, damage, income, dr, resource):
    taken = max(0.0, min(resource, income))
    energy += taken
    energy -= MAINT
    damage = min(damage + dr, 1.0)
    if damage > 0.0:
        price = damage * REPAIR
        if price < energy:
            energy -= price
            damage = 0.0
    energy = max(0.0, min(energy, CAP))
    return energy, damage

def run(income, dr, resource=None, energy0=CAP, damage0=0.0):
    if resource is None:
        resource = income
    e, d = energy0, damage0
    for t in range(STEPS):
        e, d = step(e, d, income, dr, resource)
        if e <= 0.0:
            return ('energy', t, e, d)
        if d >= 1.0:
            return ('damage', t, e, d)
    return ('alive', STEPS, e, d)

print("=" * 80)
print("СЕТКА (точная модель): income × damage_rate, resource = income")
print("=" * 80)
print(f"{'income':>7} {'dr':>7} {'причина':>8} {'шаг':>6} {'energy':>9} {'damage':>8}")
print("-" * 80)

grid_income = [0.0, 0.3, 0.5, 0.6, 0.65, 0.7, 0.8, 1.0]
grid_dr = [0.001, 0.01, 0.05, 0.1, 0.2, 0.5]

dmg_deaths, en_deaths, alive = [], [], []
for inc, dr in itertools.product(grid_income, grid_dr):
    c, t, e, d = run(inc, dr)
    print(f"{inc:>7.3f} {dr:>7.3f} {c:>8} {t:>6} {e:>9.4f} {d:>8.4f}")
    (dmg_deaths if c == 'damage' else en_deaths if c == 'energy' else alive).append((inc, dr, t))

print()
print("=" * 80)
print(f"ИТОГ: урон {len(dmg_deaths)} / голод {len(en_deaths)} / жив {len(alive)} из {len(grid_income)*len(grid_dr)}")
print("=" * 80)
if dmg_deaths:
    print("  Смерть от УРОНА достижима:")
    for inc, dr, t in dmg_deaths:
        print(f"    income={inc} dr={dr} -> шаг {t}")
    print("  ВЕРДИКТ п.3: PASSED — носитель есть")
else:
    print("  ВЕРДИКТ п.3: FAILED — урон не убивает ни на одной точке сетки")

print()
print("=" * 80)
print("ПОЧЕМУ: цена ремонта = damage*repair_cost, а damage растёт на dr/шаг")
print("  если ремонт не прошёл, на следующем шаге damage = 2*dr, цена = 3*dr")
print("  цена растёт ЛИНЕЙНО с накопленным уроном, а energy падает")
print("  => срыв ремонта — самоусиливающийся: чем дольше не чинишься, тем дороже")
print("  это и есть положительная обратная связь, которой не было в моей первой модели")
