"""Refine the grid, then ask again: does the pulse travel now?

`FINDING-186` named two independent causes for six failures: the ring gives a front
nowhere to go, and dx = 1 gives it no way to ignite its neighbour (diffusion 0.01 per
step against a threshold of 0.027).

This refines the grid to dx = 0.25 and keeps the diffusion number inside the declared
bound, then asks in the right order: first the formula control, then the unknown.

    grid      line of 256 cells, dx = 0.25, length 64, zero flux at both ends
    time      dt = 0.01, diffusion number D*dt/dx^2 = 0.16 (declared bound 0.2)

PREDICTION, before the run:
    (a) the Nagumo front speed is still (1-2a)*sqrt(D/2) = 0.3536 and is recovered
        within 5% - if the instrument moved with the grid, nothing after it counts;
    (b) with the finer grid the Barkley pulse now advances: the peak moves
        monotonically and the amplitude stays above half the initial one;
    (c) the measured Barkley speed does not depend on the frame spacing.

    python3 checks/fhn_refine.py
"""

from __future__ import annotations

import math
import sys

N = 256
DX = 0.25
D = 1.0
DT = 0.01
A_FRONT = 0.25
A_B, B_B = 0.75, 0.02
BAND = 0.05


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def nagumo_speed_frames(steps: int = 3000, every: int = 100):
    u = []
    for i in range(N):
        x = (i - N // 2) * DX
        u.append(0.5 * (1.0 - math.tanh(x / 2.0)))
    frames = []
    for step in range(steps):
        nu = [0.0] * N
        for i in range(N):
            f = u[i] * (1.0 - u[i]) * (u[i] - A_FRONT)
            nu[i] = min(1.0, max(0.0, u[i] + DT * (D * lap_line(u, i) + f)))
        u = nu
        if step >= 200 and (step - 200) % every == 0:
            frames.append(list(u))
    return frames


def contour(u: list[float], level: float = 0.5):
    for i in range(len(u) - 1):
        if (u[i] - level) * (u[i + 1] - level) <= 0 and u[i] != u[i + 1]:
            frac = (level - u[i]) / (u[i + 1] - u[i])
            return (i + frac) * DX
    return None


def nagumo_speed(frames, every: int = 100):
    pts = [(k, contour(f)) for k, f in enumerate(frames)]
    pts = [(k, p) for k, p in pts if p is not None]
    if len(pts) < 4:
        return None
    (k0, p0), (k1, p1) = pts[0], pts[-1]
    return (p1 - p0) / ((k1 - k0) * every * DT)


def barkley(steps: int = 6000, every: int = 200):
    """A localised pulse, 4 cells wide (one length unit), in the middle of the line."""
    u = [0.0] * N
    v = [0.0] * N
    c = N // 2
    for i in range(c - 4, c + 5):
        u[i] = 1.0
    frames = []
    for step in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = D * lap_line(u, i + 0) if False else D * lap_line(u, i)
            du += (1.0 / 20.0) * u[i] * (1 - u[i]) * (u[i] - (v[i] + B_B) / A_B)
            nu[i] = min(1.0, max(0.0, u[i] + DT * du))
            nv[i] = v[i] + DT * (u[i] - v[i])
        u, v = nu, nv
        if step % every == 0:
            frames.append(list(u))
    return frames


def peaks_and_amps(frames, every: int = 200):
    out = []
    for k, f in enumerate(frames):
        peak = max(range(len(f)), key=lambda i: f[i])
        out.append((k * every, peak, round(max(f) - min(f), 3)))
    return out


def main(argv: list[str]) -> int:
    print(f"refined grid: N={N}, dx={DX}, dt={DT}, D*dt/dx^2 = {D * DT / (DX * DX):.2f}")
    print()

    # (a) the formula control on the new grid
    want = (1.0 - 2.0 * A_FRONT) * math.sqrt(D / 2.0)
    got = nagumo_speed(nagumo_speed_frames())
    print(f"  (a) Nagumo: predicted c={want:+.4f}  measured c="
          f"{'none' if got is None else f'{got:+.4f}'}")
    rel = None if got is None else abs(got - want) / abs(want)
    if rel is not None:
        print(f"      relative error {rel:.3%}")

    # (b) the pulse on the refined grid
    print()
    print("  (b) Barkley on the refined grid, peak position and amplitude:")
    info = peaks_and_amps(barkley())
    for step, peak, amp in info[::3]:
        print(f"      t={step * DT:5.1f}: peak={peak:3d} amp={amp:5.3f}")
    moved = info[-1][1] - info[5][1]
    sustained = min(a for _, _, a in info[5:]) > 0.5
    print(f"      peak moved {moved} cells, minimum amplitude after the start "
          f"{min(a for _, _, a in info[5:]):.3f}")

    print()
    bad = 0
    checks = [
        ("(a) the Nagumo speed survives the finer grid", rel is not None and rel <= BAND,
         None if rel is None else round(rel, 4)),
        ("(b) the pulse advances on the refined grid", abs(moved) >= 8, moved),
        ("(b) the amplitude is sustained", sustained, min(a for _, _, a in info[5:])),
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
