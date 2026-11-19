//! The mechanism at last: depth costs **matter**, not integrity.
//!
//! The gate printout shows every part in front at exactly 1.0000 while the eleventh gate is already below one. That
//! can only happen if the parts stop being repaired - and they do: each part costs `cost * d` per step to keep whole,
//! so a chain of `n` parts costs `n * cost * d`, while the organism only has `income - maintenance` to spend.
//!
//! For `n = 16`, `d = 0.05`, `cost = 1`, `income - maintenance = 0.5`: the chain needs `0.8` a step and has `0.5`.
//!
//! PREDICTION, before the run:
//!   (a) a sixteen-part chain that dies at `income - maintenance = 0.5` **lives** when the surplus exceeds
//!       `n * d * cost = 0.8`;
//!   (b) the same holds at any depth: the threshold is `n * d * cost` per step;
//!   (c) so the depth limit is a **price**, and the earlier "limit follows the decay" was that same price seen
//!       through `d` - a smaller decay needs fewer units per part.

use medium_core::organ::{Chain, Part};

const Q_MIN: f64 = 0.2;

fn lives(n: usize, d: f64, surplus: f64) -> bool {
    let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, d, 1.0)).collect();
    let mut u = vec![d; n];
    u[n - 1] = 2.0 * d * Q_MIN;
    let mut c = Chain::new(parts, Q_MIN, 10.0);
    c.income = surplus + c.maintenance;
    for _ in 0..200_000 {
        if !c.step(&u) {
            return false;
        }
    }
    true
}

fn main() {
    println!("{:>6} {:>7} {:>9} {:>12} {:>10}", "parts", "d", "need/step", "surplus", "lives");
    let mut bad = 0;
    for (n, d) in [(8usize, 0.05), (16, 0.05), (32, 0.05)] {
        let need = n as f64 * d;
        for surplus in [0.5, need * 0.9, need * 1.1] {
            let alive = lives(n, d, surplus);
            println!("{n:>6} {d:>7.2} {need:>9.2} {surplus:>12.2} {:>10}", if alive { "yes" } else { "no" });
        }
    }

    println!();
    let a = !lives(16, 0.05, 0.5) && lives(16, 0.05, 16.0 * 0.05 * 1.1);
    println!(
        "  {} (a) sixteen parts die on a 0.5 surplus and live on one above 0.8",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let b = (2..=32).all(|n| lives(n, 0.05, n as f64 * 0.05 * 1.1));
    println!("  {} (b) every depth lives when the surplus covers its price", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let c = !lives(16, 0.05, 0.5) && lives(16, 0.02, 16.0 * 0.02 * 1.1);
    println!(
        "  {} (c) the same depth is affordable at a slower decay",
        if c { "ok   " } else { "WRONG" }
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
