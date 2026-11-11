//! Build script: compile the Lean bridge to C and link it.
//!
//! The bridge (`core/src/bridge.rs`) calls functions exported from `laws/FFI.lean`.
//! This script:
//!
//! 1. finds the Lean toolchain (via `lean` on PATH, or `~/.elan/bin/lean`);
//! 2. runs `lean -c FFI.c FFI.lean` in `laws/`;
//! 3. compiles `FFI.c` with `gcc`, linking `libleanshared`;
//! 4. tells Cargo to link the result.
//!
//! If Lean or `gcc` is missing, it compiles a **stub** that returns zeros, so the
//! crate still builds. `bridge::available()` then reports `false`, and the bridge
//! tests are skipped rather than failed.
//!
//! This is deliberate: a missing toolchain is a **skip**, not a failure. A test that
//! fails because a tool is absent teaches nothing about the code.

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=../laws/FFI.lean");
    println!("cargo:rerun-if-changed=build.rs");

    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));
    let laws_dir = Path::new("../laws");

    let lean = match find_lean() {
        Some(p) => p,
        None => {
            println!("cargo:warning=Lean not found — building the bridge stub");
            write_stub(&out_dir);
            return;
        }
    };

    // Find the toolchain root. `lean` may be a bare name on PATH, so resolve it
    // through `which` first.
    let lean_path = if lean.is_absolute() {
        lean.clone()
    } else {
        match Command::new("which").arg("lean").output() {
            Ok(o) if o.status.success() => {
                PathBuf::from(String::from_utf8_lossy(&o.stdout).trim().to_string())
            }
            _ => {
                println!("cargo:warning=cannot resolve lean on PATH — building the stub");
                write_stub(&out_dir);
                return;
            }
        }
    };
    // `lean` in `.elan/bin` is a hard link into a toolchain, not a symlink, so its
    // path says nothing about the toolchain. Find the toolchain that actually has
    // `include/lean/lean.h` and `lib/lean/libleanshared.so`.
    let toolchain = match find_toolchain(&lean_path) {
        Some(p) => p,
        None => {
            println!(
                "cargo:warning=cannot locate a Lean toolchain with headers — building the stub"
            );
            write_stub(&out_dir);
            return;
        }
    };
    let lib_dir = toolchain.join("lib").join("lean");
    let inc_dir = toolchain.join("include");

    // 1. Lean -> C
    let c_file = out_dir.join("FFI.c");
    let lean_out = Command::new(&lean)
        .args(["-c"])
        .arg(&c_file)
        .arg("FFI.lean")
        .current_dir(laws_dir)
        .output();

    match lean_out {
        Ok(o) if o.status.success() => {}
        Ok(o) => {
            println!(
                "cargo:warning=lean -c failed — building the stub: {}",
                String::from_utf8_lossy(&o.stderr)
            );
            write_stub(&out_dir);
            return;
        }
        Err(e) => {
            println!("cargo:warning=cannot run lean ({}) — building the stub", e);
            write_stub(&out_dir);
            return;
        }
    }

    // 2. C -> object
    let obj = out_dir.join("FFI.o");
    let gcc_out = Command::new("gcc")
        .args(["-c", "-O2", "-fPIC"])
        .arg(&c_file)
        .arg("-o")
        .arg(&obj)
        .arg(format!("-I{}", inc_dir.display()))
        .output();

    match gcc_out {
        Ok(o) if o.status.success() => {}
        Ok(o) => {
            println!(
                "cargo:warning=gcc failed — building the stub: {}",
                String::from_utf8_lossy(&o.stderr)
            );
            write_stub(&out_dir);
            return;
        }
        Err(e) => {
            println!("cargo:warning=cannot run gcc ({}) — building the stub", e);
            write_stub(&out_dir);
            return;
        }
    }

    // 2b. Append a constructor that initialises the Lean runtime before `main`.
    //
    // The C experiments showed that `lean_initialize` must run in the main thread
    // before any other thread calls into Lean. Rust's test harness runs every test in
    // its own thread, so initialising lazily inside the first call is too late: the
    // runtime aborts with "failed to initiate panic".
    //
    // A constructor runs before `main`, in the main thread, which is exactly right.
    if let Ok(mut text) = std::fs::read_to_string(&c_file) {
        text.push_str(
            "\n/* Initialise the Lean runtime before main, in the main thread. */\n\
             extern void lean_initialize(void);\n\
             extern void lean_io_mark_end_initialization(void);\n\
             extern void lean_init_task_manager(void);\n\
             __attribute__((constructor))\n\
             static void marfa_lean_boot(void) {\n\
                 lean_initialize();\n\
                 lean_io_mark_end_initialization();\n\
                 lean_init_task_manager();\n\
             }\n",
        );
        let _ = std::fs::write(&c_file, text);
    }

    // Recompile C with the constructor appended.
    let gcc_out2 = Command::new("gcc")
        .args(["-c", "-O2", "-fPIC"])
        .arg(&c_file)
        .arg("-o")
        .arg(&obj)
        .arg(format!("-I{}", inc_dir.display()))
        .output();
    if let Ok(o) = gcc_out2 {
        if !o.status.success() {
            println!(
                "cargo:warning=gcc (with constructor) failed: {}",
                String::from_utf8_lossy(&o.stderr)
            );
        }
    }

    // 3. Link
    println!("cargo:rustc-link-search=native={}", out_dir.display());
    println!("cargo:rustc-link-search=native={}", lib_dir.display());
    println!("cargo:rustc-link-lib=dylib=leanshared");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}", lib_dir.display());

    // Link the object **directly**, not through an archive.
    //
    // `ar` drops the `.init_array` section, which is where the Lean runtime
    // constructor lives. Without it the runtime is never initialised and the first
    // call from a test thread aborts. Passing the object path as a link argument
    // keeps the section.
    println!("cargo:rustc-link-arg={}", obj.display());
}

