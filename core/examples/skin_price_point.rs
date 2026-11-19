//! Does the price of the skin move the point of convergence?
//!
//! `FINDING-263` measured the settled intensity at **1.4 times the need**, and `FINDING-264` failed to explain it by
//! the mutation noise. The remaining suspect is the price: if the margin is a property of the economy, a dearer
//! skin should move it.
//!
//! PREDICTION, before the run (scarce medium, start at twice the need, 8000 steps, noise 0.3):
//!   (a) the settled intensity stays **near 1.4 times the need** for `repair_cost` = 1, 10 and 30 - within
//!       1.2 ... 1.8, so the price does not move it;
//!   (b) the population survives at all three prices, because the need `d*q_min` does not depend on the price.
//!
//! If (a) fails, the margin belongs to the economy and the word "safety margin" is wrong.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 8000;

fn rules(repair_cost: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost,
            income: 1.0,
            maintenance: 0.7,
        },
        u_noise: 0.3,
        u_shift: 0.003,
        birth_price: 1.5,
        max_population: 300,
    }
}

fn main() {
    let need = rules(10.0).skin.u_min();
    println!("need u_min = {need:.4} (independent of the price)");
    println!("{:>11} {:>7} {:>9} {:>10}", "repair_cost", "alive", "mean u", "x need");
    let mut rows = Vec::new();
    for cost in [1.0, 10.0, 30.0] {
        let pop = run_shared(rules(cost), SkinPool::new(50.0, 500.0, 30.0, 1.0), 1.0, 10.0, 0.02, STEPS, SEED);
        let mean = pop.mean_u();
        println!("{cost:>11.1} {:>7} {mean:>9.4} {:>10.2}", pop.forms.len(), mean / need);
        rows.push((cost, pop.forms.len(), mean, mean / need));
    }

    // the dear arm kept only six forms, so its mean is a handful of lineages and its selection is weak. The
    // control is the same price in a richer medium: if the margin comes back to the cheap value, the 2.05 was
    // the near-extinction, not the price.
    println!();
    println!("control: repair_cost 30 in a richer medium (inflow 300)");
    let rich = run_shared(
        rules(30.0),
        SkinPool::new(50.0, 500.0, 300.0, 1.0),
        1.0,
        10.0,
        0.02,
        STEPS,
        SEED,
    );
    println!(
        "  alive {:>3} mean u {:.4} x need {:.2}",
        rich.forms.len(),
        rich.mean_u(),
        rich.mean_u() / need
    );

    println!();
    let mut bad = 0;

    let stays = rows.iter().all(|r| r.3 >= 1.2 && r.3 <= 1.8);
    println!(
        "  {} (a) the ratio stays within 1.2 ... 1.8 at every price: {:?}",
        if stays { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.3 * 100.0).round() / 100.0)).collect::<Vec<_>>()
    );
    if !stays {
        bad += 1;
    }

    let alive = rows.iter().all(|r| r.1 > 0);
    println!("  {} (b) the population survives at every price", if alive { "ok   " } else { "WRONG" });
    if !alive {
        bad += 1;
    }

    let dear_rich = rich.mean_u() / need;
    let control_ok = !rich.forms.is_empty() && dear_rich < 1.7;
    println!(
        "  {} control: with a population at the dear price the margin falls back: {dear_rich:.2}",
        if control_ok { "ok   " } else { "WRONG" }
    );
    if !control_ok {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
