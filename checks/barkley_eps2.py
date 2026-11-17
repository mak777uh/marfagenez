"""eps = 2: the medium that actually recovers, and the two checks that were missing.

`FINDING-192` computed the recovery rate (1/eps)*(b/a) and the relaxation time 750 at
eps = 20, against runs of 120 - sixteen percent of the way to rest. That single number
explained eight cycles. The rate is proportional to 1/eps, so eps = 2 gives a relaxation
time of 75, which t = 300 covers four times over.

What is measured here, in the order that the eight failures taught:

    A. the control: the linear decay rate must be (1/eps)*(b/a) = 0.01333 at eps = 2.
       If the instrument moved with the parameter, nothing after this counts.
    B. the back: after a step, does the medium BEHIND the moving level return to rest?
       This is the check FINDING-191 lacked, and its absence produced eight cycles.
    C. the object: does a localised supra-threshold band nucleate a pulse - a bounded
       travelling object with rest on both sides?

    grid      line of 256, dx = 0.25, dt = 0.01, zero flux, eps = 2
    time      t = 300 (30000 steps), profiles read every 1000 steps

PREDICTION:
    (a) the linear rate is 0.01333 within 15%;
    (b) behind the moving level u falls below 0.05 within a few length units, because
        the medium now has time to recover;
    (c) a band of 2 length units nucleates a pulse that travels, with rest both ahead
        of and behind it.

    python3 checks/barkley_eps2.py
"""

from __future__ import annotations

import math
import sys

N = 256
DX = 0.25
DT = 0.01
A, B = 0.75, 0.02
EPS = 2.0
STEPS = 30000
EVERY = 1000


def f(u: float, v: float) -> float:
    return (1.0 / EPS) * u * (1.0 - u) * (u - (v + B) / A)


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def uniform_rate(steps: int = 20000, u0: float = 1e-3):
    u, v = u0, u0
    ts, us = [], []
    for step in range(steps):
        u += DT * f(u, v)
        v += DT * (u - v)
        if step % 200 == 0 and step > 0:
            ts.append(step * DT)
            us.append(abs(u))
    tail = [(t, x) for t, x in zip(ts, us) if x > 1e-12]
    if len(tail) < 6:
        return None
    tail = tail[len(tail) // 2:]
    (t0, x0), (t1, x1) = tail[0], tail[-1]
    if x0 <= 0 or x1 <= 0:
        return None
    return (math.log(x1) - math.log(x0)) / (t1 - t0)


def run_step(u: list[float], v: list[float]):
    nu = [0.0] * N
    nv = [0.0] * N
    for i in range(N):
        nu[i] = min(1.0, max(0.0, u[i] + DT * (lap_line(u, i) + f(u[i], v[i]))))
        nv[i] = v[i] + DT * (u[i] - v[i])
    return nu, nv


def step_case():
    u = [1.0 if i < N // 2 else 0.0 for i in range(N)]
    v = [0.0] * N
    for _ in range(STEPS):
        u, v = run_step(u, v)
    return u, v


def band_case(width: float):
    u = [0.0] * N
    v = [0.0] * N
    half = max(1, int(round(width / (2 * DX))))
    c = N // 2
    for i in range(c - half, c + half + 1):
        u[i] = 1.0
    peaks = []
    for step in range(STEPS):
        u, v = run_step(u, v)
        if step % EVERY == 0:
            peaks.append((step, max(range(N), key=lambda i: u[i])))
    return u, v, peaks


def level(u, target=0.5):
    for i in range(N - 1):
        if u[i] >= target and u[i + 1] < target:
            return i
    return None


def back_distance(u, front, thresh=0.05):
    for d in range(1, N - front):
        if u[min(N - 1, front + d)] < thresh:
            return d * DX
    return None


def main(argv: list[str]) -> int:
    print(f"eps = {EPS}: recovery time {(1 / ((1 / EPS) * (B / A))):.1f}, runs of t = {STEPS * DT:.0f}")
    print()
    bounds = [0.0]

    # A - the control
    predicted = -(1.0 / EPS) * (B / A)
    measured = uniform_rate()
    print(f"  (A) linear decay rate: predicted {predicted:+.6f}  "
          f"measured {'none' if measured is None else f'{measured:+.6f}'}")

    # B - the back
    u, v = step_case()
    front = level(u)
    back = None if front is None else back_distance(u, front)
    print()
    print(f"  (B) after a step at t = {STEPS * DT:.0f}: level at "
          f"{'none' if front is None else f'x = {front * DX:.2f}'}, "
          f"distance behind it to u < 0.05: {back}")
    if front is not None:
        behind = [round(u[min(N - 1, front + k)], 3) for k in (1, 4, 8, 16, 32)]
        ahead = [round(u[max(0, front - k)], 3) for k in (1, 4, 8, 16)]
        print(f"      u behind {behind}, u ahead {ahead}")

    # C - the object
    u3, v3, peaks = band_case(2.0)
    moved = peaks[-1][1] - peaks[len(peaks) // 3][1]
    front3 = level(u3)
    back3 = None if front3 is None else back_distance(u3, front3)
    print()
    print(f"  (C) a band of 2 length units: peak moved {moved} cells in "
          f"t = {STEPS * DT - STEPS * DT / 3:.0f}, amplitude {max(u3) - min(u3):.3f}, "
          f"distance behind the level to u < 0.05: {back3}")

    bad = 0
    checks = [
        ("(A) the linear rate matches (1/eps)*(b/a) at eps = 2",
         measured is not None and abs(measured - predicted) / abs(predicted) < 0.15,
         None if measured is None else round(measured, 6)),
        ("(B) behind the moving level the medium returns to rest",
         back is not None and back <= 8.0, back),
        ("(C) the band nucleates a travelling object", abs(moved) >= 10, moved),
        ("(C) that object has rest on both sides", back3 is not None and back3 <= 8.0, back3),
    ]
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
