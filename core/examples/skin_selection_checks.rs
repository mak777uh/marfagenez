//! The three checks `FINDING-259` left open: a free skin, an expensive skin, a long horizon.
//!
//! PREDICTION, written in `FINDING-259` before this example existed:
//!   1. **free skin** (`repair_cost = 0`): the mean `u` should fall to zero, because paying for something that
//!      is free buys nothing;
//!   2. **expensive skin** (`repair_cost = 30`, so 0.30 a step): in a medium with 0.15 free the population
//!      should die, and in one with 0.30 it should live at the edge;
//!   3. **long horizon** (30 000 steps): the mean `u` should not creep upwards; if it does, selection rewards a
//!      safety margin rather than the threshold.
//!
//! The first prediction is the one worth watching: with no cost there is no force downwards either, and a
//! neutral quantity drifts. If `u` stays high rather than falling, the prediction was wrong in an instructive
//! way - "no cost" is not "selection for zero".

use medium_core::skin::{run_pop, SkinPop, SkinPopRules, SkinRules};

const SEED: u64 = 7;

fn turn(r: &mut SkinPopRules, max_population: usize, birth_price: f64) {
    r.max_population = max_population;
    r.birth_price = birth_price;
}

fn rules(surplus: f64, repair_cost: f64, u_shift: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost,
            income: 1.0,
            maintenance: 1.0 - surplus,
        },
        u_noise: 0.3,
        u_shift,
        birth_price: 1.5,
        max_population: 300,
        demand_growth: None,
        repair_from_pool: false,
    }
}

fn report(label: &str, pop: &SkinPop, u_min: f64) {
    println!(
        "  {label:<22} alive {:>3}  mean u {:>8.4}  maintainers {:>5.2}  births {:>5}  deaths {:>5}",
        pop.forms.len(),
        pop.mean_u(),
        pop.maintainers(),
        pop.births,
        pop.deaths
    );
    let _ = u_min;
}

fn main() {
    let mut bad = 0;

    println!("1  free skin: repair_cost = 0 (u_min stays 0.01, but keeping it costs nothing)");
    let free = run_pop(rules(0.30, 0.0, 0.003), 1.0, 10.0, 0.0, 3000, SEED);
    report("free", &free, 0.01);
    // the design said u -> 0; the honest check asks whether it is *near* zero at all
    let fell_to_zero = free.mean_u() < 0.002;
    println!(
        "  {} 1  predicted u near zero: mean u {:.4}",
        if fell_to_zero { "ok   " } else { "WRONG" },
        free.mean_u()
    );
    if !fell_to_zero {
        bad += 1;
    }

    println!("\n2  expensive skin: repair_cost = 30, so 0.30 a step");
    for (label, surplus) in [("wide 0.30", 0.30), ("tight 0.15", 0.15)] {
        let pop = run_pop(rules(surplus, 30.0, 0.003), 1.0, 10.0, 0.0, 3000, SEED);
        report(label, &pop, 0.01);
        let expected_alive = surplus >= 0.30;
        let ok = (pop.forms.is_empty()) != expected_alive;
        println!(
            "  {} 2  {label}: expected {}, got {} alive",
            if ok { "ok   " } else { "WRONG" },
            if expected_alive { "alive" } else { "dead" },
            pop.forms.len()
        );
        if !ok {
            bad += 1;
        }
    }

    println!("\n3  long horizon: does the intensity creep upwards?");
    // with 300 forms and a birth price of 1.5 the population sat at its ceiling and nothing turned over, so
    // the first version of this check was silent: identical numbers at 3000 and 30000 steps. Room and a
    // cheaper birth are what make the horizon mean something.
    let mut short_rules = rules(0.30, 10.0, 0.003);
    turn(&mut short_rules, 5000, 1.2);
    let mut long_rules = short_rules;
    let short = run_pop(short_rules, 1.0, 10.0, 0.0, 3000, SEED);
    let long = run_pop(long_rules, 1.0, 10.0, 0.0, 30_000, SEED);
    let _ = &mut long_rules;
    report("3000 steps", &short, 0.01);
    report("30000 steps", &long, 0.01);
    let crept = long.mean_u() > short.mean_u() * 2.0;
    println!(
        "  {} 3  the intensity does not creep: {:.4} -> {:.4}",
        if !crept { "ok   " } else { "WRONG" },
        short.mean_u(),
        long.mean_u()
    );
    if crept {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
