//! Does the price weigh each part by its own cost? Two parts, one cheap and one dear.
//!
//! `FINDING-287` refined the price of a chain to `Σ u_i * cost_i`. Every test so far used `cost = 1` for every part,
//! so the sum was indistinguishable from a count. This puts a price on one of the two parts.
//!
//! PREDICTION, before the run (`d = 0.05`, both parts repaired at `d`, `q_min = 0.2`):
//!   (a) with costs 1 and 3 the chain needs **0.20** a step - against **0.10** when both cost 1;
//!   (b) the crossing sits at the sum, within one sweep step of 0.02;
//!   (c) so the price is weighted by `cost_i`, not merely counted.

use medium_core::organ::{Chain, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn lives(cost_a: f64, cost_b: f64, surplus: f64) -> bool {
    let parts = vec![Part::new(1.0, D, cost_a), Part::new(1.0, D, cost_b)];
    let u = [D, D];
    let mut c = Chain::new(parts, Q_MIN, 10.0);
    c.income = surplus + c.maintenance;
    for _ in 0..200_000 {
        if !c.step(&u) {
            return false;
        }
    }
    true
}

fn crossing(cost_a: f64, cost_b: f64) -> (f64, f64, f64) {
    let price = D * cost_a + D * cost_b;
    let mut last_dead = f64::NAN;
    let mut first_alive = f64::NAN;
    let mut s = price - 0.10;
    while s <= price + 0.10 + 1e-9 {
        if lives(cost_a, cost_b, s) {
            if first_alive.is_nan() {
                first_alive = s;
            }
        } else {
            last_dead = s;
        }
        s += 0.02;
    }
    (price, last_dead, first_alive)
}

fn main() {
    println!("{:>6} {:>6} {:>12} {:>12} {:>12}", "cost a", "cost b", "price", "last dead", "first alive");
    let arms = [(1.0, 1.0), (1.0, 3.0), (3.0, 3.0)];
    let mut rows = Vec::new();
    for (a, b) in arms {
        let (price, dead, alive) = crossing(a, b);
        println!("{a:>6.1} {b:>6.1} {price:>12.2} {dead:>12.2} {alive:>12.2}");
        rows.push((a, b, price, dead, alive));
    }

    println!();
    let mut bad = 0;

    let a = (rows[1].2 - 0.20).abs() < 1e-9;
    println!(
        "  {} (a) costs 1 and 3 make the price 0.20 (was 0.10)",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let b = rows.iter().all(|r| (r.4 - r.2).abs() <= 0.02 + 1e-9);
    println!(
        "  {} (b) every crossing sits within one step of its price: {:?}",
        if b { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.2, r.4)).collect::<Vec<_>>()
    );
    if !b {
        bad += 1;
    }

    let c = rows[1].2 > rows[0].2 && rows[2].2 > rows[1].2;
    println!("  {} (c) the price rises with the costs", if c { "ok   " } else { "WRONG" });
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
