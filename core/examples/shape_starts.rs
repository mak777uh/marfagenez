//! Is the edge-of-poverty position a property of selection, or of the starting form?
//!
//! `FINDING-238` found the median `x = cells/perimeter` at 0.417 against a solvency lower edge of 0.393 -
//! six per cent away, while the upper edge is three times further. But every run there started from a
//! two-by-two (`x = 0.5`), which is *above* the median it produced, so the result could be the start
//! sliding down rather than selection holding forms at the edge.
//!
//! This runs four starting forms with very different `x` and asks whether the median converges to the
//! same place.
//!
//! PREDICTION, before the run:
//!   (a) the median `x` over twenty-four seeds lies inside `[0.39, 0.46]` for **every** start - that is,
//!       within about ten per cent of the 0.417 of finding 238 and of the lower edge 0.393;
//!   (b) the start does not decide the answer: a three-by-three (`x = 0.75`) does not give a median near
//!       0.75, and a single cell (`x = 0.25`) does not give a median near 0.25;
//!   (c) worlds started from one cell die out more often than worlds started from four, because the
//!       first step of consumption is the one that decides (finding 226-229).

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const F0: f64 = 10.0;
const SEEDS: u64 = 24;
const BAND: (f64, f64) = (0.39, 0.46);

fn rules() -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(F0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn stats(start: &Form) -> (Vec<f64>, usize) {
    let mut medians = Vec::new();
    let mut extinct = 0;
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(), vec![start.clone()]);
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

fn median(v: &[f64]) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v[v.len() / 2]
}

fn main() {
    let starts = [
        ("1x1", Form::square(1)),
        ("2x2", Form::square(2)),
        ("3x3", Form::square(3)),
        ("strip4", Form::strip(4)),
    ];
    println!(
        "{:>7} {:>7} {:>7} {:>8} {:>18} {:>8}",
        "start", "x0", "runs", "median x", "in [0.39,0.46]", "extinct"
    );
    let mut rows = Vec::new();
    for (name, form) in starts {
        let x0 = form.x();
        let (medians, extinct) = stats(&form);
        let m = median(&medians);
        let inside = m >= BAND.0 && m <= BAND.1;
        println!(
            "{name:>7} {x0:>7.3} {:>7} {m:>8.3} {:>18} {extinct:>8}",
            medians.len(),
            if inside { "yes" } else { "no" }
        );
        rows.push((name, x0, m, inside, extinct));
    }

    println!();
    let mut bad = 0;
    let all_in = rows.iter().all(|r| r.3);
    println!(
        "  {} (a) every start gives a median inside [0.39, 0.46]",
        if all_in { "ok   " } else { "WRONG" }
    );
    if !all_in {
        bad += 1;
    }

    let start_free = rows.iter().all(|r| {
        // the median must not track the start: for the 3x3 it must be far below x0, for the cell far
        // above it
        if r.1 > 0.6 {
            r.2 < r.1 - 0.15
        } else if r.1 < 0.3 {
            r.2 > r.1 + 0.08
        } else {
            true
        }
    });
    println!(
        "  {} (b) the median does not track the start",
        if start_free { "ok   " } else { "WRONG" }
    );
    if !start_free {
        bad += 1;
    }

    let cell_extinct = rows[0].4;
    let square_extinct = rows[1].4;
    let survival = cell_extinct >= square_extinct;
    println!(
        "  {} (c) a single cell dies out at least as often as a two-by-two: {cell_extinct} vs {square_extinct}",
        if survival { "ok   " } else { "WRONG" }
    );
    if !survival {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
