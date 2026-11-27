#!/usr/bin/env python3
"""Measure LCG/xoshiro bit balance, serial correlation and Box-Muller tails.

The shuffled condition applies a deterministic Fisher-Yates permutation to the
raw uniform stream before pairing. This is a pairing-sensitivity stress test,
not the exact pair-reversal procedure studied by Chay, Fardo & Mazumdar (1975).

Usage:
  python3 tools/rng_battery.py --samples 1000000 --seed 20261127
  python3 tools/rng_battery.py --selftest
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
A = 6364136223846793005
C = 1442695040888963407
GAMMA = 0x9E3779B97F4A7C15
THRESHOLDS = (3.0, 4.0, 5.0)


def mix64(z: int) -> int:
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return (z ^ (z >> 31)) & MASK


class Lcg64:
    def __init__(self, seed: int):
        self.state = (seed * A + 1) & MASK

    def next_u64(self) -> int:
        self.state = (self.state * A + C) & MASK
        return self.state


class Xoshiro256PlusPlus:
    def __init__(self, seed: int):
        sm = seed & MASK
        self.s = []
        for _ in range(4):
            sm = (sm + GAMMA) & MASK
            self.s.append(mix64(sm))
        if not any(self.s):
            self.s[0] = GAMMA

    def next_u64(self) -> int:
        s = self.s
        base = (s[0] + s[3]) & MASK
        result = (((base << 23) | (base >> 41)) + s[0]) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = ((s[3] << 45) | (s[3] >> 19)) & MASK
        return result


def make_stream(name: str, seed: int, n: int) -> array.array:
    rng = Lcg64(seed) if name == "lcg64-v1" else Xoshiro256PlusPlus(seed)
    values = array.array("Q")
    append = values.append
    for _ in range(n):
        append(rng.next_u64())
    return values


def uniform(raw: int) -> float:
    return (raw >> 11) / float(1 << 53)


def bit_frequency_chi2(values: array.array, block_words: int = 8192) -> dict:
    # Each block aggregates 64*B bit observations; expected=32B, variance=16B.
    block_bits = []
    chi = []
    for i in range(0, len(values), block_words):
        words = values[i:i + block_words]
        b = len(words)
        ones = sum(x.bit_count() for x in words)
        block_bits.append(ones / (64.0 * b))
        chi.append(((ones - 32.0 * b) ** 2) / (16.0 * b))
    return {
        "blocks": len(chi),
        "df": len(chi),
        "one_fraction_mean": sum(block_bits) / len(block_bits) if block_bits else None,
        "chi2": sum(chi),
        "chi2_per_df": sum(chi) / len(chi) if chi else None,
        "max_block_chi2": max(chi) if chi else None,
    }


def serial_corr(values: array.array) -> float | None:
    n = 0
    prev = None
    sx = sy = sxx = syy = sxy = 0.0
    for raw in values:
        cur = uniform(raw)
        if prev is not None:
            n += 1
            sx += prev
            sy += cur
            sxx += prev * prev
            syy += cur * cur
            sxy += prev * cur
        prev = cur
    if n < 2:
        return None
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    if vx <= 0.0 or vy <= 0.0:
        return None
    return (sxy - sx * sy / n) / math.sqrt(vx * vy)


def box_muller_tails(values: array.array) -> dict:
    counts = {z: 0 for z in THRESHOLDS}
    n = len(values) // 2
    for i in range(0, n * 2, 2):
        u1 = max(uniform(values[i]), 1e-300)
        u2 = uniform(values[i + 1])
        z = abs(math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2))
        for threshold in THRESHOLDS:
            if z > threshold:
                counts[threshold] += 1
    out = {}
    normal = NormalDist()
    for threshold in THRESHOLDS:
        p = math.erfc(threshold / math.sqrt(2.0))
        k = counts[threshold]
        observed = k / n if n else 0.0
        out[str(int(threshold))] = {
            "count": k,
            "n": n,
            "observed_two_sided_p": observed,
            "theory_two_sided_p": p,
            "ratio_observed_over_theory": observed / p,
            "effective_sigma": normal.inv_cdf(1.0 - observed / 2.0)
                if 0.0 < observed < 1.0 else None,
            "zero_count_upper95_p": 3.0 / n if n and k == 0 else None,
        }
    return out


def analyse(name: str, seed: int, samples: int) -> dict:
    values = make_stream(name, seed, samples * 2)
    bit = bit_frequency_chi2(values)
    corr = serial_corr(values)
    tails = box_muller_tails(values)
    shuffled = array.array("Q", values)
    random.Random(seed ^ 0xA5A55A5AD3C1B2E7).shuffle(shuffled)
    return {
        "generator": name,
        "seed": seed,
        "n_raw_u64": len(values),
        "n_normals_per_pairing": samples,
        "bit_frequency_blocks": bit,
        "serial_corr_sequential": corr,
        "serial_corr_shuffled": serial_corr(shuffled),
        "box_muller_sequential_pairs": tails,
        "box_muller_shuffled_stream": box_muller_tails(shuffled),
    }


def run_battery(samples: int, seed: int) -> dict:
    return {
        "schema": "marfagenez.rng-battery.v1",
        "seed": seed,
        "samples_per_generator_and_pairing": samples,
        "shuffle": "Fisher-Yates using Python MT19937; seed XOR 0xA5A55A5AD3C1B2E7",
        "generators": [
            analyse("lcg64-v1", seed, samples),
            analyse("xoshiro256++-v1", seed, samples),
        ],
        "warning": "Instrument diagnostic only. At 1e6 normals the 5-sigma tail is not resolved.",
    }


def selftest() -> list[str]:
    errors = []
    lcg_expected = [
        15327728989046091365, 10190784122032440336, 11621570160334891039,
        14659357144070893506, 13560190476826518633, 17991778993386815172,
    ]
    xoshiro_expected = [
        14971601782005023387, 13781649495232077965, 1847458086238483744,
        13765271635752736470, 3406718355780431780, 10892412867582108485,
    ]
    lcg = Lcg64(1)
    xoshiro = Xoshiro256PlusPlus(1)
    if [lcg.next_u64() for _ in range(6)] != lcg_expected:
        errors.append("LCG reference vector mismatch")
    if [xoshiro.next_u64() for _ in range(6)] != xoshiro_expected:
        errors.append("xoshiro256++ reference vector mismatch")
    a = run_battery(2048, 12345)
    b = run_battery(2048, 12345)
    if a != b:
        errors.append("battery is not deterministic for identical input")
    if any(g["bit_frequency_blocks"]["df"] == 0 for g in a["generators"]):
        errors.append("bit-frequency test generated no blocks")
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
            print("\n".join("FAIL: " + e for e in errors))
            return 1
        print("OK: reference streams and deterministic battery")
        return 0
    if args.samples < 1000:
        parser.error("--samples must be >= 1000")
    result = run_battery(args.samples, args.seed)
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
        print("wrote", args.output)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
