"""Compute the region where excitability and a SHORT recovery time hold together.

`FINDING-193` left a trap: excitability needs a large eps, and a large eps means a
recovery time of 750, which is longer than any run. The two properties are not
independent, so the region has to be computed rather than sampled.

Without diffusion the two fixed points are (0,0) and (1,1). Their stability gives the
excitability condition directly:

    (0,0) stable      <=>  1 - b/a > 0        <=>  b < a
    (1,1) unstable    <=>  1 - (1+b)/a < 0    <=>  a < 1 + b

and the recovery time of the rest state is

    T = eps * a / b

So T falls with b and rises with a, while excitability needs b < a < 1 + b. The region
with a small T is therefore near the edge b ~ a, with small a.

PREDICTION, before the run:
    (a) the inequality b < a < 1+b is exactly the excitability condition;
    (b) at (a, b) = (0.40, 0.10) with eps = 20 the recovery time is 80 time units, and
        a run of t = 8T = 640 shows a recovery to rest behind the moving level;
    (c) at (a, b) = (0.30, 0.15) with eps = 20 the recovery time is 40, and t = 6T = 240
        also works;
    (d) at both, the excitation survives to the end of the run, which is what the
        trade-off failed to achieve at (0.75, 0.02).

If (b) and (c) hold, the trap of 193 is escaped by moving in the parameter plane rather
than in eps.

    python3 checks/barkley_region.py
"""

from __future__ import annotations

import math
import sys

N = 128
DX = 0.25
DT = 0.01
EPS = 20.0
CASES = [(0.40, 0.10), (0.30, 0.15)]


def lap_line(x: list[float], i: int) -> float:
    left = x[i - 1] if i > 0 else x[i]
    right = x[i + 1] if i + 1 < len(x) else x[i]
    return (left + right - 2.0 * x[i]) / (DX * DX)


def f(u: float, v: float, a: float, b: float, eps: float) -> float:
    return (1.0 / eps) * u * (1.0 - u) * (u - (v + b) / a)


def excitability(a: float, b: float):
    """(0,0) stable and (1,1) unstable."""
    rest_stable = b < a
    excited_unstable = a < 1.0 + b
    return rest_stable and excited_unstable, (rest_stable, excited_unstable)


def recovery_time(a: float, b: float, eps: float = EPS) -> float:
    return eps * a / b


def measure_rate(a: float, b: float, u0: float = 1e-3, steps: int = 40000):
    u, v = u0, u0
    ts, us = [], []
    for step in range(steps):
        u += DT * f(u, v, a, b, EPS)
        v += DT * (u - v)
        if step % 200 == 0 and step > 0:
            ts.append(step * DT)
            us.append(abs(u))
    tail = [(t, x) for t, x in zip(ts, us) if x > 1e-14]
    if len(tail) < 6:
        return None
    tail = tail[len(tail) // 2:]
    (t0, x0), (t1, x1) = tail[0], tail[-1]
    if x0 <= 0 or x1 <= 0:
        return None
    return (math.log(x1) - math.log(x0)) / (t1 - t0)


def step_run(a: float, b: float, t_end: float):
    steps = int(t_end / DT)
    u = [1.0 if i < N // 2 else 0.0 for i in range(N)]
    v = [0.0] * N
    for _ in range(steps):
        nu = [0.0] * N
        nv = [0.0] * N
        for i in range(N):
            nu[i] = min(1.0, max(0.0, u[i] + DT * (lap_line(u, i) + f(u[i], v[i], a, b, EPS))))
            nv[i] = v[i] + DT * (u[i] - v[i])
        u, v = nu, nv
    return u


def level(u, target=0.5):
    for i in range(N - 1):
        if u[i] >= target and u[i + 1] < target:
            return i
    return None


def back_to_rest(u, front, thresh=0.05):
    for d in range(1, N - front):
        if u[min(N - 1, front + d)] < thresh:
            return d * DX
    return None


def main(argv: list[str]) -> int:
    print(f"Barkley parameter region: eps = {EPS}, line of {N} at dx = {DX}")
    print()
    probe = [(0.75, 0.02), (0.40, 0.10), (0.30, 0.15), (0.02, 0.10), (1.05, 0.02)]
    print("  (a) excitability condition, b < a < 1 + b:")
    for a, b in probe:
        ok, parts = excitability(a, b)
        print(f"      a={a:4.2f} b={b:4.2f}: rest stable={parts[0]}, excited unstable={parts[1]} "
              f"-> {'EXCITABLE' if ok else 'not excitable'}, T={recovery_time(a, b):.0f}")
    print()

    rows = []
    for a, b in CASES:
        T = recovery_time(a, b)
        rate = measure_rate(a, b)
        t_end = 8 * T
        u = step_run(a, b, t_end)
        front = level(u)
        back = None if front is None else back_to_rest(u, front)
        amp = max(u) - min(u)
        rows.append((a, b, T, rate, t_end, front, back, amp))
        print(f"  (b) a={a:.2f} b={b:.2f}: T={T:.0f}, measured rate "
              f"{'none' if rate is None else f'{rate:+.5f}'} (predicted {-1 / T:+.5f})")
        print(f"      after t={t_end:.0f}: amplitude {amp:.3f}, level "
              f"{'none' if front is None else f'x={front * DX:.2f}'}, "
              f"back to rest at {back}")

    bad = 0
    checks = [
        ("(a) the condition reproduces the known cases",
         excitability(0.75, 0.02)[0] and excitability(0.40, 0.10)[0]
         and not excitability(0.02, 0.10)[0] and not excitability(1.05, 0.02)[0],
         [(a, b, excitability(a, b)[0]) for a, b in probe]),
    ]
    for a, b, T, rate, t_end, front, back, amp in rows:
        checks.append((f"a={a:.2f} b={b:.2f}: measured rate matches -1/T",
                       rate is not None and abs(rate + 1.0 / T) < 0.15 / T,
                       None if rate is None else round(rate, 5)))
        checks.append((f"a={a:.2f} b={b:.2f}: the excitation survives the run", front is not None and amp > 0.5,
                       (front, round(amp, 3))))
        checks.append((f"a={a:.2f} b={b:.2f}: the medium returns to rest behind the level",
                       back is not None and back <= 8.0, back))
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
