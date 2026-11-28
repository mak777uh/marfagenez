# EXP-2026-4106 — wear-erase pipeline contract

This directory is a local, pre-run redesign for main. It does not claim a task,
touch control state, submit artifacts, or run a real experiment. The driver is
main-owned. Task id, task version, service-issued task-version SHA256, base
commit, and task-payload SHA256 are **inputs**, never constants invented here.

## 1. Frozen grid and execution split

- Cells, in this order: `base`, `erase600`, `erase221`, `sham600`, `erand`, `silent`.
- Primary seeds: 5501..5512 (12), cohort `primary`.
- Deferred seeds: 5513..5520 (8), cohort `deferred`.
- Pairs: 0..399 (400) for every `(cell, cohort, seed)`.
- Horizon: 5000.
- Erasure times: `erase600=600`, `erase221=221`, `sham600=600` ledger mark,
  `erand` in [600,1000), `base=0`, `silent=0`.
- Primary and deferred are separate driver invocations:

```bash
exp_wear_erase --seeds 12 --deferred 0 --seed-base 5501 --pairs 400
exp_wear_erase --seeds 0 --deferred 8 --seed-base 5513 --pairs 400
```

Expected data rows are exactly `6*12*400=28800` primary and
`6*8*400=19200` deferred. Header rows are not counted.

## 2. Exact raw CSV contract

The header must match byte-for-byte after UTF-8 decoding (no BOM, reordering,
extra columns, or duplicate columns):

```text
cell,cohort,seed,pair,t_erase,event_status,applied,wearA_before,wearA_after,wearB_before,wearB_after,qA_event,dA_event,eA_event,qB_event,dB_event,eB_event,state_hash,lifeA,censA,lifeB,censB
```

Every row has exactly 22 fields. `seed`, `pair`, `t_erase`, `lifeA`, `lifeB`,
`censA`, and `censB` are decimal integers; `applied`, `censA`, and `censB` are
0/1. Wear and q/D/e fields must parse as finite IEEE-754 values; NaN and
infinity are invalid. Wear is nonnegative. A right-censored observation has
`cens=1` and `life=horizon=5000`; `cens=0` is a death.

### 2.1 Event status and ledger

Allowed `event_status` values are:

- `not_scheduled`: `base` or `silent`; `applied=0`; initial state snapshots.
- `applied`: an erase cell whose event occurred; `applied=1`; both arms are
  alive at the start of `t_erase` (a death at the event time is after the
  intervention); `wearA_after=0`.
- `sham`: `sham600` event occurred; `applied=0`; both arms are alive at the
  start of `t_erase`; wear before equals wear after in both arms.
- `not_due_death`: either arm died before its scheduled event; `applied=0`,
  at least one of `lifeA<t_erase` or `lifeB<t_erase`; snapshots are the state at
  the first death and wear is unchanged.
- `horizon`: reserved for an event not reached because the arm is
  right-censored at the horizon. All registered 4106 event times are below
  1000 and the horizon is 5000, so this status cannot validly occur in the
  fixed grid.

Without an applied/sham event, wear before equals wear after in both arms.
q/D/e event snapshots must be exactly equal between A and B, including raw-bit
comparison. Snapshot fields and a valid state hash are mandatory on every row,
including `not_scheduled` and `not_due_death`.

### 2.2 State hash

`state_hash` is 16 lowercase hexadecimal characters: FNV-1a 64 over the
little-endian IEEE-754 raw bits of these eight **post-event** values, in order:

```text
qA_event, dA_event, eA_event, wearA_after,
qB_event, dB_event, eB_event, wearB_after
```

Equivalent packing is `struct.pack("<8d", ...)`. FNV offset basis is
`14695981039346656037`, prime is `1099511628211`, multiplication is modulo
`2^64`. For `not_due_death`, post-event snapshots are the last live state; for
`not_scheduled`, they are the initial state. The analyzer recomputes every
hash; a missing, malformed, or mismatched hash is `void`.

## 3. Runner and provenance

`we_run.sh BINARY NEW_OUT --task-payload TASK [--driver-source SOURCE]`
is a dry-run: it prints the exact commands and hashes but creates no output,
claim, heartbeat, or process. `--execute` is required for driver execution.
Claimed execution uses `we_run_leased.py ... --execute`; only that path reads
claim material, writes `claim.json`, and heartbeats. A dry-run leased wrapper
does not read the claim.

The output path must be new. The leased wrapper may reserve a directory and
write only its claim/heartbeat/stdio logs before invoking the runner; the runner
still refuses every existing run artifact. Nothing is overwritten.

Layout:

```text
NEW_OUT/
  environment.json, environment.txt, toolchain.json, run-plan.json
  raw-manifest.json
  primary/raw.csv, primary/raw-manifest.json, primary/driver.stderr.log
  deferred/raw.csv, deferred/raw-manifest.json, deferred/driver.stderr.log
  analysis/...
```

