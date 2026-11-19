//! Does depth cost? A chain of parts, each holding the one behind it.
//!
//! `FINDING-281` gave the two-part law: the front part must be held above its own need, and its price falls as
//! `1/u_core`. With `n` parts and the gate `q` at each link, holding the last one needs
//!
//! ```text
//! q^(n-1) * u_last >= need_last        so        q >= (need_last/u_last)^(1/(n-1))
//! ```
//!
//! and since `q = u_front/d_front`, the front's price is `d_front * (need_last/u_last)^(1/(n-1))` - rising towards
//! **full repair** as the chain grows.
//!
//! PREDICTION, before the run (all decay 0.05, `q_min = 0.2`, `u_last = 2*need_last` so the ratio is 1/2):
//!   (a) the critical front repair for `n` = 2, 3, 4 is `d*(1/2)^(1/(n-1))` = 0.0250, 0.0354, 0.0397;
//!   (b) it **rises with depth** and never exceeds `d` itself - full repair is the limit;
//!   (c) at `n` = 2 the law must agree with `FINDING-281` where the ratio is the same.

use medium_core::organ::{run_chain, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;
const DECAY: f64 = 0.05;

fn chain(n: usize) -> Vec<Part> {
    (0..n).map(|_| Part::new(1.0, DECAY, 1.0)).collect()
}

fn lives(n: usize, u_front: f64) -> bool {
    let mut u = vec![u_front; n];
    // every part except the last is repaired generously; the last is held at twice its need
    for slot in u.iter_mut().take(n - 1) {
        *slot = DECAY * Q_MIN * 4.0;
    }
    u[n - 1] = 2.0 * DECAY * Q_MIN;
    run_chain(chain(n), Q_MIN, &u, HORIZON).alive
}

fn main() {
    let need = DECAY * Q_MIN;
    let ratio = need / (2.0 * need);
    println!("need {need:.4}, ratio need/u_last {ratio:.2}");
    println!("{:>3} {:>12} {:>10} {:>10} {:>10}", "n", "predicted", "0.9x dies", "1.1x lives", "note");
    let mut bad = 0;
    let mut predicted = Vec::new();
    for n in [2usize, 3, 4, 8] {
        let crit = DECAY * ratio.powf(1.0 / (n as f64 - 1.0));
        let low = lives(n, crit * 0.9);
        let high = lives(n, crit * 1.1);
        println!(
            "{n:>3} {crit:>12.4} {:>10} {:>10} {:>10}",
            if low { "LIVES" } else { "dies" },
            if high { "lives" } else { "DIES" },
            if n <= 4 { "checked" } else { "limit" }
        );
        predicted.push((n, crit));
        if low {
            bad += 1; // a value below the prediction must not survive
        }
        if !high && n <= 4 {
            bad += 1; // and one above it must
        }
    }

    println!();
    let rising = predicted.windows(2).all(|w| w[1].1 >= w[0].1);
    let a = rising;
    println!(
        "  {} (a) the critical repair rises with depth: {:?}",
        if a { "ok   " } else { "WRONG" },
        predicted.iter().map(|(_, c)| (c * 1000.0).round() / 1000.0).collect::<Vec<_>>()
    );
    if !a {
        bad += 1;
    }

    let bounded = predicted.iter().all(|(_, c)| *c <= DECAY + 1e-12);
    println!("  {} (b) and never exceeds full repair (0.05)", if bounded { "ok   " } else { "WRONG" });
    if !bounded {
        bad += 1;
    }

    let two = predicted[0].1;
    let c = (two - DECAY * ratio).abs() < 1e-12;
    println!("  {} (c) at n = 2 it reduces to the law of 281: {two:.4}", if c { "ok   " } else { "WRONG" });
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
