"""The crowding law, second attempt.

Rust step order within one step, organisms on the same cell in index order:
    taken = min(cell, income);  cell -= taken
and the cell regrows ONCE after all organisms have acted.

So the sequence of takes on a cell with k organisms is
    a_1 = min(M, income)
    a_j = min(M - a_1 - ... - a_{j-1}, income)
Organism j survives iff a_j >= cost, cost = maintenance + damage_rate*repair_cost.

The measured k_max is the largest k such that ALL of a_1..a_k >= cost.
Note: the takes do NOT depend on r at all -- r only sets how the cell
recovers between steps, and the recovery is irrelevant to who eats first.

That predicts k_max = floor(M / income) when income <= M... but the measurement
says otherwise, so this script checks the take sequence directly instead of
guessing.
"""
import sys


def takes(M, income, k):
    cell = M
    out = []
    for _ in range(k):
        t = min(cell, income)
        cell -= t
        out.append(round(t, 6))
    return out


def k_max_law(M, income, cost):
    k = 0
    for a in takes(M, income, 1000):
        if a < cost:
            break
        k += 1
    return k


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


for M, r, t, mc, d in [(2.0, 0.8, 0.8, 0.6, 0.02), (2.0, 0.8, 0.6, 0.1, 0.0),
                       (2.0, 0.8, 0.2, 0.1, 0.0)]:
    print("M=%.1f income=%.2f -> takes %s" % (M, t, takes(M, t, 10)))
    print("   law k_max=%.0f  measured=%d" %
          (k_max_law(M, t, mc + d * 1.5), run(M=M, r=r, income=t, maintenance=mc,
                                             repair_cost=1.5, damage_rate=d,
                                             capacity=1000.0, k=20)))
sys.exit(0)
