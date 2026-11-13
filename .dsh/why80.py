"""Why does the measurement say C = 80 when the new formula says k_max = 10?

Mirror of core/src/life.rs advance() + organism.rs step() + field.rs
regrow_all(), single cell, k organisms on it, no movement.

cell <- cell - min(cell, income)
field <- field + (M - field) * r
organism: energy += taken; energy -= maintenance; damage += d;
          repair = min(energy/repair_cost, damage); energy -= repair*repair_cost;
          energy = min(energy, capacity)
"""
import itertools


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=20000):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    for _ in range(T):
        for i in range(k):
            if not alive[i]:
                continue
            taken = min(field, income)
            field -= taken
            e[i] += taken
            e[i] -= maintenance
            dmg[i] = min(dmg[i] + damage_rate, 1.0)
            if e[i] > 0.0 and dmg[i] > 0.0:
                rep = min(e[i] / repair_cost, dmg[i])
                dmg[i] -= rep
                e[i] -= rep * repair_cost
            e[i] = min(e[i], capacity)
            e[i] = max(e[i], 0.0)
            if e[i] <= 0.0 or dmg[i] >= 1.0:
                alive[i] = False
        field = field + (M - field) * r
    return sum(alive), field, e[0] if alive[0] else 0.0


def k_max_arithmetic(M, r, income, maintenance):
    """How many can take `maintenance` before the cell falls below it?"""
    c = M
    k = 0
    while True:
        take = min(c, income)
        if take < maintenance:
            return k
        c -= take
        k += 1
        c = c + (M - c) * r


base = dict(M=2.0, r=0.8, income=0.8, maintenance=0.6, repair_cost=1.5,
            damage_rate=0.02, capacity=10.0)

print("=== k_max by the recursion (ignores repair cost) ===")
print("  k_max =", k_max_arithmetic(2.0, 0.8, 0.8, 0.6))

print("\n=== survivors vs k, base parameters ===")
for k in range(1, 13):
    a, f, en = run(k=k, **base)
    print("  k=%2d  alive=%2d  field=%.4f  e0=%.4f" % (k, a, f, en))

print("\n=== survivors vs k, repair_cost = 0 (no damage cost) ===")
b2 = dict(base)
b2["repair_cost"] = 0.0
b2["damage_rate"] = 0.0
for k in range(1, 13):
    a, f, en = run(k=k, **b2)
    print("  k=%2d  alive=%2d  field=%.4f  e0=%.4f" % (k, a, f, en))

print("\n=== survivors vs k, maintenance = 0.6 + repair 0.02*1.5 = 0.63 effective ===")
print("  effective cost per step =", 0.6 + 0.02 * 1.5)
