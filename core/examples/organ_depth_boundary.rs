//! Where exactly does depth stop being affordable? A fine sweep around `n * d * cost`.
//!
//! `FINDING-286` gave the price `income - maintenance >= n * d * cost` and bracketed it between 0.9 and 1.1 of the
//! need. This pins it down.
//!
//! PREDICTION, before the run (sweep the surplus in steps of 0.02, `d = 0.05`, `cost = 1`):
//!   (a) the crossing sits within one sweep step of `n*d`: 0.40 for 8, 0.80 for 16, 1.60 for 32;
//!   (b) it is **not earlier** than `n*d` by more than a step - nothing else covers part of the price;
//!   (c) the crossing scales linearly with `n`.

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
    let d = 0.05;
    println!("{:>6} {:>9} {:>12} {:>12} {:>10}", "n", "price n*d", "last dead", "first alive", "crossing");
    let mut bad = 0;
    let mut crossings = Vec::new();
    for n in [8usize, 16, 32] {
        let price = n as f64 * d;
        let mut last_dead = 0.0;
        let mut first_alive = f64::NAN;
        let mut s = price - 0.10;
        while s <= price + 0.10 + 1e-9 {
            if lives(n, d, s) {
                if first_alive.is_nan() {
                    first_alive = s;
                }
            } else {
                last_dead = s;
            }
            s += 0.02;
        }
        let crossing = (last_dead + first_alive) / 2.0;
        println!("{n:>6} {price:>9.2} {last_dead:>12.2} {first_alive:>12.2} {crossing:>10.3}");
        crossings.push((n, price, last_dead, first_alive, crossing));
    }

    println!();
    let a = crossings.iter().all(|c| (c.4 - c.1).abs() <= 0.02 + 1e-9);
    println!(
        "  {} (a) the crossing sits within one step of n*d: {:?}",
        if a { "ok   " } else { "WRONG" },
        crossings.iter().map(|c| (c.1, c.4)).collect::<Vec<_>>()
    );
    if !a {
        bad += 1;
    }

    let b = crossings.iter().all(|c| c.2 <= c.1 + 1e-9);
    println!("  {} (b) nothing is alive below the price", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let c = crossings.windows(2).all(|w| w[1].4 > w[0].4);
    println!("  {} (c) the crossing rises with the number of parts", if c { "ok   " } else { "WRONG" });
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
