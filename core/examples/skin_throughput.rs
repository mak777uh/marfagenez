//! What separates a thing that maintains itself from one that merely persists?
//!
//! `GOAL.md` §1a names the test: remove the exchange and a living thing falls apart, while a stone does not. In
//! this model that is not a slogan - it is a contrast between two forms with the same geometry and the same skin,
//! differing only in whether they pay to keep it:
//!
//! * a **passive** form (`u = 0`) never repairs, so its lifetime is `ln(q_min)/ln(1-d)` whatever the medium does;
//! * a **maintained** form pays `c*u` a step, so its lifetime depends on the matter coming in.
//!
//! PREDICTION, before the run (five inflows from 1 to 500, one form, 200 000 steps):
//!   (a) the passive lifetime is **the same at every inflow** - 32 steps - because nothing in it depends on the
//!       medium;
//!   (b) the maintained lifetime **orders with the inflow** and at some inflow it stops being finite at all;
//!   (c) therefore at a low inflow the maintained form dies **sooner** than the passive one - being alive in the
//!       sense of "paying for the skin" can be worse than not paying, when the medium cannot back it.

use medium_core::skin::{run, SkinRules};

const HORIZON: usize = 200_000;

fn main() {
    // maintenance is zero on purpose: otherwise the form starves before the skin matters and the contrast is never
    // exercised. Here the only thing energy is spent on is the repair itself.
    let rules = SkinRules {
        decay: 0.05,
        q_min: 0.2,
        repair_cost: 10.0,
        income: 1.0,
        maintenance: 0.0,
    };
    let need = rules.u_min();

    println!(
        "{:>8} {:>12} {:>12} {:>12}",
        "inflow", "passive life", "repaired life", "repaired alive"
    );
    let mut rows = Vec::new();
    for inflow in [0.02, 0.05, 0.09, 0.10, 0.20, 1.0] {
        // the single-form run draws its income from the rules; a "medium" here is that income
        let mut r = rules;
        r.income = inflow;
        let passive = run(r, 1.0, 10.0, 0.0, HORIZON);
        let repaired = run(r, 1.0, 10.0, need, HORIZON);
        println!(
            "{inflow:>8.1} {:>12} {:>12} {:>12}",
            passive.steps,
            repaired.steps,
            if repaired.alive { "yes" } else { "no" }
        );
        rows.push((inflow, passive.steps, repaired.steps, repaired.alive));
    }

    println!();
    let mut bad = 0;

    let passive_constant = rows.iter().all(|r| r.1 == rows[0].1);
    println!(
        "  {} (a) the passive lifetime does not depend on the medium: {:?}",
        if passive_constant { "ok   " } else { "WRONG" },
        rows.iter().map(|r| r.1).collect::<Vec<_>>()
    );
    if !passive_constant {
        bad += 1;
    }

    let ordered = rows.windows(2).all(|w| w[1].2 >= w[0].2);
    println!(
        "  {} (b) the repaired lifetime orders with the inflow: {:?}",
        if ordered { "ok   " } else { "WRONG" },
        rows.iter().map(|r| r.2).collect::<Vec<_>>()
    );
    if !ordered {
        bad += 1;
    }

    let worse_when_poor = rows.iter().any(|r| r.2 < r.1);
    println!(
        "  {} (c) at some inflow paying for the skin is worse than not paying",
        if worse_when_poor { "ok   " } else { "WRONG" }
    );
    if !worse_when_poor {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
