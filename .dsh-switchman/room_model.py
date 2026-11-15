"""Reproduce the room-law table in laws/Medium/Child.lean.

Child.lean claims spread = B/sqrt(3) for a reflected Brownian motion on [-B, B],
with the run length scaled as (B/sigma)^2 steps. That table was the last
[UNVERIFIED] block in laws/Medium: no script in checks/ produced those numbers.

Model: each step x <- reflect(x + sigma * N(0,1), B); no drift (mu = 0), because
the claim is about the space alone, not about growth.
"""

import math

import numpy as np

N = 20000
SEED = 5001
SIGMA = 1.0
B_VALUES = (0.5, 1.0, 2.0, 3.0, 5.0, 8.0)


def reflect(x: np.ndarray, b: float) -> np.ndarray:
    period = 4.0 * b
    u = np.mod(x + b, period)
    return b - np.abs(u - 2.0 * b)


def steps_for(b: float, sigma: float) -> int:
    return int(round((b / sigma) ** 2))


def spread(b: float, steps: int, rng: np.random.Generator) -> float:
    pop = rng.uniform(-b, b, N)
    for _ in range(steps):
        pop = reflect(pop + SIGMA * rng.normal(0.0, 1.0, N), b)
    return float(pop.std())


def main() -> int:
    rng = np.random.default_rng(SEED)
    print(f"sigma = {SIGMA}, N = {N}, seed = {SEED}, steps = (B/sigma)^2")
    print()
    print("| B | steps | measured spread | B/sqrt(3) | ratio |")
    print("|---|-------|-----------------|-----------|-------|")
    ok = True
    for b in B_VALUES:
        s = steps_for(b, SIGMA)
        m = spread(b, s, rng)
        ideal = b / math.sqrt(3.0)
        ratio = m / ideal
        good = abs(ratio - 1.0) <= 0.05
        ok = ok and good
        print(f"| {b:.1f} | {s} | {m:.3f} | {ideal:.3f} | {ratio:.3f} |")
    print()
    print("PASS within 5% of B/sqrt(3)" if ok else "FAIL: a row is off by more than 5%")
    print()
    print("# What this proves")
    print("Reflection keeps the population uniform on [-B, B], so the spread is")
    print("B/sqrt(3) at every half-width, provided the run is long enough.")
    print()
    print("# What this does NOT prove")
    print("- Nothing is proved: this is a simulation, not a Lean theorem.")
    print("- Only B = 0.5, 1, 2, 3, 5, 8 are measured.")
    print("- Drift (mu > 0) is not modelled; this is the space alone.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
