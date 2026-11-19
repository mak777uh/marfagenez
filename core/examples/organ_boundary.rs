//! With a link that can bite, how well must the boundary be held?
//!
//! The gate is now `q_skin^k`, so it falls as the skin sags. At the need `u_skin = d_s*q_min` the skin's own
//! equilibrium IS `q_min`, the gate is then about `q_min`, and the core is starved to a fifth of its repair however
//! much is spent on it. So "merely not dead" is not enough for a boundary that has an inside to hold.
//!
//! Arithmetic before the run: for the core to hold, the gate must keep its repair above the core's need,
//! `gate * u_core >= d_c * q_min`, i.e. `q_s >= (d_c*q_min)/u_core`. With `u_core = 4*d_c*q_min` that is
//! `q_s >= 0.25`, and since `q_s = u_s/d_s`, the skin repair must be at least `0.25 * 0.05 = 0.0125` - which is
//! **1.25 times the skin's own need**.
//!
//! PREDICTION, before the run (skin decay 0.02, core decay 0.05, `u_core = 4*need_core`, both repaired):
//!   (a) the pair lives when `u_skin >= 0.0125` and dies when it is below;
//!   (b) the boundary is therefore **above** the skin's own need (0.004 for decay 0.02) by a factor of about 3;
//!   (c) the lifetimes just below the threshold are finite and grow as the threshold is approached.

use medium_core::organ::{run, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;

fn main() {
    let skin = Part::new(1.0, 0.02, 1.0);
    let core = Part::new(1.0, 0.05, 2.0);
    let need_skin = 0.02 * Q_MIN;
    let need_core = 0.05 * Q_MIN;
    let u_core = 4.0 * need_core;
    let predicted = 0.25 * 0.02;

    println!("skin need {need_skin:.4}, predicted minimum repair {predicted:.4}");
    println!("{:>9} {:>7} {:>9}", "u_skin", "alive", "steps");
    let mut rows = Vec::new();
    for u_skin in [0.004, 0.006, 0.008, 0.010, 0.012, 0.0125, 0.013, 0.016, 0.020] {
        let o = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, u_skin, u_core, HORIZON);
        println!("{u_skin:>9.4} {:>7} {:>9}", o.alive, o.steps);
        rows.push((u_skin, o.alive, o.steps));
    }

    println!();
    let mut bad = 0;

    let above = rows.iter().filter(|r| r.0 >= predicted - 1e-12).all(|r| r.1);
    let below = rows.iter().filter(|r| r.0 < predicted - 1e-12).all(|r| !r.1);
    let a = above && below;
    println!(
        "  {} (a) lives at or above {predicted:.4} and dies below it",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let ratio = predicted / need_skin;
    let b = ratio > 2.0;
    println!(
        "  {} (b) the boundary must be held {ratio:.1} times above its own need",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let finite: Vec<usize> = rows.iter().filter(|r| !r.1).map(|r| r.2).collect();
    let c = finite.windows(2).all(|w| w[1] >= w[0]);
    println!("  {} (c) below the threshold the lifetimes grow towards it: {:?}", if c { "ok   " } else { "WRONG" }, finite);
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
