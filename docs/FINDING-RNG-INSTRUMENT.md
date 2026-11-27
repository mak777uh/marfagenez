# RNG instrument battery: LCG vs xoshiro256++

**Scope:** instrument diagnostics only; not evidence about the simulated world.
**Date:** 2026-11-27. **Seed:** `20261127`.
**Sample:** 1,000,000 Box–Muller normals per generator and pairing condition.

## Why this test

Neave reported a pathological example in which one million normal deviates
generated from a multiplicative congruential stream using Box–Muller were
restricted to approximately `(-3.3, 3.6)`, with conspicuous tail-frequency
defects. See H. R. Neave (1973), *On Using the Box–Müller Transformation with
Multiplicative Congruential Pseudo-Random Number Generators*, JRSS C 22(1),
92–97, DOI [10.2307/2346308](https://doi.org/10.2307/2346308). <Cite refs={["turn994920search0","turn994920search12"]}/>

Chay, Fardo & Mazumdar (1975) studied a specific remedy for Neave's example:
reversing the order of the two members of each successive uniform pair before
applying Box–Muller. This is not the same as shuffling the entire stream.
See JRSS C 24(1), 132–135, DOI
[10.2307/2346711](https://doi.org/10.2307/2346711). <Cite refs={["turn328134search0","turn328134search1"]}/>

## Method

The battery uses the exact current Rust recurrences and the exact 53-bit
uniform conversion:

- LCG v1: initial state `seed*A + 1`; recurrence `x' = A*x + C (mod 2^64)`.
- xoshiro256++ v1: four-word state from SplitMix64, using the xoshiro256++
  transition.
- Box–Muller cosine branch: `sqrt(-2 ln u1) * cos(2πu2)`.
- Bit balance: one-bit frequency over 64-bit words, χ² per block of 8,192
  words (one degree of freedom per block).
- Serial correlation: Pearson correlation of adjacent 53-bit uniforms.
- Pairing contrast: original sequential adjacent pairs vs the same raw stream
  after deterministic Fisher–Yates permutation (MT19937 only supplies the
  permutation). This is a sensitivity test, not the Chay et al. pair-reversal
  method.

Run: `python3 tools/rng_battery.py --samples 1000000 --seed 20261127`.
Selftest: `python3 tools/rng_battery.py --selftest`.

## Measurement

| Metric | LCG v1 | xoshiro256++ v1 |
|---|---:|---:|
| Bit blocks / df | 245 | 245 |
| Bit χ² / df | 0.741 | 0.977 |
| Max block χ² | 8.508 | 7.342 |
| Serial r, original sequence | −0.000298 | −0.001151 |
| Serial r, shuffled sequence | −0.000242 | +0.000398 |

### Box–Muller tails

Theoretical two-sided tail probabilities are (P(|Z|>3)=0.0026998),
(P(|Z|>4)=0.0000633425), and (P(|Z|>5)=0.0000005733).

| Generator / pairing | >3σ count (ratio) | >4σ count (ratio) | >5σ count (ratio) |
|---|---:|---:|---:|
| LCG sequential | 2,704 (1.002) | 64 (1.010) | 0 (0.000) |
| LCG shuffled | 2,658 (0.985) | 78 (1.231) | 0 (0.000) |
| xoshiro sequential | 2,726 (1.010) | 57 (0.900) | 2 (3.489) |
| xoshiro shuffled | 2,683 (0.994) | 66 (1.042) | 0 (0.000) |

At 3σ and 4σ the differences are consistent with ordinary sampling
fluctuation. At 5σ the expected count is only **0.573** per million. The
xoshiro sequential count of 2 is not persuasive evidence of a defect:
under a Poisson approximation with λ=0.573, (P(K\ge2)\approx0.113).
For a zero count, the rule-of-three 95% upper bound is (3\times10^{-6}),
which is still above the theoretical 5σ probability. Thus this sample cannot
resolve 5σ behaviour.

The LCG shuffled 4σ count is 1.84 standard deviations above expectation, not a
significant discrepancy. The random permutation is a stress test of pair/order
sensitivity; it is not evidence that arbitrary shuffling repairs Neave's
specific construction.

## Which historical results are exposed?

The source audit found two Box–Muller call paths in the current Rust library:

1. `Cycle::born` in `core/src/cycle.rs` draws initial traits with
   `Rng::normal() * 0.5`.
2. `Child::drift_and_noise` in `core/src/child.rs` draws per-step noise with
   `Rng::normal()`; `Medium` owns the legacy `Rng::new(seed)` stream.

The Python tilt experiment `checks/exp88_exp_tilt_noise.py` and
`checks/tilt.py` use NumPy's `default_rng`, not this Rust Box–Muller path.
No specific committed `results/<id>/run-*.json` record was confidently tied
to `Cycle::born` or `Child::drift_and_noise` in this source-only audit.
Therefore **no historic finding is labelled compromised**. The two Rust call
paths are instrument-risk candidates; any unlogged exploratory result that
used them should be re-run with RNG2 and paired seeds before it is treated as
confirmatory evidence.

## What this does not prove

- It does not reproduce Neave's historical generator parameters or his exact
  pairing convention.
- It does not certify either generator; no PractRand/TestU01 suite is run.
- One million samples cannot establish a 5σ tail.
- It does not show that any named historical result is wrong.
- It does not compare the simulated model's predictions; it audits the random
  instrument used by selected code paths.
