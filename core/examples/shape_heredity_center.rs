//! The force anchored where the operator is fair.
//!
//! `FINDING-250` measured the fair growth probability at about 0.36: with `p_grow = 0.37` and no restoring
//! force the median stays at the start, though the tails do not close. The prediction was written down
//! there, before this code: with the force anchored at 0.36 the median holds within 0.02, the interquartile
//! range falls below 0.05, and the maximum falls to twelve cells or fewer (against thirty-two).
//!
//! Three arms: fair base with no force; fair base with the constant shift; fair base with the force
//! proportional to the error.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const FAIR: f64 = 0.36;

fn walk(p_grow: f64, restore: f64, distance_scaled: bool, min_cells: usize) -> (f64, f64, usize, usize, f64) {
    let start = Form::square(2);
    let target = start.x();
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate_towards_with(
                &mut rng,
                p_grow,
                Some(target),
                restore,
                min_cells,
                distance_scaled,
            ) {
                *f = next;
            }
        }
    }
    let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    let cells: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
    (
        xs[n / 2],
        xs[n * 3 / 4] - xs[n / 4],
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
        target,
    )
}

fn main() {
    println!(
        "{:>30} {:>10} {:>8} {:>12}",
        "arm", "median x", "IQR", "cells"
    );
    let arms = [
        ("fair base, no force", FAIR, 0.0, false, 1usize),
        ("fair base, constant shift", FAIR, 0.5, false, 1),
        ("fair base, distance force", FAIR, 0.5, true, 1),
        ("fair base, distance + floor", FAIR, 0.5, true, 2),
    ];
    let mut rows = Vec::new();
    for (name, p, r, dist, floor) in arms {
        let (med, iqr, min_n, max_n, target) = walk(p, r, dist, floor);
        println!("{name:>30} {med:>10.3} {iqr:>8.3} {min_n:>5}..{max_n:<6}");
        rows.push((name, med, iqr, min_n, max_n, target));
    }

    println!();
    let mut bad = 0;
    let base = &rows[0];
    let constant = &rows[1];
    let distance = &rows[2];
    let both = &rows[3];
    let t = base.5;

    let checks: Vec<(String, bool)> = vec![
        (
            format!("base at 0.36 holds the median but not the tails: {:.3}, IQR {:.3}, {}..{}", base.1, base.2, base.3, base.4),
            (base.1 - t).abs() <= 0.02 && base.4 >= 20,
        ),
        (
            format!("constant shift narrows the spread: IQR {:.3} (base {:.3})", constant.2, base.2),
            constant.2 < base.2,
        ),
        (
            format!("distance force holds the median within 0.02: {:.3}", distance.1),
            (distance.1 - t).abs() <= 0.02,
        ),
        (
            format!("distance force narrows the spread below 0.05: IQR {:.3}", distance.2),
            distance.2 < 0.05,
        ),
        (
            format!("distance force closes the upper tail at twelve: max {}", distance.4),
            distance.4 <= 12,
        ),
        (
            format!("distance + floor also closes the lower tail: min {}", both.3),
            both.3 >= 2,
        ),
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
