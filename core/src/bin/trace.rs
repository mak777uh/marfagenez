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
    let mut capacity = 10.0f64;
    let mut damage_rate = 0.02f64;
    let mut income = 0.8f64;
    let mut maintenance = 0.6f64;
    let mut repair_cost = 1.5f64;
    let mut move_cost = 0.1f64;
    let mut energy = 5.0f64;
    let mut field_kind = "alternating".to_string();
    let mut memory_life = 300usize;
    let mut shift = 0.0f64;
    let mut rich = 2.0f64;
    let mut poor = 0.2f64;
    let mut regrow = 0.8f64;
    let mut feed = false;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--policy" => {
                i += 1;
                policy = match args.get(i).map(|s| s.as_str()) {
                    Some("stay") => Policy::Stay,
                    Some("random") => Policy::Random,
                    Some("remember") => Policy::Remember,
                    Some("memory") => Policy::Memory,
                    Some("sighted") => Policy::Sighted,
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
            "--capacity" => {
                i += 1;
                capacity = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(capacity);
            }
            "--damage-rate" => {
                i += 1;
                damage_rate = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(damage_rate);
            }
            "--income" => {
                i += 1;
                income = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(income);
            }
            "--maintenance" => {
                i += 1;
                maintenance = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(maintenance);
            }
            "--repair-cost" => {
                i += 1;
                repair_cost = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(repair_cost);
            }
            "--move-cost" => {
                i += 1;
                move_cost = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(move_cost);
            }
            "--energy" => {
                i += 1;
                energy = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(energy);
            }
            "--field" => {
                i += 1;
                field_kind = args.get(i).cloned().unwrap_or(field_kind);
            }
            "--memory-life" => {
                i += 1;
                memory_life = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(memory_life);
            }
            "--shift" => {
                i += 1;
                shift = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(shift);
            }
            "--rich" => {
                i += 1;
                rich = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(rich);
            }
            "--poor" => {
                i += 1;
                poor = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(poor);
            }
            "--feed" => {
                feed = true;
            }
            "--regrow" => {
                i += 1;
                regrow = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(regrow);
            }
            "--help" | "-h" => {
                println!("usage: trace [--policy stay|random|remember|memory|sighted] [--steps N] [--every K] [--seed S] [--n N] [--cells C]");
                println!("             [--capacity X] [--damage-rate X] [--income X] [--maintenance X]");
                println!("             [--repair-cost X] [--move-cost X] [--energy X]");
                println!("             [--field alternating|gradient|uniform|moving] [--memory-life N] [--shift X]");
                println!("             [--rich X] [--poor X] [--regrow X]");
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
        income,
        maintenance_cost: maintenance,
        repair_cost,
        damage_rate,
        capacity,
    };
    let field = match field_kind.as_str() {
        "alternating" => Field::alternating(cells, rich, poor, regrow),
        "gradient" => Field::gradient(cells, poor, rich, regrow),
        "uniform" => Field::new(cells, (rich + poor) / 2.0, regrow),
        "moving" => Field::moving(cells, rich, poor, regrow, if shift > 0.0 { shift } else { 1.0 }),
        other => {
            eprintln!("unknown field: {} (expected alternating, gradient, uniform)", other);
            std::process::exit(2);
        }
    };
    let field = match field {
        Some(f) => f,
        None => {
            eprintln!("cannot build the field");
            std::process::exit(1);
        }
    };
    let mut life = match Life::spawn(world, field, n, energy, move_cost, policy, seed, memory_life) {
        Some(l) => l,
        None => {
            eprintln!("cannot build the cycle");
            std::process::exit(1);
        }
    };

    if feed {
        life.feed = true;
    }
    let trace = record(&mut life, steps, every);

    let name = match policy {
        Policy::Stay => "stay",
        Policy::Random => "random",
        Policy::Remember => "remember",
        Policy::Memory => "memory",
        Policy::Sighted => "sighted",
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
    println!("capacity: {}", capacity);
    println!("damage:   {}", damage_rate);
    println!("field:    {}", field_kind);
    println!("memlife:  {}", memory_life);
    println!("shift:    {}", shift);
    println!("rich:     {}", rich);
    println!("poor:     {}", poor);
    println!("regrow:   {}", regrow);
    println!("feed:     {}", feed);
    println!("steps:    {}", steps);
    println!("frames:   {}", trace.frames.len());
    println!("hash:     {:016x}", trace.hash);
    println!("written:  {}", path.display());
}
