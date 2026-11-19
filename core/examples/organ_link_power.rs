//! How hard does the link bite? The gate as a power of the skin's state.
//!
//! `FINDING-280` separated the order (set by decay) from the damage the link does to the other part: at the skin's
//! death the core had sagged to 0.213 although it was repaired every step. That leaves the obvious question - is the
//! sag a property of the **link's strength**, or just of the **time** the skin took to fail?
//!
//! The gate is `min(1, (q_skin / q_min)^k)`. With `k = 0` the link is off entirely; with `k = 1` it is the relation
//! of 279; with larger `k` it chokes steeply.
//!
//! PREDICTION, before the run (repair the core only at **four times** the need, skin decay 0.02 so it dies at step
//! 80, `q_min = 0.2`):
//!   (a) the core's value at the skin's death **falls as the link hardens**: 0.5 > 1.0 > 2.0 > 4.0;
//!   (b) with `k = 0` (no link) the core reaches its own equilibrium **0.8** - it was being repaired four times over;
//!   (c) so the sag is a property of the link's strength and **not** of the time.
//!
//! The first attempt of this example used the need itself for `u_core`. Every arm then gave 0.213, including the
//! arm with no link: with `u_core = d*q_min` the core's equilibrium IS `q_min`, so it sits at its threshold whatever
//! the skin does. That arithmetic error is what the fourfold setting removes.

use medium_core::organ::{Organism, Part};

const Q_MIN: f64 = 0.2;
const HORIZON: usize = 200_000;

fn core_at_skin_death(k: f64) -> (Option<f64>, usize) {
    let skin = Part::new(1.0, 0.02, 1.0);
    let core = Part::new(1.0, 0.05, 2.0);
    let mut o = Organism::new(skin, core, Q_MIN, 10.0);
    o.link_power = k;
    // FOUR times the need: the core's own equilibrium is then 4*q_min = 0.8, well above the threshold, so a sag can
    // only come from the gate. With the need itself the equilibrium IS the threshold and every arm looks identical.
    let u_core = 4.0 * 0.05 * Q_MIN;
    for _ in 0..HORIZON {
        if !o.step(0.0, u_core, 1.0, 0.5) {
            return (Some(o.core.q), o.steps);
        }
    }
    (None, o.steps)
}

fn main() {
    println!("{:>7} {:>10} {:>8} {:>10}", "k", "steps", "core q", "note");
    let mut rows = Vec::new();
    for k in [0.0, 0.5, 1.0, 2.0, 4.0] {
        let (q, steps) = core_at_skin_death(k);
        let note = match q {
            Some(v) if v > 0.99 => "core whole",
            Some(_) => "core sagging",
            None => "never died",
        };
        println!("{k:>7.1} {steps:>10} {:>8} {note:>10}", q.map(|v| format!("{v:.3}")).unwrap_or_else(|| "-".into()));
        rows.push((k, steps, q));
    }

    println!();
    let mut bad = 0;

    let vals: Vec<Option<f64>> = rows.iter().map(|r| r.2).collect();
    let ordered = vals[1].zip(vals[2]).zip(vals[3]).zip(vals[4]).map(|(((a, b), c), d)| a > b && b > c && c > d).unwrap_or(false);
    println!(
        "  {} (a) the core's value at death falls as the link hardens: {:?}",
        if ordered { "ok   " } else { "WRONG" },
        vals
    );
    if !ordered {
        bad += 1;
    }

    let no_link = vals[0].map(|v| (v - 0.8).abs() < 0.05).unwrap_or(false);
    println!(
        "  {} (b) with no link the core reaches its own equilibrium 0.8: {:?}",
        if no_link { "ok   " } else { "WRONG" },
        vals[0]
    );
    if !no_link {
        bad += 1;
    }

    let monotone = ordered && no_link;
    println!(
        "  {} (c) so the sag is the link's strength, not the elapsed time",
        if monotone { "ok   " } else { "WRONG" }
    );
    if !monotone {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
