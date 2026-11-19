//! A population on a closed cycle: does matter reach everybody, or split into the quick and the starving?
//!
//! `FINDING-268` closed the cycle for **one** form: with `c = 1`, perfect recycling and no inflow, it lived on
//! what its own decay returned. A population is a harder question, because each form takes `c*u_min` from the same
//! `ready` stock and returns `q*d` to `spent`, and the sum is only balanced if everyone is at the threshold.
//!
//! PREDICTION, before the run (`c = 1`, maintenance 0, no inflow, start with one form, 8000 steps):
//!   (a) the population survives - the cycle is closed in total, so there is always as much matter as the forms
//!       put back;
//!   (b) but it will **not** grow large: each form draws `c*u_min` and returns `q*d` with `q` at the threshold, so
//!       the sum is exactly balanced and there is no surplus for a second form to live on;
//!   (c) with a slower conversion the `spent` stock grows and the population is smaller still - the delay is the
//!       only margin, and it works against growth.

use medium_core::skin::{SkinCycle, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 8000;
const EVERY: usize = 500;
const SEED: u64 = 3;

fn rules() -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 1.0,
            income: 1.0,
            maintenance: 0.0,
        },
        u_noise: 0.3,
        u_shift: 0.003,
        birth_price: 0.5,
        max_population: 300,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: false,
        local_share: 1.0,
    }
}

fn run(conversion: f64) -> SkinRecycle {
    let cycle = SkinCycle::new(100.0, 0.0, 1000.0, 100_000.0, 0.0, conversion);
    let mut pop = SkinRecycle::new(rules(), cycle, 1.0, 10.0, 0.01);
    let mut rng = medium_core::Rng::new(SEED);
    for _ in 0..STEPS {
        pop.step(&mut rng);
    }
    pop
}

fn main() {
    println!("{:>10} {:>7} {:>9} {:>10} {:>9} {:>8}", "conversion", "alive", "ready", "spent", "mean u", "births");
    let mut rows = Vec::new();
    for conversion in [1.0, 0.5, 0.1] {
        let pop = run(conversion);
        println!(
            "{conversion:>10.1} {:>7} {:>9.1} {:>10.1} {:.4} {:>8}",
            pop.forms.len(),
            pop.cycle.ready,
            pop.cycle.spent,
            pop.mean_u(),
            pop.births
        );
        rows.push((conversion, pop.forms.len(), pop.cycle.ready, pop.cycle.spent));
    }

    println!();
    let mut bad = 0;

    let a = rows[0].1 > 0;
    println!("  {} (a) the population survives on the closed cycle", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = rows[0].1 < 100;
    println!(
        "  {} (b) it does not grow large: {} forms",
        if b { "ok   " } else { "WRONG" },
        rows[0].1
    );
    if !b {
        bad += 1;
    }

    let c = rows[2].1 <= rows[0].1;
    println!(
        "  {} (c) a slower conversion keeps the population no larger: {} vs {}",
        if c { "ok   " } else { "WRONG" },
        rows[2].1,
        rows[0].1
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