Manifests pin task id/version/hash/base, task-payload SHA256, exact argv,
binary SHA256, optional driver-source SHA256, return codes, row counts, raw
SHA256, validation controls/errors, timestamps, and pipeline source hashes.
Environment and toolchain are captured. The new CSV contract emits event
snapshots rather than step rows, so `steps_csv` is explicitly null with
`not_emitted_by_contract`; no step hash is fabricated.

## 4. Analyzer

`we_analyze.py` is standard-library Python. The production CLI is fixed to the
grid above. Small test grids are available only through the imported core
function and cannot pass plan/submission validation.

Validation covers exact header/field count, finite numbers, integer domains,
statuses, ledger invariants, state hashes, exact cells/cohorts/seeds/pairs,
duplicates, expected row counts, argv, return codes, manifest identity, and
raw SHA256. Any schema/hash/ledger/provenance failure is an outcome-gated
`void`, not a crash that hides the evidence.

### 4.1 Kaplan-Meier and T90

At each distinct event time `t`, with `Y_t` at risk, `d_t` deaths, and `c_t`
censors:

```text
S(t) = S(t-) * (1 - d_t / Y_t)
Y_(t+) = Y_t - d_t - c_t
```

Deaths are applied before removals for censors tied at `t`. Survival is
right-continuous. `T90` is the first time `S(t) <= 0.10`. `DeltaT90` is
`T90_A - T90_B` for the same cell and seed.

An unidentified point T90 in any inference cell (`base`, `erase600`,
`erase221`) or arm/seed is `void`. An unidentified T90 in those cells in any
bootstrap draw also makes the analysis `void`; the draw count is reported, no
incomplete/conditional CI is substituted, and the horizon is never used as T90.
Unidentified descriptive quantiles in sham/erand/silent are reported as null and
do not by themselves void the inferential analysis.

### 4.2 Paired seed-cluster bootstrap

- Exactly 2000 draws for production.
- Fixed primary seed: `20261128`; fixed deferred seed: `20261129`.
- For each draw, resample primary seeds with replacement.
- Within each selected seed, resample 400 pairs with replacement.
- One `(seed,pair)` multiplicity vector is shared across every cell and both
  arms. There is no independent resampling by cell.
- A draw estimate is the mean over selected seed occurrences of that cell's
  per-draw `DeltaT90`; contrasts use the same draw.
- CI is the two-sided percentile 95% interval (2.5%, 97.5%). P3 is directional
  and requires point estimate `>0` and CI lower bound `>0`.
- Secondary directional p-values use the plus-one bootstrap tail proportion.
  P2/P5 are the fixed Holm family of size two; adjusted p-values use step-down
  cumulative maxima and alpha 0.05.

Primary estimates/bootstrap are completed and the primary decision is frozen
before deferred records are analyzed. Deferred never changes primary resamples,
estimates, CIs, p-values, or decision. Deferred uses the same frozen code and
reports descriptive CIs/Holm values; final confirmation requires valid gates,
nonzero intervention support, and the registered P3 point direction. P2/P5
remain secondary and do not determine the final scientific outcome.

### 4.3 Gates and decisions

All of the following are instrument/provenance gates; any failure is `void`:

1. Exact schema/grid/manifest/raw hash validation.
2. Full event ledger, q/D/e equality, and recomputed state hashes.
3. **P1:** among `erase600` rows with `lifeA>=600`, exact equality of
   `(lifeA,censA,lifeB,censB)`. Exact collapse among every `erase600/applied=1`
   row is also required. At least one eligible/applied row is required.
4. **P4:** `sham600` equals `base` on the canonical projection
   `(seed,pair,lifeA,censA,lifeB,censB)`; ledger metadata are not projected.
5. `silent`: A and B have identical `lifeA=lifeB` for every pair.
6. **P6 instrument part:** exact collapse among every `erand/applied=1` row;
   at least one applied row is required.
7. T90 identifiability at point estimates and in every bootstrap draw.

Primary scientific decisions:

- **P3:** `DeltaT90(erase221) - DeltaT90(base) > 0`, with bootstrap CI lower > 0.
- **P2 secondary:** `DeltaT90(erase600) - DeltaT90(base) > 0`, Holm-adjusted p < 0.05.
- **P5 secondary:** `DeltaT90(base) < 0`, Holm-adjusted p < 0.05.

P4 is a gate, not a secondary hypothesis. P6 is descriptive only:

- `collapse_given_applied` is reported separately by `t_erase` bins
  `[600,700)`, `[700,800)`, `[800,900)`, `[900,1000)` and by binary
  `survival_to_erase = (lifeA>=t_erase)`.
- Zero applied denominators are reported as null, not zero.
- Unconditional applied/collapse fractions are shown only to expose selection.
  No independence test is run and independence of the unconditional fraction
  is not required.

Outcome taxonomy:

- `passed`: every gate holds, the sole primary scientific contrast P3 holds in
  primary, and supplied deferred data confirm P3 after the primary freeze.
  Secondary P2/P5 are reported with Holm adjustment but are not outcome gates.
- `failed`: gates hold and the carrier was perturbed, but primary P3 fails or
  deferred data do not confirm the registered P3 direction.
