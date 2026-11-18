//! What is the fair growth probability? The one where a lineage neither erodes nor explodes.
//!
//! `FINDING-249` showed that the restoring force cannot be centred on 0.5, because the mutation operator
//! is itself biased: with `p_grow = 0.27` a form at its target still shrinks more often than it grows, so
//! a lineage erodes even where it "should" be in equilibrium. The force has to be centred on the operator's
//! own fair point, and that point has never been measured.
//!
//! This walks lineages with no restoring force at all, over a sweep of `p_grow`, and asks where the median
//! size stays where it started.
//!
//! PREDICTION, before the run:
//!   (a) the median rises monotonically with `p_grow` - more growth, bigger forms;
//!   (b) at `p_grow = 0.27` the median falls (erosion), as in `FINDING-247`;
//!   (c) the fair value, where the median stays within 0.02 of the start, lies **above 0.27**, and the
//!       guess is near 0.6, because a two-by-two has eight growth sites against four cells and the counts
//!       must balance for the walk to be fair.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;

fn walk(p_grow: f64) -> (f64, f64, f64, usize, usize) {
    let start = Form::square(2);
    let target = start.x();
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate(&mut rng, p_grow) {
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
        target,
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
    )
}

fn main() {
    println!(
        "{:>7} {:>10} {:>8} {:>12} {:>10}",
        "p_grow", "median x", "IQR", "cells", "at target"
    );
    let mut rows = Vec::new();
    for p in [0.27, 0.30, 0.33, 0.35, 0.37, 0.39, 0.45, 0.55] {
        let (med, iqr, target, min_n, max_n) = walk(p);
        let at = (med - target).abs() <= 0.02;
        println!(
            "{p:>7.2} {med:>10.3} {iqr:>8.3} {:>5}..{:<6} {:>10}",
            min_n, max_n, if at { "yes" } else { "no" }
        );
        rows.push((p, med, iqr, min_n, max_n, target, at));
    }

    println!();
    let mut bad = 0;
    let monotonish = rows
        .windows(2)
        .all(|w| w[1].1 >= w[0].1 - 0.02);
    println!(
        "  {} (a) the median rises with p_grow (within 0.02 of monotone)",
        if monotonish { "ok   " } else { "WRONG" }
    );
    if !monotonish {
        bad += 1;
    }

    let start_x = rows[0].5;
    let erosion = rows[0].1 < start_x - 0.05;
    println!(
        "  {} (b) at 0.27 the median falls: {:.3} against a start of {:.3}",
        if erosion { "ok   " } else { "WRONG" },
        rows[0].1,
        start_x
    );
    if !erosion {
        bad += 1;
    }

    let fair: Vec<f64> = rows.iter().filter(|r| r.6).map(|r| r.0).collect();
    let above = !fair.is_empty() && fair.iter().all(|p| *p > 0.27);
    println!(
        "  {} (c) the fair values are {fair:?} - all above 0.27: {above}",
        if above && !fair.is_empty() { "ok   " } else { "WRONG" }
    );
    if !above || fair.is_empty() {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
