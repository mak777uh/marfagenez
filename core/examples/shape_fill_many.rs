//! Does the fill formula hold with several forms at once?
//!
//! `FINDING-244` confirmed `f = 1 - d/S` after the first step for a single form, where `d = sigma*p` is
//! its demand. The natural generalisation is that the demand is the **sum** over forms: `k` single cells
//! demand `k * 8`, so the first step should leave `1 - 8k/S`.
//!
//! PREDICTION, before the run, with `S = 100`:
//!   k = 1 -> 0.92, k = 2 -> 0.84, k = 4 -> 0.68, k = 8 -> 0.36
//!
//! and every step after the first should climb back towards one, because the inflow is 300 and exceeds the
//! capacity. If the sum rule holds, many forms behave like one big form and the alternation result
//! generalises; if not, the per-form order inside a step matters and the single-form result was special.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;

fn rules() -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(4.0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn fills(starts: usize) -> Vec<f64> {
    let forms: Vec<Form> = (0..starts).map(|_| Form::square(1)).collect();
    let mut world = ShapeWorld::new(rules(), forms);
    let mut rng = Rng::new(1);
    let mut out = Vec::new();
    for _ in 0..4 {
        world.step(&mut rng);
        out.push(world.stock / CELLS);
    }
    out
}

fn main() {
    println!("{:>3} {:>8} {:>10} {:>10} {:>10} {:>10}", "k", "demand", "step 1", "step 2", "step 3", "step 4");
    let mut bad = 0;
    for k in [1usize, 2, 4, 8] {
        let f = fills(k);
        let demand = 8.0 * k as f64;
        let predicted = 1.0 - demand / CELLS;
        println!(
            "{k:>3} {demand:>8.0} {:>10.3} {:>10.3} {:>10.3} {:>10.3}",
            f[0], f[1], f[2], f[3]
        );
        let ok = (f[0] - predicted).abs() < 0.02;
        println!(
            "      {} predicted step 1 = {predicted:.3}",
            if ok { "ok   " } else { "WRONG" }
        );
        if !ok {
            bad += 1;
        }
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена: спрос складывается между формами.");
}
