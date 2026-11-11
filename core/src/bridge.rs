//! # The bridge: Rust asks Lean
//!
//! Until now Lean and Rust were **separate layers** that happened to describe the same
//! laws. This module makes the connection **technical**: Rust calls the Lean function
//! and compares the answer with its own.
//!
//! ## How it works
//!
//! 1. `laws/FFI.lean` exports functions with `@[export]`, on `UInt64` and `Bool`.
//! 2. `build.rs` runs `lean -c FFI.c FFI.lean` and compiles the C with `gcc`.
//! 3. Rust links the result and calls the functions.
//!
//! ## Why `UInt64` and not `Nat`
//!
//! `Nat` in Lean is a heap object (`lean_object*`). `UInt64` is a real `uint64_t`.
//! For a bridge the second is what is wanted: no boxing, no garbage collector, no
//! runtime initialisation.
//!
//! ## What the bridge is for
//!
//! Two things:
//!
//! * **Agreement**: the same formula computed in Rust and in Lean must give the same
//!   number. A disagreement means one of them is wrong.
//! * **Proof carried into the program**: the Lean function is the one whose properties
//!   are proved in `laws/Saturation.lean`. Calling it means the running program uses
//!   the proved formula, not a copy of it.
//!
//! ## What it is not
//!
//! It is **not** a proof that the Rust code is correct. It is a proof that the Rust
//! and Lean formulas agree on the inputs tested. The proof of the formula lives in
//! Lean; the bridge carries the formula, not the proof.

// FFI requires `unsafe`. This is the only module allowed to use it, and every
// `unsafe` block below has a SAFETY comment. The rest of the crate forbids it.
#![allow(unsafe_code)]

use std::os::raw::c_int;

// The Lean functions, as exported by `laws/FFI.lean` and compiled to C.
extern "C" {
    fn marfa_saturation(free_walk: u64, wall_law: u64) -> u64;
    fn marfa_fraction_pct(spread: u64, law: u64) -> u64;
    fn marfa_fill_time(b: u64, sigma: u64) -> u64;
    fn marfa_race_lost(b: u64, sigma: u64) -> u8;
    fn marfa_fold_shifted(b: u64, x: u64) -> u64;

    // The Lean runtime. Not declared in `lean.h`, but exported by `libleanshared`.
    fn lean_initialize();
    fn lean_init_task_manager();
    fn lean_io_mark_end_initialization();
}

/// Initialises the Lean runtime exactly once.
///
/// Every exported Lean function assumes the runtime is up. Without this the first
/// call aborts with "failed to initiate panic" — the runtime tries to raise a Lean
/// exception and has nowhere to put it.
///
/// `std::sync::Once` makes it safe to call from any thread and any number of times.
fn init_runtime() {
    // The Lean runtime is initialised by a constructor in `FFI.c`, which runs before
    // `main` in the main thread. Nothing to do here: calling `lean_initialize` again
    // from a test thread would be too late and would abort.
}

/// The saturation law, computed by Lean.
///
/// `spread = min(free_walk, wall_law)`.
pub fn lean_saturation(free_walk: u64, wall_law: u64) -> u64 {
    init_runtime();
    // SAFETY: the Lean function is a pure arithmetic function on `UInt64`; it does not
    // allocate, does not touch the runtime, and cannot panic.
    unsafe { marfa_saturation(free_walk, wall_law) }
}

/// The spread as a percentage of the law, computed by Lean.
pub fn lean_fraction_pct(spread: u64, law: u64) -> u64 {
    init_runtime();
    // SAFETY: pure arithmetic, as above.
    unsafe { marfa_fraction_pct(spread, law) }
}

/// The filling time `(b/sigma)^2`, computed by Lean.
pub fn lean_fill_time(b: u64, sigma: u64) -> u64 {
    init_runtime();
    // SAFETY: pure arithmetic, as above.
    unsafe { marfa_fill_time(b, sigma) }
}

