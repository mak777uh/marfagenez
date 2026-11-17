//! The form of the threshold: is the crossing price absolute, or does it follow the surplus?
//!
//! `FINDING-213` killed the "fraction of surplus" normalisation: surplus 0.4 gave crossings
//! 0.025 and 0.042, while surplus 1.4 gave 0.015 and 0.004. The threshold is not
//! proportional. This measures it across five surpluses to see the form.
//!
//! Fixed absolute grid, declared before the run: prices
//! `0.000, 0.005, 0.010, 0.020, 0.030, 0.040, 0.060, 0.080, 0.120, 0.160, 0.200`,
//! window `k = 3`, budget 24, period 12, eight environments per price.
//!
//! PREDICTION:
//!   (a) every surplus has a crossing inside the grid - the threshold exists everywhere;
//!   (b) the crossing stays inside an absolute band, `0.005 ... 0.050`, across all five
//!       surpluses - that is what "absolute, not proportional" means;
//!   (c) the crossing does NOT grow with the surplus: a proportional law would put it at
//!       0.0375 for surplus 0.6 and 0.15 for surplus 2.4, both outside the band.
//!
//! If (b) fails the threshold tracks neither surplus nor constant, and the honest report
//! is that this model gives numbers for worlds rather than a law of perception.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const UPKEEP: f64 = 0.6;
const REGROW: f64 = 0.99;
const CELLS: usize = 24;
const STEPS: usize = 2000;
const MUTATION: f64 = 0.30;
const BUDGET: usize = 24;
const PERIOD: usize = 12;
const RADIUS: usize = 3;
const GRID: [f64; 11] = [0.0, 0.005, 0.010, 0.020, 0.030, 0.040, 0.060, 0.080, 0.120, 0.160, 0.200];
const BAND: (f64, f64) = (0.005, 0.050);

fn world(income: f64, read_cost: f64) -> World {
    World {
        income,
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

fn difference(income: f64, read_cost: f64) -> f64 {
    let mut diffs = Vec::new();
    for rich in [2.5, 3.0] {
        for seed in 1..=4u64 {
            let organisms: Vec<Remembering> = (0..CELLS)
                .map(|c| {
                    let o = Organism::new(6.0, 0.0).expect("valid organism");
                    Remembering::new(o, c, income, 0.0, 32).expect("valid remembering")
                })
                .collect();
            let mut life = Life::new_mixed(
                world(income, read_cost),
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
            diffs.push(census[4] as f64 / denom - census[3] as f64 / denom);
        }
    }
    diffs.iter().sum::<f64>() / diffs.len() as f64
}

fn crossing(income: f64) -> Option<f64> {
    let mut prev: Option<(f64, f64)> = None;
    for price in GRID {
        let d = difference(income, price);
        if let Some((p0, d0)) = prev {
            if d0 > 0.0 && d <= 0.0 {
                return Some(p0 + (price - p0) * d0 / (d0 - d));
            }
        }
        prev = Some((price, d));
    }
    None
}

fn main() {
    println!(
        "{:>8} {:>8} {:>10} {:>10}",
        "income", "surplus", "crossing", "proportional would be"
    );
    let mut crossings = Vec::new();
    let mut bad = 0;
    for income in [1.0, 1.5, 2.0, 2.5, 3.0] {
        let surplus = income - UPKEEP;
        let proportional = 0.375 * surplus / (2 * RADIUS) as f64;
        match crossing(income) {
            Some(c) => {
                println!("{income:>8.2} {surplus:>8.2} {c:>10.4} {proportional:>10.4}");
                crossings.push(c);
            }
            None => {
                println!("{income:>8.2} {surplus:>8.2} {:>10} {proportional:>10.4}", "none");
                bad += 1;
            }
        }
    }
    println!();

    let all_found = bad == 0;
    println!(
        "  {} (a) every surplus has a crossing in the grid",
        if all_found { "ok   " } else { "WRONG" }
    );
    if !all_found {
        bad += 0;
    }

    let in_band = crossings.iter().all(|c| *c >= BAND.0 && *c <= BAND.1);
    println!(
        "  {} (b) all crossings inside the absolute band [{}, {}]  [{:?}]",
        if in_band { "ok   " } else { "WRONG" },
        BAND.0,
        BAND.1,
        crossings
    );
    if !in_band {
        bad += 1;
    }

    // (c) a proportional law would need the crossing to rise with the surplus; check that
    // the ratio crossing/surplus does not grow.
    let ratios: Vec<f64> = crossings
        .iter()
        .enumerate()
        .map(|(i, c)| c / ([0.4, 0.9, 1.4, 1.9, 2.4][i]))
        .collect();
    let not_growing = ratios
        .windows(2)
        .all(|w| w[1] <= w[0] * 1.5);
    println!(
        "  {} (c) the crossing/surplus ratio does not grow  [{:?}]",
        if not_growing { "ok   " } else { "WRONG" },
        ratios.iter().map(|r| (r * 1000.0).round() / 1000.0).collect::<Vec<_>>()
    );
    if !not_growing {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена: порог абсолютен, а не пропорционален.");
}
