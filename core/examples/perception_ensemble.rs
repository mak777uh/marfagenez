//! Does a window beat memory when both finally have a signal?
//!
//! `checks/perception_signal.py` measured that a one-neighbour rule is silent in 71% of
//! the sea between islands, so the medium could reward returning but never searching, and
//! every earlier comparison between memory and sight was therefore ill-posed.
//! `Life::set_sight_radius(3)` gives sight a signal.
//!
//! PREDICTION, written before the run:
//!   (a) with the window, `Sighted` takes a larger share than `Memory` at **sparse**
//!       spacing (period 12), because memory needs the island to have been found first
//!       while a window finds it on the first pass;
//!   (b) at **dense** spacing (period 4) the two do not separate, because the island is
//!       visible to a single neighbour there and the window buys nothing;
//!   (c) `Random` loses share at both, and more at the sparse spacing.
//!
//! If (a) fails, the honest conclusion is that a signal is necessary but not sufficient,
//! and the advantage of perception over memory is not established in this architecture.

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

fn run(period: usize, rich: f64, seed: u64, read_cost: f64) -> ([usize; 5], usize) {
    let organisms: Vec<Remembering> = (0..CELLS)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(read_cost),
        Field::peaks(CELLS, rich, 1.65, REGROW, period).expect("valid field"),
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
    (life.policy_census(), life.organisms_alive())
}

/// Percentile bootstrap over environments, the only interval this project uses.
fn bootstrap_ci(xs: &[f64], draws: usize) -> (f64, f64) {
    if xs.len() < 2 {
        return (0.0, 0.0);
    }
    let mut means = Vec::with_capacity(draws);
    let mut state: u64 = 0x9E3779B97F4A7C15;
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

fn mean(xs: &[f64]) -> f64 {
    if xs.is_empty() {
        0.0
    } else {
        xs.iter().sum::<f64>() / xs.len() as f64
    }
}

fn main() {
    // Reading is free by default, and that made the earlier comparison unfair: a window
    // of radius three costs six looks per step while memory costs two, so sight was
    // buying information with a currency nobody charged for. `read_cost` exists and is
    // already exercised elsewhere (`FINDING-156`), so this runs the same comparison at
    // two prices: free, and paid.
    for read_cost in [0.0, 0.05, 0.15] {
        println!();
        println!("read_cost = {read_cost} per look");
        println!(
            "{:<10} {:>6} {:>8} {:>9} {:>8} {:>8} {:>7}",
            "period", "alive", "random", "remember", "memory", "sighted", "n"
        );
        for period in [4usize, 12] {
            let mut shares: Vec<[f64; 5]> = Vec::new();
            let mut alive_sum = 0usize;
            for rich in [2.5, 3.0] {
                for seed in 1..=4u64 {
                    let (census, alive) = run(period, rich, seed, read_cost);
                    let total: usize = census.iter().sum();
                    alive_sum += alive;
                    let denom = total.max(1) as f64;
                    shares.push([
                        census[0] as f64 / denom,
                        census[1] as f64 / denom,
                        census[2] as f64 / denom,
                        census[3] as f64 / denom,
                        census[4] as f64 / denom,
                    ]);
                }
            }
            let n = shares.len();
            let col = |k: usize| mean(&shares.iter().map(|s| s[k]).collect::<Vec<_>>());
            let memory: Vec<f64> = shares.iter().map(|s| s[3]).collect();
            let sighted: Vec<f64> = shares.iter().map(|s| s[4]).collect();
            let (mlo, mhi) = bootstrap_ci(&memory, 2000);
            let (slo, shi) = bootstrap_ci(&sighted, 2000);
            println!(
                "{period:<10} {:>6} {:>8.3} {:>9.3} {:>8.3} {:>8.3} {n:>7}",
                alive_sum / n,
                col(1),
                col(2),
                col(3),
                col(4)
            );
            println!(
                "           memory 90% [{mlo:.3}, {mhi:.3}]   sighted 90% [{slo:.3}, {shi:.3}]"
            );
        }
    }
    println!();
    println!("predicted: pricing the look shrinks the window's advantage");
}
