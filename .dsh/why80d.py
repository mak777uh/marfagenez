"""Crowding law, derived from the Rust step order.

Rust: within one step, organisms on the same cell take in index order
(`field.take` = min(cell, income)); the field regrows ONCE after all of them.

So on a cell with k organisms, organism j (0-based) takes
    take_j = min(max(M - j*income, 0), income)
and survives iff take_j >= maintenance (plus repair cost).

Predicted crowding limit:
    k_max = 1 + floor((M - maintenance) / income)      when income <= M
    k_max = 1                                          when income > M
    (with maintenance replaced by maintenance + damage_rate*repair_cost)

Capacity = cells * k_max.
"""
import sys


def k_max_law(M, income, cost):
    if income > M:
        return 1
    if income <= 0:
        return None
    return 1 + int((M - cost) // income)


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=3000):
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
            if e[i] <= 0.0 or dmg[i] >= 1.0:
                alive[i] = False
        field = field + (M - field) * r
    return sum(alive)


grid = [
    # M, r, income, maintenance, damage_rate
    (2.0, 0.8, 0.8, 0.6, 0.02),
    (2.0, 0.8, 0.8, 0.6, 0.00),
    (2.0, 0.8, 0.2, 0.1, 0.00),
    (2.0, 0.8, 0.2, 0.5, 0.00),
    (2.0, 0.8, 0.6, 0.1, 0.00),
    (2.0, 0.8, 0.6, 0.5, 0.00),
    (2.0, 0.8, 1.0, 0.1, 0.00),
    (2.0, 0.8, 1.0, 0.7, 0.00),
    (2.0, 0.5, 0.6, 0.1, 0.00),
    (2.0, 0.5, 0.6, 0.0, 0.00),
    (3.0, 0.8, 0.6, 0.1, 0.00),
    (3.0, 0.8, 0.6, 0.0, 0.00),
    (4.0, 0.8, 0.6, 0.1, 0.00),
    (4.0, 0.8, 0.9, 0.1, 0.00),
    (2.0, 0.9, 0.6, 0.1, 0.00),
    (2.0, 0.9, 0.6, 0.0, 0.00),
]

print("%-5s %-5s %-6s %-6s %-6s | %-6s %-6s %-6s" %
      ("M", "r", "income", "maint", "dmg", "law", "meas", "ok"))
bad = 0
for M, r, t, mc, d in grid:
    cost = mc + d * 1.5
    pred = k_max_law(M, t, cost)
    meas = run(M=M, r=r, income=t, maintenance=mc, repair_cost=1.5,
               damage_rate=d, capacity=1000.0, k=(pred or 1) + 3)
    ok = (pred == meas)
    if not ok:
        bad += 1
    print("%-5.1f %-5.1f %-6.2f %-6.2f %-6.2f | %-6s %-6d %-6s" %
          (M, r, t, mc, d, pred, meas, "yes" if ok else "NO"))
print("\nmismatches:", bad, "of", len(grid))
sys.exit(0)
