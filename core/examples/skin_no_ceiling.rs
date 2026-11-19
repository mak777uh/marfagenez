//! With the income ceiling removed, does a dear skin work in a rich medium?
//!
//! `FINDING-265` found the ceiling: every form asked for the same fixed `income`, so a richer pool could never
//! give it more, and a dear skin killed the population even where matter was abundant. Here a form asks for what
//! it **needs** - maintenance, the price of its own repair, and a small margin for breeding - and the pool is
//! shared proportionally when it cannot cover everyone.
//!
//! PREDICTION, before the run (8000 steps, start at twice the need):
//!   (a) with the ceiling removed, `repair_cost = 30` in a **rich** medium keeps a **live** population - where
//!       the ceiling kept six dying ones;
//!   (b) at the dear price in a **poor** medium it still dies, because there is not enough matter to pay;
//!   (c) the margin at the dear price in the rich medium falls back towards 1.3, i.e. **below 1.7** - so the
//!       2.05 measured under the ceiling was the turnover of a dying population, not the price.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 8000;

fn rules(cost: f64, need_mode: bool) -> SkinPopRules {
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
        demand_growth: if need_mode { Some(0.1) } else { None },
        repair_from_pool: false,
        local_recycle: false,
        local_share: 1.0,
    }
}

fn main() {
    let need = rules(10.0, true).skin.u_min();
    println!("need u_min = {need:.4}");
    println!(
        "{:>7} {:>6} {:>9} {:>7} {:>9} {:>8}",
        "cost", "inflow", "mode", "alive", "mean u", "x need"
    );
    let mut rows = Vec::new();
    for cost in [1.0, 10.0, 30.0] {
        for (inflow, mode) in [(30.0, false), (30.0, true), (300.0, true), (300.0, false)] {
            let pop = run_shared(
                rules(cost, mode),
                SkinPool::new(50.0, 500.0, inflow, 1.0),
                1.0,
                10.0,
                0.02,
                STEPS,
                SEED,
            );
            let mean = pop.mean_u();
            println!(
                "{cost:>7.1} {inflow:>6.0} {:>9} {:>7} {mean:>9.4} {:>8.2}",
                if mode { "need" } else { "fixed" },
                pop.forms.len(),
                mean / need
            );
            rows.push((cost, inflow, mode, pop.forms.len(), mean / need));
        }
    }

    println!();
    let mut bad = 0;
    let get = |c: f64, inf: f64, m: bool| {
        rows.iter()
            .find(|r| r.0 == c && r.1 == inf && r.2 == m)
            .copied()
            .expect("row")
    };

    let dear_rich_need = get(30.0, 300.0, true);
    let dear_rich_fixed = get(30.0, 300.0, false);
    let dear_poor_need = get(30.0, 30.0, true);

    let a = dear_rich_need.3 > dear_rich_fixed.3;
    println!(
        "  {} (a) a dear skin in a rich medium lives under 'need', not under 'fixed': {} vs {}",
        if a { "ok   " } else { "WRONG" },
        dear_rich_need.3,
        dear_rich_fixed.3
    );
    if !a {
        bad += 1;
    }

    let b = dear_poor_need.3 == 0 || dear_poor_need.3 < dear_rich_need.3;
    println!(
        "  {} (b) the same price in a poor medium keeps fewer or none: {}",
        if b { "ok   " } else { "WRONG" },
        dear_poor_need.3
    );
    if !b {
        bad += 1;
    }

    let c = dear_rich_need.4 < 1.7;
    println!(
        "  {} (c) the margin falls back below 1.7: {:.2}",
        if c { "ok   " } else { "WRONG" },
        dear_rich_need.4
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
