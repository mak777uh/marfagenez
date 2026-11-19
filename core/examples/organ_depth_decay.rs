//! Does the depth limit move with the decay rate? The residual deficit is `d/(1 - d)`, so a slower decay should
//! push the limit further out - or the limit is about the number of parts and not about decay.
//!
//! `FINDING-283` measured the limit between 8 and 16 parts at `d = 0.05`: eight hold, sixteen do not. The reason given
//! there is that a repaired part settles just below one, and the deficit `d/(1-d)` compounds along the chain.
//!
//! PREDICTION, before the run (all parts decay `d`, `q_min = 0.2`, front parts held at full repair `u = d`, last held
//! at twice its need):
//!   (a) at `d = 0.01` a chain of **16** parts **lives**, where at 0.05 it died;
//!   (b) the limit is a number of parts at a given decay: at `d = 0.05` sixteen dies, at `0.01` sixteen lives, and at
//!       `0.01` even thirty-two lives;
//!   (c) therefore the limit follows the deficit, not the depth itself.

use medium_core::organ::{run_chain, Part};

const HORIZON: usize = 300_000;
const Q_MIN: f64 = 0.2;

fn lives(n: usize, d: f64) -> bool {
    let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, d, 1.0)).collect();
    let mut u = vec![d; n];
    u[n - 1] = 2.0 * d * Q_MIN;
    run_chain(parts, Q_MIN, &u, HORIZON).alive
}

fn main() {
    println!("{:>6} {:>10} {:>10} {:>10}", "parts", "d=0.05", "d=0.02", "d=0.01");
    let mut bad = 0;
    for n in [8usize, 16, 32] {
        let row = [0.05, 0.02, 0.01].map(|d| lives(n, d));
        println!(
            "{n:>6} {:>10} {:>10} {:>10}",
            if row[0] { "lives" } else { "dies" },
            if row[1] { "lives" } else { "dies" },
            if row[2] { "lives" } else { "dies" }
        );
    }

    println!();
    let a = lives(16, 0.01);
    println!(
        "  {} (a) at d = 0.01 sixteen parts live: {}",
        if a { "ok   " } else { "WRONG" },
        if a { "yes" } else { "no" }
    );
    if !a {
        bad += 1;
    }

    let b = lives(16, 0.01) && lives(32, 0.01) && !lives(16, 0.05);
    println!(
        "  {} (b) the limit is a number of parts at a given decay: 16 lives at 0.01, dies at 0.05; 32 lives at 0.01",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = lives(32, 0.01) || lives(16, 0.02);
    let narrows = lives(16, 0.02) && !lives(16, 0.05);
    println!(
        "  {} (c) the limit follows the decay: 16 parts #{} at 0.05, #{} at 0.02, #{} at 0.01",
        if narrows || c { "ok   " } else { "WRONG" },
        if lives(16, 0.05) { "lives" } else { "dies" },
        if lives(16, 0.02) { "lives" } else { "dies" },
        if lives(16, 0.01) { "lives" } else { "dies" }
    );
    if !(narrows || c) {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
