//! P5: is the intensity of self-maintenance chosen by the medium?
//!
//! `FINDING-258` priced the skin. This runs a population whose repair intensity is inherited with mutation and
//! asks whether the price picks it.
//!
//! Arithmetic before the code: a form repaying `u` pays `c*u` a step and holds `q* = u/d`, so it lives iff
//! `u >= d*q_min = 0.01`. Even a maintainer grows only at `income - maintenance - c*u` per step. A lineage
//! that pays nothing lives `ln(q_min)/ln(1-d) = 32` steps but keeps every unit of surplus for breeding.
//!
//! PREDICTION (before the run, 3000 steps, 300 forms, mutation 0.3 on `u`, birth price 1.5):
//!   A  generous medium (surplus 0.30 vs skin 0.10): the mean `u` rises from 0.01 and settles **at or just
//!      above `u_min`** - more repair than that is wasted, less is fatal;
//!   B  tight medium (surplus 0.15): the mean `u` still settles near `u_min`, but the population is smaller;
//!   C  medium below the skin price (surplus 0.05 < 0.10): no `u` can both pay the skin and breed, so the
//!      population dies out and the last `u` is not near `u_min`.

use medium_core::skin::{run_pop, SkinPopRules, SkinRules};

const STEPS: usize = 3000;
const SEED: u64 = 7;

fn rules(surplus: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 1.0 - surplus,
        },
        u_noise: 0.3,
        u_shift: 0.003,
        birth_price: 1.5,
        max_population: 300,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: false,
        local_share: 1.0,
        pocket_max: None,
    }
}

fn main() {
    println!(
        "{:>8} {:>9} {:>10} {:>10} {:>12} {:>9}",
        "surplus", "u_min", "skin cost", "alive", "mean u", "maintainers"
    );
    let mut rows = Vec::new();
    for (label, surplus) in [("A", 0.30), ("B", 0.15), ("C", 0.05)] {
        let r = rules(surplus);
        let pop = run_pop(r, 1.0, 10.0, 0.0, STEPS, SEED);
        let u_min = r.skin.u_min();
        let cost = r.skin.skin_cost();
        println!(
            "{label:>8} {surplus:>9.2} {cost:>10.2} {:>10} {:>12.4} {:>9.2}",
            pop.forms.len(),
            pop.mean_u(),
            pop.maintainers()
        );
        rows.push((label, surplus, cost, pop.forms.len(), pop.mean_u(), pop.maintainers(), u_min));
    }

    println!();
    let mut bad = 0;
    for (label, surplus, cost, alive, mean_u, maint, u_min) in &rows {
        let affordable = surplus > cost;
        if *label == "C" {
            let ok = *alive == 0 || mean_u.is_nan();
            println!(
                "  {} C  the medium below the skin price kills everyone: alive {alive}, mean u {mean_u:.4}",
                if ok { "ok   " } else { "WRONG" }
            );
            if !ok {
                bad += 1;
            }
            continue;
        }
        let holds = *alive > 0 && *mean_u >= *u_min * 0.9 && *mean_u <= *u_min * 3.0;
        println!(
            "  {} {label}  mean u {mean_u:.4} against u_min {u_min:.4}: {} (affordable: {affordable})",
            if holds { "ok   " } else { "WRONG" },
            if holds { "at or near the threshold" } else { "away from it" }
        );
        if !holds {
            bad += 1;
        }
        let _ = maint;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
