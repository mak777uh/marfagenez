//! Is "37% of the surplus" a law or a number for one world?
//!
//! `FINDING-211` placed the crossing where six looks cost about 37% of the surplus
//! `income - upkeep`. That is a single world: surplus 0.4 and a window of six looks. If
//! the figure is structural, the crossing price should scale as
//!
//!     c*  ≈  fraction * surplus / (2k)
//!
//! with the same `fraction` for every surplus and every window. This runs four worlds that
//! differ in both.
//!
//! PREDICTION, before the run:
//!   (a) each world has a crossing inside its swept range;
//!   (b) the measured `fraction = 2k * c* / surplus` is within 40% of 0.375 in every world
//!       - a wide band, because each crossing is a point estimate from eight environments;
//!   (c) the crossing price falls as the window widens and rises with the surplus.
//!
//! If (b) fails, the 37% is a fact about one world and has to be reported as such.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const UPKEEP: f64 = 0.6;
const REGROW: f64 = 0.99;
const CELLS: usize = 24;
const STEPS: usize = 2000;
const MUTATION: f64 = 0.30;
const BUDGET: usize = 12;
const PERIOD: usize = 12;
const FRACTION: f64 = 0.375;

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

fn difference(income: f64, radius: usize, read_cost: f64) -> f64 {
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
            assert!(life.set_sight_radius(radius));
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

fn crossing(income: f64, radius: usize) -> Option<f64> {
    // A FIXED absolute grid, not one scaled by the hypothesis under test. The first
    // version swept `0 .. 2 * predicted`, which meant that wherever the prediction was
    // low the search stopped early: two worlds reported "no crossing" and that answer
    // could not distinguish "the fraction is bigger" from "the fraction is not
    // constant". The range must not depend on the thing being tested.
    let grid = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.16, 0.20];
    let mut prev: Option<(f64, f64)> = None;
    for price in grid {
        let d = difference(income, radius, price);
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
        "{:>7} {:>4} {:>8} {:>10} {:>10} {:>9}",
        "income", "k", "looks", "surplus", "crossing", "fraction"
    );
    let worlds = [(1.0, 3usize), (1.2, 3), (1.0, 2), (1.0, 5)];
    let mut bad = 0;
    for (income, radius) in worlds {
        let surplus = income - UPKEEP;
        let looks = 2 * radius;
        match crossing(income, radius) {
            Some(c) => {
                let fraction = looks as f64 * c / surplus;
                let ok = (fraction - FRACTION).abs() / FRACTION <= 0.40;
                println!(
                    "{income:>7.2} {radius:>4} {looks:>8} {surplus:>10.2} {c:>10.4} {fraction:>9.3}{}",
                    if ok { "" } else { "  <- outside the band" }
                );
                if !ok {
                    bad += 1;
                }
            }
            None => {
                println!("{income:>7.2} {radius:>4} {looks:>8} {surplus:>10.2}   no crossing");
                bad += 1;
            }
        }
    }
    println!();
    println!("declared fraction: {FRACTION} (2k * c* / surplus), band +/- 40%");
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена: доля сохраняется.");
}
