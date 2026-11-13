"""Crowding: who actually dies, and when?

Prints the per-organism fate for k = 3..8 on one cell, so the pattern is visible
instead of inferred.
"""
import sys


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=3000):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    death = [None] * k
    for step in range(T):
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
                death[i] = step
        field = field + (M - field) * r
    return alive, death, e


for k in (3, 5, 7, 8):
    alive, death, e = run(M=2.0, r=0.8, income=0.6, maintenance=0.1,
                          repair_cost=1.5, damage_rate=0.0, capacity=1000.0, k=k)
    print("k=%d alive=%d deaths=%s" % (k, sum(alive),
                                       [d for d in death if d is not None]))

print()
for k in (3, 5, 7, 8):
    alive, death, e = run(M=2.0, r=0.8, income=0.2, maintenance=0.1,
                          repair_cost=1.5, damage_rate=0.0, capacity=1000.0, k=k)
    print("income 0.2  k=%d alive=%d deaths=%s" % (k, sum(alive),
                                                   [d for d in death if d is not None]))
sys.exit(0)
