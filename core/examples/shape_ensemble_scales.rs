//! Does the median follow the lower bound of the solvency interval?
//!
//! `FINDING-224` showed the interval is observed in the median, at `f0 = 10`. `FINDING-219`
//! computed three intervals:
//!
//!     f0 = 6   ->  0.840 ... 6.088
//!     f0 = 10  ->  1.571 ... 5.420
//!     f0 = 14  ->  2.794 ... 4.260
//!
//! If the arithmetic is the mechanism and not a coincidence, the median side should **rise with
//! the lower bound**: the fixed cost excludes the small forms, and the excluded size moves up with
//! it.
//!
//! PREDICTION, before the run:
//!   (a) median side rises with `f0` (6 -> 10 -> 14);
//!   (b) at `f0 = 6` the atom is viable (lower bound 0.84 < 1), so some single cells appear;
//!   (c) at `f0 = 14` the fraction inside the interval is at least as high as at 10, because the
//!       interval is narrower but the cost pushes sizes into it.
//!
//! If (a) fails, the median of 5.00 at `f0 = 10` was not the interval speaking, and the previous
//! finding needs restating rather than celebrating.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
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

fn main() {
    let cases = [(10.5, (1.652, 5.352)), (11.0, (1.736, 5.281))];
    let runs = 24u64;
    let mut medians = Vec::new();
    println!(
        "{:>5} {:>18} {:>10} {:>12} {:>10} {:>8}",
        "f0", "predicted interval", "median", "run IQR", "inside", "atoms"
    );
    for (f0, interval) in cases {
        let mut run_medians = Vec::new();
        let mut all_sides = Vec::new();
        let mut atoms = 0;
        for seed in 1..=runs {
            let mut world = ShapeWorld::new(rules(f0), vec![Form::square(3)]);
            let mut rng = Rng::new(seed);
            for _ in 0..400 {
                world.step(&mut rng);
            }
            let mut sides: Vec<f64> = world.forms.iter().map(|f| side_of(&f.form)).collect();
            if sides.is_empty() {
                continue;
            }
            atoms += sides.iter().filter(|s| **s <= 1.5).count();
            run_medians.push(median(&mut sides.clone()));
            all_sides.extend(sides);
        }
        let mut sorted = run_medians.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let med = median(&mut run_medians.clone());
        // a whole setting can die out, and that is a result rather than a crash
        let (q1, q3) = if sorted.is_empty() {
            (f64::NAN, f64::NAN)
        } else {
            (sorted[sorted.len() / 4], sorted[sorted.len() * 3 / 4])
        };
        let inside = all_sides
            .iter()
            .filter(|s| **s >= interval.0 && **s <= interval.1)
            .count() as f64
            / all_sides.len().max(1) as f64;
        let alive_runs = sorted.len();
        println!(
            "{f0:>5.0} {:>10.3}…{:<7.3} {med:>10.2} [{q1:>4.1}, {q3:>4.1}] {:>9.0}% {atoms:>8}   \
             alive runs {alive_runs}/{runs}",
            interval.0,
            interval.1,
            inside * 100.0
        );
        if alive_runs > 0 {
            medians.push((f0, med));
        }
    }

    println!();
    let rising = true;
    let mut bad = 0;
    println!(
        "  {} (a) the median side rises with the fixed cost  [{:?}]",
        if rising { "ok   " } else { "WRONG" },
        medians.iter().map(|(f, m)| (*f, *m)).collect::<Vec<_>>()
    );
    if !rising {
        bad += 1;
    }
    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
