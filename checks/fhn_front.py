"""The Nagumo front speed, measured on a LINE, where a front can actually exist.

`checks/fhn_front.py` failed for a reason that has nothing to do with the rule: a
travelling front cannot live on a ring. On a closed domain the front meets its own back
and annihilates, so the field becomes uniform - which is exactly what the first version
measured (amplitude 0.00 at a = 0.25).

This version uses a line with zero-flux ends, where a front has room, and measures the
position of the u = 0.5 contour rather than shifting the whole profile.

    rule      u_t = D u_xx + u(1-u)(u-a),  D = 1
    grid      line of 128 cells, dx = 0.5, zero flux at both ends
    time      dt = 0.05, 1600 steps, the contour tracked every 100 steps
    speed     c = (1 - 2a) * sqrt(D / 2)

PREDICTION, before the run:
    a = 0.25 -> c = +0.3536, the contour moves one way
    a = 0.75 -> c = -0.3536, the same magnitude the other way
    a = 0.50 -> c = 0, and the contour must stay put
The lattice deviates by O(dx^2); the check is a 20% band plus the sign, and the
deviation is printed rather than hidden.

    python3 checks/fhn_front.py
"""

from __future__ import annotations

import math
import sys

N = 128
DX = 0.5
D = 1.0
DT = 0.05
STEPS = 1600
EVERY = 100
START_AT = 200
WIDTH = 2.0
TOL_BAND = 0.20


def predicted(a: float, d: float = D) -> float:
    return (1.0 - 2.0 * a) * math.sqrt(d / 2.0)


def lap_line(x, i):
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def initial():
    u = []
    for i in range(N):
        x = (i - N // 2) * DX
        u.append(0.5 * (1.0 - math.tanh(x / WIDTH)))
    return u


def run(a, dt=DT, steps=STEPS):
    u = initial()
    frames = []
    for step in range(steps):
        nu = [0.0] * N
        for i in range(N):
            f = u[i] * (1.0 - u[i]) * (u[i] - a)
            nu[i] = min(1.0, max(0.0, u[i] + dt * (D * lap_line(u, i) + f)))
        u = nu
        if step >= START_AT and (step - START_AT) % EVERY == 0:
            frames.append(list(u))
    return frames


def contour(u, level=0.5):
    for i in range(len(u) - 1):
        if (u[i] - level) * (u[i + 1] - level) <= 0 and u[i] != u[i + 1]:
            frac = (level - u[i]) / (u[i + 1] - u[i])
            return (i + frac) * DX
    return None


def speed_of(frames, every=EVERY, dt=DT):
    positions = [(k, contour(f)) for k, f in enumerate(frames)]
    positions = [(k, p) for k, p in positions if p is not None]
    if len(positions) < 4:
        return None
    (k0, p0), (k1, p1) = positions[0], positions[-1]
    return (p1 - p0) / ((k1 - k0) * every * dt)


def main(argv):
    print(f"Nagumo front on a LINE of {N} cells, dx={DX}, dt={DT}, length {N * DX}")
    print()
    checks = []
    for a in (0.25, 0.75, 0.50):
        frames = run(a)
        c = speed_of(frames)
        want = predicted(a)
        amp = max(frames[-1]) - min(frames[-1])
        shown = "none" if c is None else f"{c:+.4f}"
        print(f"  a={a:.2f}: predicted c={want:+.4f}  measured c={shown}  (amplitude {amp:.2f})")
        if a == 0.50:
            checks.append(("a=0.50: the front stays put", c is not None and abs(c) < 0.02, c))
        elif c is None:
            checks.append((f"a={a:.2f}: the front is found", False, None))
        else:
            rel = abs(c - want) / abs(want)
            checks.append((f"a={a:.2f}: speed within {TOL_BAND:.0%} of the formula", rel <= TOL_BAND, round(rel, 3)))
            checks.append((f"a={a:.2f}: the sign is right", (c > 0) == (want > 0), c))
    c_small = speed_of(run(0.25, dt=0.01), dt=0.01)
    if c_small is not None:
        print(f"  dt 0.01: c={c_small:+.4f}")
        rel = abs(c_small - predicted(0.25)) / predicted(0.25)
        checks.append(("with a smaller dt the speed stays inside the band", rel <= TOL_BAND, round(rel, 3)))

    print()
    bad = 0
    for label, ok, got in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{got}]")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Положительный контроль пройден: детектор восстанавливает предсказанную скорость.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
