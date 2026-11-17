"""The analysis that should have come before eight cycles of simulation.

`FINDING-191` ended with a confession and a question: what is the rest state of this
medium, and does a perturbation return to it? Both are answerable from the rule in a few
lines, and neither was ever computed. This file computes them.

The Barkley rule without diffusion:

    f(u,v) = (1/eps) u (1-u) (u - (v+b)/a)
    g(u,v) = u - v

Fixed points need g = 0, so v = u, and then f = 0 gives

    u = 0,   u = 1,   u = b/(a-1)

The third root is negative for a < 1, so outside the physical square.

PREDICTION, before the run:
    (a) exactly two fixed points in [0,1]x[0,1]: (0,0) stable and (1,1) unstable;
    (b) the decay rate of a small perturbation near rest is (1/eps)*(b/a), which for
        eps = 20, a = 0.75, b = 0.02 is 1.33e-3, so the relaxation time is about 750
        time units;
    (c) therefore a run of 120 time units - what FINDING-187..191 used - cannot reach
        rest, and the medium seen there was in its early transient, not at rest.

If (c) holds, it explains all eight failures at once, and the fix is a longer run or a
faster-resting parameter set, not a better initial condition.

    python3 checks/barkley_fixed_points.py
"""

from __future__ import annotations

import sys

A, B, EPS = 0.75, 0.02, 20.0
N = 64
DT = 0.01


def f(u: float, v: float) -> float:
    return (1.0 / EPS) * u * (1.0 - u) * (u - (v + B) / A)


def g(u: float, v: float) -> float:
    return u - v


def jacobian(u: float, v: float):
    # d/du of u(1-u)(u-(v+b)/a)
    hu = (1 - 2 * u) * (u - (v + B) / A) + u * (1 - u)
    huu = hu / EPS
    huv = (1.0 / EPS) * u * (1 - u) * (-1.0 / A)
    return huu, huv, 1.0, -1.0


def eigenvalues(u: float, v: float):
    a11, a12, a21, a22 = jacobian(u, v)
    tr = a11 + a22
    det = a11 * a22 - a12 * a21
    disc = tr * tr - 4 * det
    if disc >= 0:
        r = disc ** 0.5
        return (tr + r) / 2, (tr - r) / 2
    r = (-disc) ** 0.5
    return complex(tr / 2, r / 2), complex(tr / 2, -r / 2)


def roots():
    """All roots of f = 0 with v = u."""
    out = [0.0, 1.0]
    if abs(A - 1.0) > 1e-12:
        out.append(B / (A - 1.0))
    return out


def relaxation_rate(steps: int = 20000, u0: float = 0.10):
    """Spatially uniform, near rest. Fit the slow decay of u."""
    u, v = u0, u0
    ts, us = [], []
    for step in range(steps):
        du = f(u, v)
        dv = g(u, v)
        u += DT * du
        v += DT * dv
        if step % 200 == 0 and step > 0:
            ts.append(step * DT)
            us.append(abs(u))
    # exponential fit on the tail
    import math
    tail = [(t, x) for t, x in zip(ts, us) if x > 1e-9]
    if len(tail) < 6:
        return None
    tail = tail[len(tail) // 2:]
    (t0, x0), (t1, x1) = tail[0], tail[-1]
    if x0 <= 0 or x1 <= 0:
        return None
    return (math.log(x1) - math.log(x0)) / (t1 - t0)


def main(argv: list[str]) -> int:
    print(f"Barkley fixed points: a={A}, b={B}, eps={EPS}")
    print()
    print("  roots of f = 0 with v = u:", [round(r, 6) for r in roots()])
    print()
    physical = []
    for r in roots():
        if 0.0 <= r <= 1.0:
            ev = eigenvalues(r, r)
            physical.append((r, ev))
            shown = ", ".join(
                f"{e.real:+.6f}" if not isinstance(e, complex) else f"{e.real:+.6f}{e.imag:+.6f}i"
                for e in ev
            )
            stable = all((e.real < 0) for e in ev)
            print(f"  fixed point ({r:.2f}, {r:.2f}): eigenvalues {shown}  -> "
                  f"{'STABLE' if stable else 'UNSTABLE'}")

    predicted_rate = -(1.0 / EPS) * (B / A)
    # The Jacobian gives the ASYMPTOTIC rate. Measuring it means starting close
    # enough to rest that the cubic term is negligible: at u0 = 0.1 the nonlinear
    # part dominates and the rate comes out 74% too fast, which is what the first
    # version of this file reported.
    measured_far = relaxation_rate(u0=0.10)
    measured = relaxation_rate(u0=1e-3)
    print()
    print(f"  predicted near-rest decay rate: {predicted_rate:+.6f} per time unit")
    print(f"  predicted relaxation time:      {1 / abs(predicted_rate):.1f} time units")
    print(f"  measured at u0 = 1e-3 (linear regime): "
          f"{'none' if measured is None else f'{measured:+.6f}'}")
    print(f"  measured at u0 = 0.10 (nonlinear, reported only): "
          f"{'none' if measured_far is None else f'{measured_far:+.6f}'}")

    print()
    bad = 0
    checks = [
        ("(a) exactly two fixed points in the square", len(physical) == 2,
         [round(r, 4) for r, _ in physical]),
        ("(a) (0,0) is stable and (1,1) is unstable",
         len(physical) == 2 and all(e.real < 0 for e in physical[0][1]) and any(e.real > 0 for e in physical[-1][1]),
         [("stable" if all(e.real < 0 for e in ev) else "unstable") for _, ev in physical]),
        ("(b) the measured LINEAR decay rate matches (1/eps)*(b/a)",
         measured is not None and abs(measured - predicted_rate) / abs(predicted_rate) < 0.15,
         None if measured is None else round(measured, 6)),
        ("(c) the relaxation time exceeds the 120 time units used in 187 to 191",
         1 / abs(predicted_rate) > 120, round(1 / abs(predicted_rate), 1)),
    ]
    for label, ok, val in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{val}]")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Проверка пройдена.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
