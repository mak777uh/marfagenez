# Lean FFI test feature

The default feature set is empty. The normal Rust suite therefore excludes
unit tests that enter the embedded Lean runtime:

```bash
cd core
cargo test --release --no-default-features --tests -- --test-threads=1
```

Lean-backed bridge tests are opt-in and should run serially after the Lean
toolchain has been installed and `lake build` has completed:

```bash
cd core
cargo test --release --no-default-features --lib --features lean-ffi -- --test-threads=1
```

A source audit of the current snapshot found calls to the Lean FFI only in
`core/src/bridge.rs`. The test modules in `organism.rs`, `form.rs`,
`skin.rs`, and the integration tests in `tests/sustainability.rs` do not
call the bridge and remain in the ordinary Rust suite. They should be gated
only if a future test actually starts calling an exported Lean function.

`python3 checks/lean_ffi_feature.py` compiles/lists both configurations and
asserts that `bridge::tests::*` is absent by default and present with the
feature. The GitHub Actions gate then executes the Lean-backed tests.
