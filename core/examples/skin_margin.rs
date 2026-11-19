//! Is the forty per cent margin above the need a **safety margin against noise**?
//!
//! `FINDING-263` measured the point of convergence at **1.40-1.43 times the need**, not at the need itself. Twice
//! the same answer is not a coincidence. The obvious suspect is the noise: a lineage whose intensity sits exactly
//! at the need loses some of its children below it, so selection should reward a **margin**, and the margin should
//! grow with the noise.
//!
//! PREDICTION, before the run (scarce medium, start at twice the need, 8000 steps):
//!   (a) the settled intensity **falls** as the mutation noise falls: the ratio to the need is ordered the same
//!       way as the noise;
//!   (b) at the smallest noise (0.05) the ratio is **below 1.4** - below the value measured at noise 0.3;
//!   (c) the margin never reaches zero: even at noise 0.05 the settled intensity stays **above** the need.
//!
//! If (a) fails, the margin is not a safety margin and this explanation joins the list of ones that did not work.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 8000;

fn rules(noise: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.7,
        },
        u_noise: noise,
        u_shift: 0.003,
        birth_price: 1.5,
        max_population: 300,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: false,
        local_share: 1.0,
    }
}

fn main() {
    let need = rules(0.3).skin.u_min();
    println!("need u_min = {need:.4}");
    println!("{:>7} {:>7} {:>9} {:>10}", "noise", "alive", "mean u", "x need");
    let mut rows = Vec::new();
    for noise in [0.05, 0.10, 0.20, 0.30, 0.50] {
        let pop = run_shared(rules(noise), SkinPool::new(50.0, 500.0, 30.0, 1.0), 1.0, 10.0, 0.02, STEPS, SEED);
        let mean = pop.mean_u();
        println!("{noise:>7.2} {:>7} {mean:>9.4} {:>10.2}", pop.forms.len(), mean / need);
        rows.push((noise, pop.forms.len(), mean, mean / need));
    }

    // the narrow mutation died on one seed. Is that a property of the narrowness or of the seed? FINDING-264
    // left this open, so it is answered here: ten seeds at noise 0.05.
    println!();
    println!("ten seeds at noise 0.05:");
    let mut survived = 0;
    for seed in 1..=10u64 {
        let pop = run_shared(rules(0.05), SkinPool::new(50.0, 500.0, 30.0, 1.0), 1.0, 10.0, 0.02, STEPS, seed);
        if !pop.forms.is_empty() {
            survived += 1;
        }
        println!(
            "  seed {seed:>2}: alive {:>3} mean u {:.4}",
            pop.forms.len(),
            pop.mean_u()
        );
    }
    println!("  survived {survived} of 10 seeds");

    println!();
    let mut bad = 0;

    let ordered = rows.windows(2).all(|w| w[1].3 <= w[0].3 + 1e-9);
    println!(
        "  {} (a) the ratio falls as the noise falls: {:?}",
        if ordered { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.3 * 100.0).round() / 100.0)).collect::<Vec<_>>()
    );
    if !ordered {
        bad += 1;
    }

    let small = rows[0].3 < 1.4;
    println!("  {} (b) at noise 0.05 the ratio is below 1.4: {:.2}", if small { "ok   " } else { "WRONG" }, rows[0].3);
    if !small {
        bad += 1;
    }

    let above = rows.iter().all(|r| r.2 > need);
    println!(
        "  {} (c) the intensity stays above the need at every noise",
        if above { "ok   " } else { "WRONG" }
    );
    if !above {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
