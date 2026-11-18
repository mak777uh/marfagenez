//! The same statistics in the continuous measure `x = n/p`, which is what the economy actually prices.
//!
//! `FINDING-237` measured the size as the side of the bounding square, an integer, and the
//! interquartile range came out at exactly 2.00 in every setting - coarse enough that it could not
//! separate the settings. The economy's own measure is continuous: `x = cells / perimeter`, and a
//! square of side `s` has `x = s/4`. The solvency interval `[1.571, 5.420]` in side units is
//! `[0.393, 1.355]` in `x`.
//!
//! PREDICTION, before the run:
//!   (a) the median `x` lies inside `[0.393, 1.355]` at every price, as the median side did;
//!   (b) the interquartile range of `x` is **no longer identical** across the three settings - the
//!       integer measure gave 2.00 for all three, and a continuous one should not;
//!   (c) the share of forms whose `x` is above `x_limit` gets the same survival difference: at
//!       `per_cell = 0` some worlds die out, at `4` none do.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const F0: f64 = 10.0;
const SEEDS: u64 = 24;
/// side-unit interval from the paper, divided by four to become `x`
const X_INTERVAL: (f64, f64) = (1.571 / 4.0, 5.420 / 4.0);

fn rules(per_cell: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(F0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = per_cell;
    r
}

fn run(per_cell: f64) -> (Vec<f64>, usize) {
    let mut medians = Vec::new();
    let mut extinct = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(per_cell), vec![Form::square(2)]);
        let mut rng = Rng::new(seed);
        for _ in 0..STEPS {
            world.step(&mut rng);
        }
        if world.forms.is_empty() {
            extinct += 1;
            continue;
        }
        let mut xs: Vec<f64> = world.forms.iter().map(|f| f.form.x()).collect();
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        medians.push(xs[xs.len() / 2]);
    }
    medians.sort_by(|a, b| a.partial_cmp(b).unwrap());
    (medians, extinct)
}

fn quantile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    let idx = ((sorted.len() - 1) as f64 * q).round() as usize;
    sorted[idx]
}

fn main() {
    println!(
        "{:>9} {:>7} {:>8} {:>8} {:>18} {:>8}",
        "per_cell", "runs", "med x", "IQR x", "inside [0.393,1.355]", "extinct"
    );
    let mut out = Vec::new();
    for per_cell in [0.0, 2.0, 4.0] {
        let (medians, extinct) = run(per_cell);
        let m = quantile(&medians, 0.5);
        let iqr = quantile(&medians, 0.75) - quantile(&medians, 0.25);
        let inside = m >= X_INTERVAL.0 && m <= X_INTERVAL.1;
        println!(
            "{per_cell:>9.1} {:>7} {m:>8.3} {iqr:>8.3} {:>18} {extinct:>8}",
            medians.len(),
            if inside { "yes" } else { "no" }
        );
        out.push((per_cell, m, iqr, inside, extinct));
    }

    println!();
    let mut bad = 0;
    let all_inside = out.iter().all(|(_, _, _, inside, _)| *inside);
    println!(
        "  {} (a) the median x is inside the interval at every price",
        if all_inside { "ok   " } else { "WRONG" }
    );
    if !all_inside {
        bad += 1;
    }

    let iqrs: Vec<f64> = out.iter().map(|(_, _, i, _, _)| (i * 1000.0).round() / 1000.0).collect();
    let distinct = iqrs.windows(2).any(|w| w[0] != w[1]);
    println!(
        "  {} (b) the IQR differs across settings: {iqrs:?} (integer measure gave [2.0, 2.0, 2.0])",
        if distinct { "ok   " } else { "WRONG" }
    );
    if !distinct {
        bad += 1;
    }

    let extinct0 = out[0].4;
    let extinct4 = out[2].4;
    let survival_diff = extinct0 > extinct4;
    println!(
        "  {} (c) more worlds die without the per-cell price: {extinct0} vs {extinct4} of {SEEDS}",
        if survival_diff { "ok   " } else { "WRONG" }
    );
    if !survival_diff {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