- `void`: any gate, provenance check, or inference-cell T90 identifiability
  check fails; missing registered deferred confirmation is also `void`.
- `insensitive_by_construction`: gates hold but no applied erase event in
  primary has nonzero `wearA_before`; alternatively, primary passes but the
  supplied confirmation cohort never perturbs its carrier. The intervention
  does not test the hypothesis in the relevant cohort.

If deferred is deliberately not supplied, the analyzer reports
`decision_scope=primary_only`; submission planning still requires both frozen
cohort artifacts.

### 4.4 Analysis artifacts

- `per_seed.csv`: deaths/censors, T90, DeltaT90, identifiability, and KM
  quantiles q75/q50/q25/q10/q05 for every cohort/cell/seed/arm.
- `distribution.csv`: mean per-seed KM quantiles and mean per-seed survival at
  221, 400, 600, 800, 1000, 5000, with A, B, and A−B. Negative survival
  difference means lower A survival.
- `landmarks.csv`: P6 conditional and unconditional descriptive strata.
- `controls.csv`, `predictions.csv`: gate and decision audit tables.
- `summary.json`: identity, raw/analyzer hashes, outcome/reason, frozen primary
  decision, deferred confirmation, Holm details, full distribution summary,
  limitations, and SHA256 for every other analysis artifact.

## 5. Finding, plan, and submission

`we_make_finding.py` and `we_make_plan.py` validate task id/version/hash/base,
task-payload hash, raw hashes, analyzer source hash, and analysis artifact
hashes. Their text is selected from the actual `passed`, `failed`, `void`, or
`insensitive_by_construction` outcome. Limitations and reproduce commands are
mandatory; no positive claim is emitted for failed/void/insensitive results.

`we_submit.py` preserves the `submission/v1` bundle shape and dry-run default.
It validates claim/task/plan/summary identity, exact outcome agreement, safe
artifact paths, planned/current artifact SHA256 and byte counts, summary/raw
cross-hashes, task-payload artifact hash, environment/toolchain, mandatory
finding sections, disk budget, and canonical bundle SHA256. Local validation
is stdlib-only; the repository service remains authoritative for its full
JSON Schema. Only explicit `--execute --root ...` imports the service and
uploads/submits.

Accepted task-payload wrappers are raw `task/v1`, `{payload: task, ...}`, and
`{task: task, ...}`. Inner/outer `task_version_sha256` must agree when both are
present. The service-issued hash is checked for shape and consistency, not
recomputed with an invented canonicalization.

## 6. Reproduce

```bash
# Safe preview: no output directory, claim, or execution.
bash we_run.sh /path/to/exp_wear_erase /new/results-directory \
  --task-payload task.json --driver-source driver.rs

# Explicit real execution; claimed runs must use the leased wrapper.
bash we_run.sh /path/to/exp_wear_erase /new/results-directory \
  --task-payload task.json --driver-source driver.rs --execute
python we_run_leased.py --driver /path/to/exp_wear_erase \
  --out /new/results-directory --runner we_run.sh --task-payload task.json \
  --driver-source driver.rs --claim claim.json \
  --db /path/to/lab/state/control.db --cli /path/to/lab/cli/main.py \
  --agent exper --execute

python we_analyze.py \
  --primary-raw /new/results-directory/primary/raw.csv \
  --primary-manifest /new/results-directory/primary/raw-manifest.json \
  --deferred-raw /new/results-directory/deferred/raw.csv \
  --deferred-manifest /new/results-directory/deferred/raw-manifest.json \
  --task-payload task.json --out /new/results-directory/analysis

python we_make_finding.py --results-dir /new/results-directory \
  --lease-run /new/results-directory/lease-run.json --task-payload task.json \
  --out FINDING-EXP-2026-4106.md --submission-status not_submitted
python we_make_plan.py --artifacts-dir /path/to/artifact-root \
  --summary /path/to/artifact-root/analysis/summary.json \
  --environment /path/to/artifact-root/run/environment.json \
  --toolchain /path/to/artifact-root/run/toolchain.json \
  --task-payload task.json --submission-id <submission-id> \
  --instance-id <instance-id> --out plan.json
python we_submit.py --claim claim.json --task-payload task.json --plan plan.json \
  --summary /path/to/artifact-root/analysis/summary.json \
  --artifacts-dir /path/to/artifact-root --out-dir /new/submission-bundle \
  --idem-key <idem-key>  # dry-run unless --execute --root is explicitly added
```

## 7. Tests and scope

`tests/test_analyzer.py` uses small synthetic CSV fixtures for pass,
scientific failure, void control failure, censored/unidentifiable T90, Holm,
state-hash/schema failure, and construction insensitivity. Fixtures use an
explicitly synthetic identity and never masquerade as production provenance.
The production analyzer remains fixed at 2000 draws and the full grid.

This is a standalone wear-erase/R test design. It is not a live-core experiment,
not closure, and makes no claim beyond the tested model, seeds, pairs, and
pinned artifacts.
