//! Can a form be its own supplier? The arithmetic of closing the cycle.
//!
//! `SKIN-LINE-CLOSED.md` recommended the exchange: matter a form decays should return to the medium and shape its
//! own future. With a recycling medium in place, the first question is not ecological - it is arithmetic:
//!
//! ```text
//! taken   = c * u_min  = 10 * 0.01 = 0.10  per step   (the price of staying whole)
//! returned = q * decay = 1.00 * 0.05 = 0.05 per step   (what decay gives back)
//! ```
//!
//! Even at perfect recycling the form **takes twice what it returns**, so the cycle cannot close: a form that
//! lives on nothing but its own decay runs down.
//!
//! PREDICTION, before the run (one form at the need, inflow 0, ready 100, 200 000 steps):
//!   (a) with **no** recycling (conversion 0) the form dies, and the `spent` stock holds exactly what it
//!       returned - the matter is not lost, it is unusable;
//!   (b) with **perfect** recycling (conversion 1) the form still dies, because it takes twice what it returns;
//!   (c) therefore the cycle cannot be closed by any conversion rate: **a form cannot be its own supplier**, and
//!       what the model needs for a closed cycle is more returned than taken.

use medium_core::skin::{run_recycle, SkinCycle, SkinPopRules, SkinRules};

const STEPS: usize = 200_000;

fn rules(u_noise: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.0,
        },
        u_noise,
        u_shift: 0.0,
        birth_price: 1.5,
        max_population: 1,
        demand_growth: None,
        repair_from_pool: false,
    }
}

fn main() {
    let base = rules(0.0);
    let need = base.skin.u_min();
    let taken = base.skin.repair_cost * need;
    let returned = 1.0 * base.skin.decay;
    println!("taken per step {taken:.3}, returned per step {returned:.3}");
    println!("{:>12} {:>7} {:>10} {:>9} {:>8}", "conversion", "alive", "steps", "ready", "spent");

    let mut rows = Vec::new();
    for conversion in [0.0, 0.5, 1.0] {
        let cycle = SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, conversion);
        let pop = run_recycle(base, cycle, 1.0, 10.0, need, STEPS, 1);
        let alive = pop.forms.len();
        println!(
            "{conversion:>12.1} {alive:>7} {:>10} {:>9.1} {:>8.1}",
            pop.steps, pop.cycle.ready, pop.cycle.spent
        );
        rows.push((conversion, alive, pop.steps, pop.cycle.ready, pop.cycle.spent));
    }

    println!();
    let mut bad = 0;

    let a = rows[0].1 == 0 && rows[0].4 > 0.0;
    println!(
        "  {} (a) without recycling the form dies and its returned matter sits unusable: spent {:.1}",
        if a { "ok   " } else { "WRONG" },
        rows[0].4
    );
    if !a {
        bad += 1;
    }

    let b = rows[2].1 == 0;
    println!("  {} (b) with perfect recycling it still dies", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let c = taken > returned;
    println!(
        "  {} (c) the arithmetic says the cycle cannot close: taken {taken:.3} > returned {returned:.3}",
        if c { "ok   " } else { "WRONG" }
    );
    if !c {
        bad += 1;
    }

    // the condition for a closable cycle: taken <= returned, i.e. c*u_min <= q*decay, i.e. roughly c*q_min <= q.
    // With c = 10 that is impossible (10 * 0.2 = 2 > 1), so a cheaper skin should close the loop with no inflow.
    println!();
    println!("a cheaper skin, perfect recycling, no inflow:");
    println!("{:>7} {:>7} {:>10} {:>9} {:>8}", "cost", "alive", "steps", "ready", "spent");
    let mut closed = Vec::new();
    for cost in [1.0, 2.0, 4.0, 6.0] {
        let mut r = rules(0.0);
        r.skin.repair_cost = cost;
        let need = r.skin.u_min();
        let cycle = SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, 1.0);
        let pop = run_recycle(r, cycle, 1.0, 10.0, need, STEPS, 1);
        println!(
            "{cost:>7.1} {:>7} {:>10} {:>9.1} {:>8.1}",
            pop.forms.len(),
            pop.steps,
            pop.cycle.ready,
            pop.cycle.spent
        );
        closed.push((cost, pop.forms.len()));
    }

    // the derived condition: a cycle closes when the price of staying whole is at most what decay returns
    let closes_cheap = closed[0].1 > 0;
    let fails_dear = closed[3].1 == 0;
    println!(
        "  {} the loop closes for a cheap skin (cost 1) and not for a dear one (cost 6)",
        if closes_cheap && fails_dear { "ok   " } else { "WRONG" }
    );
    if !(closes_cheap && fails_dear) {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