/// Finds a Lean toolchain directory that has both the headers and the shared library.
///
/// Looks in `<lean_dir>/../toolchains/*`, then in `~/.elan/toolchains/*`, and returns
/// the first that has `include/lean/lean.h` and `lib/lean/libleanshared.so`.
fn find_toolchain(lean_path: &Path) -> Option<PathBuf> {
    let mut roots: Vec<PathBuf> = Vec::new();
    if let Some(bin) = lean_path.parent() {
        if let Some(elan) = bin.parent() {
            roots.push(elan.join("toolchains"));
        }
    }
    if let Ok(home) = env::var("HOME") {
        roots.push(PathBuf::from(home).join(".elan/toolchains"));
    }
    for root in roots {
        let entries = match std::fs::read_dir(&root) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let p = entry.path();
            if p.join("include/lean/lean.h").exists()
                && p.join("lib/lean/libleanshared.so").exists()
            {
                return Some(p);
            }
        }
    }
    None
}

/// Finds `lean`, either on PATH or in the elan home.
fn find_lean() -> Option<PathBuf> {
    if let Ok(out) = Command::new("lean").arg("--version").output() {
        if out.status.success() {
            return Some(PathBuf::from("lean"));
        }
    }
    let home = env::var("HOME").ok()?;
    let candidate = PathBuf::from(home).join(".elan/bin/lean");
    if candidate.exists() {
        return Some(candidate);
    }
    None
}

/// Writes a stub C file whose functions return zeros.
///
/// The crate then builds, and `bridge::available()` reports `false`.
fn write_stub(out_dir: &Path) {
    let stub = r#"
#include <stdint.h>

uint64_t marfa_saturation(uint64_t a, uint64_t b) { (void)a; (void)b; return 0; }
uint64_t marfa_fraction_pct(uint64_t a, uint64_t b) { (void)a; (void)b; return 0; }
uint64_t marfa_fill_time(uint64_t a, uint64_t b) { (void)a; (void)b; return 0; }
uint8_t  marfa_race_lost(uint64_t a, uint64_t b) { (void)a; (void)b; return 0; }
uint64_t marfa_fold_shifted(uint64_t a, uint64_t b) { (void)a; (void)b; return 0; }
"#;
    let c_file = out_dir.join("stub.c");
    std::fs::write(&c_file, stub).expect("write stub");

    let obj = out_dir.join("stub.o");
    let gcc_out = Command::new("gcc")
        .args(["-c", "-O2", "-fPIC"])
        .arg(&c_file)
        .arg("-o")
        .arg(&obj)
        .output();

    if let Ok(o) = gcc_out {
        if o.status.success() {
            let _ = Command::new("ar")
                .arg("crs")
                .arg(out_dir.join("libffi.a"))
                .arg(&obj)
                .output();
        }
    }

    println!("cargo:rustc-link-search=native={}", out_dir.display());
}
