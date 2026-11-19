//! A per-step log, not another formula.
//!
//! `FINDING-261` measured that a scarcer medium keeps a **higher** intensity of self-maintenance and could not
//! explain it. The lesson from `FINDING-240` is that when an explanation fails twice, the next move is not a
//! third formula but a **log**: print what happens step by step and read where the two worlds part.
//!
//! PREDICTION, before the run: the mean intensity of the tight world separates from the rich one **before** the
//! rich population reaches its ceiling of 300, so the cause is the share `stock/n` and not the ceiling itself.

use medium_core::skin::{SkinPool, SkinPopRules, SkinRules, SkinShared};

const SEED: u64 = 11;
const EVERY: usize = 200;
const STEPS: usize = 4000;

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
    }
}

fn run(inflow: f64) -> Vec<(usize, usize, f64, f64, f64)> {
    let mut pop = SkinShared::new(rules(), SkinPool::new(50.0, 500.0, inflow, 1.0), 1.0, 10.0, 0.0);
    let mut rng = medium_core::Rng::new(SEED);
    let mut log = Vec::new();
    for step in 1..=STEPS {
        pop.step(&mut rng);
        if step % EVERY == 0 {
            let mean_age = if pop.forms.is_empty() {
                f64::NAN
            } else {
                pop.forms.iter().map(|f| f.age as f64).sum::<f64>() / pop.forms.len() as f64
            };
            log.push((step, pop.forms.len(), pop.mean_u(), pop.pool.stock, mean_age));
        }
    }
    log
}

fn main() {
    let rich = run(600.0);
    let tight = run(30.0);

    println!(
        "{:>6} | {:>6} {:>8} {:>8} {:>7} | {:>6} {:>8} {:>8} {:>7}",
        "step", "alive", "mean u", "stock", "age", "alive", "mean u", "stock", "age"
    );
    println!("{:>6} | {:^32} | {:^32}", "", "rich (600)", "tight (30)");

    let n = rich.len().min(tight.len());
    for i in 0..n {
        let (s, a1, u1, st1, ag1) = rich[i];
        let (_, a2, u2, st2, ag2) = tight[i];
        println!(
            "{s:>6} | {a1:>6} {u1:>8.4} {st1:>8.1} {ag1:>7.1} | {a2:>6} {u2:>8.4} {st2:>8.1} {ag2:>7.1}"
        );
    }

    // where do the intensities first differ by more than five per cent?
    let mut first_difference = None;
    for i in 0..n {
        let (s, _, u1, _, _) = rich[i];
        let (_, _, u2, _, _) = tight[i];
        if u1.is_finite() && u2.is_finite() && u1 > 0.0 && (u2 - u1).abs() / u1 > 0.05 {
            first_difference = Some(s);
            break;
        }
    }

    let ceiling_step = rich.iter().find(|r| r.1 >= 300).map(|r| r.0);
    println!();
    println!("first separation at step {first_difference:?}, rich population hit 300 at {ceiling_step:?}");

    let mut bad = 0;
    match (first_difference, ceiling_step) {
        (Some(sep), Some(ceil)) => {
            let ok = sep < ceil;
            println!(
                "  {} the separation comes before the ceiling",
                if ok { "ok   " } else { "WRONG" }
            );
            if !ok {
                bad += 1;
            }
        }
        _ => {
            println!("  WRONG the worlds never separated (or never reached the ceiling)");
            bad += 1;
        }
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
