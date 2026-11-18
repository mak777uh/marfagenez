//! Does the arithmetic that explained the dead single-cell start actually hold?
//!
//! `FINDING-239` found that a world started from one cell dies in twenty-four of twenty-four seeds at
//! `f0 = 10`, and explained it: the first step of consumption leaves `f = 0.76`, the cell's income is
//! `0.76 * 8 = 6.08`, and its upkeep is `f0 + mu*n + kappa*n^2/p = f0 + 1 + 0.025`. Solving
//! `6.08 >= f0 + 1.025` gives `f0 <= 5.055`.
//!
//! An explanation that is only asserted is not an explanation. This sweeps the fixed cost across that
//! boundary.
//!
//! PREDICTION, before the run:
//!   (a) at `f0 = 3` and `f0 = 4` every seed survives;
//!   (b) at `f0 = 6`, above the computed edge of 5.055, **no** seed survives;
//!   (c) the transition happens between 5 and 6, i.e. `f0 = 5` survives at least once and `f0 = 6`
//!       never does.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const SEEDS: u64 = 24;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn survivors(f0: f64) -> usize {
    let mut alive = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(1)]);
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

fn main() {
    println!("{:>6} {:>10} {:>9}", "f0", "survivors", "of");
    let mut table = Vec::new();
    for f0 in [3.0, 4.0, 5.0, 6.0, 7.0] {
        let n = survivors(f0);
        println!("{f0:>6.1} {n:>10} {SEEDS:>9}");
        table.push((f0, n));
    }

    let edge = 6.08 - 1.025;
    println!();
    println!("computed edge for a single cell: f0 <= {edge:.3}");
    println!();
    let mut bad = 0;

    let at = |f: f64| table.iter().find(|(x, _)| *x == f).map(|(_, n)| *n).unwrap_or(0);
    let checks = [
        ("(a) f0 = 3 and 4: every seed survives", at(3.0) == SEEDS as usize && at(4.0) == SEEDS as usize),
        ("(b) f0 = 6: no seed survives", at(6.0) == 0),
        ("(c) the transition is between 5 and 6", at(5.0) > 0 && at(6.0) == 0),
        ("    and f0 = 7 stays dead", at(7.0) == 0),
    ];
    for (label, ok) in checks {
        println!("  {} {label}", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }
    // a one-cell world at f0 = 5 is a concentration this model did not promise; if it fails the
    // arithmetic edge is not exactly where the formula puts it
    if at(5.0) == 0 {
        println!("  note: f0 = 5 died everywhere, so the edge is below 5.055");
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
