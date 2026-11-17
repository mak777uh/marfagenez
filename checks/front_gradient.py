"""Does the front go faster toward food? The question that twice could not be asked.

`FINDING-181` and `182` tried to ask it and failed twice for the same reason: the
measurements were taken where the structure was already dead. Now the front is alive
under a price (`FINDING-188`), so the question is finally askable, and the speed is
measured as a **slope over all frames** rather than a difference between two - the
defect that `FINDING-188` admitted.

    rule      Barkley with a resource channel, as in FINDING-188
              u_t = D u_xx + (1/eps) u(1-u)(u-(v+b)/a) * r
              r_t = grow*(ceiling - r) - consume*u
    grid      line of 256, dx = 0.25, dt = 0.01, eps = 20, grow = 0.2
    price     consume = 0.02, the value at which the front is known to travel (188)
    start     a step: the left half excited, so the front runs to the LEFT
    speed     least-squares slope of the contour position over the frames after the
              first third, which removes the window dependence of reading two frames

PREDICTION, before the run:
    (a) with no gradient the speed is the priced baseline, about -0.077 (188);
    (b) with the resource richer toward the LEFT - the direction the front travels -
        the front moves FASTER than the baseline;
    (c) with the resource poorer toward the left, it moves SLOWER.
    (d) the two gradients are the same field mirrored, so the two deviations from the
        baseline must be comparable in size.

If (b) and (c) both hold, the structure goes uphill. If only one holds, the asymmetry
is not a preference but an artefact of the gating, and that is the result.

    python3 checks/front_gradient.py
"""

from __future__ import annotations

import sys

N = 256
DX = 0.25
D = 1.0
DT = 0.01
A_B, B_B = 0.75, 0.02
EPS = 20.0
GROW = 0.2
CONSUME = 0.02
GRAD = 0.3
STEPS = 12000
EVERY = 200


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def run(rich_toward: int):
    """rich_toward = 0 for a flat field, +1 when cell 0 is rich, -1 when cell N-1 is."""
    u = [0.0] * N
    v = [0.0] * N
    for i in range(N // 2):
        u[i] = 1.0
    if rich_toward == 0:
        ceiling = [1.0] * N
    elif rich_toward > 0:
        ceiling = [1.0 - GRAD * (i / (N - 1)) for i in range(N)]
    else:
        ceiling = [1.0 - GRAD * ((N - 1 - i) / (N - 1)) for i in range(N)]
    r = list(ceiling)
    frames = []
    for step in range(STEPS):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = D * lap_line(u, i) + (1.0 / EPS) * u[i] * (1 - u[i]) * (
                u[i] - (v[i] + B_B) / A_B
            ) * r[i]
            nu[i] = min(1.0, max(0.0, u[i] + DT * du))
            nv[i] = v[i] + DT * (u[i] - v[i])
            r[i] = min(1.0, max(0.0, r[i] + GROW * (ceiling[i] - r[i]) * DT - CONSUME * u[i] * DT))
        u, v = nu, nv
        if step % EVERY == 0:
            frames.append(list(u))
    return frames


def contour(u: list[float], level: float = 0.5):
    for i in range(len(u) - 1):
        if (u[i] - level) * (u[i + 1] - level) <= 0 and u[i] != u[i + 1]:
            frac = (level - u[i]) / (u[i + 1] - u[i])
            return (i + frac) * DX
    return None


def slope_speed(frames):
    """Least squares slope of the contour position, after the first third."""
    pts = []
    for k, f in enumerate(frames):
        c = contour(f)
        if c is not None:
            pts.append((k * EVERY * DT, c))
    if len(pts) < 8:
        return None, 0
    pts = pts[len(pts) // 3:]
    n = len(pts)
    sx = sum(t for t, _ in pts)
    sy = sum(x for _, x in pts)
    sxx = sum(t * t for t, _ in pts)
    sxy = sum(t * x for t, x in pts)
    den = n * sxx - sx * sx
    if abs(den) < 1e-12:
        return None, n
    return (n * sxy - sx * sy) / den, n


def main(argv: list[str]) -> int:
    print(f"front under a price and a resource gradient: eps={EPS}, consume={CONSUME}, grad={GRAD}")
    print()

    cases = [("flat", 0), ("rich toward the front (left)", +1), ("poor toward the front", -1)]
    got = {}
    for name, direction in cases:
        speed, n = slope_speed(run(direction))
        got[name] = speed
        shown = "no contour" if speed is None else f"{speed:+.4f}"
        print(f"  {name:32s}: speed={shown:>10}  ({n} frames used)")

    base = got["flat"]
    up = got["rich toward the front (left)"]
    down = got["poor toward the front"]

    print()
    precheck = base is not None and abs(base) > 0.02
    print(f"  PRE-RUN CHECK: the flat baseline moves = {precheck}")
    if not precheck:
        print("  -> the comparison is INVALID: no baseline motion, so nothing about")
        print("     the gradient can be attributed to the gradient.")
        print("РАСХОЖДЕНИЙ: 1")
        return 1

    bad = 0
    checks = [
        ("(a) flat baseline is the priced speed of 188, about -0.077",
         base is not None and abs(base + 0.077) < 0.02, None if base is None else round(base, 4)),
        ("(b) richer ahead -> faster", up is not None and up < base, None if up is None else round(up, 4)),
        ("(c) poorer ahead -> slower", down is not None and down > base, None if down is None else round(down, 4)),
    ]
    if up is not None and down is not None and base is not None:
        d_up = abs(up - base)
        d_down = abs(down - base)
        checks.append(("(d) the two deviations are comparable (mirror symmetry)",
                       max(d_up, d_down) / max(min(d_up, d_down), 1e-9) < 2.0,
                       (round(d_up, 4), round(d_down, 4))))
    print()
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
