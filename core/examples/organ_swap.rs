//! Swapping the decay rates: is "the skin goes first" a fact about decay or about the link?
//!
//! `FINDING-279` measured the order with the skin decaying faster (0.05 against 0.02): repairing only the core lived
//! 32 steps, repairing only the skin lived 80. That is exactly what the decay rates predict - but it leaves open
//! whether the link adds anything, or whether the order was simply the faster decay.
//!
//! PREDICTION, before the run (swap to skin 0.02, core 0.05, everything else as in 279):
//!   (a) the order **reverses**: repairing only the **core** now lives longer than repairing only the skin;
//!   (b) each lifetime still matches the law of `FINDING-258` for its own decay rate: 79.7 -> 80 steps for the
//!       slow part, 31.4 -> 32 for the fast one;
//!   (c) the link still shows: the arm that repairs only the core still cannot keep the core whole after the skin is
//!       gone, so its core is decaying at the end - the gate bites even when the order reverses.

use medium_core::organ::{run, Organism, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;

fn main() {
    let skin = Part::new(1.0, 0.02, 1.0);
    let core = Part::new(1.0, 0.05, 2.0);
    let u_skin = 0.02 * Q_MIN;
    let u_core = 0.05 * Q_MIN;

    println!("{:>28} {:>7} {:>9} {:>10}", "arm", "alive", "steps", "killed by");
    let arms = [
        ("A repair both", u_skin, u_core),
        ("B repair only the core", 0.0, u_core),
        ("C repair only the skin", u_skin, 0.0),
    ];
    let mut rows = Vec::new();
    for (label, us, uc) in arms {
        let o = run(skin, core, Q_MIN, 10.0, 1.0, 0.5, us, uc, HORIZON);
        println!(
            "{label:>28} {:>7} {:>9} {:>10}",
            o.alive,
            o.steps,
            format!("{:?}", o.killed_by)
        );
        rows.push((label, o.alive, o.steps, o.killed_by));
    }

    println!();
    let mut bad = 0;

    let a = rows[1].2 > rows[2].2;
    println!(
        "  {} (a) the order reverses: only core {} steps, only skin {} steps",
        if a { "ok   " } else { "WRONG" },
        rows[1].2,
        rows[2].2
    );
    if !a {
        bad += 1;
    }

    let law_slow = ((Q_MIN as f64).ln() / (1.0_f64 - 0.02).ln()).floor() as usize + 1;
    let law_fast = ((Q_MIN as f64).ln() / (1.0_f64 - 0.05).ln()).floor() as usize + 1;
    let b = rows[1].2 == law_slow && rows[2].2 == law_fast;
    println!(
        "  {} (b) each lifetime follows the law for its own decay: {} vs {}, {} vs {}",
        if b { "ok   " } else { "WRONG" },
        rows[1].2,
        law_slow,
        rows[2].2,
        law_fast
    );
    if !b {
        bad += 1;
    }

    // (c) the gate still bites: in arm B the core is being repaired but its value must sag once the skin is gone
    let mut o = Organism::new(skin, core, Q_MIN, 10.0);
    let mut core_at_skin_death = None;
    for _ in 0..HORIZON {
        let alive = o.step(0.0, u_core, 1.0, 0.5);
        if !alive {
            core_at_skin_death = Some(o.core.q);
            break;
        }
    }
    let c = core_at_skin_death.map(|q| q < 1.0).unwrap_or(false);
    println!(
        "  {} (c) at the skin's death the core was already sagging: {:?}",
        if c { "ok   " } else { "WRONG" },
        core_at_skin_death
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
