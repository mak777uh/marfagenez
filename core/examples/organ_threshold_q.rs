//! Measure `q_a` and `q_b` at the threshold instead of deriving them. `FINDING-291` predicted `q_a` about 0.36 rather
//! than the 0.30 I assumed in 290.
//!
//! PREDICTION, before the run:
//!   (a) at a yield just above the measured threshold (1.667) the settled `q_a` is **about 0.36**;
//!   (b) `q_b` sits at or just above `q_min` there - which is why the support mechanism cannot help;
//!   (c) `0.03 / (q_a * 0.05)` reproduces the measured threshold.

use medium_core::organ::{Flow, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn settle(yield_rate: f64) -> (f64, f64, bool, usize) {
    let mut f = Flow::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    f.yield_rate = yield_rate;
    for step in 1..=200_000 {
        if !f.step() {
            return (f.a.q, f.b.q, false, step);
        }
    }
    (f.a.q, f.b.q, true, 200_000)
}

fn main() {
    println!("{:>8} {:>8} {:>9} {:>9} {:>9}", "yield", "alive", "steps", "q_a", "q_b");
    let mut rows = Vec::new();
    for y in [1.6, 1.667, 1.7, 2.0] {
        let (qa, qb, alive, steps) = settle(y);
        println!("{y:>8.3} {alive:>8} {steps:>9} {qa:>9.4} {qb:>9.4}");
        rows.push((y, alive, qa, qb));
    }

    println!();
    let mut bad = 0;
    let live = rows.iter().find(|r| r.1).expect("something must live");
    let a = (live.2 - 0.36).abs() < 0.03;
    println!("  {} (a) q_a settles near 0.36: {:.4}", if a { "ok   " } else { "WRONG" }, live.2);
    if !a {
        bad += 1;
    }

    let b = live.3 <= Q_MIN + 0.05;
    println!("  {} (b) q_b is near the minimum: {:.4}", if b { "ok   " } else { "WRONG" }, live.3);
    if !b {
        bad += 1;
    }

    let predicted = 0.03 / (live.2 * D);
    let c = (predicted - live.0).abs() < 0.1;
    println!(
        "  {} (c) the formula reproduces the threshold: {predicted:.3} against {:.3}",
        if c { "ok   " } else { "WRONG" },
        live.0
    );
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
