#!/usr/bin/env python3
"""kappa_sim.py -- is the judge-admission rule strong enough at this n?

The rule under test (T-12):
    pass  iff  kappa_hat >= KAPPA and bootstrap_lower_95 >= LOWER

Why a script and not an opinion: at n = 30-50 the same rule passes a judge whose true
kappa is 0.55 in a noticeable fraction of runs. That number must be reproducible, with
its assumptions written down, before the rule is frozen.

Model (binary verdicts, two raters):
    The basic table assumes BOTH raters have the same marginal p. That assumption is exactly what
    the policy forbids: a judge shifted by delta is modelled here, because "a shift of 0.15 makes
    admission impossible" must be a measured number, not a guess. `--shift` sweeps p_owner and
    p_owner + delta and reports the maximum achievable kappa next to the measured one.
    Optional `--groups 4` resamples blocks of items (calibration items inside one question are
    dependent, so an item-level bootstrap would overstate precision).

Same marginals p:
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


def joint2(p0, p1, kappa):
    """Two raters with different marginals. a is chosen so that observed agreement matches kappa."""
    pe = p0 * p1 + (1 - p0) * (1 - p1)
    po = kappa * (1 - pe) + pe
    a = (po + p0 + p1 - 1) / 2
    lo, hi = max(0.0, p0 + p1 - 1), min(p0, p1)
    if not (lo - 1e-12 <= a <= hi + 1e-12):
        return None
    b, c = p0 - a, p1 - a
    d = 1 - p0 - p1 + a
    if min(a, b, c, d) < -1e-12:
        return None
    return a, b, c, d


def max_kappa(p0, p1):
    """The ceiling: the best agreement the marginals allow at all."""
    pe = p0 * p1 + (1 - p0) * (1 - p1)
    po = min(p0, p1) + (1 - p0 - p1 + min(p0, p1))
    if pe >= 1:
        return 1.0
    return (po - pe) / (1 - pe)


def raw_agreement(pairs):
    n = len(pairs)
    return sum(1 for a, b in pairs if a == b) / n if n else 0.0


def gwet_ac1(pairs):
    n = len(pairs)
    if n == 0:
        return 0.0
    po = raw_agreement(pairs)
    p0 = sum(a for a, _ in pairs) / n
    p1 = sum(b for _, b in pairs) / n
    pbar = (p0 + p1) / 2
    pe = 2 * pbar * (1 - pbar)
    return 1.0 if pe >= 1 else (po - pe) / (1 - pe)


def confusion(pairs):
    tp = sum(1 for a, b in pairs if a == 1 and b == 1)
    tn = sum(1 for a, b in pairs if a == 0 and b == 0)
    fp = sum(1 for a, b in pairs if a == 0 and b == 1)
    fn = sum(1 for a, b in pairs if a == 1 and b == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "precision": round(prec, 3), "recall_yes": round(rec, 3)}


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


def lower_bound(pairs, rng, groups=1):
    vals = []
    n = len(pairs)
    if groups <= 1:
        for _ in range(BOOT):
            vals.append(kappa([pairs[rng.randrange(n)] for _ in range(n)]))
    else:
        blocks = [pairs[i:i + groups] for i in range(0, n, groups)]
        for _ in range(BOOT):
            picked = [blocks[rng.randrange(len(blocks))] for _ in range(len(blocks))]
            vals.append(kappa([item for b in picked for item in b]))
    vals.sort()
    return vals[int(len(vals) * PCTL / 100)]


def shift_table(trials, rng_seed=20261121):
    print("смещение маргиналов: p_владельца = 0.50, p_судьи = 0.50 + delta")
    print("  delta | потолок kappa | измеренная | P(пройти) | raw | AC1 | recall судьи | точность")
    for delta in (0.0, 0.05, 0.10, 0.15, 0.20):
        p0, p1 = 0.50, 0.50 + delta
        ceiling = max_kappa(p0, p1)
        target = min(0.80, ceiling)
        j = joint2(p0, p1, target)
        if j is None:
            continue
        rng = random.Random(rng_seed + int(delta * 100))
        passed = 0
        raws, ac1s, recs, precs = [], [], [], []
        for _ in range(trials):
            pairs = sample(j, 50, rng)
            k = kappa(pairs)
            if k >= KAPPA and lower_bound(pairs, rng) >= LOWER:
                passed += 1
            raws.append(raw_agreement(pairs))
            ac1s.append(gwet_ac1(pairs))
            cm = confusion(pairs)
            recs.append(cm["recall_yes"])
            precs.append(cm["precision"])
        print("  %5.2f | %12.3f | %10.3f | %8.1f%% | %.2f | %.2f | %11.2f | %8.2f" % (
            delta, ceiling, target, 100 * passed / trials,
            sum(raws) / trials, sum(ac1s) / trials, sum(recs) / trials, sum(precs) / trials))
    print()
    print("  вывод: при delta >= 0.15 потолок kappa <= 0.70, поэтому правило недостижимо;")
    print("         это свойство маргиналов, а не выборки — добор пунктов не помогает.")


def main(argv):
    if "--shift" in argv:
        trials = int(argv[argv.index("--shift") + 1]) if len(argv) > argv.index("--shift") + 1 else 400
        return shift_table(trials)
    args = [a for a in argv[1:] if not a.startswith("--")]
    groups = 1
    if "--groups" in argv:
        groups = int(argv[argv.index("--groups") + 1])
    trials = int(args[0]) if args else 400
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
                        if lower_bound(pairs, rng, groups) >= LOWER:
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
