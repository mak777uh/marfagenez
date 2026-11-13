"""The crowding law: with zero maintenance the extra organisms still live.

M = 2, r = 0.8, income = 0.6, maintenance = 0. The law says k_max = 3 because
the 4th organism takes 0.0. But 7 survive.

With maintenance = 0 an organism that takes nothing neither gains nor loses, so
it survives forever on an initial energy of 10. That is not a crowding law, it
is a "no cost, no death" law. So the law needs cost > 0 to say anything.

The one real mismatch is (2.0, 0.8, 0.2, 0.5): law says 6, measurement says 0.
Supply = 1.6, cost = 0.5, so 3 organisms can each take 0.2 and be short by 0.3
per step. They start at 10, so they should last 33 steps. Measurement says 0
survive after 1500 steps, which is consistent -- they all starve.

So the law must be: k_max counts organisms that can take >= cost FOREVER.
With income 0.2 < cost 0.5, no organism can ever take enough, so k_max = 0.
The law as written returns 6 because it only checks the remainder, not income.
"""
import sys

M, r = 2.0, 0.8
supply = M * r


def k_max_law(income, cost):
    if cost <= 0:
        return None  # nothing to pay, everything survives; not a law
    if income < cost:
        return 0  # nobody can ever pay the cost
    if supply < cost:
        return 0
    k = 1
    while True:
        rest = supply - k * income
        if rest < cost:
            return k
        k += 1
        if k > 1000:
            return None


cases = [
    (0.6, 0.1, 3),
    (0.6, 0.5, 2),
    (0.2, 0.1, 8),
    (0.2, 0.5, 0),
    (1.0, 0.1, 2),
    (1.0, 0.7, 1),
    (0.6, 0.1, 4),
    (0.9, 0.1, 4),
]

print("supply = M*r = %.2f" % supply)
print("%-7s %-6s %-6s %-6s %s" % ("income", "cost", "law", "meas", "ok"))
bad = 0
for income, cost, meas in cases:
    pred = k_max_law(income, cost)
    ok = pred == meas
    if not ok:
        bad += 1
    print("%-7.2f %-6.2f %-6s %-6d %s" % (income, cost, pred, meas, "yes" if ok else "NO"))

print("\nclosed form when income >= cost:")
print("  k_max = floor((supply - cost) / income) + 1")
for income, cost, meas in cases:
    if income >= cost and supply >= cost:
        cf = int((supply - cost) // income) + 1
        print("  income=%.2f cost=%.2f -> %d (measured %d)" % (income, cost, cf, meas))
print("\nmismatches:", bad)
sys.exit(0)
