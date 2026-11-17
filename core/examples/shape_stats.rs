//! Statistics instead of one more single run: twenty-four runs per setting.
//!
//! `FINDING-223` ended with the admission that nine single runs had each corrected the last one.
//! This replaces the single run with a distribution: twenty-four independent runs per setting,
//! the **median** side of the surviving forms, an interquartile range, and the fraction of forms
//! whose side lies inside the solvency interval of `FINDING-219` (1.571 ... 5.420 for `f0 = 10`).
//!
//! A note on replication, because this project has been strict about it (`FINDING-158`: the unit
//! of replication is the environment, not the seed). Here there is one environment - one set of
//! prices and one patch structure - and the variation is **stochastic**, so twenty-four runs give
//! a distribution of outcomes for that environment. That is a weaker claim than "over
//! environments", and it is stated that way.
//!
//! PREDICTION, before the run:
//!   (a) with a per-cell birth price the median side falls inside the interval;
//!   (b) without it the median side lies above the interval;
//!   (c) the spread is wide enough that a single run could have landed anywhere - which is the
//!       reason the earlier single runs disagreed.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const INTERVAL: (f64, f64) = (1.571, 5.420);

fn rules(per_cell: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(10.0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = per_cell;
    r
}

fn side_of(f: &Form) -> f64 {
    let (lo, hi) = f.extent();
    ((hi.0 - lo.0 + 1) as f64).max((hi.1 - lo.1 + 1) as f64)
}

fn median(xs: &mut [f64]) -> f64 {
    if xs.is_empty() {
        return f64::NAN;
    }
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    if n % 2 == 1 {
        xs[n / 2]
    } else {
        (xs[n / 2 - 1] + xs[n / 2]) / 2.0
    }
}

/// One run: the sides of the forms alive at the end (empty when the world died out).
fn one_run(per_cell: f64, seed: u64) -> Vec<f64> {
    let mut world = ShapeWorld::new(rules(per_cell), vec![Form::square(3)]);
    let mut rng = Rng::new(seed);
    for _ in 0..400 {
        world.step(&mut rng);
    }
    world.forms.iter().map(|f| side_of(&f.form)).collect()
}

fn main() {
    let runs = 24u64;
    for per_cell in [0.0, 4.0] {
        let mut run_medians = Vec::new();
        let mut all_sides = Vec::new();
        let mut empty = 0;
        for seed in 1..=runs {
            let sides = one_run(per_cell, seed);
            if sides.is_empty() {
                empty += 1;
                continue;
            }
            let m = median(&mut sides.clone());
            run_medians.push(m);
            all_sides.extend(sides.iter().copied());
        }
        let mut rm = run_medians.clone();
        let med = median(&mut rm);
        let mut sorted_runs = run_medians.clone();
        sorted_runs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let q1 = sorted_runs[sorted_runs.len() / 4];
        let q3 = sorted_runs[sorted_runs.len() * 3 / 4];
        let inside = all_sides
            .iter()
            .filter(|s| **s >= INTERVAL.0 && **s <= INTERVAL.1)
            .count() as f64
            / all_sides.len().max(1) as f64;
        println!(
            "per_cell {per_cell:>4}: runs {} empty {empty}  median of run-medians {med:.2}  \
             runs IQR [{q1:.1}, {q3:.1}]  sides in interval {:.0}%  forms {}",
            run_medians.len(),
            inside * 100.0,
            all_sides.len()
        );
        println!(
            "                     run medians: {:?}",
            run_medians
                .iter()
                .map(|m| (m * 10.0).round() / 10.0)
                .collect::<Vec<_>>()
        );
        println!();
    }
}
