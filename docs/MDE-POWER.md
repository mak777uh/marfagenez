# MDE / power audit

**Date:** 2026-11-27. **alpha:** 0.05 two-sided. **Target power:** 0.80.

## Statistical contract

The nominal two-arm binomial screen is

\[
MDE = (z_{1-\alpha/2}+z_{1-\beta})\sqrt{\frac{2\hat p(1-\hat p)}{n}}.
\]

Here n is the recorded number of organisms per arm and
p-hat = (success_a + success_b + 1)/(2n + 2) uses Laplace smoothing: +1 pooled success and +1 pooled failure.
This avoids zero estimated variance for all-alive/all-dead pairs.

**Critical limitation:** this is an optimistic organism-level screen. The organisms
share one finite resource field, so independence is not established. The lab's
formal MDE formula in checks/result.py uses **between-seed** sigma. These latest
environment records have one seed per environment, so true seed-level sigma and
true seed-level MDE are **not estimable** from these rows. Do not read the nominal
screen as confirmatory evidence.

The confirmed / questionable labels below mean only observed delta >= nominal MDE
or not. They do not upgrade a simulation finding to external validation.

## Findings 176–178 and 226–229

| Finding | Threshold anchor | Independent seed replicates / point | MDE interpretation |
|---|---|---:|---|
| FINDING-176 | income = 1.8211; N = 12, 24, 48, 96 | 1 | not estimable: no between-seed sigma |
| FINDING-177 | repair-cost edge = 0.4000 vs 0.3333 | 1 | not estimable: no between-seed sigma |
| FINDING-178 | poor-cell edge = 1.8395 vs 1.8496 | 1 | not estimable: no between-seed sigma |
| FINDING-226 | f0 in (11, 12); 24/24 vs 0/24 | 24 | nominal binary MDE ≈ 0.404; observed contrast 1.0 |
| FINDING-227 | f0 = 11 vs 12; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ 0.700; observed contrast 1.0 |
| FINDING-228 | stock0 = 100 vs 50 at f0 = 4; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ 0.700; observed contrast 1.0 |
| FINDING-229 | stock0 = 50: f0 = 2 vs 4; 8/8 vs 0/8 | 8 | nominal binary MDE ≈ 0.700; observed contrast 1.0 |

Interpretation: the source experiments use one deterministic scene/seed per parameter point in FINDING-176–178; the four world sizes in 176 and the different threshold points in 177–178 are not independent replicates. The table therefore records 1 available observation per point, not a basis for estimating between-seed sigma. FINDING-176 uses four world sizes, not four replicate seeds;
177 and 178 use different deterministic parameter points, not replicate trials.
FINDING-226 records 24/24 versus 0/24 around its sharp f0 threshold. FINDING-227–229
report 8 runs per point. Their large binary survival contrasts are detectable under
the binomial approximation, but they do not estimate continuous between-seed
variance or show power for small effects.

## Frozen-ceiling contrasts

Source: results/frozen-ceiling/run-2026-11-15T19-29-24.json.

| Contrast | n/arm | Observed delta survival | Nominal MDE | Screen | Continuous energy MDE |
|---|---:|---:|---:|---|---|
| A-B | 40 | 0.000 | 0.313 | questionable | not estimable |
| A-C | 40 | 0.000 | 0.313 | questionable | not estimable |
| B-C | 40 | 0.000 | 0.313 | questionable | not estimable |

The file stores means/maxima and a one-element energies summary, not per-organism
energies or replicated seeds; a continuous-energy MDE cannot be back-calculated.
All three pairwise survival contrasts are zero.

## Protocol-capacity paired environments

Source: results/protocol-capacity/run-2026-11-15T19-29-24.json.

**Rows:** 30; nominal screen: 18 confirmed, 12 questionable. Nominally confirmed on **18/30 environments**; mean observed Δ = **0.638**, range = **0.167–1.000**. This is a descriptive within-environment organism contrast, not independent-seed replication.

