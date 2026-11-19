//! Сходится ли доля штамма при росте популяции? `FINDING-303` показал, что при 200 формах доля A 0.790, а при 2000 —
//! 0.990. Значит вопрос не в конкретном числе, а в том, **есть ли предел**.
//!
//! PREDICTION, before the run (`FINDING-305` §конец, `q = 0.5`, 50 000 шагов, **N = 2000**):
//!   (a) доля A **растёт** с `inherit` = 0.5 / 0.6 / 0.7 / 0.8 / 0.9 / 1.0;
//!   (b) рост **не ровный**: где-то есть **крутой участок** (наибольший шаг больше среднего вдвое);
//!   (c) концы далеки: разница между 0.5 и 1.0 больше 0.3.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const INHERIT_DEFAULT: f64 = 1.0;
const STEPS: usize = 50_000;

struct Form {
    strain_a: bool,
    damage: f64,
}

fn run(inherit_b: f64, n: usize) -> f64 {
    let mut rng = Rng::new(20261119);
    let mut pop: Vec<Form> = (0..n)
        .map(|i| Form { strain_a: i % 2 == 0, damage: 0.0 })
        .collect();

    for _ in 0..STEPS {
        let mean_b = {
            let mut total = 0.0;
            let mut count = 0;
            for f in &pop {
                if !f.strain_a {
                    total += f.damage;
                    count += 1;
                }
            }
            if count > 0 { total / count as f64 } else { 0.0 }
        };
        // fitness is judged by the newborn's entry damage
        let life_a = 1.0 / aging_mortality(Q, RATE, P, FLOOR, LAMBDA, 0.0);
        let life_b = 1.0 / aging_mortality(Q, RATE, P, FLOOR, LAMBDA, inherit_b * mean_b);
        let total_life = life_a + life_b;

        for i in 0..pop.len() {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, pop[i].damage);
            let survive = (-mu).exp();
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u > survive {
                let pick = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
                let newcomer_a = pick * total_life < life_a;
                let parent_damage = if newcomer_a { 0.0 } else { mean_b };
                let inherit = if newcomer_a { 0.0 } else { inherit_b };
                pop[i].strain_a = newcomer_a;
                pop[i].damage = inherit * parent_damage;
            } else {
                pop[i].damage += DELTA;
            }
        }
    }

    pop.iter().filter(|f| f.strain_a).count() as f64 / pop.len() as f64
}

fn main() {
    // the threshold question: how strong must the advantage be before it evicts?
    println!("{:>9} {:>10}", "inherit", "share A");
    let mut rows = Vec::new();
    for inherit in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0] {
        let share = run(inherit, 2000);
        println!("{inherit:>9.1} {share:>10.3}");
        rows.push((inherit, share));
    }

    println!();
    let mut bad = 0;

    // (a) the share rises with the strength of the advantage
    let a = rows.windows(2).all(|w| w[1].1 >= w[0].1 - 0.02);
    println!(
        "  {} (a) the share rises with the strength: {:?}",
        if a { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 * 1000.0).round() / 1000.0)).collect::<Vec<_>>()
    );
    if !a {
        bad += 1;
    }

    // (b) there is a steep step somewhere in the middle, not a uniform rise
    let steps: Vec<f64> = rows.windows(2).map(|w| w[1].1 - w[0].1).collect();
    let biggest = steps.iter().cloned().fold(f64::MIN, f64::max);
    let mean = steps.iter().sum::<f64>() / steps.len() as f64;
    let b = biggest > 0.25 && biggest > 2.0 * mean.abs();
    println!(
        "  {} (b) the rise is steep at one point: biggest step {biggest:.3}, mean {mean:.3}",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    // (c) the ends differ a lot
    let c = rows[rows.len() - 1].1 - rows[0].1 > 0.3;
    println!(
        "  {} (c) the ends are far apart: {:.3} against {:.3}",
        if c { "ok   " } else { "WRONG" },
        rows[rows.len() - 1].1,
        rows[0].1
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
