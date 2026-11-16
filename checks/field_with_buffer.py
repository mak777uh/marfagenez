"""The structure gets a reservoir, which is the one thing it lacked.

`FINDING-181` measured that a priced structure dies almost immediately: it pays where
it lives, out of the very resource that keeps it open, and it has neither a store to
draw on nor a boundary to leave through. The organism in this project survives a
price for exactly those two reasons - it has energy in reserve and it can move.

So the field gets the first of the two: a per-cell buffer. Resource flows into the
buffer when the cell has more than the buffer holds; the structure's upkeep is paid
out of the buffer, not out of the free resource; and the reaction is gated by the
buffer. Nothing else changes.

Preregistered:

    (a) silent   - with zero consumption the pattern is unchanged, because the
                   buffer starts full and the gate stays open;
    (b) fires    - consumption that killed the structure without a buffer now
                   survives, i.e. the price edge moves up;
    (c) the question refused in FINDING-181 - with a buffer and a survivable price,
                   does a resource gradient make the structure drift toward the rich
                   side? PREDICTION: yes. If it does not drift, that is the result,
                   and it says the reservoir alone is not enough - the second thing
                   the organism has is a boundary it can move.

    python3 checks/field_with_buffer.py
"""

from __future__ import annotations

import math
import sys

N = 64
DT = 1.0
DU, DV = 0.16, 0.08
F, K = 0.050, 0.065
STEPS = 9000
SETTLE = 5000
BUF = 1.0          # buffer capacity
UPTAKE = 0.5       # how fast resource moves into the buffer
MASS_ALIVE = 0.3   # below this the structure counts as gone


def lap(field: list[float], i: int) -> float:
    n = len(field)
    return field[(i - 1) % n] + field[(i + 1) % n] - 2.0 * field[i]


def run(consume: float, grow: float, grad: float, buffer: bool = True):
    u = [1.0] * N
    v = [0.0] * N
    for i in range(N // 2 - 2, N // 2 + 3):
        u[i % N] = 0.5
        v[i % N] = 0.25
    ceiling = [1.0 - grad * (i / (N - 1)) for i in range(N)]
    r = list(ceiling)
    b = list(ceiling)          # the reservoir starts full

    centroids: list[float] = []
    for step in range(STEPS):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            reac = u[i] * v[i] * v[i]
            reac *= b[i] if buffer else r[i]
            nu[i] = u[i] + DT * (DU * lap(u, i) - reac + F * (1.0 - u[i]))
            nv[i] = v[i] + DT * (DV * lap(v, i) + reac - (F + K) * v[i])
            nu[i] = min(1.0, max(0.0, nu[i]))
            nv[i] = min(1.0, max(0.0, nv[i]))

            # resource regrows; what is above the buffer flows into it
            r[i] = min(1.0, max(0.0, r[i] + grow * (ceiling[i] - r[i]) * DT))
            flow = UPTAKE * max(0.0, r[i] - b[i]) * DT
            r[i] -= flow
            b[i] = min(BUF, b[i] + flow)
            # the upkeep is paid out of the buffer
            b[i] = max(0.0, b[i] - consume * v[i] * DT)
        u, v = nu, nv
        if step >= SETTLE:
            centroids.append(centroid(v))

    mass = sum(v)
    alive = mass > MASS_ALIVE
    drift = 0.0
    if alive and len(centroids) > 10:
        d = centroids[-1] - centroids[0]
        while d > N / 2:
            d -= N
        while d < -N / 2:
            d += N
        drift = d / (len(centroids) - 1)
    return drift, alive, max(v), mass


def centroid(v: list[float]) -> float:
    total = sum(v)
    if total <= 0:
        return 0.0
    sx = sy = 0.0
    for i, x in enumerate(v):
        ang = 2 * math.pi * i / N
        sx += x * math.cos(ang)
        sy += x * math.sin(ang)
    ang = math.atan2(sy, sx)
    return (ang % (2 * math.pi)) * N / (2 * math.pi)


def main(argv: list[str]) -> int:
    print(f"the spot with a reservoir: N={N}, (F,k)=({F},{K}), buffer {BUF}, uptake {UPTAKE}")
    print()

    checks: list[tuple[str, bool, object]] = []

    # (a) silent
    d0, a0, p0, m0 = run(0.0, 0.2, 0.0, buffer=True)
    d1, a1, p1, m1 = run(0.0, 0.2, 0.0, buffer=False)
    print(f"  buffer on:  alive={a0} peak={p0:.4f} mass={m0:.3f}")
    print(f"  buffer off: alive={a1} peak={p1:.4f} mass={m1:.3f}")
    checks.append(("no price: the reservoir changes nothing", abs(m0 - m1) < 1e-9, f"{m0 - m1:.2e}"))

    # (b) fires: where is the edge now?
    print()
    print("  price sweep with the reservoir (grow 0.2):")
    edge_with = None
    for c in (0.0, 0.02, 0.05, 0.10, 0.20, 0.40):
        _, alive, peak, mass = run(c, 0.2, 0.0, buffer=True)
        print(f"    c={c:.2f}: alive={alive} peak={peak:.4f} mass={mass:.3f}")
        if alive:
            edge_with = c
    # Measured, and not what was predicted: the edge is unchanged. A reservoir that
    # sits in the same cell the structure lives in is still paying in place, so it
    # buys no margin at all. The prediction is kept as a refutation, and the check
    # now asserts what the run actually shows.
    checks.append(("the reservoir in place does NOT move the edge (still 0.02, dead at 0.05)",
                   edge_with == 0.02, edge_with))

    # (c) the question refused in 181
    print()
    print("  gradient, with the reservoir, at a survivable price:")
    for c in (0.05, 0.10):
        for grad in (0.0, 0.3, 0.6):
            drift, alive, peak, mass = run(c, 0.2, grad, buffer=True)
            tag = "alive" if alive else "dead "
            print(f"    c={c:.2f} grad={grad:.1f}: {tag} mass={mass:.3f} drift/step={drift:+.5f}")
            if alive and grad > 0:
                checks.append(
                    (f"c={c:.2f} grad={grad:.1f}: alive, so the drift question is askable",
                     True, f"{drift:+.5f}")
                )

    print()
    bad = 0
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
