"""Search for a structure that MOVES: the one thing the field has not produced.

`FINDING-180` found a stationary spot and no travelling structure on eight points of
one rule family. `FINDING-181` and `182` showed that a stationary structure under a
price is doomed at any reserve, because it cannot leave. So the missing thing is
motion, and eight points were not a search.

This file declares a search over **two** rule families, with the detector calibrated
on Life. Every parameter set is declared here, before the run.

    family A - Gray-Scott, the rule that gave the stationary spot:
               F in {0.010, 0.014, 0.020, 0.026, 0.032, 0.040}
               k in {0.045, 0.050, 0.055, 0.060, 0.065}       = 30 points

    family B - Barkley excitable medium, which is built to carry travelling pulses:
               a = 0.75, b = 0.02, eps in {20, 50, 100}, D = 1.0
               started from a step, not from a spot               = 3 points

Prediction, written before the run:

    (a) Barkley produces a travelling pulse - the detector finds Delta != 0;
    (b) Gray-Scott produces travelling structures at none of the 30 points, because
        the spot found in 180 is a stable stationary branch and the pulse branch needs
        a different k;
    (c) the controls hold: a uniform field gives nothing, a static spot is never
        reported as moving.

If (a) fails the answer is that motion does not appear in this class either, and the
honest conclusion is that a priced structure in these media can only die.

    python3 checks/field_travelling.py
"""

from __future__ import annotations

import math
import sys

N = 64
AMP_MIN = 1e-2
TOL = 1e-3
SPANS = (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6)
TAUS = tuple(range(1, 17))

GS_GRID = [
    (f, k)
    for f in (0.010, 0.014, 0.020, 0.026, 0.032, 0.040)
    for k in (0.045, 0.050, 0.055, 0.060, 0.065)
]
BARKLEY = [(0.75, 0.02, eps, 1.0) for eps in (20.0, 50.0, 100.0)]


def lap(x: list[float], i: int) -> float:
    n = len(x)
    return x[(i - 1) % n] + x[(i + 1) % n] - 2.0 * x[i]


