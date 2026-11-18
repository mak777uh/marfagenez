//! The bounded step: growth refused past the edge of the band.
//!
//! `FINDING-251` closed with the prediction: a mechanism that acts on the **step** rather than on its
//! probability should finally close the tails. Growth is refused when it would leave
//! `[target*(1-delta), target*(1+delta)]`, shrinkage is refused below it, and inside the band the walk is
//! free.
//!
//! PREDICTION, before the run (target 0.5, 200 lineages, 100 mutations):
//!   (a) the median stays within 0.02 of 0.5;
//!   (b) the interquartile range falls below 0.05;
//!   (c) the maximum falls to twelve cells or fewer - for the first time in this line;
//!   (d) narrowing the band narrows the spread: delta 0.1 gives a smaller IQR than delta 0.5.

use medium_core::form::{Form, Heredity};
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const FAIR: f64 = 0.36;

fn walk(band: Option<f64>, restore: f64) -> (f64, f64, usize, usize, f64) {
    let start = Form::square(2);
    let target = start.x();
    let mut h = Heredity::with_target(target);
    h.band = band;
    h.restore = restore;
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate_heredity(&mut rng, FAIR, &h) {
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
    println!("{:>10} {:>8} {:>10} {:>8} {:>12}", "band", "restore", "median x", "IQR", "cells");
    let arms = [
        (None, 0.0),
        (Some(0.5), 0.0),
        (Some(0.5), 0.5),
        (Some(0.2), 0.0),
        (Some(0.1), 0.0),
    ];
    let mut rows = Vec::new();
    for (band, restore) in arms {
        let (med, iqr, min_n, max_n, target) = walk(band, restore);
        let label = band.map(|b| format!("{b:.1}")).unwrap_or_else(|| "none".to_string());
        println!("{label:>10} {restore:>8.1} {med:>10.3} {iqr:>8.3} {min_n:>5}..{max_n:<6}");
        rows.push((label, restore, med, iqr, min_n, max_n, target));
    }

    println!();
    let mut bad = 0;
    let none = &rows[0];
    let b05 = &rows[1];
    let b05r = &rows[2];
    let b01 = &rows[4];
    let t = none.6;

    let checks: Vec<(String, bool)> = vec![
        (
            format!("no band reproduces 251: IQR {:.3}, cells {}..{}", none.3, none.4, none.5),
            none.5 >= 20,
        ),
        (
            format!("(a) with the band the median holds: {:.3} vs {:.3}", b05.2, t),
            (b05.2 - t).abs() <= 0.02,
        ),
        (
            format!("(b) with the band the IQR is below 0.05: {:.3}", b05.3),
            b05.3 < 0.05,
        ),
        (
            format!("(c) with the band the maximum is twelve or fewer: {}", b05.5),
            b05.5 <= 12,
        ),
        (
            format!("(d) a narrower band is tighter: {:.3} (0.1) vs {:.3} (0.5)", b01.3, b05.3),
            b01.3 <= b05.3,
        ),
        (
            format!("band plus force is no worse: IQR {:.3}", b05r.3),
            (b05r.3 - b05.3).abs() < 0.02,
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
