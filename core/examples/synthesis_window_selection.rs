//! The synthesis: two closed lines in one world, with a prediction from the calculation.
//!
//! The perception line measured that a one-neighbour rule is silent on the flat sea; the selection
//! line measured that a population's policy mix follows the spacing of the medium. Neither line ran
//! with **variation and a window together**. `checks/synthesis_visibility.py` gives the visibility
//! fraction for a window of three: 0.75 at spacing 4, 0.62 at spacing 8, 0.38 at spacing 12.
//!
//! The look is **priced** at 0.03, because `FINDING-210` measured that a free look is worth nothing
//! in this economy and the first version of this probe accordingly found nothing.
//!
//! PREDICTION, before the run:
//!   (a) the evolved share of `Sighted` falls with the spacing: p4 > p8 > p12;
//!   (b) its order of magnitude follows the visibility fraction - share near 0.75 / 0.62 / 0.38
//!       is too strong a claim for a binary "was it seen" measure, so the weaker one is declared:
//!       the share at spacing 4 should be at least twice the share at spacing 12;
//!   (c) `Random` keeps the majority in every world, as it did without a window.
//!
//! If (a) fails, the visibility of the medium does not select behaviour in this world and the two
//! lines do not combine.

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

fn world() -> World {
    World {
        income: INCOME,
        read_cost: 0.03,
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

fn census(period: usize, rich: f64, seed: u64) -> [usize; 5] {
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
    assert!(life.set_sight_radius(RADIUS));
    for _ in 0..STEPS {
        life.advance();
    }
    life.policy_census()
}

fn share(census: &[usize; 5], k: usize) -> f64 {
    let total: usize = census.iter().sum();
    if total == 0 {
        0.0
    } else {
        census[k] as f64 / total as f64
    }
}

fn main() {
    println!(
        "{:>8} {:>10} {:>8} {:>9} {:>8} {:>8} {:>7}",
        "period", "visibility", "random", "remember", "memory", "sighted", "alive"
    );
    let mut sighted = Vec::new();
    for period in [4usize, 8, 12] {
        let mut sum = [0.0f64; 5];
        let mut alive = 0;
        let mut n = 0.0;
        for rich in [2.5, 3.0] {
            for seed in 1..=8u64 {
                let c = census(period, rich, seed);
                for k in 0..5 {
                    sum[k] += share(&c, k);
                }
                alive += c.iter().sum::<usize>();
                n += 1.0;
            }
        }
        let visibility = match period {
            4 => 0.75,
            8 => 0.62,
            _ => 0.38,
        };
        sighted.push((period, sum[4] / n));
        println!(
            "{period:>8} {visibility:>10.2} {:>8.2} {:>9.2} {:>8.2} {:>8.2} {:>7.0}",
            sum[1] / n,
            sum[2] / n,
            sum[3] / n,
            sum[4] / n,
            alive as f64 / n
        );
    }

    println!();
    let falling = sighted.windows(2).all(|w| w[1].1 <= w[0].1);
    let ratio = sighted.first().map(|(_, a)| *a).unwrap_or(0.0)
        / sighted.last().map(|(_, b)| *b).unwrap_or(f64::NAN);
    let mut bad = 0;
    println!(
        "  {} (a) the sighted share falls with the spacing  [{:?}]",
        if falling { "ok   " } else { "WRONG" },
        sighted.iter().map(|(p, s)| (*p, (*s * 1000.0).round() / 1000.0)).collect::<Vec<_>>()
    );
    if !falling {
        bad += 1;
    }
    println!(
        "  {} (b) the share at spacing 4 is at least twice the share at 12  [{ratio:.2}x]",
        if ratio >= 2.0 { "ok   " } else { "WRONG" }
    );
    if ratio < 2.0 {
        bad += 1;
    }
    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
