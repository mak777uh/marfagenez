#!/usr/bin/env python3
"""bridge_price_derivative.py -- F2: is the recorded price the envelope derivative?

The bridge `C-001/C-002 <-> L-062` claims our price is the derivative of the value function
with respect to the resource. That is checkable without trusting the experiment:

    V(a) = max { 2u1 + 5u2 + u3 : u1+u2+u3 <= 1, u1 >= a, u3 >= 0.1, u2 <= 0.5, u >= 0 }
    price(a) = |dV/da|   for the repair-capacity constraint

EXP-PRICE-KINKS records 1 before the kink and 3 after. The instrument must be able to disagree,
otherwise it is a decoration.
"""
import sys

import numpy as np
from scipy.optimize import linprog

W = np.array([2.0, 5.0, 1.0])
I, R_MAX, U3_MIN, U2_MAX = 1.0, 0.5, 0.1, 0.5
KINK = 0.4


def value_and_dual(a):
    A = [[1.0, 1.0, 1.0], [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]
    b = [I, -a, R_MAX, U2_MAX, -U3_MIN]
    r = linprog(-W, A_ub=A, b_ub=b, bounds=[(0, None)] * 3, method="highs")
    if not r.success:
        return None, None
    return -r.fun, -r.ineqlin.marginals[1]   # dV/da


def fd_price(a, eps=1e-5):
    vp, _ = value_and_dual(a + eps)
    vm, _ = value_and_dual(a - eps)
    if vp is None or vm is None:
        return None
    return (vp - vm) / (2 * eps)


def claimed(a):
    return 3.0 if a > KINK else 1.0


def main():
    print("F2: цена как производная функции значения")
    print("  a      V(a)     dV/da     |dV/da|   правило   совпадает")
    bad = []
    for a in (0.20, 0.30, 0.35, 0.42, 0.46):
        v, dual = value_and_dual(a)
        d = fd_price(a)
        if v is None or d is None:
            print("  %.2f   ---      ---       ---       ---        void" % a)
            continue
        ok = abs(abs(d) - claimed(a)) < 1e-3
        if not ok:
            bad.append((a, d, claimed(a)))
        print("  %.2f  %7.4f  %8.4f  %8.4f  %7.1f   %s" % (a, v, d, abs(d), claimed(a), "да" if ok else "нет"))
    print()
    if bad:
        a, d, c = bad[0]
        print("  ДИАГНОЗ: до излома цена по правилу = %.0f, а производная функции значения = %.0f." % (c, abs(d)))
        print("  Прогон назначал цену условием, а не брал из двойственной задачи (дефект постановки, Q16).")
        print("  C-001 при этом согласуется: при несязывающем ограничении цена равна нулю.")
        print("  Подробности: docs/FINDING-320-price-rule-vs-derivative.md")
    else:
        print("  правило совпадает с производной во всех точках")
    return 0


if __name__ == "__main__":
    sys.exit(main())
