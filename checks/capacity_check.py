"""Capacity: what does the corrected formula predict, and what is measured?

The formula was corrected on 2026-11-12/13:
    c* = M + t - t/r          (old, wrong: M - t/r)
    k_max = 0 if income < cost else 1 + floor((c* - cost)/income)
    C = cells * k_max

Measurement says C = 80 at n = 120 and n = 160, crowding 2.00.

So: what does the corrected formula give for the parameters that were measured?
This script only does arithmetic. It does not run the simulation.
"""
from math import floor

# Parameters used in the capacity experiments (see checks/exp*.py).
CELLS = 40
M = 2.0
R = 0.8
INCOME = 1.2
MAINTENANCE = 0.2
REPAIR_COST = 1.5


def cstar(M, r, t):
    return M + t - t / r


def cstar_old(M, r, t):
    return M - t / r


def k_max(M, r, income, cost):
    c = cstar(M, r, income)
    if income < cost:
        return 0
    return 1 + floor((c - cost) / income)


def k_max_old(M, r, income, cost):
    c = cstar_old(M, r, income)
    if income < cost:
        return 0
    return 1 + floor((c - cost) / income)


if __name__ == "__main__":
    print(f"parameters: cells={CELLS} M={M} r={R} income={INCOME} "
          f"maintenance={MAINTENANCE} repair_cost={REPAIR_COST}")
    print()

    co = cstar_old(M, R, INCOME)
    cn = cstar(M, R, INCOME)
    print(f"c* old = M - t/r          = {co:.4f}")
    print(f"c* new = M + t - t/r      = {cn:.4f}")
    print(f"difference                = {cn - co:.4f}  (= t = {INCOME})")
    print()

    ko = k_max_old(M, R, INCOME, MAINTENANCE)
    kn = k_max(M, R, INCOME, MAINTENANCE)
    print(f"k_max old = 1 + floor(({co:.4f} - {MAINTENANCE})/{INCOME}) = {ko}")
    print(f"k_max new = 1 + floor(({cn:.4f} - {MAINTENANCE})/{INCOME}) = {kn}")
    print()

    print(f"C old = {CELLS} * {ko} = {CELLS * ko}")
    print(f"C new = {CELLS} * {kn} = {CELLS * kn}")
    print(f"C measured = 80  (crowding 2.00)")
    print()

    print("=== which formula matches the measurement? ===")
    print(f"  old formula -> {CELLS * ko}   measured 80   "
          f"{'MATCH' if CELLS * ko == 80 else 'no'}")
    print(f"  new formula -> {CELLS * kn}   measured 80   "
          f"{'MATCH' if CELLS * kn == 80 else 'no'}")
    print()

    # The second seat is only worth taking if it pays for itself.
    # An organism on a shared cell gets income but pays maintenance and repair;
    # what it actually nets per step is what decides whether it stays.
    print("=== why is the second seat not taken? ===")
    print(f"  net per step on 1st seat = income - maintenance = "
          f"{INCOME - MAINTENANCE:.4f}")
    print(f"  the 2nd organism on the same cell draws the same income,")
    print(f"  so the cell's level drops by t per occupant:")
    for k in (1, 2, 3):
        print(f"    k={k}: c* = M + {k}*t - {k}*t/r = "
              f"{M + k * INCOME - k * INCOME / R:.4f}")
    print()
    print("  The level falls by t*(1-r)/r = "
          f"{INCOME * (1 - R) / R:.4f} per extra occupant.")
    print("  It stays above maintenance = "
          f"{MAINTENANCE:.4f} until k*t*(1-r)/r > c*(1) - maintenance = "
          f"{cstar(M, R, INCOME) - MAINTENANCE:.4f}")
    k_star = (cstar(M, R, INCOME) - MAINTENANCE) * R / (INCOME * (1 - R))
    print(f"  k* = {k_star:.4f}")
    print()
    print("  So the LEVEL permits about "
          f"{k_star:.2f} occupants, while k_max (the floor formula) says {kn}.")
    print("  The two disagree because k_max asks 'does the cell still hold")
    print("  income after k takes', and the level asks 'is the level still")
    print("  above maintenance'. They are different questions.")
