"""A field with no player: does anything persist, and does anything travel?

Conway's Life showed that a fixed local rule with no agent and no price grows
structure. Our world has the opposite trade: a price on everything and no space of
configurations, so nothing can compound. This file takes the one thing we did not
take - **remove the player** - and asks the field question directly.

The medium is two continuous channels on a ring of `N` cells, updated by a local
rule (Gray-Scott form, which is the standard generator of localised structures in
one dimension):

    u' = u + dt*( Du*lap(u) - u*v^2 + F*(1 - u) )
    v' = v + dt*( Dv*lap(v) + u*v^2 - (F + k)*v )

with a five-point Laplacian on the ring. Nothing else: no organism, no energy, no
maintenance, no policy.

The detector is the one calibrated on Life (`checks/life_calibration.py`): a
structure with `P(t+tau) == shift(P(t), delta)` sustained over several cycles, now
with a declared tolerance because the values are continuous.

PREDICTION, written before the run, in three parts:

    (a) pure diffusion (F = 0, k = 0) produces no detected structure - it decays to
        uniform, which is the `silent` control;
    (b) at least one point of the declared (F, k) grid produces a localised
        structure that the detector finds, either static (delta = 0) or travelling
        (delta != 0) - the `fires` control;
    (c) any detection depends on the reaction term, i.e. it vanishes when u*v^2 is
        removed while everything else is held - the `specific` control.

    python3 checks/field_no_player.py
"""

from __future__ import annotations

import itertools
import sys

N = 64
DT = 1.0
DU, DV = 0.16, 0.08
STEPS = 6000
TOL = 1e-4          # declared tolerance for "the same pattern"
AMP_MIN = 1e-2      # below this amplitude the field is uniform and "everything matches"
WINDOW = 5          # half-width of the locality window, in cells
LOCAL_MIN = 0.5     # declared minimum share of the mass inside that window

GRID = [
    (0.000, 0.000),
    (0.014, 0.054), (0.020, 0.050), (0.025, 0.055), (0.030, 0.062),
    (0.035, 0.060), (0.040, 0.060), (0.045, 0.065), (0.050, 0.065),
]


def lap(field: list[float], i: int) -> float:
    n = len(field)
    return field[(i - 1) % n] + field[(i + 1) % n] - 2.0 * field[i]


def make_initial(n: int, seed: int = 1):
    """A uniform background with a small seeded perturbation in the middle."""
    u = [1.0] * n
    v = [0.0] * n
    for i in range(n // 2 - 2, n // 2 + 3):
        u[i % n] = 0.5
        v[i % n] = 0.25
    return u, v


def run(f: float, k: float, reaction: bool = True, steps: int = STEPS):
    u, v = make_initial(N)
    frames = []
    for _ in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            reac = u[i] * v[i] * v[i] if reaction else 0.0
            nu[i] = u[i] + DT * (DU * lap(u, i) - reac + f * (1.0 - u[i]))
            nv[i] = v[i] + DT * (DV * lap(v, i) + reac - (f + k) * v[i])
            nu[i] = min(1.0, max(0.0, nu[i]))
            nv[i] = min(1.0, max(0.0, nv[i]))
        u, v = nu, nv
        if len(frames) < 12:
            frames.append(list(v))
        else:
            frames.pop(0)
            frames.append(list(v))
    return frames


def shifted_close(a: list[float], b: list[float], delta: int, tol: float) -> bool:
    n = len(a)
    return all(abs(b[(i + delta) % n] - a[i]) <= tol for i in range(n))


def detect(frames: list[list[float]], taus=range(1, 9), spans=(-3, -2, -1, 1, 2, 3)):
    """(tau, delta) holding for the last three cycles, with delta != 0.

    A uniform field is invariant under every shift, so the trivial case has to be
    refused explicitly: without the amplitude test the detector fires on a fully
    decayed diffusion field, which is exactly what the first run did.
    """
    if amplitude(frames[-1]) < AMP_MIN:
        return []
    found = []
    for tau in taus:
        for delta in spans:
            ok = 0
            for c in range(3):
                i = len(frames) - 1 - c * tau
                j = i - tau
                if j < 0:
                    break
                if shifted_close(frames[j], frames[i], delta, TOL):
                    ok += 1
            if ok == 3:
                found.append((tau, delta))
    return found


def detected_static(frames: list[list[float]], taus=range(1, 9)):
    if amplitude(frames[-1]) < AMP_MIN:
        return None
    for tau in taus:
        ok = 0
        for c in range(3):
            i = len(frames) - 1 - c * tau
            j = i - tau
            if j < 0:
                break
            if shifted_close(frames[j], frames[i], 0, TOL):
                ok += 1
        if ok == 3:
            return tau
    return None


def amplitude(field: list[float]) -> float:
    return max(field) - min(field)


def localised(frames: list[list[float]]) -> bool:
    """The mass sits in one window, not spread around the ring."""
    v = frames[-1]
    total = sum(v)
    if total <= 0:
        return False
    peak = max(range(len(v)), key=lambda i: v[i])
    n = len(v)
    inside = sum(v[(peak + d) % n] for d in range(-WINDOW, WINDOW + 1))
    return inside / total >= LOCAL_MIN


def main(argv: list[str]) -> int:
    checks = []

    print(f"field with no player: ring of {N}, Gray-Scott, {STEPS} steps, tol {TOL}")
    print()

    # (a) silent control: pure diffusion
    frames = run(0.0, 0.0, reaction=False)
    moving = detect(frames)
    static = detected_static(frames)
    checks.append(("F=0 k=0 (diffusion only): no moving structure", not moving, moving))
    checks.append(("F=0 k=0 (diffusion only): no periodic structure", static is None, static))

    # (b) the declared grid
    produced = []
    for f, k in GRID[1:]:
        frames = run(f, k)
        moving = detect(frames)
        static = detected_static(frames)
        loc = localised(frames)
        kind = "localised spot" if loc else ("extended periodic" if static is not None else "none")
        produced.append((f, k, moving, static, loc, kind))
        print(f"  F={f:.3f} k={k:.3f}: moving={moving} static_tau={static} kind={kind}")
    checks.append(
        (
            "at least one (F,k) produces a detected structure",
            any(m or s is not None for _, _, m, s, _, _ in produced),
            [(f, k) for f, k, m, s, _, _ in produced if m or s is not None],
        )
    )
    checks.append(
        (
            "at least one detected structure is a localised spot",
            any(loc for _, _, _, _, loc, _ in produced),
            [kind for _, _, _, _, loc, kind in produced if loc],
        )
    )
    travelling = [(f, k) for f, k, m, _, _, _ in produced if m]
    print()
    print(f"  travelling structures found: {travelling if travelling else 'none'}")

    # (c) specific control: remove the reaction term, keep F and k
    f, k = GRID[1]
    frames = run(f, k, reaction=False)
    moving = detect(frames)
    checks.append(
        (f"F={f:.3f} k={k:.3f} without the reaction term: nothing detected",
         not moving and detected_static(frames) is None, moving)
    )

    bad = 0
    print()
    for label, ok, got in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}  [{got}]")
        bad += 0 if ok else 1

    print()
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Контроли пройдены: чистый диффузионный распад ничего не даёт; на сетке (F,k) структуры найдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
