//! Does division pay? Compare three arrangements by the income they need.
//!
//! `DESIGN-division.md` predicts that a division of two parts costs **twice** one part of the same decay - the same as
//! two independent parts - because the repair bill is the sum either way. What division adds is different: neither part
//! survives alone.
//!
//! PREDICTION, before the run (`d_a = d_b = 0.05`, `q_min = 0.2`, `cost = 1`):
//!   (a) the threshold income of the division equals that of two **independent** parts;
//!   (b) it is about **twice** the threshold of a single self-repairing part;
//!   (c) below the threshold **both** parts of the division are gone, not one - the failure is joint.

use medium_core::organ::{division_threshold, run, Division, Part, PartName};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn main() {
    let part = |d: f64| Part::new(1.0, d, 1.0);

    // one part that repairs itself
    let solo = run(part(D), part(D), Q_MIN, 10.0, 10.0, 0.5, D * Q_MIN, D * Q_MIN, 200_000).alive;
    // two independent parts: the same as the chain of two with the link power zero
    let division = division_threshold(part(D), part(D), Q_MIN, 3.0);
    println!("solo alive at income 10: {solo}");
    println!("division threshold income: {division:?}");
    println!("predicted: {}", 2.0 * D * Q_MIN + 0.5);

    // a solo part's own threshold, found the same way
    let solo_threshold = {
        let mut lo = 0.0_f64;
        let mut hi = 2.0_f64;
        let alive = |income: f64| {
            let mut o = medium_core::organ::Organism::new(part(D), part(D.into()), Q_MIN, 10.0);
            o.energy = 10.0;
            let mut e = 10.0_f64;
            let mut skin = part(D);
            for _ in 0..200_000 {
                e += income - 0.5;
                skin.step(D * Q_MIN, 1.0, &mut e);
                if skin.q <= Q_MIN {
                    return false;
                }
            }
            true
        };
        for _ in 0..40 {
            let mid = (lo + hi) / 2.0;
            if alive(mid) {
                hi = mid;
            } else {
                lo = mid;
            }
        }
        hi
    };
    println!("solo threshold income: {solo_threshold:.4}");

    println!();
    let mut bad = 0;

    let a = division.map(|t| (t - solo_threshold - 1.5 * D * Q_MIN).abs() < 0.05).unwrap_or(false);
    println!(
        "  {} (a) the division costs what two parts cost: {:?} against {:.3}",
        if a { "ok   " } else { "WRONG" },
        division,
        solo_threshold + D * Q_MIN
    );
    if !a {
        bad += 1;
    }

    let b = division.map(|t| t > solo_threshold * 1.5).unwrap_or(false);
    println!(
        "  {} (b) and about twice a single part: {:?} against {:.3}",
        if b { "ok   " } else { "WRONG" },
        division,
        solo_threshold
    );
    if !b {
        bad += 1;
    }

    // (c) below the threshold both are gone: the division collapses jointly
    let mut d = Division::new(part(D), part(D), Q_MIN, 10.0);
    d.income = 0.5 + 1.5 * D * Q_MIN; // the price of one part, half of what two need
    let mut fell_first = None;
    for _ in 0..200_000 {
        if !d.step(1.5 * D * Q_MIN) {
            fell_first = d.killed_first;
            break;
        }
    }
    let c = fell_first == Some(PartName::Skin);
    println!(
        "  {} (c) below the threshold the division dies of A: {fell_first:?}",
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
