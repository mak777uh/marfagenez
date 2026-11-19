//! Does a form's own decay shape its own future supply?
//!
//! `SKIN-LINE-CLOSED.md` recommended one thing: the project has a quantity a form **keeps** and none that it
//! **exchanges**. `GOAL.md` §1a makes the exchange a condition of life - take it away and a living thing falls
//! apart, while a stone does not.
//!
//! Here the medium has two kinds of matter: `ready`, which forms can draw, and `spent`, which their decay returns
//! and which must be **converted** back before anyone can use it. A form that keeps more integrity alive holds
//! more matter in circulation and therefore loses more to decay every step: **maintenance itself loads the medium
//! it depends on**.
//!
//! PREDICTION, before the run (inflow 300, 8000 steps, start at twice the need):
//!   (a) with a slow conversion the `spent` stock **accumulates** and the `ready` stock stays low;
//!   (b) the population at a slow conversion is **smaller** than at a fast one, with the same external inflow;
//!   (c) the mean intensity of maintenance is **lower** at a slow conversion - because keeping yourself whole is
//!       what loads the medium, and at a slow conversion that load falls on your own descendants.

use medium_core::skin::{run_recycle, SkinCycle, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 8000;

fn rules() -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.7,
        },
        u_noise: 0.3,
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
    println!(
        "{:>10} {:>7} {:>9} {:>9} {:>9} {:>8}",
        "conversion", "alive", "ready", "spent", "mean u", "x need"
    );
    let need = rules().skin.u_min();
    let mut rows = Vec::new();
    for conversion in [0.02, 0.10, 0.50, 1.00] {
        let cycle = SkinCycle::new(100.0, 0.0, 2000.0, 100_000.0, 300.0, conversion);
        let pop = run_recycle(rules(), cycle, 1.0, 10.0, 0.02, STEPS, SEED);
        println!(
            "{conversion:>10.2} {:>7} {:>9.1} {:>9.1} {:.4} {:>8.2}",
            pop.forms.len(),
            pop.cycle.ready,
            pop.cycle.spent,
            pop.mean_u(),
            pop.mean_u() / need
        );
        rows.push((conversion, pop.forms.len(), pop.cycle.ready, pop.cycle.spent, pop.mean_u() / need));
    }

    println!();
    let mut bad = 0;
    let slow = rows[0];
    let fast = rows[3];

    let a = slow.3 > fast.3 && slow.2 < fast.2;
    println!(
        "  {} (a) a slow conversion accumulates `spent` ({:.0}) and starves `ready` ({:.0})",
        if a { "ok   " } else { "WRONG" },
        slow.3,
        slow.2
    );
    if !a {
        bad += 1;
    }

    let b = slow.1 < fast.1;
    println!(
        "  {} (b) the population is smaller at a slow conversion: {} vs {}",
        if b { "ok   " } else { "WRONG" },
        slow.1,
        fast.1
    );
    if !b {
        bad += 1;
    }

    let c = slow.4 < fast.4;
    println!(
        "  {} (c) the intensity is lower at a slow conversion: {:.2} vs {:.2} times the need",
        if c { "ok   " } else { "WRONG" },
        slow.4,
        fast.4
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
