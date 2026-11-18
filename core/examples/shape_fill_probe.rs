//! Is the fill fraction `f` after the first step really 0.760?
//!
//! The paper's threshold section rests on one sentence: "the first step of consumption leaves
//! `f = 0.760`", with `f = stock / stock_max`. `FINDING-240` showed that the same number was wrongly
//! applied to a one-form world, so this measures the fill directly in the configuration the sentence
//! was written for: a three-by-three start, eight seeds, `f0` at 11 and 12.
//!
//! PREDICTION, before the run:
//!   (a) the stock starts at capacity, so `f` after the first step is **near one**, not 0.760;
//!   (b) at `f0 = 11` the worlds are alive at the end and their living median `f` is high (0.8 and up);
//!   (c) at `f0 = 12` every world is dead by the end, and the `f` recorded at the step of death is the
//!       number that got quoted as 0.760.
//!
//! If (a) holds, the sentence in the paper describes the step of death, not the first step, and says so
//! wrongly.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const SEEDS: u64 = 8;

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

fn run(f0: f64) -> (Vec<f64>, Vec<f64>, usize, Vec<usize>) {
    let mut first_step = Vec::new();
    let mut living = Vec::new();
    let mut alive_at_end = 0;
    let mut death_step = Vec::new();
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(f0), vec![Form::square(3)]);
        let mut rng = Rng::new(seed);
        let mut prev_alive = true;
        for step in 0..STEPS {
            world.step(&mut rng);
            let f = world.stock / CELLS;
            if step == 0 {
                first_step.push(f);
            }
            let alive = !world.forms.is_empty();
            if alive {
                living.push(f);
            } else if prev_alive {
                death_step.push(step + 1);
            }
            prev_alive = alive;
        }
        if !world.forms.is_empty() {
            alive_at_end += 1;
        }
    }
    (first_step, living, alive_at_end, death_step)
}

fn median(v: &mut Vec<f64>) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    v[v.len() / 2]
}

fn main() {
    println!(
        "{:>6} {:>14} {:>14} {:>10} {:>12}",
        "f0", "f first step", "f median alive", "alive", "death step"
    );
    let mut rows = Vec::new();
    for f0 in [11.0, 12.0] {
        let (mut first, mut living, alive, deaths) = run(f0);
        let f_first = median(&mut first);
        let f_live = median(&mut living);
        let death = deaths.first().copied().unwrap_or(0);
        println!("{f0:>6.1} {f_first:>14.3} {f_live:>14.3} {alive:>10} {death:>12}");
        rows.push((f0, f_first, f_live, alive, death));
    }

    println!();
    let mut bad = 0;
    let (f0_11, first_11, live_11, alive_11, _) = rows[0];
    let (f0_12, _, _, alive_12, death_12) = rows[1];
    let _ = f0_11;

    let checks = [
        (
            format!("(a) f after the first step is near one, not 0.760 (got {first_11:.3})"),
            first_11 > 0.95,
        ),
        (
            format!("(b) at f0 = 11 the worlds live and hold f above 0.8 (got {live_11:.3})"),
            alive_11 == SEEDS as usize && live_11 > 0.8,
        ),
        (
            format!("(c) at f0 = 12 nothing survives and death comes at step {death_12}"),
            alive_12 == 0 && death_12 <= 2,
        ),
        (format!("    and the 0.760 is not the first-step value (first {first_11:.3})"), (first_11 - 0.760).abs() > 0.05),
    ];
    for (label, ok) in checks {
        println!("  {} {label}", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }
    let _ = f0_12;

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
