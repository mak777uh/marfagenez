"""Why does the field stay at 1.6 when 5 organisms eat 1.3 per step?

M = 2, r = 0.8, income = 0.6, one cell, 5 organisms.
Measured: the field sits at 1.6 every step, and the takes are 0.5, 0.5, 0.3.

If the field were at 1.6 and the first organism took min(1.6, 0.6) = 0.6, the
cell would fall to 1.0 and the second would take 0.6, not 0.5. So the first two
take 0.5 each. That means the cell is at 1.1 when they eat, not 1.6.

1.1 + regrow: 1.1 + (2 - 1.1)*0.8 = 1.82. Not 1.6 either.
1.1 -> after taking 1.1 total -> 0.0 -> regrow to 2*0.8 = 1.6. That fits!

So the field is emptied every step and regrows to M*r = 1.6, and the takes are
0.5, 0.5, 0.3 -- which sums to 1.3, more than the 1.1 available.

That cannot be. Unless the takes are not what the energy deltas suggest: energy
also pays maintenance 0.1. So a gain of 0.5 in energy = take 0.6 - 0.1.
A gain of 0.3 = take 0.4 - 0.1. A loss of 0.1 = take 0.0 - 0.1.

Takes: 0.6, 0.6, 0.4, 0.0, 0.0 -- sum 1.6. And 1.6 = M*r. The cell is emptied
every step and regrows to M*r. The arithmetic was right; I was reading energy
deltas as takes and forgetting maintenance.
"""
import sys

M, r, income, maintenance = 2.0, 0.8, 0.6, 0.1


def takes_of(k):
    cell = M * r  # the cell is at M*r at the start of the step (emptied last step)
    out = []
    for _ in range(k):
        t = min(cell, income)
        cell -= t
        out.append(round(t, 6))
    return out


def k_max(cost):
    k = 0
    for t in takes_of(200):
        if t < cost:
            break
        k += 1
    return k


print("cell at start of step = M*r =", M * r)
print("takes:", takes_of(8))
print("sum of takes:", sum(takes_of(8)))
print()
print("cost = maintenance =", maintenance, "-> k_max =", k_max(maintenance))
print("cost = maintenance + damage*repair =", maintenance + 0.02 * 1.5,
      "-> k_max =", k_max(maintenance + 0.02 * 1.5))
print()
print("closed form: the cell holds M*r per step, each organism needs `cost`,")
print("so k_max = floor(M*r / cost) =", int((M * r) // maintenance))
print("and the last one may take a remainder if it exceeds `cost`.")
sys.exit(0)
