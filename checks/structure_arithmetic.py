"""Arithmetic before code: what shapes can pay for themselves, and how big can they get?

The project has a price and no space of configurations (`docs/WHERE-WE-ARE.md`, limit 3), so no
structure could ever be selected for. This computes the economy of a **shape** before anything
is implemented, because a design that cannot pay for itself in arithmetic will not pay for
itself in code either.

The proposed economy for a form made of `n` cells with `p` boundary edges:

    income      sigma * p        only the boundary touches the medium
    upkeep      mu * n           every cell costs
    transport   kappa * n^2 / p  the interior is further from the boundary, and
                                 mean distance scales as n/p

A form survives while `sigma*p >= mu*n + kappa*n^2/p`. Dividing by `p` and writing
`x = n/p` (cells per unit of boundary):

    sigma >= mu*x + kappa*x^2        =>    x <= x* = (sqrt(mu^2 + 4*kappa*sigma) - mu) / (2*kappa)

So the economy fixes a **maximum number of cells per unit of boundary**. Since a square of side
`s` has `x = s/4`, the largest sustainable square has side `4*x*` - a finite size, from
arithmetic, without a single simulation.

    python3 checks/structure_arithmetic.py
"""

from __future__ import annotations

import math
import sys

MU = 1.0
KAPPA = 0.1
SIGMA = 2.0


def x_limit(mu: float = MU, kappa: float = KAPPA, sigma: float = SIGMA) -> float:
    return (math.sqrt(mu * mu + 4 * kappa * sigma) - mu) / (2 * kappa)


def rect(w: int, h: int) -> tuple[int, int]:
    """Cells and boundary edges of a w-by-h rectangle."""
    n = w * h
    p = 2 * (w + h)
    return n, p


def ring(side: int) -> tuple[int, int]:
    """A hollow ring: outer boundary plus the inner hole's edges."""
    n = side * side - (side - 2) * (side - 2)
    p = 4 * side + 4 * (side - 2)
    return n, p


def l_shape(arm: int) -> tuple[int, int]:
    """An L made of two arms of length `arm` at right angles, no overlap."""
    n = 2 * arm - 1
    p = 2 * arm + 2
    return n, p


def survives(n: int, p: int) -> bool:
    return SIGMA * p >= MU * n + KAPPA * n * n / p


def main(argv: list[str]) -> int:
    x_star = x_limit()
    print(f"economy: sigma={SIGMA}, mu={MU}, kappa={KAPPA}")
    print(f"maximum cells per boundary edge: x* = {x_star:.4f}")
    print(f"largest sustainable square: side {4 * x_star:.1f} (so {4 * x_star:.0f} is the limit)")
    print()
    print(f"{'shape':<16} {'n':>4} {'p':>4} {'x=n/p':>8} {'x<=x*':>6} {'survives':>9}")
    shapes = [
        ("square 2x2", rect(2, 2)),
        ("square 4x4", rect(4, 4)),
        ("square 6x6", rect(6, 6)),
        ("square 7x7", rect(7, 7)),
        ("square 8x8", rect(8, 8)),
        ("square 12x12", rect(12, 12)),
        ("strip 1x8", rect(1, 8)),
        ("strip 2x8", rect(2, 8)),
        ("strip 4x4", rect(4, 4)),
        ("ring 5", ring(5)),
        ("ring 8", ring(8)),
        ("L arm 6", l_shape(6)),
    ]
    bad = 0
    for name, (n, p) in shapes:
        x = n / p
        ok_x = x <= x_star
        ok_s = survives(n, p)
        print(f"{name:<16} {n:>4} {p:>4} {x:>8.3f} {str(ok_x):>6} {str(ok_s):>9}")
        if ok_x != ok_s:
            print("  FAIL: the x-test and the full inequality disagree")
            bad += 1

    print()
    checks = [
        ("a square of side s has x = s/4",
         all(abs(rect(s, s)[0] / rect(s, s)[1] - s / 4) < 1e-12 for s in (2, 4, 7, 12))),
        ("a long strip has x approaching 0.5",
         abs(rect(1, 40)[0] / rect(1, 40)[1] - 40 / 82) < 1e-12 and 40 / 82 > 0.48),
        ("the largest square that survives is side 6, and 7 does not",
         survives(*rect(6, 6)) and not survives(*rect(7, 7))),
        ("size, not shape alone, decides for squares: 12 is refused while 2 is kept",
         survives(*rect(2, 2)) and not survives(*rect(12, 12))),
        ("a ring of side 8 is cheaper per cell than a solid square of the same extent",
         (ring(8)[0] / ring(8)[1]) < (rect(8, 8)[0] / rect(8, 8)[1])),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Расчёт пройден: экономия формы задаёт предельный размер.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
