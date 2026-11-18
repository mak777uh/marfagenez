//! Does the alternating fill generalise to another stock size?
//!
//! `FINDING-243` derived the edge of a one-cell world from the **alternating** fill: consumption is taken
//! before the inflow is credited, so the stock alternates between `1 - d/S` and `1`, where `d` is the
//! cell's demand and `S` the stock capacity. The average is `(1 + (1 - d/S)) / 2`, and the edge is
//! `sigma * p * mean - (mu*n + kappa*n^2/p)`.
//!
//! With `S = 100` and `d = 8` that gave 6.655, inside the measured `(6.65, 6.7)`. This sweeps `S`.
//!
//! PREDICTION, before the run - the formula alone, no fitting:
//!   S =  50: mean = (1 + 0.84)/2 = 0.920 -> edge = 8*0.92 - 1.025 = 6.335
//!   S = 100: mean = (1 + 0.92)/2 = 0.960 -> edge = 8*0.96 - 1.025 = 6.655
//!   S = 200: mean = (1 + 0.96)/2 = 0.980 -> edge = 8*0.98 - 1.025 = 6.815
//!
//! and at each edge minus 0.05 the world lives, at plus 0.05 it dies. If the formula generalises, all
//! three checks pass; if only `S = 100` worked, the alternation was a coincidence of one setting.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const SEEDS: u64 = 16;
const MARGIN: f64 = 0.05;

fn rules(f0: f64, stock: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(stock, INFLOW, stock);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn survivors(f0: f64, stock: f64) -> usize {
    let mut alive = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(f0, stock), vec![Form::square(1)]);
        let mut rng = Rng::new(seed);
        for _ in 0..STEPS {
            world.step(&mut rng);
        }
        if !world.forms.is_empty() {
            alive += 1;
        }
    }
    alive
}

/// the first-step fill, measured rather than assumed
fn first_fill(stock: f64) -> f64 {
    let mut world = ShapeWorld::new(rules(4.0, stock), vec![Form::square(1)]);
    let mut rng = Rng::new(1);
    world.step(&mut rng);
    world.stock / stock
}

fn main() {
    println!(
        "{:>6} {:>6} {:>8} {:>8} {:>8} {:>10} {:>10}",
        "S", "d", "f1 meas", "mean", "edge", "edge-0.05", "edge+0.05"
    );
    let mut bad = 0;
    for stock in [50.0f64, 100.0, 200.0] {
        let d = 8.0; // one cell: income = sigma * perimeter = 2 * 4
        let f1 = first_fill(stock);
        let predicted_f1 = 1.0 - d / stock;
        let mean = (1.0 + predicted_f1) / 2.0;
        let edge = 8.0 * mean - 1.025;
        let below = survivors(edge - MARGIN, stock);
        let above = survivors(edge + MARGIN, stock);
        println!(
            "{stock:>6.0} {d:>6.1} {f1:>8.3} {mean:>8.3} {edge:>8.3} {below:>10} {above:>10}"
        );

        let fill_ok = (f1 - predicted_f1).abs() < 0.01;
        let ok = fill_ok && below == SEEDS as usize && above == 0;
        if !fill_ok {
            println!("      WRONG first fill: measured {f1:.3}, predicted {predicted_f1:.3}");
        }
        if !ok {
            bad += 1;
        }
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена: формула обобщается на все три размера запаса.");
}
