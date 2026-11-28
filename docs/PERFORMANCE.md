# Life performance measurements

The hot-loop changes in this branch are allocation reductions, not a claim that
the model has already become faster. Use the same host, Rust toolchain, release
flags, CPU governor/power mode and input matrix for baseline and candidate.
Do not compare GitHub runner timings from different machines.

## Reproducible command

```bash
cd core
cargo build --release --example bench_life
./target/release/examples/bench_life \
  --populations 24,256,1024 \
  --cells 40,256,1024 \
  --steps 1000 \
  --repeats 7 \
  --policy stay \
  --share sequential
```

The example emits one metadata JSON line followed by one JSON line per
population × field-size pair. Preserve stdout together with:

```bash
rustc --version --verbose
uname -a
git rev-parse HEAD
lscpu
```

Repeat for `--policy random`, `--policy memory`, and `--share proportional`.
The proportional protocol must be measured separately: its per-cell arrays are
required state, while Sequential no longer pays for them. Use 10000 steps for
stable long-run throughput and repeat the complete command at least three
times. Report medians across repeats, not a single fastest run.

## Removed work

- Two O(cells) allocations per step for the default Sequential share protocol.
- One O(population) policy clone per step.
- One visit-order Vec per step for Historical and Rotate (Random still uses the
  same Fisher-Yates Vec and consumes exactly the same random draws).
- One O(population) presence snapshot per step when claims are enabled.
- One process-environment lookup per organism per step for the debug-only path.

No SIMD, parallel execution, RNG algorithm change, field representation change,
or reordered organism action is included. The full gate and unchanged golden
trajectory hashes remain the correctness authority. Performance improvement
must only be claimed after baseline/candidate measurements on the same host.
