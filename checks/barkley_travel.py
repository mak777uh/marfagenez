"""Get the Barkley pulse to travel, or find out why it does not.

`FINDING-183` failed its own positive control: the impulse decayed to an exactly
stationary state and the residual at zero shift was 0.0000. Reading my own
implementation again, the likely cause is not the rule but the **window**: a pulse on a
ring of 64 cells wraps around and annihilates on itself, and I only kept the last 24
frames - that is, the tail after the collision, when the field is uniform and dead.

So this file records frames *during* the travelling phase and looks there. Everything
is declared before the run.

    rule      Barkley: u_t = (1/eps) u(1-u)(u - (v+b)/a) + D lap(u),  v_t = u - v
    grid      ring of 64, dt = 0.01, D = 1.0, Euler
    start     a localised block of width 3, u = 1
    window    frames every 200 steps from step 2000 to 14000 (60 frames)
    detector  fractional shift, and the shift must beat standing still by 3x

Prediction: at eps = 20 and 50 a travelling pulse is found, with a shift per frame of
the order of 0.1-1 cell, and the same speed inferred from different frame lags. At
eps = 10 the medium is less excitable and may not sustain it.

    python3 checks/barkley_travel.py
"""

from __future__ import annotations

import math
import sys

N = 64
DT = 0.01
D = 1.0
A, B = 0.75, 0.02
STEPS = 14000
RECORD_FROM = 2000
EVERY = 200
WIDTH = 3
TOL = 2e-3
BEAT = 3.0     # the shift must explain the step this many times better than standing
AMP_MIN = 0.2  # a real excited pulse has a much larger range than a ripple


def lap(x: list[float], i: int) -> float:
    n = len(x)
    return x[(i - 1) % n] + x[(i + 1) % n] - 2.0 * x[i]


def run(eps: float) -> list[list[float]]:
    u = [0.0] * N
    v = [0.0] * N
    for i in range(N // 2 - WIDTH, N // 2 + WIDTH + 1):
        u[i % N] = 1.0
    frames: list[list[float]] = []
    for step in range(STEPS):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = D * lap(u, i) + (1.0 / eps) * u[i] * (1 - u[i]) * (u[i] - (v[i] + B) / A)
            nu[i] = min(1.0, max(0.0, u[i] + DT * du))
            nv[i] = v[i] + DT * (u[i] - v[i])
        u, v = nu, nv
        if step >= RECORD_FROM and (step - RECORD_FROM) % EVERY == 0:
            frames.append(list(u))
    return frames


def shift_frac(field: list[float], delta: float) -> list[float]:
    n = len(field)
    whole = math.floor(delta)
    frac = delta - whole
    return [
        (1 - frac) * field[(i - whole) % n] + frac * field[(i - whole - 1) % n]
        for i in range(n)
    ]


def resid(a: list[float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def best(prev: list[float], curr: list[float]):
    best_d, best_r = None, 1e9
    d = -6.0
    while d <= 6.0:
        if abs(d) > 1e-9:
            r = resid(shift_frac(prev, d), curr)
            if r < best_r:
                best_d, best_r = d, r
        d += 0.05
    return best_d, best_r


def analyse(frames: list[list[float]]):
    """Speed from consecutive frames and from a longer lag, plus the beat ratio."""
    amp = max(frames[-1]) - min(frames[-1])
    results = []
    for lag in (1, 2, 4):
        if len(frames) <= lag:
            continue
        prev, curr = frames[-1 - lag], frames[-1]
        r0 = resid(prev, curr)
        d, r = best(prev, curr)
        if d is None:
            continue
        beat = r0 / r if r > 1e-12 else float("inf")
        results.append((lag, d, r, beat, d / lag))
    return amp, results


def main(argv: list[str]) -> int:
    print(f"Barkley on a ring of {N}: frames from step {RECORD_FROM} every {EVERY}")
    print()
    checks = []
    for eps in (10.0, 20.0, 50.0):
        frames = run(eps)
        amp, results = analyse(frames)
        speeds = [s for _, d, r, beat, s in results if beat > BEAT and amp > AMP_MIN]
        print(f"  eps={eps:5.1f}: amp={amp:.3f}")
        for lag, d, r, beat, speed in results:
            print(f"      lag={lag}: shift={d:+.2f} residual={r:.5f} beat={beat:6.1f} "
                  f"speed={speed:+.4f} cells/frame")
        moving = bool(speeds)
        print(f"      -> {'TRAVELLING' if moving else 'stationary'}")
        checks.append((f"eps={eps:g}: a travelling pulse is found", moving, speeds))
        if len(speeds) > 1:
            spread = max(speeds) - min(speeds)
            checks.append((f"eps={eps:g}: the speed agrees across lags", spread < 0.05, round(spread, 4)))
        print()

    bad = 0
    for label, ok, got in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{got}]")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Положительный контроль сработал: детектор видит заведомо движущийся импульс.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
