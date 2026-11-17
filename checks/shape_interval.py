"""The interval of sizes that pays for itself once a form has a fixed cost.

`FINDING-218` ended with the atom winning: with income proportional to the boundary and no fixed
cost, the smallest form has the best ratio and structure is dismantled. Adding a fixed cost `f0`
per form turns the survival condition into a quadratic and creates an **interval**: too small
and a form cannot cover `f0`, too large and transport eats it.

For a square of side `s`, income is `4*sigma*s` and upkeep is `f0 + mu*s^2 + kappa*s^3/4`, so

    survives  <=>  g(s) = 4*sigma*s - mu*s^2 - kappa*s^3/4  >=  f0

`g` rises from zero, peaks, and falls, so `g(s) = f0` has two roots below the peak and none
above it. This prints the interval for several `f0` and checks the arithmetic.

    python3 checks/shape_interval.py
"""

from __future__ import annotations

import math
import sys

SIGMA = 2.0
MU = 1.0
KAPPA = 0.1


def g(s: float) -> float:
    """The surplus of a square of side `s`, before the fixed cost."""
    return 4.0 * SIGMA * s - MU * s * s - KAPPA * s ** 3 / 4.0


def peak() -> tuple[float, float]:
    """The side at which the surplus is greatest, and that greatest surplus.

    `g'(s) = 4*sigma - 2*mu*s - 3*kappa*s^2/4 = 0`, positive root.
    """
    a = 3.0 * KAPPA / 4.0
    b = 2.0 * MU
    c = 4.0 * SIGMA
    s = (-b + math.sqrt(b * b + 4.0 * a * c)) / (2.0 * a)
    return s, g(s)


def interval(f0: float, coarse: float = 0.001) -> tuple[float, float] | None:
    """The sides that survive at fixed cost `f0`, by scanning and bisecting."""
    s_peak, g_peak = peak()
    if f0 >= g_peak:
        return None
    # lower root on [0, s_peak]
    lo, hi = 0.0, s_peak
    while hi - lo > coarse:
        mid = (lo + hi) / 2.0
        if g(mid) < f0:
            lo = mid
        else:
            hi = mid
    lower = (lo + hi) / 2.0
    # upper root on [s_peak, ...]
    lo, hi = s_peak, s_peak
    while g(hi) >= f0:
        hi *= 2.0
        if hi > 1e6:
            return (lower, math.inf)
    while hi - lo > coarse:
        mid = (lo + hi) / 2.0
        if g(mid) >= f0:
            lo = mid
        else:
            hi = mid
    upper = (lo + hi) / 2.0
    return (lower, upper)


def main(argv: list[str]) -> int:
    s_peak, g_peak = peak()
    print(f"surplus of a square: g(s) = {4 * SIGMA:.0f}s - {MU:.0f}s^2 - {KAPPA / 4:.3f}s^3")
    print(f"greatest surplus {g_peak:.3f} at side {s_peak:.3f}")
    print(f"so no fixed cost above {g_peak:.2f} can be paid by any square")
    print()
    print(f"{'f0':>6} {'lowest side':>12} {'highest side':>13} {'width':>7}")
    rows = []
    for f0 in [0.0, 2.0, 6.0, 10.0, 14.0, 15.0, 20.0]:
        iv = interval(f0)
        if iv is None:
            print(f"{f0:>6.1f} {'none':>12} {'none':>13} {'-':>7}")
            rows.append((f0, None))
        else:
            lo, hi = iv
            width = hi - lo
            print(f"{f0:>6.1f} {lo:>12.3f} {hi:>13.3f} {width:>7.3f}")
            rows.append((f0, (lo, hi)))

    print()
    bad = 0
    checks = [
        ("a fixed cost of zero keeps the atom alive (the interval starts at zero)",
         rows[0][1] is not None and rows[0][1][0] < 0.01),
        ("a fixed cost of eight excludes the atom", interval(8.0) is not None and interval(8.0)[0] > 1.0),
        ("every interval is non-empty below the peak", all(
            iv is not None and iv[1] > iv[0] for f0, iv in rows if f0 < g_peak)),
        ("no square can pay a fixed cost above the peak", interval(g_peak + 0.5) is None),
        ("income at the top of the interval equals upkeep",
         abs(g(interval(8.0)[1]) - 8.0) < 0.01),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Расчёт пройден: фиксированный расход задаёт интервал размеров.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