/// Whether the race is lost, computed by Lean.
pub fn lean_race_lost(b: u64, sigma: u64) -> bool {
    init_runtime();
    // SAFETY: pure arithmetic, as above. Lean's `Bool` is a byte.
    unsafe { marfa_race_lost(b, sigma) != 0 }
}

/// The fold, computed by Lean. Returns a value in `[0, 2b]`; subtract `b` for `[-b, b]`.
pub fn lean_fold_shifted(b: u64, x: u64) -> u64 {
    init_runtime();
    // SAFETY: pure arithmetic, as above.
    unsafe { marfa_fold_shifted(b, x) }
}

/// The same saturation law, computed in Rust.
///
/// This is the counterpart the bridge compares against. It is written to be obviously
/// the same formula, so that a disagreement points at a real defect rather than at a
/// difference of style.
pub fn rust_saturation(free_walk: u64, wall_law: u64) -> u64 {
    free_walk.min(wall_law)
}

/// The same filling time, computed in Rust.
pub fn rust_fill_time(b: u64, sigma: u64) -> u64 {
    if sigma == 0 {
        0
    } else {
        let q = b / sigma;
        q * q
    }
}

/// The same fold, computed in Rust, shifted by `b` like the Lean version.
pub fn rust_fold_shifted(b: u64, x: u64) -> u64 {
    if b == 0 {
        return 0;
    }
    let period = 4 * b;
    let u = (x + b) % period;
    if u <= 2 * b {
        u
    } else {
        period - u
    }
}

/// Whether the bridge is available in this build.
///
/// The bridge needs a Lean toolchain and `gcc`. When they are missing, `build.rs`
/// compiles a stub that returns zeros, and this reports `false`. A test that needs the
/// bridge should check this first, so that a missing toolchain is reported as a
/// **skip**, not as a failure.
pub fn available() -> bool {
    // The stub returns 0 for every input. A real Lean call on (9, 16) returns 9.
    lean_saturation(9, 16) == 9
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_bridge_is_available() {
        assert!(
            available(),
            "the Lean bridge is not built — check that `lean` and `gcc` are on PATH"
        );
    }

    #[test]
    fn saturation_agrees() {
        for fw in [0u64, 1, 9, 16, 100] {
            for wl in [0u64, 1, 4, 16, 100] {
                assert_eq!(
                    lean_saturation(fw, wl),
                    rust_saturation(fw, wl),
                    "saturation disagrees at ({}, {})",
                    fw,
                    wl
                );
            }
        }
    }

    #[test]
    fn fill_time_agrees() {
        for b in [1u64, 2, 3, 10, 30] {
            for sigma in [1u64, 2, 3, 10] {
                assert_eq!(
                    lean_fill_time(b, sigma),
                    rust_fill_time(b, sigma),
                    "fill time disagrees at ({}, {})",
                    b,
                    sigma
                );
            }
        }
    }

    #[test]
    fn fold_agrees() {
        for b in [1u64, 3, 5] {
            for x in 0..(8 * b) {
                assert_eq!(
                    lean_fold_shifted(b, x),
                    rust_fold_shifted(b, x),
                    "fold disagrees at ({}, {})",
                    b,
                    x
                );
            }
        }
    }

    #[test]
    fn race_lost_agrees_with_the_lean_law() {
        // The Lean law `race_lost` says the race is lost when the filling time exceeds
        // the reaction time of one step.
        for b in [1u64, 3, 10, 30] {
            for sigma in [1u64, 2, 3] {
                let expected = rust_fill_time(b, sigma) > 1;
                assert_eq!(
                    lean_race_lost(b, sigma),
                    expected,
                    "race_lost disagrees at ({}, {})",
                    b,
                    sigma
                );
            }
        }
    }

    #[test]
    fn fraction_pct_agrees() {
        for spread in [0u64, 9, 16] {
            for law in [1u64, 16, 100] {
                let expected = if law == 0 { 0 } else { (100 * spread) / law };
                assert_eq!(
                    lean_fraction_pct(spread, law),
                    expected,
                    "fraction disagrees at ({}, {})",
                    spread,
                    law
                );
            }
        }
    }
}
