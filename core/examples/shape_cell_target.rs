//! Regulating the number of cells instead of the ratio.
//!
//! `FINDING-252` found the flaw behind four failed mechanisms: `x = n/p` is scale-free, so bounding it
//! leaves the absolute size free, and the tails were always in the size. This regulates `n` itself.
//!
//! PREDICTION, before the run (target 4 cells, 200 lineages, 100 mutations):
//!   (a) the median cell count stays within one cell of 4;
//!   (b) the maximum falls to twelve or fewer - for the first time in this line;
//!   (c) the spread of `x` does not grow: IQR at most 0.05, because the shape can still change at a fixed
//!       size but with far less room;
//!   (d) a narrower band on the count narrows the count spread: delta 0.2 is tighter than delta 0.5.

use medium_core::form::{Form, Heredity};
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const FAIR: f64 = 0.36;

fn walk(n_star: Option<usize>, delta: Option<f64>) -> (f64, f64, f64, usize, usize) {
    let start = Form::square(2);
    let mut h = Heredity::plain();
    h.target_cells = n_star;
    h.band_cells = delta;
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate_heredity(&mut rng, FAIR, &h) {
                *f = next;
            }
        }
    }
    let mut ns: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
    ns.sort_unstable();
    let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let x_iqr = xs[xs.len() * 3 / 4] - xs[xs.len() / 4];
    (
        ns[ns.len() / 2] as f64,
        x_iqr,
        ns.iter().map(|n| *n as f64).sum::<f64>() / ns.len() as f64,
        ns[0],
        ns[ns.len() - 1],
    )
}

fn main() {
    println!(
        "{:>10} {:>7} {:>8} {:>8} {:>8} {:>12}",
        "target", "band", "med n", "mean n", "IQR x", "cells"
    );
    let arms: Vec<(Option<usize>, Option<f64>)> = vec![
        (None, None),
        (Some(4), Some(0.5)),
        (Some(4), Some(0.2)),
        (Some(10), Some(0.5)),
    ];
    let mut rows = Vec::new();
    for (n_star, delta) in arms {
        let (med, iqr, mean, min_n, max_n) = walk(n_star, delta);
        let tl = n_star.map(|n| n.to_string()).unwrap_or_else(|| "none".into());
        let dl = delta.map(|d| format!("{d:.1}")).unwrap_or_else(|| "-".into());
        println!("{tl:>10} {dl:>7} {med:>8.0} {mean:>8.2} {iqr:>8.3} {min_n:>5}..{max_n:<6}");
        rows.push((tl, dl, med, mean, iqr, min_n, max_n));
    }

    println!();
    let mut bad = 0;
    let none = &rows[0];
    let a = &rows[1];
    let tight = &rows[2];
    let big = &rows[3];

    let checks: Vec<(String, bool)> = vec![
        (
            format!("no target reproduces 252: cells {}..{}", none.5, none.6),
            none.6 >= 20,
        ),
        (
            format!("(a) the median count sits at four: {:.0}", a.2),
            (a.2 - 4.0).abs() <= 1.0,
        ),
        (
            format!("(b) the maximum is twelve or fewer: {}", a.6),
            a.6 <= 12,
        ),
        (
            format!("(c) the spread of x stays at 0.05 or less: {:.3}", a.4),
            a.4 <= 0.05,
        ),
        (
            format!("(d) a narrower band is tighter on the count: max {} vs {}", tight.6, a.6),
            tight.6 <= a.6,
        ),
        (
            format!("a larger target gives a larger world: median {} at target 10", big.2),
            (big.2 - 10.0).abs() <= 1.0,
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
