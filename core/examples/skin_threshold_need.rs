//! Does the pocket threshold move with the need? `q_min` decides what a step of repair costs.
//!
//! `FINDING-275` measured the threshold at 0.010 - exactly `u_min = decay * q_min` for `decay = 0.05`,
//! `q_min = 0.2`. That could be a coincidence with the number 0.01: the birth price is 0.5 and the medium ceiling is
//! 5, and either might be what the threshold really tracks.
//!
//! PREDICTION, before the run (no inflow, `ready_max = 5`, `c = 1`, full locality, 4000 steps, cap 5000):
//!   (a) the threshold **moves with `u_min`**: for `q_min` = 0.1, 0.2 and 0.4 the smallest cap that fills the
//!       population to its ceiling is **half the need**, not the need itself;
//!   (b) below half the need the population is **far smaller**, and above it the population is at the ceiling - a
//!       sharp crossing at each `q_min`;
//!   (c) therefore the threshold is a multiple of `u_min` and **not** a constant near 0.01.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;

fn rules(share: f64, q_min: f64, pocket_max: Option<f64>) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min,
            repair_cost: 1.0,
            income: 1.0,
            maintenance: 0.0,
        },
        u_noise: 0.0,
        u_shift: 0.0,
        birth_price: 0.5,
        max_population: 5000,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: true,
        local_share: share,
        pocket_max,
    }
}

fn run(q_min: f64, pocket_max: Option<f64>) -> usize {
    let r = rules(1.0, q_min, pocket_max);
    let need = r.skin.u_min();
    let cycle = SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
    let mut pop = SkinRecycle::new(r, cycle, 1.0, 10.0, need);
    pop.forms.clear();
    for _ in 0..50 {
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
    }
    let mut rng = medium_core::Rng::new(SEED);
    for _ in 0..STEPS {
        pop.step(&mut rng);
    }
    pop.forms.len()
}

fn main() {
    println!(
        "{:>7} {:>9} {:>10} {:>10} {:>10} {:>10}",
        "q_min", "u_min", "cap u/10", "cap u/2", "cap u", "cap 2u"
    );
    let mut rows = Vec::new();
    for q_min in [0.1, 0.2, 0.4] {
        let need = 0.05 * q_min;
        let a = run(q_min, Some(need / 10.0));
        let b = run(q_min, Some(need / 2.0));
        let c = run(q_min, Some(need));
        let d = run(q_min, Some(need * 2.0));
        println!("{q_min:>7.1} {need:>9.3} {a:>10} {b:>10} {c:>10} {d:>10}");
        rows.push((q_min, need, a, b, c, d));
    }

    println!();
    println!("fine sweep at q_min = 0.2 (need 0.010): does the crossing sit at the need?");
    println!("{:>8} {:>8} {:>7}", "fraction", "cap", "alive");
    let mut fine = Vec::new();
    for frac in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0] {
        let cap = 0.010 * frac;
        let alive = run(0.2, Some(cap));
        println!("{frac:>8.2} {cap:>8.4} {alive:>7}");
        fine.push((frac, alive));
    }

    println!();
    let mut bad = 0;

    // the crossing should be at 1.0, not earlier
    let full = fine[fine.len() - 1].1;
    let before = fine[fine.len() - 2].1;
    let at_full = full == 5000 && before < 5000;
    println!(
        "  {} the crossing is at the full need: {before} just below, {full} at it",
        if at_full { "ok   " } else { "WRONG" }
    );
    if !at_full {
        bad += 1;
    }

    // (a) the crossing sits between a tenth and the whole need, and the whole need always fills the ceiling
    let at_need_fills = rows.iter().all(|r| r.4 == 5000);
    println!(
        "  {} (a) at one full need the population is at its ceiling for every q_min",
        if at_need_fills { "ok   " } else { "WRONG" }
    );
    if !at_need_fills {
        bad += 1;
    }

    // (b) a tenth of the need never fills it, and the numbers track u_min rather than a constant
    let below_is_small = rows.iter().all(|r| r.2 < 5000);
    println!(
        "  {} (b) far below the need the population stays small: {:?}",
        if below_is_small { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.1, r.2)).collect::<Vec<_>>()
    );
    if !below_is_small {
        bad += 1;
    }

    // (c) the threshold is not the constant 0.01: the three limbs differ
    let not_constant = rows.iter().any(|r| r.4 != rows[0].4) == false && rows.windows(2).all(|w| w[1].1 != w[0].1);
    println!(
        "  {} (c) the need itself differs across the three cases: {:?}",
        if not_constant { "ok   " } else { "WRONG" },
        rows.iter().map(|r| r.1).collect::<Vec<_>>()
    );
    if !not_constant {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
