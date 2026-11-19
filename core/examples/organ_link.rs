//! The numbers behind the link: is being skinless worse than being hollow?
//!
//! `core/src/organ.rs` gives a form **two** integrities and one link: the core's repair is scaled by
//! `min(1, q_skin / q_min)`, so a broken boundary stops the inside from being maintained however much is spent.
//!
//! PREDICTION (one form, income 1.0, maintenance 0.5, 200 000 steps):
//!   A  repairing both - lives the whole horizon;
//!   B  repairing **only the core** - dies when the **skin** goes (not when the core would);
//!   C  repairing **only the skin** - lives **longer than B**, because the core decays more slowly;
//!   D  the same as B but with the link **off** - the core stays whole while the skin goes, which shows that the
//!      gate, not the decay rates, kills B.

use medium_core::organ::{run, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;

fn main() {
    let skin = Part::new(1.0, 0.05, 1.0);
    let core = Part::new(1.0, 0.02, 2.0);
    let u_skin = 0.05 * Q_MIN;
    let u_core = 0.02 * Q_MIN;

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

    let a = rows[0].1;
    println!("  {} A repairing both lives the whole horizon", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = !rows[1].1 && format!("{:?}", rows[1].3) == "Some(Skin)";
    println!(
        "  {} B dies of the SKIN, not the core: {:?}",
        if b { "ok   " } else { "WRONG" },
        rows[1].3
    );
    if !b {
        bad += 1;
    }

    let c = rows[2].2 > rows[1].2;
    println!(
        "  {} C lives longer than B: {} vs {} steps",
        if c { "ok   " } else { "WRONG" },
        rows[2].2,
        rows[1].2
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