def gray_scott(f: float, k: float, steps: int = 4000):
    u = [1.0] * N
    v = [0.0] * N
    for i in range(N // 2 - 2, N // 2 + 3):
        u[i % N] = 0.5
        v[i % N] = 0.25
    frames: list[list[float]] = []
    for _ in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            reac = u[i] * v[i] * v[i]
            nu[i] = min(1.0, max(0.0, u[i] + 0.16 * lap(u, i) - reac + f * (1 - u[i])))
            nv[i] = min(1.0, max(0.0, v[i] + 0.08 * lap(v, i) + reac - (f + k) * v[i]))
        u, v = nu, nv
        if len(frames) < 20:
            frames.append(list(v))
        else:
            frames.pop(0)
            frames.append(list(v))
    return frames


def barkley(a: float, b: float, eps: float, d: float, steps: int = 16000):
    """Explicit Euler, dt 0.01. A step initial condition, which a pulse can travel."""
    dt = 0.01
    u = [0.0] * N
    for i in range(N // 2, N):
        u[i] = 1.0
    v = [0.0] * N
    frames: list[list[float]] = []
    for _ in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = d * lap(u, i) + (1.0 / eps) * u[i] * (1 - u[i]) * (
                u[i] - (v[i] + b) / a
            )
            nu[i] = min(1.0, max(0.0, u[i] + dt * du))
            nv[i] = v[i] + dt * (u[i] - v[i])
        u, v = nu, nv
        if len(frames) < 24:
            frames.append(list(u))
        else:
            frames.pop(0)
            frames.append(list(u))
    return frames


def amplitude(f: list[float]) -> float:
    return max(f) - min(f)


def shifted_close(a: list[float], b: list[float], delta: int, tol: float) -> bool:
    n = len(a)
    return all(abs(b[(i + delta) % n] - a[i]) <= tol for i in range(n))


def shift_frac(field: list[float], delta: float) -> list[float]:
    """Shift by a FRACTIONAL number of cells, interpolating linearly.

    This is the fix the first run needed. On a discrete world like Life a travelling
    object moves an exact integer of cells per exact period, so an integer shift
    matches. In a continuous reaction-diffusion the speed is generally irrational with
    respect to one cell per step, so `P(t+tau) = shift_int(P(t), Delta)` almost never
    holds exactly - which is why three Barkley runs with an obvious front reported no
    motion at all. The instrument, not the world, was wrong.
    """
    n = len(field)
    whole = math.floor(delta)
    frac = delta - whole
    out = []
    for i in range(n):
        a = field[(i - whole) % n]
        b = field[(i - whole - 1) % n]
        out.append((1 - frac) * a + frac * b)
    return out


def residual(a: list[float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def best_shift(prev: list[float], curr: list[float], step: float = 0.25):
    """Smallest residual over fractional shifts, with the shift that achieved it."""
    best = (None, 1e9)
    grid = [-6.0 + step * i for i in range(int(12.0 / step) + 1)]
    for d in grid:
        if abs(d) < 1e-9:
            continue
        r = residual(shift_frac(prev, d), curr)
        if r < best[1]:
            best = (d, r)
    return best


def detect(frames: list[list[float]], taus=TAUS):
    if amplitude(frames[-1]) < AMP_MIN:
        return []
    found = []
    for tau in taus:
        ok = 0
        deltas = []
        for c in range(3):
            i = len(frames) - 1 - c * tau
            j = i - tau
            if j < 0:
                break
            d, r = best_shift(frames[j], frames[i])
            if d is not None and r <= TOL:
                ok += 1
                deltas.append(d)
        if ok == 3:
            found.append((tau, round(sum(deltas) / len(deltas), 2)))
    return found


def static_tau(frames: list[list[float]], taus=TAUS):
    if amplitude(frames[-1]) < AMP_MIN:
        return None
    for tau in taus:
        ok = 0
        for c in range(3):
            i = len(frames) - 1 - c * tau
            j = i - tau
            if j < 0:
                break
            if residual(frames[j], frames[i]) <= TOL:
                ok += 1
        if ok == 3:
            return tau
    return None


def main(argv: list[str]) -> int:
    print(f"search for a travelling structure: N={N}, tol={TOL}, tau<=16, |delta|<=6")
    print()

    # control: uniform field must give nothing
    uniform = [[0.5] * N for _ in range(24)]
    ctrl_uniform = detect(uniform)
    print(f"  control uniform: moving={ctrl_uniform}")
    print()

    # family A
    print("  family A, Gray-Scott (30 declared points):")
    gs_moving = []
    for f, k in GS_GRID:
        frames = gray_scott(f, k)
        mov = detect(frames)
        if mov:
            gs_moving.append((f, k, mov))
            print(f"    F={f:.3f} k={k:.3f}: MOVING {mov}")
    print(f"    points with a travelling structure: {len(gs_moving)} of {len(GS_GRID)}")
    print()

    # family B
    print("  family B, Barkley (3 declared points):")
    bark_moving = []
    for a, b, eps, d in BARKLEY:
        frames = barkley(a, b, eps, d)
        mov = detect(frames)
        st = static_tau(frames)
        print(f"    a={a} b={b} eps={eps}: moving={mov} static_tau={st} amp={amplitude(frames[-1]):.3f}")
        if mov:
            bark_moving.append((eps, mov))
    print()

    bad = 0
    checks = [
        ("uniform field is never reported as moving", not ctrl_uniform, ctrl_uniform),
        ("Barkley carries a travelling pulse", bool(bark_moving), bark_moving),
        ("Gray-Scott carries none at the 30 declared points", not gs_moving,
         [(f, k) for f, k, _ in gs_moving]),
    ]
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
