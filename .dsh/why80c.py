"""Exact mirror of the Rust step order, to find the real crowding limit.

Rust order (core/src/life.rs advance):
  for each organism, in index order:
     move (optional)
     taken = field.take(cell, income)      # min(cell, income), cell -= taken
     organism.step(world, taken)           # energy += taken; -maintenance;
                                           # damage += d; repair; cap; die
  field.regrow_all()                       # cell += (M - cell) * r   ONCE per step

So within one step the FIRST organism on a cell takes min(M, income) and every
later organism on the same cell takes min(M - income, income) = M - income.
"""
import sys


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=3000):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    min_field = M
    for _ in range(T):
        for i in range(k):
            if not alive[i]:
                continue
            taken = min(field, income)
            field -= taken
            if field < min_field:
                min_field = field
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
    return sum(alive), field, min_field


def predict_kmax(M, r, income, maintenance):
    """Second organism on a cell takes min(M - income, income) every step.
    It survives iff that >= maintenance."""
    second = min(M - income, income)
    if second < maintenance:
        return 1
    # k-th organism takes min(M - (k-1)*income, income)
    k = 1
    while True:
        nxt = min(M - k * income, income)
        if nxt < maintenance:
            return k
        k += 1
        if k > 500:
            return None


base = dict(M=2.0, r=0.8, income=0.8, maintenance=0.6, repair_cost=1.5,
            damage_rate=0.02, capacity=10.0)

print("=== exact mirror, base parameters ===")
print("  predicted k_max =", predict_kmax(2.0, 0.8, 0.8, 0.6))
for k in range(1, 7):
    a, f, mf = run(k=k, **base)
    print("  k=%2d alive=%2d field_end=%.4f field_min=%.4f" % (k, a, f, mf))

print("\n=== income 10 (no rationing) ===")
b = dict(base); b["income"] = 10.0
print("  predicted k_max =", predict_kmax(2.0, 0.8, 10.0, 0.6))
for k in range(1, 7):
    a, f, mf = run(k=k, **b)
    print("  k=%2d alive=%2d field_end=%.4f field_min=%.4f" % (k, a, f, mf))
sys.exit(0)
