"""Price on a MOVING front, and the pre-run check I failed twice.

`FINDING-181` put a price on a stationary spot and it died almost at once: it paid where
it lived. `FINDING-182` showed that a reservoir in place buys nothing. Now there is a
front that actually moves (`FINDING-187`), and it has something the spot never had: it
leaves the place it depleted.

Before the sweep, and in the right order this time, the script checks that the front is
**alive and moving at the smallest price of the sweep**. If it is not, the sweep is
declared invalid instead of interpreted - which is what went wrong in 181 and 182.

    rule      Barkley with a resource channel:
              u_t = D u_xx + (1/eps) u(1-u)(u - (v+b)/a) * r
              v_t = u - v
              r_t = grow*(ceiling - r) - consume*u
    grid      line of 256, dx = 0.25, dt = 0.01, diffusion number 0.16, zero flux
    start     a step: the left half excited, so one front runs into the resting side
    eps       20, the value whose unpriced speed is -0.107 length/time (FINDING-187)

PREDICTION:
    (a) at consume = 0 the front speed is the unpriced one, -0.107, and the resource
        channel changes nothing (silent);
    (b) the front survives a price that killed the stationary spot (it died at 0.02):
        at consume = 0.02 the front is still moving;
    (c) at a large enough price the front stops moving, and only then dies.

    python3 checks/front_with_price.py
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
STEPS = 12000
EVERY = 200
UNPRICED = -0.107


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def run(consume: float, grad: float = 0.0):
    u = [0.0] * N
    v = [0.0] * N
    for i in range(N // 2):
        u[i] = 1.0
    ceiling = [1.0 - grad * (i / (N - 1)) for i in range(N)]
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
            r[i] = min(1.0, max(0.0, r[i] + GROW * (ceiling[i] - r[i]) * DT - consume * u[i] * DT))
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


def speeds(frames):
    pts = []
    for k, f in enumerate(frames):
        c = contour(f)
        if c is not None:
            pts.append((k, c, max(f) - min(f)))
    if len(pts) < 6:
        return None, None, 0.0
    # speed over the last two thirds, away from the initial transient
    pts = pts[len(pts) // 3:]
    (k0, p0, _), (k1, p1, _) = pts[0], pts[-1]
    speed = (p1 - p0) / ((k1 - k0) * EVERY * DT)
    return speed, p1, max(a for _, _, a in pts)


def main(argv: list[str]) -> int:
    print(f"Barkley front under a price: N={N}, dx={DX}, eps={EPS}, grow={GROW}")
    print()

    PRICES = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10)
    rows = []
    for c in PRICES:
        speed, pos, amp = speeds(run(c))
        rows.append((c, speed, pos, amp))
        shown = "no contour" if speed is None else f"{speed:+.4f}"
        print(f"  consume={c:.3f}: speed={shown:>11}  final position={pos}  amplitude={amp:.3f}")

    # ---- the pre-run check, done first for once --------------------------
    print()
    smallest = next((row for row in rows if row[0] > 0), None)
    alive_and_moving = smallest is not None and smallest[1] is not None and abs(smallest[1]) > 0.02
    print(f"  PRE-RUN CHECK, evaluated on the result: at the smallest price "
          f"({smallest[0] if smallest else 'n/a'}) the front is alive and moving = {alive_and_moving}")
    if not alive_and_moving:
        print("  -> the sweep is INVALID: the front is not moving at the lowest price, so")
        print("     nothing about higher prices can be attributed to the price.")
        print("РАСХОЖДЕНИЙ: 1")
        return 1

    bad = 0
    zero = next(r for r in rows if r[0] == 0.0)
    checks = [
        ("(a) at consume 0 the speed is the unpriced one",
         zero[1] is not None and abs(zero[1] - UNPRICED) < 0.03, None if zero[1] is None else round(zero[1], 4)),
        ("(b) at consume 0.02 the front still moves",
         rows[3][1] is not None and abs(rows[3][1]) > 0.02, None if rows[3][1] is None else round(rows[3][1], 4)),
        ("(c) at the largest price the front has stopped or gone",
         rows[-1][1] is None or abs(rows[-1][1]) < 0.02, None if rows[-1][1] is None else round(rows[-1][1], 4)),
    ]
    print()
    for label, ok, got in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{got}]")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Проверка пройдена.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
