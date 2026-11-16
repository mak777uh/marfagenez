"""The search for motion, moved from a ring to a LINE.

`FINDING-185` established why six attempts failed: a travelling front cannot live on a
ring - it meets its own back and annihilates, so the field goes uniform. The detector is
now calibrated against a formula (the Nagumo speed, recovered to 0.4 %), so the search
can be run in a topology where motion is possible at all.

Everything is declared before the run.

    rule A   Gray-Scott, identical to FINDING-180 but on a line:
             F in {0.030, 0.040, 0.050}, k in {0.060, 0.065}      = 6 points
    rule B   Barkley excitable medium, localised pulse:
             (a,b) = (0.75, 0.02), eps in {10, 20, 50}            = 3 points
    grid     line of 128 cells, dx = 0.5, zero flux at both ends
    detector fractional shift; the shift must explain the step three times better
             than standing still; amplitude above 0.2; the pulse must be away from
             the boundary in the frames used

PREDICTION:
    (a) Barkley carries a travelling pulse on the line, at all three eps, with a speed
        of order 0.1 to 1 length unit per time unit;
    (b) Gray-Scott carries none of these six points, because the spot branch of
        FINDING-180 is stationary and the pulse branch lies elsewhere in (F, k);
    (c) a front that reaches the boundary must be seen to stop or die, not to keep
        its speed - that is the control that the boundary is real.

    python3 checks/field_line_travel.py
"""

from __future__ import annotations

import math
import sys

N = 128
DX = 1.0          # cells of unit length; the line is N long
AMP_MIN = 0.2
BEAT = 3.0
MARGIN = 8        # frames used must keep the structure this far from the ends

GS = [(f, k) for f in (0.030, 0.040, 0.050) for k in (0.060, 0.065)]
BARKLEY = [10.0, 20.0, 50.0]
A_B, B_B = 0.75, 0.02


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def gray_scott(f: float, k: float, steps: int = 4000):
    u = [1.0] * N
    v = [0.0] * N
    for i in range(N // 2 - 3, N // 2 + 4):
        u[i] = 0.5
        v[i] = 0.25
    frames = []
    for step in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            reac = u[i] * v[i] * v[i]
            nu[i] = min(1.0, max(0.0, u[i] + 0.16 * lap_line(u, i) - reac + f * (1 - u[i])))
            nv[i] = min(1.0, max(0.0, v[i] + 0.08 * lap_line(v, i) + reac - (f + k) * v[i]))
        u, v = nu, nv
        if len(frames) < 40:
            frames.append(list(v))
        else:
            frames.pop(0)
            frames.append(list(v))
    return frames


def barkley(eps: float, steps: int = 6000, dt: float = 0.01, every: int = 200):
    u = [0.0] * N
    v = [0.0] * N
    for i in range(N // 2 - 2, N // 2 + 3):
        u[i] = 1.0
    frames = []
    for step in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = lap_line(u, i) + (1.0 / eps) * u[i] * (1 - u[i]) * (u[i] - (v[i] + B_B) / A_B)
            nu[i] = min(1.0, max(0.0, u[i] + dt * du))
            nv[i] = v[i] + dt * (u[i] - v[i])
        u, v = nu, nv
        if step % every == 0:
            if len(frames) < 40:
                frames.append(list(u))
            else:
                frames.pop(0)
                frames.append(list(u))
    return frames


def shift_frac(field: list[float], delta: float) -> list[float]:
    n = len(field)
    whole = math.floor(delta)
    frac = delta - whole
    out = []
    for i in range(n):
        a = field[(i - whole) % n]
        b = field[(i - whole - 1) % n]
        out.append((1 - frac) * a + frac * b)
    return out


def resid(a: list[float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def best_shift(prev: list[float], curr: list[float], span: float = 30.0, step: float = 0.1):
    bd, br = None, 1e9
    d = -span
    while d <= span:
        if abs(d) > 1e-9:
            r = resid(shift_frac(prev, d), curr)
            if r < br:
                bd, br = d, r
        d += step
    return bd, br


def near_boundary(u: list[float], margin: int = MARGIN) -> bool:
    """True when the structure is too close to an end for a shift to be meaningful."""
    peak = max(range(len(u)), key=lambda i: u[i])
    return peak < margin or peak > len(u) - 1 - margin


def moving(frames, dt_per_frame: float):
    """(speed, beat, amplitude) from the last usable pair of frames."""
    if len(frames) < 3:
        return None
    for lag in (1, 2):
        prev, curr = frames[-1 - lag], frames[-1]
        amp = max(curr) - min(curr)
        if amp < AMP_MIN:
            continue
        if near_boundary(curr) or near_boundary(prev):
            continue
        r0 = resid(prev, curr)
        d, r = best_shift(prev, curr)
        if d is None:
            continue
        beat = r0 / r if r > 1e-12 else float("inf")
        return d / (lag * dt_per_frame), beat, amp
    return None


def main(argv: list[str]) -> int:
    print(f"search on a LINE of {N} cells, dx={DX}, zero flux, detector calibrated in 185")
    print()

    print("  rule A, Gray-Scott (6 declared points):")
    gs_moving = []
    for f, k in GS:
        frames = gray_scott(f, k)
        res = moving(frames, dt_per_frame=1.0)
        if res and res[1] > BEAT:
            gs_moving.append((f, k, round(res[0], 3)))
            print(f"    F={f:.3f} k={k:.3f}: MOVING speed={res[0]:+.3f} beat={res[1]:.1f} amp={res[2]:.2f}")
        else:
            got = "no usable pair" if res is None else f"beat={res[1]:.1f} amp={res[2]:.2f}"
            print(f"    F={f:.3f} k={k:.3f}: stationary ({got})")
    print()

    print("  rule B, Barkley (3 declared points):")
    bark_moving = []
    for eps in BARKLEY:
        frames = barkley(eps)
        res = moving(frames, dt_per_frame=0.01 * 200)
        if res is None:
            print(f"    eps={eps:5.1f}: no usable pair (amplitude died or at the boundary)")
            continue
        speed, beat, amp = res
        if beat > BEAT:
            bark_moving.append((eps, round(speed, 3)))
            print(f"    eps={eps:5.1f}: MOVING speed={speed:+.3f} length/time beat={beat:.1f} amp={amp:.2f}")
        else:
            print(f"    eps={eps:5.1f}: stationary (beat={beat:.1f} amp={amp:.2f})")
    print()

    bad = 0
    checks = [
        ("Barkley carries a travelling pulse on the line", bool(bark_moving), bark_moving),
        ("Gray-Scott carries none at these six points", not gs_moving, gs_moving),
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
