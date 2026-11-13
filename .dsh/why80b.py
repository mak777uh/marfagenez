"""Does the crowding limit come from the take cap or from regrow?

Same mirror as why80.py, but report the *minimum* field the cell ever reaches
and how much each organism actually takes at steady state.
"""
import sys


def run(M, r, income, maintenance, repair_cost, damage_rate, capacity, k, T=2000):
    field = M
    e = [capacity] * k
    dmg = [0.0] * k
    alive = [True] * k
    min_field = field
    last_taken = 0.0
    for _ in range(T):
        taken = min(field, income)
        last_taken = taken
        field -= taken
        if field < min_field:
            min_field = field
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
    return sum(alive), field, min_field, last_taken


def report(label, **kw):
    print("=== %s ===" % label)
    for k in range(1, 9):
        a, f, mf, tk = run(k=k, **kw)
        print("  k=%2d alive=%2d field_end=%.4f field_min=%.4f take=%.4f"
              % (k, a, f, mf, tk))


base = dict(M=2.0, r=0.8, income=0.8, maintenance=0.6, repair_cost=1.5,
            damage_rate=0.02, capacity=10.0)
report("base (income 0.8, maintenance 0.6)", **base)

b = dict(base); b["income"] = 10.0
report("income 10 (no rationing)", **b)

b = dict(base); b["maintenance"] = 0.0
report("maintenance 0 (any take keeps you alive)", **b)

b = dict(base); b["income"] = 10.0; b["maintenance"] = 0.0
report("income 10, maintenance 0", **b)
sys.exit(0)
