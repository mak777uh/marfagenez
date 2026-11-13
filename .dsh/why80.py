"""Why does the measurement say C = 80 when the recursion says k_max = 10?

Mirror of core/src/life.rs advance() + organism.rs step() + field.rs regrow_all().
Single cell, k organisms on it, no movement.

Per step:
  field <- field - min(field, income)          (take, capped by income)
  for each organism:
      energy += taken
      energy -= maintenance
      damage += damage_rate  (capped 1)
      repair = min(energy/repair_cost, damage); damage -= repair; energy -= repair*repair_cost
      energy = min(energy, capacity)
      dead if energy <= 0 or damage >= 1
  field <- field + (M - field) * r             (regrow)
"""
import sys


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=3000):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    for _ in range(T):
        taken = min(field, income)
        field -= taken
        for i in range(k):
            if not alive[i]:
                continue
            e[i] += taken
            e[i] -= maintenance
            dmg[i] = min(dmg[i] + damage_rate, 1.0)
            if e[i] > 0.0 and dmg[i] > 0.0:
                rep = min(e[i] / repair_cost, dmg[i])
                dmg[i] -= rep
                e[i] -= rep * repair_cost
            e[i] = min(e[i], capacity)
            if e[i] <= 0.0 or dmg[i] >= 1.0:
                alive[i] = False
        field = field + (M - field) * r
    return sum(alive), field, e[0] if alive[0] else 0.0


def k_max_arithmetic(M, r, income, maintenance, cap=200):
    """How many organisms can take `maintenance` before the cell falls below it?
    Bounded loop: if it does not stop within `cap`, say so."""
    c = M
    k = 0
    while k < cap:
        take = min(c, income)
        if take < maintenance:
            return k
        c -= take
        k += 1
        c = c + (M - c) * r
    return None  # did not stop


base = dict(M=2.0, r=0.8, income=0.8, maintenance=0.6, repair_cost=1.5,
            damage_rate=0.02, capacity=10.0)

print("=== k_max by the recursion (bounded at 200) ===")
print("  k_max =", k_max_arithmetic(2.0, 0.8, 0.8, 0.6))

print("\n=== survivors vs k, base parameters ===")
for k in range(1, 13):
    a, f, en = run(k=k, **base)
    print("  k=%2d  alive=%2d  field=%.4f  e0=%.4f" % (k, a, f, en))

print("\n=== survivors vs k, no damage cost (repair_cost=0, damage_rate=0) ===")
b2 = dict(base)
b2["repair_cost"] = 0.0
b2["damage_rate"] = 0.0
for k in range(1, 13):
    a, f, en = run(k=k, **b2)
    print("  k=%2d  alive=%2d  field=%.4f  e0=%.4f" % (k, a, f, en))

print("\n  effective cost per step with damage = 0.6 + 0.02*1.5 =", 0.6 + 0.02 * 1.5)
sys.exit(0)
