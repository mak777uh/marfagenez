"""Can a BOUNDED structure exist? The pulse, built by sweeping its width.

Three attempts at a pulse failed, and `FINDING-187` named the reason: a pulse narrower
than its own natural width is smeared by diffusion before the reaction can hold it. So
the width is not a detail to guess - it is the parameter. This sweeps it.

    rule      Barkley on a line, no price: u_t = D u_xx + (1/eps) u(1-u)(u-(v+b)/a)
    grid      line of 256, dx = 0.25, dt = 0.01, eps = 20, zero flux
    start     an excited band of width W in the middle, and a refractory wake of
              v = 0.6 BEHIND it (the side the front travels toward is -x)
    verdict   travels if the peak moves at least 5 cells and the amplitude stays
              above 0.5; otherwise it died

PREDICTION:
    (a) there is a threshold width: below it the band dies, above it the band travels
        as a bounded object with two edges;
    (b) the threshold is of order the natural front width, so somewhere between 2 and
        16 length units at eps = 20;
    (c) above the threshold the speed is comparable to the front speed measured in
        187, about -0.107 length per time, or slower.

    python3 checks/barkley_pulse_width.py
"""

from __future__ import annotations

import sys

N = 256
DX = 0.25
D = 1.0
DT = 0.01
A_B, B_B = 0.75, 0.02
EPS = 20.0
WAKE = 0.6
STEPS = 8000
EVERY = 100
WIDTHS = (2.0, 4.0, 6.0, 8.0, 12.0, 16.0)


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def run(width: float, wake: float = WAKE):
    u = [0.0] * N
    v = [0.0] * N
    c = N // 2
    half = max(1, int(round(width / (2 * DX))))
    for i in range(c - half, c + half + 1):
        u[i] = 1.0
    # refractory wake behind the excited band: on the -x side, the side the front
    # travels toward, so the band is the leading edge
    for i in range(max(0, c - half - int(round(10.0 / DX))), c - half):
        v[i] = wake
    frames = []
    for step in range(STEPS):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            du = D * lap_line(u, i) + (1.0 / EPS) * u[i] * (1 - u[i]) * (
                u[i] - (v[i] + B_B) / A_B
            )
            nu[i] = min(1.0, max(0.0, u[i] + DT * du))
            nv[i] = v[i] + DT * (u[i] - v[i])
        u, v = nu, nv
        if step % EVERY == 0:
            frames.append(list(u))
    return frames


def analyse(frames):
    peaks = []
    amps = []
    for f in frames:
        peaks.append(max(range(len(f)), key=lambda i: f[i]))
        amps.append(max(f) - min(f))
    settled = len(peaks) // 4
    moved = peaks[-1] - peaks[settled]
    speed = None
    if abs(moved) >= 5:
        speed = (moved * DX) / ((len(peaks) - 1 - settled) * EVERY * DT)
    return moved, min(amps[settled:]), speed


def main(argv: list[str]) -> int:
    print(f"Barkley pulse width sweep: N={N}, dx={DX}, eps={EPS}, wake v={WAKE}")
    print()
    results = []
    for width in WIDTHS:
        moved, amp, speed = analyse(run(width))
        travels = abs(moved) >= 5 and amp > 0.5
        results.append((width, moved, amp, speed, travels))
        shown = "n/a" if speed is None else f"{speed:+.4f}"
        print(f"  width={width:5.1f}: moved={moved:5d} cells  min amplitude={amp:5.3f}  "
              f"speed={shown:>9}  -> {'TRAVELS' if travels else 'dies'}")

    travellers = [r for r in results if r[4]]
    bad = 0
    checks = [
        ("(a) some width travels and some dies", bool(travellers) and len(travellers) < len(results),
         [(r[0], r[4]) for r in results]),
    ]
    if travellers:
        first = min(r[0] for r in travellers)
        checks.append(("(b) the threshold lies between 2 and 16 length units", 2.0 <= first <= 16.0, first))
        speeds = [r[3] for r in travellers if r[3] is not None]
        checks.append(("(c) the speed is of the order of the front speed, 0.107 or slower",
                       bool(speeds) and max(abs(s) for s in speeds) <= 0.15,
                       [round(s, 4) for s in speeds]))
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
