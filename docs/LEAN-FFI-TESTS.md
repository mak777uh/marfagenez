# Lean FFI test feature

The default Cargo feature set is deliberately empty. Tests which call into the
Lean runtime are selected with:

```bash
cargo test --release --no-default-features --features lean-ffi -- --test-threads=1
```

The ordinary Rust test suite can be compiled/listed without that feature:

```bash
cargo test --release --no-default-features --tests -- --list
```

The source audit for the current snapshot found the Lean-backed tests only in
`core/src/bridge.rs`. `core/src/organism.rs`, `core/src/form.rs`,
`core/src/skin.rs` and `core/tests/sustainability.rs` have no direct calls to
`bridge::*` or exported Lean functions; they remain in the parallel suite.
They should be gated only if a later source change introduces a Lean-runtime
dependency.

`python3 checks/lean_ffi_feature.py` compiles/lists both modes and fails if
`bridge::tests::*` appears in the default parallel mode or disappears when
`lean-ffi` is enabled. It deliberately does not execute the FFI tests.