| # | Environment (case, n, r, t, m) | Seq alive | Prop alive | delta survival | MDE | Screen |
|---:|---|---:|---:|---:|---:|---|
| 0 | case=0, n=30, r=0.8, t=0.6, m=0.1 | 30 | 30 | 0.000 | 0.091 | questionable |
| 1 | case=0, n=60, r=0.8, t=0.6, m=0.1 | 60 | 60 | 0.000 | 0.046 | questionable |
| 2 | case=0, n=120, r=0.8, t=0.6, m=0.1 | 60 | 120 | 0.500 | 0.157 | confirmed |
| 3 | case=0, n=140, r=0.8, t=0.6, m=0.1 | 60 | 0 | 0.429 | 0.138 | confirmed |
| 4 | case=0, n=160, r=0.8, t=0.6, m=0.1 | 60 | 0 | 0.375 | 0.123 | confirmed |
| 5 | case=1, n=20, r=0.8, t=1, m=0.1 | 20 | 20 | 0.000 | 0.135 | questionable |
| 6 | case=1, n=40, r=0.8, t=1, m=0.1 | 40 | 40 | 0.000 | 0.069 | questionable |
| 7 | case=1, n=200, r=0.8, t=1, m=0.1 | 40 | 200 | 0.800 | 0.137 | confirmed |
| 8 | case=1, n=220, r=0.8, t=1, m=0.1 | 40 | 0 | 0.182 | 0.078 | confirmed |
| 9 | case=1, n=240, r=0.8, t=1, m=0.1 | 40 | 0 | 0.167 | 0.071 | confirmed |
| 10 | case=2, n=10, r=0.8, t=0.6, m=0.5 | 10 | 10 | 0.000 | 0.261 | questionable |
| 11 | case=2, n=20, r=0.8, t=0.6, m=0.5 | 20 | 20 | 0.000 | 0.135 | questionable |
| 12 | case=2, n=40, r=0.8, t=0.6, m=0.5 | 40 | 0 | 1.000 | 0.313 | confirmed |
| 13 | case=2, n=60, r=0.8, t=0.6, m=0.5 | 40 | 0 | 0.667 | 0.242 | confirmed |
| 14 | case=2, n=80, r=0.8, t=0.6, m=0.5 | 40 | 0 | 0.500 | 0.193 | confirmed |
| 15 | case=3, n=10, r=0.85, t=0.6, m=0.5 | 10 | 10 | 0.000 | 0.261 | questionable |
| 16 | case=3, n=20, r=0.85, t=0.6, m=0.5 | 20 | 20 | 0.000 | 0.135 | questionable |
| 17 | case=3, n=60, r=0.85, t=0.6, m=0.5 | 60 | 0 | 1.000 | 0.256 | confirmed |
| 18 | case=3, n=80, r=0.85, t=0.6, m=0.5 | 60 | 0 | 0.750 | 0.215 | confirmed |
| 19 | case=3, n=100, r=0.85, t=0.6, m=0.5 | 60 | 0 | 0.600 | 0.182 | confirmed |
| 20 | case=4, n=10, r=0.875, t=0.6, m=0.55 | 10 | 10 | 0.000 | 0.261 | questionable |
| 21 | case=4, n=20, r=0.875, t=0.6, m=0.55 | 20 | 20 | 0.000 | 0.135 | questionable |
| 22 | case=4, n=60, r=0.875, t=0.6, m=0.55 | 60 | 0 | 1.000 | 0.256 | confirmed |
| 23 | case=4, n=80, r=0.875, t=0.6, m=0.55 | 60 | 0 | 0.750 | 0.215 | confirmed |
| 24 | case=4, n=100, r=0.875, t=0.6, m=0.55 | 60 | 0 | 0.600 | 0.182 | confirmed |
| 25 | case=5, n=10, r=0.825, t=0.6, m=0.5 | 10 | 10 | 0.000 | 0.261 | questionable |
| 26 | case=5, n=20, r=0.825, t=0.6, m=0.5 | 20 | 20 | 0.000 | 0.135 | questionable |
| 27 | case=5, n=40, r=0.825, t=0.6, m=0.5 | 40 | 0 | 1.000 | 0.313 | confirmed |
| 28 | case=5, n=60, r=0.825, t=0.6, m=0.5 | 40 | 0 | 0.667 | 0.242 | confirmed |
| 29 | case=5, n=80, r=0.825, t=0.6, m=0.5 | 40 | 0 | 0.500 | 0.193 | confirmed |

## Decision

Some large within-environment survival separations are much larger than the
nominal organism-level MDE; the no-difference rows are below it. However, the
environment/seed is the intended independent unit. The table therefore does
not close the formal power requirement. Confirmatory follow-up should use
predeclared independent seeds per environment, estimate sigma between those seeds,
then calculate MDE with the checks/result.py:arms_needed contract before running.

Reproduce with:

    python3 tools/mde_power.py --selftest
    python3 tools/mde_power.py --write
