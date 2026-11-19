//! What does a fully repaired part actually settle at? The depth law rests on `q̄ ≈ 1 - d/(1-d)`, which I derived and
//! never measured.
//!
//! `FINDING-284` fitted the depth limit with `n* ≈ ln(q_min*d/u_last) / ln(q̄)` where `q̄ = 1 - d/(1-d)`. The fit landed
//! inside the measured intervals but no closer. So: measure `q̄` itself.
//!
//! PREDICTION, before the run (one part, repair exactly at its decay `u = d`, `q_min = 0.2`, long horizon):
//!   (a) the part settles **below** 1, never at it, because repair is capped by `1 - q`;
//!   (b) `q̄` is close to `1 - d/(1-d)`: 0.947 at `d = 0.05`, 0.980 at 0.02, 0.990 at 0.01;
//!   (c) the deficit `1 - q̄` is close to `d/(1-d)` and grows with the decay.

use medium_core::organ::Part;

const Q_MIN: f64 = 0.2;

fn settle(d: f64) -> f64 {
    let mut part = Part::new(1.0, d, 1.0);
    let mut energy = 1.0e9_f64;
    for _ in 0..200_000 {
        part.step(d, 1.0, &mut energy);
    }
    part.q
}

fn main() {
    println!("{:>8} {:>10} {:>12} {:>12}", "d", "q settled", "predicted", "deficit/pred");
    let mut bad = 0;
    let mut rows = Vec::new();
    for d in [0.05, 0.02, 0.01] {
        let q = settle(d);
        let predicted = 1.0 - d / (1.0 - d);
        let ratio = (1.0 - q) / (d / (1.0 - d));
        println!("{d:>8.2} {q:>10.5} {predicted:>12.5} {ratio:>12.3}");
        rows.push((d, q, predicted, ratio));
    }

    println!();
    let a = rows.iter().all(|r| r.1 < 1.0);
    println!("  {} (a) a fully repaired part sits below 1", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = rows.iter().all(|r| (r.1 - r.2).abs() < 0.01);
    println!(
        "  {} (b) it is close to 1 - d/(1-d): {:?}",
        if b { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 * 1000.0).round() / 1000.0)).collect::<Vec<_>>()
    );
    if !b {
        bad += 1;
    }

    let c = rows.windows(2).all(|w| w[1].3 <= w[0].3 + 0.2);
    println!(
        "  {} (c) the deficit tracks d/(1-d): ratios {:?}",
        if c { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.3 * 100.0).round() / 100.0).collect::<Vec<_>>()
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
