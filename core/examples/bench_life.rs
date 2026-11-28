//! Reproducible release-mode microbenchmark for Life::advance.
//!
//! Build/run:
//!   cargo build --release --example bench_life
//!   ./target/release/examples/bench_life --populations 24,256,1024 \
//!       --cells 40,256,1024 --steps 1000 --repeats 7 \
//!       --policy stay --share sequential
//!
//! This reports raw timings, not a pass/fail performance claim. Run baseline
//! and candidate on the same host, toolchain, power mode and input matrix.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{ShareProtocol, World};
use std::time::{Duration, Instant};

fn parse_list(raw: &str, name: &str) -> Vec<usize> {
    let values = raw.split(',')
        .map(|part| part.parse::<usize>().unwrap_or_else(|_| {
            eprintln!("{name}: invalid integer {part:?}");
            std::process::exit(2);
        }))
        .collect::<Vec<_>>();
    if values.is_empty() || values.iter().any(|value| *value == 0) {
        eprintln!("{name}: values must be positive integers");
        std::process::exit(2);
    }
    values
}

fn usage() {
    println!("bench_life [--populations 24,256] [--cells 40,256]");
    println!("           [--steps 1000] [--repeats 7]");
    println!("           [--policy stay|random|remember|memory|sighted]");
    println!("           [--share sequential|proportional]");
}

fn parse_args() -> (String, String, usize, usize, Policy, ShareProtocol) {
    let mut populations = "24,256".to_string();
    let mut cells = "40,256".to_string();
    let mut steps = 1000usize;
    let mut repeats = 7usize;
    let mut policy = Policy::Stay;
    let mut share = ShareProtocol::Sequential;
    let mut iter = std::env::args().skip(1);
    while let Some(flag) = iter.next() {
        match flag.as_str() {
            "--help" | "-h" => { usage(); std::process::exit(0); }
            "--populations" => populations = iter.next().unwrap_or_else(|| {
                eprintln!("--populations requires a value"); std::process::exit(2)
            }),
            "--cells" => cells = iter.next().unwrap_or_else(|| {
                eprintln!("--cells requires a value"); std::process::exit(2)
            }),
            "--steps" => steps = iter.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| {
                eprintln!("--steps requires a positive integer"); std::process::exit(2)
            }),
            "--repeats" => repeats = iter.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| {
                eprintln!("--repeats requires a positive integer"); std::process::exit(2)
            }),
            "--policy" => {
                let value = iter.next().unwrap_or_default();
                policy = match value.as_str() {
                    "stay" => Policy::Stay,
                    "random" => Policy::Random,
                    "remember" => Policy::Remember,
                    "memory" => Policy::Memory,
                    "sighted" => Policy::Sighted,
                    _ => { eprintln!("unknown policy: {value}"); std::process::exit(2); }
                };
            }
            "--share" => {
                let value = iter.next().unwrap_or_default();
                share = match value.as_str() {
                    "sequential" => ShareProtocol::Sequential,
                    "proportional" => ShareProtocol::Proportional,
                    _ => { eprintln!("unknown share protocol: {value}"); std::process::exit(2); }
                };
            }
            _ => { eprintln!("unknown option: {flag}"); usage(); std::process::exit(2); }
        }
    }
    if steps == 0 || repeats == 0 {
        eprintln!("steps and repeats must be positive");
        std::process::exit(2);
    }
    (populations, cells, steps, repeats, policy, share)
}

fn policy_name(policy: Policy) -> &'static str {
    match policy {
        Policy::Stay => "stay",
        Policy::Random => "random",
        Policy::Remember => "remember",
        Policy::Memory => "memory",
        Policy::Sighted => "sighted",
    }
}

fn share_name(share: ShareProtocol) -> &'static str {
    match share {
        ShareProtocol::Sequential => "sequential",
        ShareProtocol::Proportional => "proportional",
    }
}

fn run_once(population: usize, cells: usize, steps: usize, policy: Policy,
            share: ShareProtocol, seed: u64) -> (Duration, usize, usize, u64) {
    let world = World { share, ..World::default() };
    let field = Field::new(cells, 10.0, 0.2).expect("valid benchmark field");
    let mut life = Life::spawn_even(
        world, field, population, 10.0, 0.1, policy, seed, 300
    ).expect("valid benchmark population");
    let started = Instant::now();
    let mut completed = 0usize;
    for _ in 0..steps {
        if life.advance().is_none() { break; }
        completed += 1;
    }
    let elapsed = started.elapsed();
    let census = life.census();
    (elapsed, completed, census.alive, census.moves)
}

fn median(values: &mut [u128]) -> u128 {
    values.sort_unstable();
    values[values.len() / 2]
}

fn main() {
    let (populations_arg, cells_arg, steps, repeats, policy, share) = parse_args();
    let populations = parse_list(&populations_arg, "--populations");
    let cell_counts = parse_list(&cells_arg, "--cells");

    println!(
        "{{\"schema\":\"marfagenez.life-bench.v1\",\"policy\":\"{}\",\"share\":\"{}\",\"steps_requested\":{},\"repeats\":{}}}",
        policy_name(policy), share_name(share), steps, repeats
    );
    for &population in &populations {
        for &cells in &cell_counts {
            // One untimed warm-up per cell keeps first-use effects out of samples.
            let _ = run_once(population, cells, steps.min(100), policy, share, 0xBEEF);
            let mut nanos = Vec::with_capacity(repeats);
            let mut completed = 0usize;
            let mut alive = 0usize;
            let mut moves = 0u64;
            for repeat in 0..repeats {
                let (elapsed, did_steps, survivors, move_count) = run_once(
                    population, cells, steps, policy, share,
                    0xBEEF_u64.wrapping_add(repeat as u64),
                );
                nanos.push(elapsed.as_nanos());
                completed = did_steps;
                alive = survivors;
                moves = move_count;
            }
            let median_ns = median(&mut nanos);
            let ns_per_step = median_ns as f64 / completed.max(1) as f64;
            println!(
                "{{\"population\":{},\"cells\":{},\"steps_completed\":{},\"median_ns\":{},\"ns_per_step\":{:.2},\"alive\":{},\"moves_last_repeat\":{},\"samples_ns\":[{}]}}",
                population, cells, completed, median_ns, ns_per_step, alive, moves,
                nanos.iter().map(u128::to_string).collect::<Vec<_>>().join(",")
            );
        }
    }
}
