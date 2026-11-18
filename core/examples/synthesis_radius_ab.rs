//! The same price, two windows: does the window change anything at all?
//!
//! `FINDING-232` said the window gives no improvement even when a look is nearly free, but it
//! compared two runs at **different** prices and attached no interval. This compares radius 1 and
//! radius 3 at the **same** price, so the only difference is the window, and it reports a bootstrap
//! interval over environments.
//!
//! PREDICTION, before the run: the two intervals overlap at every spacing, i.e. the window changes
//! nothing measurable. If instead the radius-3 share is separated above radius 1 at the dense
//! spacing, then 232 was wrong and the window does help where the medium is dense.

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
const READ_COST: f64 = 0.002;
const BUDGET: usize = 8;

fn world() -> World {
    World {
        income: INCOME,
        read_cost: READ_COST,
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

fn memory_share(period: usize, rich: f64, seed: u64, radius: usize) -> f64 {
    let organisms: Vec<Remembering> = (0..CELLS)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(),
        Field::peaks(CELLS, rich, 1.65, REGROW, period).expect("valid field"),
        organisms,
        vec![Policy::Random; CELLS],
        seed,
        32,
    )
    .expect("built");
    life.set_policy_mutation(MUTATION);
    assert!(life.set_sight_radius(radius));
    for _ in 0..STEPS {
        life.advance();
    }
    let census = life.policy_census();
    let total: usize = census.iter().sum();
    if total == 0 {
        0.0
    } else {
        census[3] as f64 / total as f64
    }
}

fn mean(xs: &[f64]) -> f64 {
    xs.iter().sum::<f64>() / xs.len().max(1) as f64
}

fn bootstrap_ci(xs: &[f64], draws: usize) -> (f64, f64) {
    if xs.len() < 2 {
        return (0.0, 0.0);
    }
    let mut state: u64 = 0x2545F4914F6CDD1D;
    let mut means = Vec::with_capacity(draws);
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
    let runs = 16u64;
    println!(
        "{:>8} {:>8} {:>22} {:>22} {:>9}",
        "period", "radius", "memory share 90%", "difference 90%", "separated"
    );
    for period in [4usize, 8, 12] {
        let mut one = Vec::new();
        let mut three = Vec::new();
        for rich in [2.5, 3.0] {
            for seed in 1..=(runs / 2) {
                one.push(memory_share(period, rich, seed, 1));
                three.push(memory_share(period, rich, seed, 3));
            }
        }
        let (a_lo, a_hi) = bootstrap_ci(&one, 2000);
        let (b_lo, b_hi) = bootstrap_ci(&three, 2000);
        let diff: Vec<f64> = three.iter().zip(one.iter()).map(|(b, a)| b - a).collect();
        let (d_lo, d_hi) = bootstrap_ci(&diff, 2000);
        let separated = d_lo > 0.0 || d_hi < 0.0;
        println!(
            "{period:>8} {:>8} {:>10.3} [{:.3}, {:.3}] {:>8.3} [{:+.3}, {:+.3}] {:>9}",
            "1 vs 3",
            mean(&one),
            a_lo,
            a_hi,
            mean(&diff),
            d_lo,
            d_hi,
            if separated { "yes" } else { "no" }
        );
        println!(
            "         {:>8} {:>10.3} [{:.3}, {:.3}]",
            "radius 1", mean(&one), a_lo, a_hi
        );
        println!(
            "         {:>8} {:>10.3} [{:.3}, {:.3}]",
            "radius 3", mean(&three), b_lo, b_hi
        );
    }
    println!();
    println!("(a) the difference interval should contain zero everywhere -> no effect");
}
