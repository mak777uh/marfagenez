//! Is the threshold a fraction of the need, or does it drift with `q_min`?
//!
//! `FINDING-277` found the crossing between 0.8 and 0.9 of `u_min` at `q_min = 0.2`. If the threshold is really "a
//! fraction of a step", the same fraction should appear at other `q_min`. If it drifts, the fraction is an artefact
//! and only "on the order of the need" survives.
//!
//! PREDICTION, before the run (no inflow, `ready_max = 5`, `c = 1`, full locality, 4000 steps, cap 5000):
//!   (a) at each `q_min` the crossing lies in the same window, **0.8 ... 0.9** of `u_min`;
//!   (b) therefore the three crossings agree to within one step of the sweep (0.05);
//!   (c) below the crossing the population grows smoothly with the cap, above it sits at the ceiling.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;

fn run(q_min: f64, cap_fraction: f64) -> usize {
    let need = 0.05 * q_min;
    let rules = SkinPopRules {
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
        local_share: 1.0,
        pocket_max: Some(need * cap_fraction),
    };
    let cycle = SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
    let mut pop = SkinRecycle::new(rules, cycle, 1.0, 10.0, need);
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
    let fractions = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00];
    print!("{:>7} {:>9}", "q_min", "u_min");
    for f in fractions {
        print!(" {:>9.2}", f);
    }
    println!();

    let mut crossings = Vec::new();
    for q_min in [0.1, 0.2, 0.4] {
        let need = 0.05 * q_min;
        print!("{q_min:>7.1} {need:>9.3}");
        let mut crossing = None;
        for f in fractions {
            let alive = run(q_min, f);
            print!(" {alive:>9}");
            if crossing.is_none() && alive == 5000 {
                crossing = Some(f);
            }
        }
        println!();
        crossings.push((q_min, crossing));
    }

    println!();
    for (q_min, crossing) in &crossings {
        println!("  q_min {q_min}: crossing at {crossing:?} of the need");
    }

    let mut bad = 0;
    let a = crossings.iter().all(|(_, c)| c.map(|f| f >= 0.75 && f <= 0.95).unwrap_or(false));
    println!(
        "  {} (a) every crossing lies in the window 0.75 ... 0.95",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let values: Vec<f64> = crossings.iter().filter_map(|(_, c)| *c).collect();
    let spread = values.iter().cloned().fold(f64::MIN, f64::max) - values.iter().cloned().fold(f64::MAX, f64::min);
    let b = spread <= 0.05 + 1e-9;
    println!(
        "  {} (b) the three crossings agree within the sweep step: spread {spread:.2}",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = run(0.2, 0.5) < 5000 && run(0.2, 1.0) == 5000;
    println!("  {} (c) below the crossing it is small, above it at the ceiling", if c { "ok   " } else { "WRONG" });
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
