//! Where does the intensity actually settle? The point of convergence has never been measured.
//!
//! `FINDING-262` showed convergence from both sides -- up from zero (0.0134) and down from twice the need
//! (0.0171) -- but those are two stops on the way, not a settled point: 1.3 and 1.7 times the need, a spread of
//! thirty per cent.
//!
//! PREDICTION, before the run (scarce medium, inflow 30, two starts, two horizons):
//!   (a) at 8000 steps the run started above the need is **lower** than at 4000: below 0.0171;
//!   (b) at 8000 steps the run started at zero is **higher** than at 4000: above 0.0134;
//!   (c) the two 8000-step values are **closer to each other** than the two 4000-step values - that is what
//!       "converging" means, and if it fails, the word has to be replaced by "moving towards".

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;

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
    }
}

fn at(start: f64, steps: usize) -> (usize, f64) {
    let pop = run_shared(rules(), SkinPool::new(50.0, 500.0, 30.0, 1.0), 1.0, 10.0, start, steps, SEED);
    (pop.forms.len(), pop.mean_u())
}

fn main() {
    let need = rules().skin.u_min();
    println!("need u_min = {need:.4}");
    println!("{:>6} {:>8} {:>9} {:>9}", "start", "steps", "alive", "mean u");
    let mut rows = Vec::new();
    for start in [0.0, 0.02] {
        for steps in [4000, 8000] {
            let (alive, mean) = at(start, steps);
            println!("{start:>6.3} {steps:>8} {alive:>9} {mean:>9.4}");
            rows.push((start, steps, alive, mean));
        }
    }

    let above4 = rows.iter().find(|r| r.0 == 0.02 && r.1 == 4000).unwrap().3;
    let above8 = rows.iter().find(|r| r.0 == 0.02 && r.1 == 8000).unwrap().3;
    let below4 = rows.iter().find(|r| r.0 == 0.0 && r.1 == 4000).unwrap().3;
    let below8 = rows.iter().find(|r| r.0 == 0.0 && r.1 == 8000).unwrap().3;

    println!();
    let mut bad = 0;

    let a = above8 < above4;
    println!("  {} (a) from above at 8000 is lower: {above4:.4} -> {above8:.4}", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = below8 > below4;
    println!("  {} (b) from below at 8000 is higher: {below4:.4} -> {below8:.4}", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let gap4 = (above4 - below4).abs();
    let gap8 = (above8 - below8).abs();
    let c = gap8 < gap4;
    println!(
        "  {} (c) the gap narrows: {gap4:.4} -> {gap8:.4} (times the need: {:.2} -> {:.2})",
        if c { "ok   " } else { "WRONG" },
        gap4 / need,
        gap8 / need
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
