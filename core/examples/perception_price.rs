//! Where is the price at which searching stops paying? The crossing, not three points.
//!
//! `FINDING-210` measured three prices: at zero the sighted share is marginally ahead, at
//! 0.05 it collapses to a seventh of memory's, at 0.15 it is extinct. A crossing between
//! the first two is the number worth having: **how many times cheaper must information be
//! before searching pays?**
//!
//! Sweep, declared before the run: periods 12 only (sparse, where a window is supposed to
//! help), eight environments per price, prices 0.000 to 0.050 in steps of 0.010.
//!
//! PREDICTION:
//!   (a) the sighted-minus-memory difference is positive at 0.00 and negative at 0.05, so
//!       a crossing exists in the swept range;
//!   (b) the crossing lies where six looks cost between a quarter and a half of the
//!       surplus `income - upkeep = 0.4`, i.e. `read_cost` between 0.017 and 0.033;
//!   (c) the sighted share falls monotonically with the price.
//!
//! If (a) fails the earlier three points were noise and there is no crossing to report.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const INCOME: f64 = 1.0;
const UPKEEP: f64 = 0.6;
const REGROW: f64 = 0.99;
const CELLS: usize = 24;
const STEPS: usize = 2000;
const MUTATION: f64 = 0.30;
const RADIUS: usize = 3;
const BUDGET: usize = 8;
const PERIOD: usize = 12;

fn world(read_cost: f64) -> World {
    World {
        income: INCOME,
        read_cost,
        maintenance_cost: UPKEEP,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: BUDGET,
        max_population: 24,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

fn shares(read_cost: f64, rich: f64, seed: u64) -> (f64, f64) {
    let organisms: Vec<Remembering> = (0..CELLS)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(read_cost),
        Field::peaks(CELLS, rich, 1.65, REGROW, PERIOD).expect("valid field"),
        organisms,
        vec![Policy::Random; CELLS],
        seed,
        32,
    )
    .expect("built");
    life.set_policy_mutation(MUTATION);
    assert!(life.set_sight_radius(RADIUS));
    for _ in 0..STEPS {
        life.advance();
    }
    let census = life.policy_census();
    let total: usize = census.iter().sum();
    let denom = total.max(1) as f64;
    (census[3] as f64 / denom, census[4] as f64 / denom)
}

fn mean(xs: &[f64]) -> f64 {
    if xs.is_empty() {
        0.0
    } else {
        xs.iter().sum::<f64>() / xs.len() as f64
    }
}

fn bootstrap_ci(xs: &[f64], draws: usize) -> (f64, f64) {
    if xs.len() < 2 {
        return (0.0, 0.0);
    }
    let mut means = Vec::with_capacity(draws);
    let mut state: u64 = 0xD1B54A32D192ED03;
    for _ in 0..draws {
        let mut acc = 0.0;
        for _ in 0..xs.len() {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            acc += xs[(state % xs.len() as u64) as usize];
        }
        means.push(acc / xs.len() as f64);
    }
    means.sort_by(|a, b| a.partial_cmp(b).unwrap());
    (means[draws / 40], means[draws - 1 - draws / 40])
}

fn main() {
    println!(
        "{:>9} {:>9} {:>9} {:>11} {:>24}",
        "read_cost", "memory", "sighted", "difference", "sighted-memory 90%"
    );
    let mut diffs: Vec<(f64, f64)> = Vec::new();
    for step in 0..=5 {
        let read_cost = 0.010 * step as f64;
        let mut memory = Vec::new();
        let mut sighted = Vec::new();
        for rich in [2.5, 3.0] {
            for seed in 1..=4u64 {
                let (m, s) = shares(read_cost, rich, seed);
                memory.push(m);
                sighted.push(s);
            }
        }
        let diff: Vec<f64> = memory
            .iter()
            .zip(sighted.iter())
            .map(|(m, s)| s - m)
            .collect();
        let (lo, hi) = bootstrap_ci(&diff, 2000);
        let d = mean(&diff);
        diffs.push((read_cost, d));
        println!(
            "{read_cost:>9.3} {:>9.3} {:>9.3} {:>+11.3} {:>24}",
            mean(&memory),
            mean(&sighted),
            d,
            format!("[{lo:+.3}, {hi:+.3}]")
        );
    }

    println!();
    let first = diffs.first().copied().unwrap_or((0.0, 0.0));
    let last = diffs.last().copied().unwrap_or((0.0, 0.0));
    let crossing = diffs
        .windows(2)
        .find(|w| w[0].1 > 0.0 && w[1].1 <= 0.0)
        .map(|w| (w[0].0, w[1].0));
    let monotone = diffs.windows(2).all(|w| w[1].1 <= w[0].1 + 1e-9);
    let mut bad = 0;
    let ok_a = first.1 > 0.0 && last.1 < 0.0;
    println!("  {} (a) positive at the cheapest price and negative at the dearest [{:?}]",
             if ok_a { "ok   " } else { "WRONG" }, (first.1, last.1));
    if !ok_a { bad += 1; }

    let ok_cross = crossing.is_some();
    println!("  {} (a) a crossing exists in the swept range [{:?}]",
             if ok_cross { "ok   " } else { "WRONG" }, crossing);
    if !ok_cross { bad += 1; }

    let ok_b = crossing.map(|(a, b)| a >= 0.01 && b <= 0.04).unwrap_or(false);
    println!("  {} (b) the crossing lies within [0.01, 0.04] [{:?}]",
             if ok_b { "ok   " } else { "WRONG" }, crossing);
    if !ok_b { bad += 1; }

    println!("  {} (c) the sighted advantage falls monotonically [{:?}]",
             if monotone { "ok   " } else { "WRONG" },
             diffs.iter().map(|(c, d)| (*c, *d)).collect::<Vec<_>>());
    if !monotone { bad += 1; }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
