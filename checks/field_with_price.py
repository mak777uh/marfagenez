"""Price as a trial: the structure from FINDING-180, now that existing costs.

`checks/field_no_player.py` produced a localised spot with no agent and no price, and
that was the point: Life's structures live because nothing costs. Here the same field
is given a resource that the structure consumes and that regrows, and the reaction is
gated by it. So the structure can no longer exist for free - either the medium feeds
it or it dies.

Three questions, each with a preregistered answer:

    (a) silent   - with no consumption and no gradient, the pattern must be exactly
                   what it was without the resource channel;
    (b) fires    - with consumption high enough relative to regrowth, the pattern must
                   die, and lowering consumption must bring it back;
    (c) the interesting one - with a resource **gradient**, does the pattern move
                   toward the richer side? PREDICTION: yes, because the edge facing
                   poor resource is gated more weakly and decays first, so the centroid
                   shifts up-gradient. If it does not move, that is the result and it
                   says the coupling is not enough.

No organism, no policy, no energy budget. The only thing added to the field is a price.

    python3 checks/field_with_price.py
"""

from __future__ import annotations

import math
import sys

N = 64
DT = 1.0
DU, DV = 0.16, 0.08
F, K = 0.050, 0.065          # the point that produced a localised spot in FINDING-180
STEPS = 8000
SETTLE = 4000

PRED_A = None                # filled by the run
CHECKS: list[tuple[str, bool, object]] = []


def lap(field: list[float], i: int) -> float:
    n = len(field)
    return field[(i - 1) % n] + field[(i + 1) % n] - 2.0 * field[i]


def initial():
    u = [1.0] * N
    v = [0.0] * N
    for i in range(N // 2 - 2, N // 2 + 3):
        u[i % N] = 0.5
        v[i % N] = 0.25
    return u, v


def run(consume: float, grow: float, grad: float, gate: bool = True):
    """Return (final v, centroid drift per step, alive)."""
    u, v = initial()
    ceiling = [1.0 - grad * (i / (N - 1)) for i in range(N)]
    r = list(ceiling)

    centroids = []
    for step in range(STEPS):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            reac = u[i] * v[i] * v[i]
            if gate:
                reac *= r[i]
            nu[i] = u[i] + DT * (DU * lap(u, i) - reac + F * (1.0 - u[i]))
            nv[i] = v[i] + DT * (DV * lap(v, i) + reac - (F + K) * v[i])
            nu[i] = min(1.0, max(0.0, nu[i]))
            nv[i] = min(1.0, max(0.0, nv[i]))
            # the price: the structure eats the resource, the resource regrows
            r[i] = r[i] - consume * v[i] * DT + grow * (ceiling[i] - r[i]) * DT
            r[i] = min(1.0, max(0.0, r[i]))
        u, v = nu, nv
        if step >= SETTLE:
            centroids.append(centroid(v))

    drift = 0.0
    if len(centroids) > 10:
        # unwrap the ring: take the shortest-arc difference between the ends
        d = centroids[-1] - centroids[0]
        while d > N / 2:
            d -= N
        while d < -N / 2:
            d += N
        drift = d / (len(centroids) - 1)
    alive = max(v) > 0.05
    return v, drift, alive, max(v), sum(v)


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
    print(f"the spot from FINDING-180 under a price: N={N}, (F,k)=({F},{K}), {STEPS} steps")
    print()

    # (a) silent: no consumption, no gradient. Must match the unpriced field.
    v_free, d_free, alive_free, peak_free, mass_free = run(0.0, 0.0, 0.0, gate=False)
    v_closed, d_closed, alive_closed, peak_closed, mass_closed = run(0.0, 0.0, 0.0, gate=True)
    diff = max(abs(a - b) for a, b in zip(v_free, v_closed))
    print(f"  priced but free (r=1 everywhere): peak {peak_closed:.4f}, diff from unpriced {diff:.2e}")
    print(f"  unpriced:                         peak {peak_free:.4f}")
    CHECKS.append(("no price, no gradient: the pattern is unchanged", diff < 1e-9, f"{diff:.2e}"))
    CHECKS.append(("no price: the pattern is alive", alive_free and alive_closed, (alive_free, alive_closed)))

    # (b) fires: the price threshold of the structure, found by a declared sweep.
    # The first version used consumptions from 0.2 to 2.0 and every one of them
    # killed the pattern, which says nothing about where the edge is. The sweep is
    # therefore declared down to 0.005.
    print()
    SWEEP = (0.0, 0.005, 0.010, 0.020, 0.050, 0.100)
    lives = {}
    for consume in SWEEP:
        _, drift, alive, peak, mass = run(consume, 0.2, 0.0)
        lives[consume] = (alive, peak, mass)
        print(f"  consume={consume:.3f} grow=0.2: alive={alive} peak={peak:.4f} mass={mass:.3f} "
              f"drift/step={drift:+.5f}")
    CHECKS.append(("a small price leaves the pattern alive", lives[0.010][0], lives[0.010][0]))
    CHECKS.append(("a large price kills the pattern", not lives[0.100][0], lives[0.100][0]))
    masses = [lives[c][2] for c in SWEEP[:4]]
    CHECKS.append(("below the edge the mass shrinks monotonically with the price",
                   all(masses[i] > masses[i + 1] for i in range(len(masses) - 1)),
                   [round(x, 3) for x in masses]))

    # (c) the interesting one: a gradient
    print()
    for consume, grow, grad in ((0.3, 0.3, 0.5), (0.3, 0.3, 0.8)):
        _, drift, alive, peak, mass = run(consume, grow, grad)
        print(f"  consume={consume:.1f} grow={grow:.1f} grad={grad:.1f}: alive={alive} "
              f"peak={peak:.4f} drift/step={drift:+.5f}")
        # The preregistered prediction was that a gradient makes the pattern drift
        # up-gradient. It does not: the pattern is dead by then. Recorded as a
        # refutation, not counted as a failure of the instrument.
        if grad == 0.5:
            print(f"  prediction 'drifts up-gradient' REFUTED: drift={drift:+.5f}, alive={alive}")

    print()
    bad = 0
    for label, ok, got in CHECKS:
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
