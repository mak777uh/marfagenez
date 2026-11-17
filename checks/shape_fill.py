"""The interval at the stock the world actually has, and the fill fraction it demands.

`FINDING-225` found that the solvency interval of `FINDING-219` was computed at a **full** stock,
while the world's shared pool is often empty - so forms were being judged against a medium that
does not exist. This puts the fill fraction into the arithmetic.

Income is `f * 4*sigma*s` where `f = stock/stock_max`, so survival is

    f * g(s) >= f0        with   g(s) = 4*sigma*s - mu*s^2 - kappa*s^3/4

`g` peaks at `g(3.532) = 14.679`, so a setting can support any form at all only while

    f >= f* = f0 / 14.679

and at a given `f` the surviving sides are the two roots of `g(s) = f0/f`.

This prints the demanded fill fraction for the prices already measured and for two prices that
have **not** been run - 12 and 13 - so the prediction is out of sample.

    python3 checks/shape_fill.py
"""

from __future__ import annotations

import math
import sys

SIGMA = 2.0
MU = 1.0
KAPPA = 0.1
PEAK_S = 3.532
PEAK_G = 14.679


def g(s: float) -> float:
    return 4.0 * SIGMA * s - MU * s * s - KAPPA * s ** 3 / 4.0


def interval_at(f: float, f0: float) -> tuple[float, float] | None:
    """Sides that survive when the stock is `f` full and the fixed cost is `f0`."""
    if f <= 0.0:
        return None
    target = f0 / f
    if target >= PEAK_G:
        return None
    lo, hi, steps = 0.0, PEAK_S, 2000
    for _ in range(steps):
        mid = (lo + hi) / 2
        if g(mid) < target:
            lo = mid
        else:
            hi = mid
    lower = (lo + hi) / 2
    lo, hi = PEAK_S, 1e4
    for _ in range(steps):
        mid = (lo + hi) / 2
        if g(mid) >= target:
            lo = mid
        else:
            hi = mid
    return (lower, (lo + hi) / 2)


def main(argv: list[str]) -> int:
    print(f"peak of g: {PEAK_G} at side {PEAK_S}")
    print()
    print(f"{'f0':>6} {'needs fill f*':>14} {'interval at f=1':>24} {'interval at f=0.5':>26}")
    rows = []
    for f0 in [6.0, 10.0, 12.0, 13.0, 14.0]:
        f_star = f0 / PEAK_G
        iv1 = interval_at(1.0, f0)
        iv_half = interval_at(0.5, f0)
        def show(iv):
            return "none" if iv is None else f"{iv[0]:.3f}...{iv[1]:.3f}"
        print(f"{f0:>6.1f} {f_star:>14.3f} {show(iv1):>24} {show(iv_half):>26}")
        rows.append((f0, f_star, iv1, iv_half))

    print()
    bad = 0
    checks = [
        ("a fill fraction is between zero and one for every affordable price",
         all(0.0 < r[1] < 1.0 for r in rows if r[0] < PEAK_G)),
        ("f0 = 14 demands more than 95% fill", rows[4][1] > 0.95),
        ("f0 = 6 demands less than half fill", rows[0][1] < 0.5),
        ("at half a stock only the cheapest price can support anything",
         rows[0][3] is not None and all(r[3] is None for r in rows[1:])),
        ("the interval shrinks as the demanded fill grows",
         rows[0][2] is not None and rows[4][2] is not None
         and (rows[4][2][1] - rows[4][2][0]) < (rows[0][2][1] - rows[0][2][0])),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Расчёт пройден.")
    print()
    print("PREDICTION, out of sample (prices 12 and 13 were never run):")
    print(f"  f0 = 12 needs fill {rows[2][1]:.3f}: the pool must stay above {rows[2][1]:.0%}, "
          f"which the world reaches only when few forms are alive -> expect survival of a few runs")
    print(f"  f0 = 13 needs fill {rows[3][1]:.3f}: expect mostly extinction")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
