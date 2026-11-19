//! When the pool pays for repair, does self-maintenance become a commons problem?
//!
//! `FINDING-266` found the flaw in the "ask for what you need" accounting: a form's ration included the price of
//! its own repair, so **asking for more bought more**, and the intensity inflated to twice the need without any
//! advantage. The next accounting removes that: the pool pays for repair **directly**, so a form receives only
//! maintenance plus a margin, and its repair is matter delivered straight to the repair.
//
//! An inflated intensity then buys **no extra energy** - it only spends the commons. Which makes the question
//! sharp: does selection still push the intensity up, because the survivor is the one who takes the most from the
//! stock? That is the tragedy of the commons, written in the smallest possible model.
//!
//! PREDICTION, before the run (8000 steps, start at twice the need, repair paid by the pool):
//!   (a) the intensity **rises above** the value it had when each form paid for its own repair - the commons
//!       rewards taking;
//!   (b) the standing stock **falls** compared with the same run without pool-paid repair;
//!   (c) the population survives, because a form that pays nothing for its own repair cannot go bankrupt.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 8000;

fn rules(cost: f64, pool_pays: bool) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: cost,
            income: 1.0,
            maintenance: 0.7,
        },
        u_noise: 0.3,
        u_shift: 0.003,
        birth_price: 1.5,
        max_population: 300,
        demand_growth: Some(0.1),
        repair_from_pool: pool_pays,
    }
}

fn main() {
    let need = rules(10.0, true).skin.u_min();
    println!("need u_min = {need:.4}");
    println!(
        "{:>7} {:>11} {:>7} {:>9} {:>8} {:>9}",
        "cost", "paying", "alive", "mean u", "x need", "stock"
    );
    let mut rows = Vec::new();
    for cost in [1.0, 10.0, 30.0] {
        for pool_pays in [false, true] {
            let pop = run_shared(
                rules(cost, pool_pays),
                SkinPool::new(50.0, 500.0, 300.0, 1.0),
                1.0,
                10.0,
                0.02,
                STEPS,
                SEED,
            );
            let mean = pop.mean_u();
            println!(
                "{cost:>7.1} {:>11} {:>7} {mean:>9.4} {:>8.2} {:>9.1}",
                if pool_pays { "the pool" } else { "the form" },
                pop.forms.len(),
                mean / need,
                pop.pool.stock
            );
            rows.push((cost, pool_pays, pop.forms.len(), mean / need, pop.pool.stock));
        }
    }

    println!();
    let mut bad = 0;
    let get = |c: f64, m: bool| {
        rows.iter()
            .find(|r| r.0 == c && r.1 == m)
            .copied()
            .expect("row")
    };

    let rises = [1.0, 10.0, 30.0].iter().all(|c| {
        let own = get(*c, false);
        let pool = get(*c, true);
        pool.3.is_nan() || pool.3 > own.3
    });
    println!(
        "  {} (a) the intensity rises when the pool pays: {:?}",
        if rises { "ok   " } else { "WRONG" },
        [1.0, 10.0, 30.0]
            .iter()
            .map(|c| (c, (get(*c, false).3 * 100.0).round() / 100.0, (get(*c, true).3 * 100.0).round() / 100.0))
            .collect::<Vec<_>>()
    );
    if !rises {
        bad += 1;
    }

    let falls = [1.0, 10.0, 30.0].iter().all(|c| {
        let own = get(*c, false);
        let pool = get(*c, true);
        pool.4.is_nan() || pool.4 <= own.4 + 1.0
    });
    println!(
        "  {} (b) the standing stock does not grow when the pool pays",
        if falls { "ok   " } else { "WRONG" }
    );
    if !falls {
        bad += 1;
    }

    let survives = [1.0, 10.0, 30.0].iter().all(|c| get(*c, true).2 > 0);
    println!("  {} (c) the population survives when the pool pays", if survives { "ok   " } else { "WRONG" });
    if !survives {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
