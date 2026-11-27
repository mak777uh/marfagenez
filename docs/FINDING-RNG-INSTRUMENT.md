# RNG as an instrument: Box–Muller tail probe

**Status:** instrument-validation finding; not evidence about the simulated world.
**Date:** 2026-11-27.
**Generators:** historical 64-bit LCG v1 (default) and xoshiro256++ v1 (RNG2).
**Transform:** the same Box–Muller cosine branch used by `Rng::normal`.

## Why test the instrument

Henry R. Neave documented a serious interaction between a multiplicative
congruential generator and the Box–Muller normal transform. In his 1973 example,
one million generated values were restricted to approximately (-3.3, 3.6),
with conspicuous local maxima in the tails. This is the reason to measure the
generator and transform together rather than assuming that a normal transform
makes its input stream harmless.

- Neave, H. R. (1973), *On Using the Box–Müller Transformation with Multiplicative
  Congruential Pseudo-Random Number Generators*, Journal of the Royal Statistical
  Society: Series C (Applied Statistics), 22(1), 92–97.
- DOI: [10.2307/2346308](https://doi.org/10.2307/2346308).

This is an instrument issue, not a phenomenon in the simulated world. The
measurement below is not a reproduction of Neave's parameterisation: it tests
the repository's 64-bit mixed LCG and its currently used cosine branch only.

## One-million-draw deterministic probe

A deterministic reimplementation of the exact Rust LCG recurrence and the
xoshiro256++ v1 transition was run with seed `20261127`. Each generator produced
one million standard-normal values through the same Box–Muller cosine branch.

| Tail | Normal expectation | LCG v1 observed | xoshiro256++ v1 observed |
|---|---:|---:|---:|
| `|Z| > 2` | 45,500.3 | 45,583 | 45,557 |
| `|Z| > 3` | 2,699.8 | 2,704 | 2,726 |
| `|Z| > 4` | 63.34 | 64 | 57 |
| `|Z| > 5` | 0.57 | 0 | 2 |
| `|Z| > 6` | 0.002 | 0 | 0 |

Sample moments: LCG mean `−0.00210`, SD `1.00101`; xoshiro mean
`−0.00106`, SD `1.00052`.

For this 64-bit LCG and this one seed, the probe does **not** show Neave's dramatic
tail truncation. The difference between zero and two observations beyond five
sigma is not evidence that one generator is superior: the expected count is
below one. The result is a reproducible instrument check, not a certification
of either generator.

The Rust regression test re-runs one million values for both versions and uses
a five-standard-deviation binomial acceptance band at thresholds 2, 3, 4 and 5.
It does not pin these counts as universal constants.

## Versioning contract

- `Rng::new` remains the historical LCG, preserving the old stream.
- `Rng2` is xoshiro256++ v1, seeded via SplitMix64.
- Indexed streams derive from `(seed, entity_id)`; they do not depend on how
  many values another entity consumed.
- `RNG_VERSION` is separate from `HASH_VERSION`. The latter remains
  `2-prev-cell`.
- Traces record `rng_version`. The historical LCG default adds no new hash tag,
  so old LCG hashes remain unchanged; a non-default RNG is tagged in the
  dynamics hash.
- This probe is not a replacement for PractRand, TestU01, or multi-seed testing,
  and makes no claim about model predictions.
