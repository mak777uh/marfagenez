"""Item B4 of the plan: is the first noise draw correlated with the initial state?

`docs/PLAN-NEXT.md` §3 B4 says the model uses one LCG stream for everything and that the
completion criterion is:

    the correlation between the initial state and the first noise is measured and is zero
    within noise.

The generator is a pure function of the seed, so this needs no Rust: the recurrence is
deterministic and is reproduced here exactly.

    new(seed):    state = seed * A + 1
    next_u64():   state = state * A + C          (modulo 2^64)
    uniform():    (state >> 11) / 2^53

    python3 checks/rng_seed_noise.py
"""

from __future__ import annotations

import math
import sys

A = 6364136223846793005
C = 1442695040888963407
MASK = (1 << 64) - 1
TWO53 = float(1 << 53)


def first_uniform(seed: int) -> float:
    state = (seed * A + 1) & MASK
    state = (state * A + C) & MASK
    return (state >> 11) / TWO53


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else 0.0


def main(argv: list[str]) -> int:
    n = 20000
    seeds = list(range(n))
    draws = [first_uniform(s) for s in seeds]

    r = pearson([float(s) for s in seeds], draws)
    # the noise level of a correlation coefficient is 1/sqrt(n)
    noise = 1.0 / math.sqrt(n)
    print(f"seeds 0..{n - 1}")
    print(f"  mean of the first uniform      {sum(draws) / n:.6f}   (ideal 0.500000)")
    print(f"  Pearson r(seed, first uniform) {r:+.6f}   (noise level ±{noise:.6f})")

    # uniformity in ten bins
    bins = [0] * 10
    for u in draws:
        bins[min(9, int(u * 10))] += 1
    expected = n / 10
    chi2 = sum((b - expected) ** 2 / expected for b in bins)
    # 9 degrees of freedom: 95% critical value 16.92
    print(f"  bins of uniformity             {bins}")
    print(f"  chi-square (9 dof)             {chi2:.2f}   (95% critical 16.92)")

    bad = 0
    checks = [
        ("the correlation is within noise of zero", abs(r) <= 3 * noise),
        ("the first uniform is uniform across seeds", chi2 < 16.92),
        ("the mean is 0.5 within noise", abs(sum(draws) / n - 0.5) <= 3 * noise),
    ]
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'WRONG'} {label}")
        if not ok:
            bad += 1

    print()
    print("criterion B4 is about correlation only; splitting the streams is a separate change")
    if bad:
        print(f"РАСХОЖДЕНИЙ: {bad}")
        return 1
    print("Проверка пройдена: первый шум не связан с начальным состоянием.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
