//! The ensemble that `FINDING-205` asked for: is the memory share a signal or a fluke?
//!
//! `FINDING-205` found the memory share rising from one to four of twenty-four on one
//! patchy world, and said plainly that this is a signal, not an effect, and that the
//! unit of replication has to be the **environment** (`FINDING-158`), not the seed.
//!
//! This runs a declared family of environments and reports the memory share with a
//! bootstrap interval over environments.
//!
//!   periods   4, 6, 8, 12 cells between rich islands
//!   rich      2.5, 3.0        poor 1.65 (above upkeep: FINDING-203)
//!   seeds     1..4
//!   controls  uniform-poor 1.65 and uniform-rich 3.0
//!
//! PREDICTION, before the run:
//!   (a) the mean memory share in patchy environments exceeds the uniform controls;
//!   (b) it grows with island spacing (12 > 8 > 6 > 4), because the further the island,
//!       the less a one-neighbour look can find it and the more returning is worth;
//!   (c) the two richness levels do not separate - spacing is the variable, not wealth.
//!
//! If (b) fails, the earlier finding was a fluke of one period and the honest statement
//! is that patchiness as such was never shown to matter.

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

fn world() -> World {
    World {
        income: INCOME,
        maintenance_cost: UPKEEP,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 3,
        max_population: 24,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

/// The share of memory-holders among the living, and the population.
fn run(field: Field, seed: u64) -> (f64, usize) {
    let organisms: Vec<Remembering> = (0..CELLS)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(),
        field,
        organisms,
        vec![Policy::Random; CELLS],
        seed,
        32,
    )
    .expect("built");
    life.set_policy_mutation(MUTATION);
    for _ in 0..STEPS {
        life.advance();
    }
    let census = life.policy_census();
    let alive = life.organisms_alive();
    let share = if alive == 0 {
        0.0
    } else {
        census[3] as f64 / alive as f64
    };
    (share, alive)
}

fn mean(xs: &[f64]) -> f64 {
    if xs.is_empty() {
        0.0
    } else {
        xs.iter().sum::<f64>() / xs.len() as f64
    }
}

/// Percentile bootstrap over the given values.
fn bootstrap_ci(xs: &[f64], draws: usize) -> (f64, f64) {
    if xs.len() < 2 {
        return (0.0, 0.0);
    }
    let mut means = Vec::with_capacity(draws);
    let mut state: u64 = 0x2545F4914F6CDD1D;
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
    let lo = means[draws / 40];
    let hi = means[draws - 1 - draws / 40];
    (lo, hi)
}

fn main() {
    println!(
        "{:<18} {:>6} {:>8} {:>18} {:>8}",
        "class", "n", "mean", "[5%, 95%]", "alive"
    );

    let mut all_patchy: Vec<f64> = Vec::new();
    let mut by_period: Vec<(usize, Vec<f64>)> = Vec::new();

    for period in [4usize, 8, 12, 16, 20, 24] {
        let mut shares = Vec::new();
        let mut alive_sum = 0usize;
        for rich in [2.5, 3.0] {
            for seed in 1..=4u64 {
                let field = Field::peaks(CELLS, rich, 1.65, REGROW, period).expect("field");
                let (share, alive) = run(field, seed);
                shares.push(share);
                alive_sum += alive;
            }
        }
        let islands = CELLS / period;
        let (lo, hi) = bootstrap_ci(&shares, 2000);
        println!(
            "period {period:<2} ({islands} isl) {:>6} {:>8.3} {:>18} {:>8}",
            shares.len(),
            mean(&shares),
            format!("[{lo:.3}, {hi:.3}]"),
            alive_sum / shares.len()
        );
        all_patchy.extend(shares.iter().copied());
        by_period.push((period, shares));
    }

    let (lo, hi) = bootstrap_ci(&all_patchy, 2000);
    println!(
        "patchy (all)       {:>6} {:>8.3} {:>18}",
        all_patchy.len(),
        mean(&all_patchy),
        format!("[{lo:.3}, {hi:.3}]")
    );

    for (name, level) in [("uniform-poor", 1.65), ("uniform-rich", 3.0)] {
        let mut shares = Vec::new();
        let mut alive_sum = 0usize;
        for seed in 1..=4u64 {
            let field = Field::new(CELLS, level, REGROW).expect("field");
            let (share, alive) = run(field, seed);
            shares.push(share);
            alive_sum += alive;
        }
        let (lo, hi) = bootstrap_ci(&shares, 2000);
        println!(
            "{name:<18} {:>6} {:>8.3} {:>18} {:>8}",
            shares.len(),
            mean(&shares),
            format!("[{lo:.3}, {hi:.3}]"),
            alive_sum / shares.len()
        );
    }

    println!();
    println!("spacing trend (predicted: rise to a peak, then fall when the island is too rare to feed anyone):");
    for (period, shares) in &by_period {
        println!("  period {period:>2}: mean memory share {:.3}", mean(shares));
    }
}
