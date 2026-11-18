//! The size regulator, run at the probability that is actually fair for the count.
//!
//! `FINDING-253` bounded the cell count but ran at `p_grow = 0.36`, which is the fair value for the
//! **ratio**; `FINDING-255` measured the fair value for the **count** at 0.27 and predicted that the band
//! would stop hugging its upper edge.
//!
//! PREDICTION, before the run (200 lineages, 100 mutations, band 0.2):
//!   (a) with target `n*` the median count sits at `n*` within one cell, for `n*` = 4, 10 and 16;
//!   (b) the distribution no longer sits at the top edge: the mean is within one cell of the target, not
//!       three, as it was at 0.36;
//!   (c) the interquartile range of `x` stays below 0.05 at every target.

use medium_core::form::{Form, Heredity};
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const FAIR: f64 = 0.27;

fn walk(n_star: usize, delta: f64) -> (f64, f64, f64, usize, usize) {
    let start = Form::square(2);
    let mut h = Heredity::plain();
    h.target_cells = Some(n_star);
    h.band_cells = Some(delta);
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
    let iqr = xs[xs.len() * 3 / 4] - xs[xs.len() / 4];
    let mean = ns.iter().map(|n| *n as f64).sum::<f64>() / ns.len() as f64;
    (
        ns[ns.len() / 2] as f64,
        mean,
        iqr,
        ns[0],
        ns[ns.len() - 1],
    )
}

fn main() {
    println!(
        "{:>8} {:>7} {:>8} {:>8} {:>8} {:>12}",
        "target", "band", "med n", "mean n", "IQR x", "cells"
    );
    let mut rows = Vec::new();
    for (n_star, delta) in [(4usize, 0.2), (10, 0.2), (16, 0.2), (10, 0.5)] {
        let (med, mean, iqr, lo, hi) = walk(n_star, delta);
        println!("{n_star:>8} {delta:>7.1} {med:>8.0} {mean:>8.2} {iqr:>8.3} {lo:>5}..{hi:<6}");
        rows.push((n_star, delta, med, mean, iqr, lo, hi));
    }

    println!();
    let mut bad = 0;
    for (n_star, delta, med, mean, iqr, _lo, _hi) in &rows {
        if *delta != 0.2 {
            continue;
        }
        let ok = (*med - *n_star as f64).abs() <= 1.0;
        println!(
            "  {} (a) target {n_star}: the median sits at {med:.0}",
            if ok { "ok   " } else { "WRONG" }
        );
        if !ok {
            bad += 1;
        }
        let ok2 = (*mean - *n_star as f64).abs() <= 1.0;
        println!(
            "  {} (b) target {n_star}: the mean is {mean:.2}, not at the top edge",
            if ok2 { "ok   " } else { "WRONG" }
        );
        if !ok2 {
            bad += 1;
        }
        let ok3 = *iqr < 0.05;
        println!(
            "  {} (c) target {n_star}: the shape spread is {iqr:.3}",
            if ok3 { "ok   " } else { "WRONG" }
        );
        if !ok3 {
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
