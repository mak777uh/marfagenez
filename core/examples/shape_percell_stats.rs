//! The statistics `FINDING-223` asked for: twenty-four seeds per point, a distribution, not a mean.
//!
//! `FINDING-223` closed with an explicit instruction - do not add another mechanism, add statistics:
//! 20-30 seeds, the distribution of sizes, and the question whether the **median** lies inside the
//! solvency interval. This runs exactly that.
//!
//! The interval for `f0 = 10` is `1.571 ... 5.420` (fixed by `ShapeEconomy::x_limit` and the
//! perimeter bound; see the paper §9.6).
//!
//! PREDICTION, before the run:
//!   (a) with the birth price proportional to the child's size (`per_cell = 4`) the median side over
//!       twenty-four seeds lies **inside** the interval `[1.571, 5.420]`;
//!   (b) without that price (`per_cell = 0`) the median lies **above** it, because growth pays;
//!   (c) the run-to-run interquartile range at `per_cell = 4` is narrower than at `per_cell = 0`.
//!
//! If (a) holds and (b) holds, the interval is visible in the distribution only when fitness is put on
//! the same footing as solvency - which is what 222 predicted and 223 could not show with one seed.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const STEPS: usize = 400;
const F0: f64 = 10.0;
const SEEDS: u64 = 24;
const INTERVAL: (f64, f64) = (1.571, 5.420);

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

fn side_of(form: &Form) -> f64 {
    // the side of the bounding square, the same measure the paper uses
    let ((lo_x, lo_y), (hi_x, hi_y)) = form.extent();
    let w = (hi_x - lo_x + 1) as f64;
    let h = (hi_y - lo_y + 1) as f64;
    (w.max(h)).max(1.0)
}

fn final_sides(per_cell: f64) -> Vec<f64> {
    let mut sides = Vec::new();
    for seed in 1..=SEEDS {
        let mut world = ShapeWorld::new(rules(per_cell), vec![Form::square(2)]);
        let mut rng = Rng::new(seed);
        for _ in 0..STEPS {
            world.step(&mut rng);
        }
        if world.forms.is_empty() {
            continue;
        }
        // the median side of the living forms, as the paper does
        let mut s: Vec<f64> = world.forms.iter().map(|f| side_of(&f.form)).collect();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        sides.push(s[s.len() / 2]);
    }
    sides.sort_by(|a, b| a.partial_cmp(b).unwrap());
    sides
}

fn quantile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    let idx = ((sorted.len() - 1) as f64 * q).round() as usize;
    sorted[idx]
}

fn median(sorted: &[f64]) -> f64 {
    quantile(sorted, 0.5)
}

fn main() {
    println!(
        "{:>9} {:>7} {:>7} {:>7} {:>16} {:>9}",
        "per_cell", "runs", "median", "IQR", "inside interval", "predicted"
    );
    let mut medians = Vec::new();
    for per_cell in [0.0, 2.0, 4.0] {
        let sides = final_sides(per_cell);
        let m = median(&sides);
        let q1 = quantile(&sides, 0.25);
        let q3 = quantile(&sides, 0.75);
        let inside = m >= INTERVAL.0 && m <= INTERVAL.1;
        medians.push((per_cell, m, q3 - q1, inside));
        println!(
            "{per_cell:>9.1} {:>7} {m:>7.2} {:>7.2} {:>16} {:>9}",
            sides.len(),
            q3 - q1,
            if inside { "yes" } else { "no" },
            match per_cell {
                4.0 => "inside",
                0.0 => "above",
                _ => "-",
            }
        );
    }

    println!();
    let mut bad = 0;
    // (a) and (b)
    for (per_cell, m, iqr, inside) in &medians {
        let want = if *per_cell == 4.0 {
            true
        } else if *per_cell == 0.0 {
            false
        } else {
            continue
        };
        let ok = *inside == want;
        println!(
            "  {} ({}) per_cell {per_cell}: median {m:.2} {} the interval ({INTERVAL:?})",
            if ok { "ok   " } else { "WRONG" },
            if want { "a" } else { "b" },
            if *inside { "inside" } else { "outside" },
        );
        if !ok {
            bad += 1;
        }
        let _ = iqr;
    }
    // (c) narrower spread with the per-cell price
    let iqr0 = medians.iter().find(|(c, _, _, _)| *c == 0.0).map(|(_, _, i, _)| *i).unwrap_or(0.0);
    let iqr4 = medians.iter().find(|(c, _, _, _)| *c == 4.0).map(|(_, _, i, _)| *i).unwrap_or(0.0);
    let narrower = iqr4 < iqr0;
    println!(
        "  {} (c) the spread is narrower with the per-cell price ({iqr4:.2} < {iqr0:.2})",
        if narrower { "ok   " } else { "WRONG" }
    );
    if !narrower {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
