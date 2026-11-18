//! Where does the band stop holding? The threshold between delta 0.2 and 0.5.
//!
//! `FINDING-256` recorded the failure of a wide band (delta = 0.5 gives a median of 7 at a target of 10) and
//! predicted the collapse between 0.3 and 0.4: at 0.2 the band is narrower than the drift it must beat, at
//! 0.5 it is wider.
//!
//! PREDICTION, before the run (target 10 cells, 200 lineages, 100 mutations, p = 0.27):
//!   (a) the median sits at 10 for delta up to and including 0.3;
//!   (b) it has fallen below 9 by delta = 0.4;
//!   (c) the collapse is monotone in delta: a wider band never holds better than a narrower one.

use medium_core::form::{Form, Heredity};
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const FAIR: f64 = 0.27;
const TARGET: usize = 10;

fn walk(delta: f64) -> (f64, f64, usize, usize) {
    let start = Form::square(2);
    let mut h = Heredity::plain();
    h.target_cells = Some(TARGET);
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
    let mean = ns.iter().map(|n| *n as f64).sum::<f64>() / ns.len() as f64;
    (
        ns[ns.len() / 2] as f64,
        mean,
        ns[0],
        ns[ns.len() - 1],
    )
}

fn main() {
    println!("{:>6} {:>8} {:>8} {:>12}", "delta", "med n", "mean n", "cells");
    let mut rows = Vec::new();
    for delta in [0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50] {
        let (med, mean, lo, hi) = walk(delta);
        println!("{delta:>6.2} {med:>8.0} {mean:>8.2} {lo:>5}..{hi:<6}");
        rows.push((delta, med, mean, lo, hi));
    }

    println!();
    let mut bad = 0;
    let at = |d: f64| rows.iter().find(|r| (r.0 - d).abs() < 1e-9).copied().expect("row");

    let holds_upto_03 = [0.10, 0.20, 0.25, 0.30]
        .iter()
        .all(|d| (at(*d).1 - TARGET as f64).abs() <= 1.0);
    println!(
        "  {} (a) the median holds through delta 0.3",
        if holds_upto_03 { "ok   " } else { "WRONG" }
    );
    if !holds_upto_03 {
        bad += 1;
    }

    let falls_at_04 = at(0.40).1 < 9.0;
    println!(
        "  {} (b) by delta 0.4 the median is below 9: {:.0}",
        if falls_at_04 { "ok   " } else { "WRONG" },
        at(0.40).1
    );
    if !falls_at_04 {
        bad += 1;
    }

    let monotone = rows.windows(2).all(|w| w[1].1 <= w[0].1 + 1.0);
    println!(
        "  {} (c) the collapse is monotone in delta (within one cell)",
        if monotone { "ok   " } else { "WRONG" }
    );
    if !monotone {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
