//! A shared medium: does competition lower the price of self-maintenance, and can it kill it?
//!
//! `FINDING-260` closed with two predictions, written before this example existed:
//!   1. with a shared stock the mean intensity of maintenance **falls below 0.0134** - the value it held when
//!      income came from nowhere - because matter is now contested and a cheaper skin leaves more for breeding;
//!   2. there appears a regime where **maintenance dies out although the medium could afford it**, if the
//!      lineage that pays nothing breeds fast enough before it falls apart.
//!
//! Three inflows: generous, medium, tight. The stock is finite, so scarcity - not our bookkeeping - decides who
//! dies.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const STEPS: usize = 6000;
const SEED: u64 = 11;

fn rules(skin_cost: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: skin_cost,
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
        "{:>6} {:>8} {:>8} {:>9} {:>9} {:>10} {:>12} {:>9}",
        "inflow", "stock", "alive", "mean u", "maint.", "births", "returned/drawn", "lifetime"
    );
    let mut rows = Vec::new();
    for inflow in [600.0, 120.0, 30.0] {
        let pool = SkinPool::new(50.0, 500.0, inflow, 1.0);
        let pop = run_shared(rules(10.0), pool, 1.0, 10.0, 0.0, STEPS, SEED);
        let ratio = if pop.drawn > 0.0 { pop.returned / pop.drawn } else { f64::NAN };
        println!(
            "{inflow:>6.0} {:>8.1} {:>8} {:>9.4} {:>9.2} {:>10} {:>12.3} {:>9.1}",
            pop.pool.stock,
            pop.forms.len(),
            pop.mean_u(),
            pop.maintainers(),
            pop.births,
            ratio,
            pop.mean_lifetime()
        );
        rows.push((inflow, pop.forms.len(), pop.mean_u(), pop.maintainers(), ratio));
    }

    println!();
    let mut bad = 0;
    let baseline = 0.0134; // FINDING-259, income from nowhere

    // 1. the intensity falls below the unshared value
    let lowered = rows.iter().all(|r| r.2.is_nan() || r.2 < baseline);
    println!(
        "  {} 1  every surviving mean is below {baseline}: {:?}",
        if lowered { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, r.2)).collect::<Vec<_>>()
    );
    if !lowered {
        bad += 1;
    }

    // 2. the medium returns matter: the boundary is not a pure sink
    let soft = rows.iter().all(|r| r.4.is_nan() || r.4 > 0.0);
    println!(
        "  {} 2  decay returns matter to the stock: {:?}",
        if soft { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, r.4)).collect::<Vec<_>>()
    );
    if !soft {
        bad += 1;
    }

    // 3. the population is limited by the stock, not by the ceiling
    let limited = rows.iter().any(|r| r.0 == 30.0 && r.1 < 300);
    println!(
        "  {} 3  a tight inflow keeps the population below the ceiling",
        if limited { "ok   " } else { "WRONG" }
    );
    if !limited {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
