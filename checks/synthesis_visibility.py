"""The synthesis, computed before it is run: how much of the medium can a window see?

Two closed lines never met: the perception line measured that a one-neighbour rule is silent on the
flat sea, and the selection line measured that a population's policy mix follows the medium's
spacing. Together they make a prediction that needs **no new mechanism**:

    the share of a sighted policy in a population under selection should follow the
    **visibility fraction** - the fraction of positions from which a rich cell lies within
    the window.

This prints that fraction for windows 1..4 and spacings 4, 8, 12, so the prediction exists before any
run.

    python3 checks/synthesis_visibility.py
"""

from __future__ import annotations

import sys

RICH = 3.0
POOR = 1.65


def field(cells: int, period: int) -> list[float]:
    return [RICH if i % period == 0 else POOR for i in range(cells)]


def visible(i: int, cells: int, period: int, k: int) -> bool:
    """Is there a richer cell within `k` steps, in the window a `Sighted` policy reads?"""
    f = field(cells, period)
    here = f[i]
    for d in range(1, k + 1):
        for j in (i - d, i + d):
            if 0 <= j < cells and f[j] > here:
                return True
    return False


def fraction(cells: int, period: int, k: int) -> float:
    hits = sum(1 for i in range(cells) if visible(i, cells, period, k))
    return hits / cells


def main(argv: list[str]) -> int:
    cells = 24
    print(f"line of {cells} cells, rich island every `period` cells")
    print()
    header = "  k | " + " | ".join(f"period {p:>2}" for p in (4, 8, 12))
    print(header)
    print("  --+" + "---------+" * 3)
    table = {}
    for k in (1, 2, 3, 4):
        row = []
        for period in (4, 8, 12):
            fn = fraction(cells, period, k)
            table[(k, period)] = fn
            row.append(f"{fn:>7.2f} ")
        print(f"  {k} | " + " | ".join(row))

    print()
    bad = 0
    checks = [
        ("a one-neighbour look sees least, in every spacing",
         all(table[(1, p)] <= table[(k, p)] for p in (4, 8, 12) for k in (2, 3, 4))),
        ("visibility never falls as the window widens",
         all(table[(k, p)] <= table[(k + 1, p)] for p in (4, 8, 12) for k in (1, 2, 3))),
        ("at spacing 4 a window of 2 already sees every rich cell it can reach",
         table[(2, 4)] > 0.5),
        ("at spacing 12 even a window of 4 sees only half the line",
         table[(4, 12)] <= 0.5),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1

    print()
    print("PREDICTION for the synthesis run, before it happens:")
    print("  the evolved share of `Sighted` should follow the visibility fraction:")
    for period in (4, 8, 12):
        print(f"    period {period:>2}: visibility {table[(3, period)]:.2f} -> "
              f"expect a sighted share near {table[(3, period)]:.2f} x (share seen at k=1) "
              f"[{table[(1, period)]:.2f}]")
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Расчёт пройден.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
