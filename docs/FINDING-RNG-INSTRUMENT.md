# RNG instrument battery: LCG v1 vs xoshiro256++ v1

**Date:** 2026-11-27. **Seed:** `20261127`.
**Sample:** 1,000,000 Box–Muller normals for each generator and pairing arm.
**Purpose:** finite-sample instrument diagnostic, not a certification of either RNG.

## Exact implementation

The battery is implemented in `tools/rng_battery.py` and mirrors
`core/src/lib.rs`:

- LCG v1 starts from `seed*A + 1`, then updates `x' = A*x + C (mod 2^64)`.
- xoshiro256++ v1 uses SplitMix64 to seed four words, then the xoshiro256++
  transition.
- Uniform conversion is exactly `(next_u64 >> 11) / 2^53`.
- Box–Muller uses `sqrt(-2 ln u1) * cos(2πu2)`.

Run the full battery:

```bash
python3 tools/rng_battery.py --samples 1000000 --seed 20261127 --output /tmp/rng-battery.json
python3 tools/rng_battery.py --selftest
python3 tools/rng_result_audit.py
```

The selftest checks fixed reference vectors against the Rust recurrences and
determinism of the four pairing arms.

## Methods

**Bit-frequency χ².** For each block of 8,192 64-bit words, test each bit
position against a Bernoulli(0.5) split. There are 64 degrees of freedom per
block. The statistic is diagnostic: bit positions/blocks are not treated as an
independent certification suite.

**Serial correlation.** Pearson correlation of adjacent 53-bit uniforms at
lags 1, 2, 8 and 32.

**Pairing arms.** Sequential pairs are the baseline. Pair-reversed swaps the
two uniforms inside each pair. Shuffled permutes the entire raw stream once.
Reshuffled-blocks applies independent Fisher–Yates permutations to successive
4,096-word blocks. The latter two are sensitivity probes, not proposed fixes.
They do not reproduce the exact historical intervention in every cited RNG
paper.

**Tail and quantile comparison.** For |Z|, compare empirical p50/p90/p99/p99.9/
p99.99 against the standard-normal absolute quantile. Also count |Z| > 3, 4, 5
and compare observed probabilities with the theoretical two-sided normal
tail. At N=1,000,000, the expected >5σ count is only 0.573.

## Measured output

### Bit balance and serial correlation

| Generator | χ² / df | Maximum block χ² (64 df) | r₁ | r₂ | r₈ | r₃₂ |
|---|---:|---:|---:|---:|---:|---:|
| LCG v1 | 0.826 | 90.03 | −0.000298 | −0.000536 | −0.001069 | +0.000022 |
| xoshiro256++ v1 | 1.000 | 111.32 | −0.001151 | +0.000707 | −0.001164 | −0.000303 |

These aggregate diagnostics do not establish independence. They are a screen
for gross imbalance/correlation only.

### Empirical |Z| quantiles vs theory

Each cell is observed / theoretical.

| Generator / arm | p50 | p90 | p99 | p99.9 | p99.99 |
|---|---:|---:|---:|---:|---:|
| LCG sequential | 0.6755 / 0.6745 | 1.6468 / 1.6449 | 2.5796 / 2.5758 | 3.3026 / 3.2905 | 3.8760 / 3.8906 |
| LCG pair-reversed | 0.6744 / 0.6745 | 1.6434 / 1.6449 | 2.5777 / 2.5758 | 3.2901 / 3.2905 | 3.8892 / 3.8906 |
| LCG shuffled | 0.6756 / 0.6745 | 1.6453 / 1.6449 | 2.5758 / 2.5758 | 3.2878 / 3.2905 | 3.9310 / 3.8906 |
| LCG reshuffled blocks | 0.6755 / 0.6745 | 1.6452 / 1.6449 | 2.5782 / 2.5758 | 3.2948 / 3.2905 | 3.9088 / 3.8906 |
| xoshiro sequential | 0.6753 / 0.6745 | 1.6459 / 1.6449 | 2.5767 / 2.5758 | 3.2829 / 3.2905 | 3.8694 / 3.8906 |
| xoshiro pair-reversed | 0.6745 / 0.6745 | 1.6442 / 1.6449 | 2.5786 / 2.5758 | 3.2959 / 3.2905 | 3.8760 / 3.8906 |
| xoshiro shuffled | 0.6741 / 0.6745 | 1.6460 / 1.6449 | 2.5735 / 2.5758 | 3.2858 / 3.2905 | 3.9051 / 3.8906 |
| xoshiro reshuffled blocks | 0.6753 / 0.6745 | 1.6469 / 1.6449 | 2.5772 / 2.5758 | 3.2839 / 3.2905 | 3.8759 / 3.8906 |

### Tail counts

| Generator / arm | >3σ | >4σ | >5σ |
|---|---:|---:|---:|
| LCG sequential | 2,704 (1.002× theory) | 64 (1.010×) | 0 |
| LCG pair-reversed | 2,792 (1.034×) | 63 (0.995×) | 0 |
| LCG shuffled | 2,658 (0.985×) | 78 (1.231×) | 0 |
| LCG reshuffled blocks | 2,752 (1.019×) | 61 (0.963×) | 1 |
| xoshiro sequential | 2,726 (1.010×) | 57 (0.900×) | 2 |
| xoshiro pair-reversed | 2,728 (1.010×) | 56 (0.884×) | 0 |
| xoshiro shuffled | 2,683 (0.994×) | 66 (1.042×) | 0 |
| xoshiro reshuffled blocks | 2,701 (1.000×) | 68 (1.074×) | 2 |

The >3σ and >4σ counts are close to expectation in this sample. The LCG
shuffled >4σ count is 1.84 Poisson standard deviations above expectation, a
single exploratory fluctuation rather than evidence of a stable defect. The
xoshiro sequential >5σ count of 2 has a Poisson diagnostic z of about 1.88;
with expected count 0.573, this is not compelling. Zero counts are also
uninformative: the 95% rule-of-three upper bound is 3×10⁻⁶, above the theoretical
5σ probability (~5.73×10⁻⁷). This sample cannot resolve the 5σ tail.

## Historical result audit

The active result tree has 407 `run-*.json` records. The v2 result schema does
not include an RNG-version field. The checked legacy record examples also do
not carry a pairing declaration. The current `Life` run path consumes
uniform draws; the Box–Muller calls are in the separate `Cycle/Child` path
(`core/src/cycle.rs`, `core/src/child.rs`) and in RNG unit tests. Thus:

- historical runs without an RNG-version field are **unpaired/unversioned** for
  RNG2 comparison;
- they are **not automatically labelled Box–Muller runs**;
- no specific historic result is marked compromised without a result/trace
  locator proving it used that path.

`tools/rng_result_audit.py` generates the per-record list and treats missing
metadata as unknown rather than assuming an algorithm. Any historic record
shown to use a Box–Muller path should be rerun with both algorithms and paired
seeds before it is treated as confirmatory.

## Interpretation

This experiment does not reproduce Neave's specific multiplicative-generator
construction. Current LCG v1 is a mixed 64-bit LCG with an increment, and the
pairing arms here are explicit diagnostics. No result here demonstrates that
LCG v1 is certified or that xoshiro is universally superior. The battery says
only that these particular samples did not reveal a large 3σ/4σ tail defect;
5σ remains unresolved.
