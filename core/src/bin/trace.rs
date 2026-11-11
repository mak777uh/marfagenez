//! # `trace` binary
//!
//! Runs the cycle with each policy and writes a JSON trace to `results/`.
//!
//! ```bash
//! cargo run --release --bin trace -- --policy remember --steps 500 --every 10
//! ```
//!
//! The output goes to `results/<policy>/trace-<timestamp>.json`.
//!
//! ## Why a binary and not a test
//!
//! A test asserts something. This **records** — it has no expectation, only a
//! description. That is Krishnamurti's P204: watch without judging.

use std::fs;
use std::path::PathBuf;

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;
use medium_core::trace::record;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut policy = Policy::Remember;
    let mut steps = 500usize;
    let mut every = 10usize;
    let mut seed = 20250101u64;
    let mut n = 40usize;
    let mut cells = 40usize;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--policy" => {
                i += 1;
                policy = match args.get(i).map(|s| s.as_str()) {
                    Some("stay") => Policy::Stay,
                    Some("random") => Policy::Random,
                    Some("remember") => Policy::Remember,
                    other => {
                        eprintln!("unknown policy: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--steps" => {
                i += 1;
                steps = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(steps);
            }
            "--every" => {
                i += 1;
                every = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(every);
            }
            "--seed" => {
                i += 1;
                seed = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(seed);
            }
            "--n" => {
                i += 1;
                n = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(n);
            }
            "--cells" => {
                i += 1;
                cells = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(cells);
            }
            "--help" | "-h" => {
                println!("usage: trace [--policy stay|random|remember] [--steps N] [--every K] [--seed S] [--n N] [--cells C]");
                return;
            }
            other => {
                eprintln!("unknown argument: {}", other);
                std::process::exit(2);
            }
        }
        i += 1;
    }

    let world = World {
        income: 0.8,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
    };
    let field = match Field::alternating(cells, 2.0, 0.2, 0.8) {
        Some(f) => f,
        None => {
            eprintln!("cannot build the field");
            std::process::exit(1);
        }
    };
    let mut life = match Life::spawn(world, field, n, 5.0, 0.1, policy, seed, 300) {
        Some(l) => l,
        None => {
            eprintln!("cannot build the cycle");
            std::process::exit(1);
        }
    };

    let trace = record(&mut life, steps, every);

    let name = match policy {
        Policy::Stay => "stay",
        Policy::Random => "random",
        Policy::Remember => "remember",
    };
    let dir = PathBuf::from("results").join(name);
    if let Err(e) = fs::create_dir_all(&dir) {
        eprintln!("cannot create {}: {}", dir.display(), e);
        std::process::exit(1);
    }
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let path = dir.join(format!("trace-{}-{}.json", name, stamp));
    if let Err(e) = fs::write(&path, trace.to_json()) {
        eprintln!("cannot write {}: {}", path.display(), e);
        std::process::exit(1);
    }

    println!("policy:   {}", name);
    println!("steps:    {}", steps);
    println!("frames:   {}", trace.frames.len());
    println!("hash:     {:016x}", trace.hash);
    println!("written:  {}", path.display());
}
