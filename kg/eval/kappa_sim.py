#!/usr/bin/env python3
"""kappa_sim.py -- is the judge-admission rule strong enough at this n?

The rule under test (T-12):
    pass  iff  kappa_hat >= KAPPA and bootstrap_lower_95 >= LOWER

Why a script and not an opinion: at n = 30-50 the same rule passes a judge whose true
kappa is 0.55 in a noticeable fraction of runs. That number must be reproducible, with
its assumptions written down, before the rule is frozen.

Model (binary verdicts, two raters, same marginals p):
    pe = p^2 + (1-p)^2
    po = kappa*(1-pe) + pe            <- target agreement for a given true kappa
    a  = (po + 2p - 1) / 2            <- P(both say 1)
    b  = c = p - a ;  d = 1 - 2p + a
Bootstrap: resample items with replacement, recompute kappa, take the 5th percentile.

Usage: python3 kappa_sim.py [trials]
"""
import random
import sys

KAPPA = 0.70
LOWER = 0.55
BOOT = 399
PCTL = 5


def joint(p, kappa):
    pe = p * p + (1 - p) * (1 - p)
    po = kappa * (1 - pe) + pe
    a = (po + 2 * p - 1) / 2
    lo, hi = max(0.0, 2 * p - 1), min(p, 1.0)
    if not (lo - 1e-12 <= a <= hi + 1e-12):
        return None
    return a, p - a, p - a, 1 - 2 * p + a


def sample(j, n, rng):
    a, b, c, d = j
    edges = ((0, 0, d), (1, 0, b), (0, 1, c), (1, 1, a))
    tot = sum(e[2] for e in edges)
    pairs = []
    for _ in range(n):
        x = rng.random() * tot
        acc = 0.0
        for i, jj, w in edges:
            acc += w
            if x <= acc:
                pairs.append((i, jj))
                break
    return pairs


def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return 0.0
    po = sum(1 for a, b in pairs if a == b) / n
    p1 = sum(a for a, _ in pairs) / n
    q1 = sum(b for _, b in pairs) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    if pe >= 1:
        return 1.0
    return (po - pe) / (1 - pe)


def lower_bound(pairs, rng):
    vals = []
    n = len(pairs)
    for _ in range(BOOT):
        vals.append(kappa([pairs[rng.randrange(n)] for _ in range(n)]))
    vals.sort()
    return vals[int(len(vals) * PCTL / 100)]


def main(argv):
    trials = int(argv[1]) if len(argv) > 1 else 400
    print("правило: kappa_hat >= " + str(KAPPA) + " и bootstrap-" + str(PCTL) + "% >= " + str(LOWER))
    print("прогонов на конфигурацию: " + str(trials) + " · bootstrap: " + str(BOOT))
    print("истинная kappa | n | p | P(пройти)   (наивный порог kappa>=0.70 отдельно)")
    rows = []
    for kappa_true in (0.55, 0.70, 0.80):
        for n in (30, 50, 80):
            for p in (0.5, 0.7):
                j = joint(p, kappa_true)
                if j is None:
                    continue
                rng = random.Random(20261120 + int(kappa_true * 100) + n + int(p * 10))
                passed = naive = 0
                for _ in range(trials):
                    pairs = sample(j, n, rng)
                    k = kappa(pairs)
                    if k >= KAPPA:
                        naive += 1
                        if lower_bound(pairs, rng) >= LOWER:
                            passed += 1
                rows.append((kappa_true, n, p, passed / trials, naive / trials))
                print("      %.2f      | %2d | %.1f | %5.1f%%      (%.1f%%)" %
                      (kappa_true, n, p, 100 * passed / trials, 100 * naive / trials))
    hard = [r for r in rows if r[0] == 0.55 and r[1] == 50 and r[2] == 0.5]
    if hard:
        print()
        print("вывод: при истинной kappa 0.55 и n=50 правило проходит в " +
              "%.0f%% прогонов" % (100 * hard[0][3]) + "; при 0.70 -- в " +
              "%.0f%%" % (100 * [r for r in rows if r[0] == 0.70 and r[1] == 50 and r[2] == 0.5][0][3]) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
