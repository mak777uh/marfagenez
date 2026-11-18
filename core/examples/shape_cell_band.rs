//! The decisive case: a fixed cost where the two arithmetics disagree.
//!
//! `FINDING-241` left a corridor for a one-cell world: `[6.34, 6.975]`. The two hypotheses differ in the
//! band between them - full-stock arithmetic says a cell survives up to `f0 = 6.975`, and charging the
//! first step's own consumption (which leaves the stock at `1 - 8/100 = 0.92`) says it dies above
//! `6.34`. Sweeping `f0` inside that band separates them.
//!
//! PREDICTION, before the run:
//!   (a) the stock after the first step is 0.92, not 1.00, because one cell consumes eight of a hundred;
//!   (b) at `f0 = 6.5` and `6.7` - inside the band - no seed survives: the fill binds, and the cell dies
//!       before the stock can recover;
//!   (c) at `f0 = 7` nothing survives either, which both hypotheses agree on.
//!
//! If (b) is wrong and the worlds live, then the full-stock arithmetic is what binds and the corridor
//! collapses to 6.975.

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

/// survivors, and the fill fraction after the first step of the first seed
fn run(f0: f64) -> (usize, f64, usize) {
    let mut alive = 0;
    let mut first_fill = f64::NAN;
    let mut death_step = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(1)]);
        let mut rng = Rng::new(seed);
        let mut died_at = 0;
        for step in 0..STEPS {
            world.step(&mut rng);
            let f = world.stock / CELLS;
            if step == 0 && seed == 1 {
                first_fill = f;
            }
            if world.forms.is_empty() && died_at == 0 {
                died_at = step + 1;
            }
        }
        if !world.forms.is_empty() {
            alive += 1;
        } else if death_step == 0 {
            death_step = died_at;
        }
    }
    (alive, first_fill, death_step)
}

fn main() {
    println!(
        "{:>6} {:>13} {:>10} {:>12}",
        "f0", "f after step 1", "survivors", "first death"
    );
    let mut rows: Vec<(f64, usize, f64, usize)> = Vec::new();
    for f0 in [6.5, 6.6, 6.65, 6.7] {
        let (alive, fill, death) = run(f0);
        println!("{f0:>6.1} {fill:>13.3} {alive:>10} {death:>12}");
        rows.push((f0, alive, fill, death));
    }

    println!();
    let mut bad = 0;
    let at = |f: f64| {
        rows.iter()
            .find(|r| (r.0 - f).abs() < 1e-9)
            .map(|r| r.1)
            .unwrap_or(99)
    };
    let fill = rows[0].2;

    let checks = [
        (format!("(a) one cell leaves the stock at 0.92 (got {fill:.3})"), (fill - 0.92).abs() < 0.02),
        ("(b) inside the band, at 6.5 and 6.7, nothing survives".to_string(), at(6.5) == 0 && at(6.7) == 0),
        ("(c) at 7.0 nothing survives".to_string(), at(7.0) == 0),
        ("    and 6.0 still lives, so the edge is above it".to_string(), at(6.0) > 0),
    ];
    for (label, ok) in checks {
        println!("  {} {label}", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
