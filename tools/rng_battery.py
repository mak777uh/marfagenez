#!/usr/bin/env python3
"""Measure RNG bit balance, serial correlation and Box-Muller tails.

The generators and 53-bit float conversion match core/src/lib.rs:
  - lcg64-v1: state = seed*A+1, then state = A*state+C (mod 2^64)
  - xoshiro256++-v1: SplitMix64 seeding and the xoshiro256++ transition

Pairing arms are diagnostics, not proposed production fixes:
  sequential        successive uniforms (historical Box-Muller pairing)
  pair-reversed     swap u1/u2 within every consecutive pair
  shuffled         one deterministic global Fisher-Yates permutation
  reshuffled-blocks independent deterministic permutations in 4096-word blocks

No third-party packages are used.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import random
import sys
from pathlib import Path
from statistics import NormalDist

MASK = (1 << 64) - 1
LCG_A = 6364136223846793005
LCG_C = 1442695040888963407
SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
SHUFFLE_A = 0xA5A55A5AD3C1B2E7
SHUFFLE_B = 0x5F35649517C4A5D1
BLOCK_WORDS = 8192
RESHUFFLE_WORDS = 4096
TAILS = (3.0, 4.0, 5.0)
QUANTILES = (0.5, 0.9, 0.99, 0.999, 0.9999)


def mix64(z: int) -> int:
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return (z ^ (z >> 31)) & MASK


class Lcg64:
    def __init__(self, seed: int):
        self.state = (seed * LCG_A + 1) & MASK

    def next_u64(self) -> int:
        self.state = (self.state * LCG_A + LCG_C) & MASK
        return self.state


class Xoshiro256PlusPlus:
    def __init__(self, seed: int):
        sm = seed & MASK
        self.state = []
        for _ in range(4):
            sm = (sm + SPLITMIX_GAMMA) & MASK
            self.state.append(mix64(sm))
        if not any(self.state):
            self.state[0] = SPLITMIX_GAMMA

    def next_u64(self) -> int:
        s = self.state
        base = (s[0] + s[3]) & MASK
        result = ((((base << 23) | (base >> 41)) & MASK) + s[0]) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = ((s[3] << 45) | (s[3] >> 19)) & MASK
        return result


def make_stream(generator: str, seed: int, n: int) -> array.array:
    rng = Lcg64(seed) if generator == "lcg64-v1" else Xoshiro256PlusPlus(seed)
    values = array.array("Q")
    append = values.append
    for _ in range(n):
        append(rng.next_u64())
    return values


def uniform(raw: int) -> float:
    return (raw >> 11) / float(1 << 53)


def bit_frequency_chi2(values: array.array, block_words: int = BLOCK_WORDS) -> dict:
    """Per-bit Bernoulli chi-square, 64 degrees of freedom per word block."""
    chi_total = 0.0
    blocks = 0
    max_block = 0.0
    per_bit_total = [0.0] * 64
    per_bit_worst = [0.0] * 64
    for start in range(0, len(values), block_words):
        words = values[start:start + block_words]
        n = len(words)
        if not n:
            continue
        block_chi = 0.0
        for bit in range(64):
            ones = sum((word >> bit) & 1 for word in words)
            # χ² for the two bins {0,1}, each with expected n/2.
            value = 4.0 * (ones - n / 2.0) ** 2 / n
            per_bit_total[bit] += value
            per_bit_worst[bit] = max(per_bit_worst[bit], value)
            block_chi += value
        chi_total += block_chi
        max_block = max(max_block, block_chi)
        blocks += 1
    df = blocks * 64
    return {
        "block_words": block_words,
        "blocks": blocks,
        "degrees_of_freedom": df,
        "chi2": chi_total,
        "chi2_per_df": chi_total / df if df else None,
        "max_block_chi2_64df": max_block if blocks else None,
        "worst_bit_chi2": max(per_bit_total) if blocks else None,
        "worst_single_block_bit_chi2": max(per_bit_worst) if blocks else None,
    }


def serial_correlation(values: array.array, lag: int = 1) -> float | None:
    n = len(values) - lag
    if n < 2:
        return None
    sx = sy = sxx = syy = sxy = 0.0
    for i in range(n):
        x = uniform(values[i])
        y = uniform(values[i + lag])
        sx += x
        sy += y
        sxx += x * x
        syy += y * y
        sxy += x * y
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    if vx <= 0.0 or vy <= 0.0:
        return None
    return (sxy - sx * sy / n) / math.sqrt(vx * vy)


def box_muller(values: array.array, pair_reversed: bool = False) -> array.array:
    out = array.array("d")
    for i in range(0, len(values) - 1, 2):
        a, b = (values[i + 1], values[i]) if pair_reversed else (values[i], values[i + 1])
        u1 = max(uniform(a), 1e-300)
        u2 = uniform(b)
        out.append(math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2))
    return out


def shuffle_global(values: array.array, seed: int) -> array.array:
    out = array.array("Q", values)
    random.Random(seed).shuffle(out)
    return out


def reshuffle_blocks(values: array.array, seed: int) -> array.array:
    out = array.array("Q", values)
    rng = random.Random(seed)
    for start in range(0, len(out), RESHUFFLE_WORDS):
        end = min(start + RESHUFFLE_WORDS, len(out))
        block = list(out[start:end])
        rng.shuffle(block)
        out[start:end] = array.array("Q", block)
    return out


def normal_statistics(samples: array.array) -> dict:
    absolute = sorted(abs(value) for value in samples)
    n = len(absolute)
    normal = NormalDist()
    quantiles = {}
    for probability in QUANTILES:
        index = min(n - 1, max(0, math.ceil(probability * n) - 1))
        quantiles[str(probability)] = {
            "observed_abs_z": absolute[index],
            "normal_theory_abs_z": normal.inv_cdf((1.0 + probability) / 2.0),
        }
    tails = {}
    for threshold in TAILS:
        count = sum(value > threshold for value in absolute)
        theory = math.erfc(threshold / math.sqrt(2.0))
        expected = n * theory
        tails[str(int(threshold))] = {
            "count": count,
            "n": n,
            "observed_two_sided_p": count / n if n else None,
            "theory_two_sided_p": theory,
            "ratio_observed_over_theory": count / expected if expected else None,
            "poisson_z_diagnostic": (count - expected) / math.sqrt(expected)
                if expected > 0 else None,
            "zero_count_upper95_p": 3.0 / n if n and count == 0 else None,
        }
    return {"n": n, "abs_quantiles": quantiles, "tails": tails}


def analyse(generator: str, seed: int, samples: int) -> dict:
    raw = make_stream(generator, seed, samples * 2)
    sequential = box_muller(raw)
    pair_reversed = box_muller(raw, pair_reversed=True)
    shuffled = box_muller(shuffle_global(raw, seed ^ SHUFFLE_A))
    reshuffled = box_muller(reshuffle_blocks(raw, seed ^ SHUFFLE_B))
    return {
        "generator": generator,
        "seed": seed,
        "raw_u64": len(raw),
        "bit_frequency": bit_frequency_chi2(raw),
        "serial_correlation": {
            str(lag): serial_correlation(raw, lag)
            for lag in (1, 2, 8, 32)
        },
        "box_muller": {
            "sequential": normal_statistics(sequential),
            "pair_reversed": normal_statistics(pair_reversed),
            "shuffled": normal_statistics(shuffled),
            "reshuffled_blocks": normal_statistics(reshuffled),
        },
    }


def run_battery(samples: int, seed: int) -> dict:
    return {
        "schema": "marfagenez.rng-battery.v2",
        "seed": seed,
        "samples_per_generator_and_pairing": samples,
        "uniform_conversion": "(next_u64 >> 11) / 2^53",
        "pairing_protocols": {
            "sequential": "use consecutive stream values as (u1,u2)",
            "pair_reversed": "swap u1 and u2 within each consecutive pair",
            "shuffled": f"global Fisher-Yates using Python MT19937 seed XOR {SHUFFLE_A:#x}",
            "reshuffled_blocks": f"Fisher-Yates independently inside {RESHUFFLE_WORDS}-word blocks; seed XOR {SHUFFLE_B:#x}",
        },
        "generators": [
            analyse("lcg64-v1", seed, samples),
            analyse("xoshiro256++-v1", seed, samples),
        ],
        "limitations": [
            "The battery is a finite-sample instrument diagnostic, not a generator certification.",
            "Post-hoc shuffling is a pairing-sensitivity diagnostic, not a justified production repair.",
            "A million normals has expected 0.573 observations beyond 5 sigma; it cannot resolve the 5-sigma tail.",
            "The chi-square values are diagnostics; adjacent bits and blocks are not assumed independent for a certification claim.",
        ],
    }


def selftest() -> list[str]:
    errors = []
    expected = {
        "lcg64-v1": [
            15327728989046091365, 10190784122032440336, 11621570160334891039,
            14659357144070893506, 13560190476826518633, 17991778993386815172,
        ],
        "xoshiro256++-v1": [
            14971601782005023387, 13781649495232077965, 1847458086238483744,
            13765271635752736470, 3406718355780431780, 10892412867582108485,
        ],
    }
    for name, cls in (("lcg64-v1", Lcg64), ("xoshiro256++-v1", Xoshiro256PlusPlus)):
        rng = cls(1)
        if [rng.next_u64() for _ in range(6)] != expected[name]:
            errors.append(f"{name} reference stream mismatch")
    first = run_battery(2048, 12345)
    second = run_battery(2048, 12345)
    if first != second:
        errors.append("battery is not deterministic for identical inputs")
    if any(item["bit_frequency"]["degrees_of_freedom"] == 0 for item in first["generators"]):
        errors.append("bit-frequency test generated no degrees of freedom")
    if any(set(item["box_muller"]) != {"sequential", "pair_reversed", "shuffled", "reshuffled_blocks"}
           for item in first["generators"]):
        errors.append("a pairing arm is missing")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        errors = selftest()
        if errors:
            print("\n".join("FAIL: " + error for error in errors))
            return 1
        print("OK: Rust reference streams and deterministic four-arm battery")
        return 0
    if args.samples < 1000:
        parser.error("--samples must be >= 1000")
    result = run_battery(args.samples, args.seed)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
