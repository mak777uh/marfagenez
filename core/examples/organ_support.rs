//! Does support from the other part lower the price of a division?
//!
//! `FINDING-290`: a division lives only when one part yields a surplus equal to the other's price - `yield >= 2` at
//! `q_a = 0.3`. Now B supports A's productivity:
//!
//! ```text
//! lift = 1 + support * (q_b - q_min)/(1 - q_min)
//! shed = yield * lift * q_a * d_a
//! ```
//!
//! At `q_b = 0.3`, `q_min = 0.2`, `support = 1` the lift is 1.125, so the threshold should fall from 2 to about 1.78.
//!
//! PREDICTION, before the run (`d = 0.05`, `q_min = 0.2`, `q_a = q_b = 0.3`, `support = 1`):
//!   (a) the division now lives at a **lower** `yield` than 2 - the threshold falls by the lift;
//!   (b) measured crossing is about **1.78**;
//!   (c) with `support = 0` the threshold is 2, as in 290.

use medium_core::organ::{Flow, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn lives(yield_rate: f64, support: f64) -> bool {
    let mut f = Flow::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    f.yield_rate = yield_rate;
    f.support = support;
    for _ in 0..200_000 {
        if !f.step() {
            return false;
        }
    }
    true
}

fn crossing(support: f64) -> f64 {
    let mut lo = 0.5_f64;
    let mut hi = 4.0_f64;
    for _ in 0..40 {
        let mid = (lo + hi) / 2.0;
        if lives(mid, support) {
            hi = mid;
        } else {
            lo = mid;
        }
    }
    hi
}

fn main() {
    let none = crossing(0.0);
    let some = crossing(1.0);
    println!("threshold with support 0: {none:.4}");
    println!("threshold with support 1: {some:.4}");
    println!("predicted from the lift: {:.4}", 2.0 / 1.125);

    println!();
    let mut bad = 0;

    let a = some < none;
    println!("  {} (a) support lowers the threshold: {some:.3} < {none:.3}", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = (some - 2.0 / 1.125).abs() < 0.15;
    println!(
        "  {} (b) the crossing is near 1.78: {some:.3}",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = (none - 2.0).abs() < 0.15;
    println!("  {} (c) without support it is 2, as in 290: {none:.3}", if c { "ok   " } else { "WRONG" });
    if !c {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
