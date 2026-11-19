//! Сходится ли доля штамма при росте популяции? `FINDING-303` показал, что при 200 формах доля A 0.790, а при 2000 —
//! 0.990. Значит вопрос не в конкретном числе, а в том, **есть ли предел**.
//!
//! PREDICTION, before the run (`inherit = 1.0`, `q = 0.5`, 50 000 шагов, размеры 200 / 500 / 1000 / 2000 / 5000):
//!   (a) доля A **растёт** с размером и **сходится** к пределу выше 0.95;
//!   (b) разброс между соседними размерами **падает**;
//!   (c) при 5000 доля A **выше**, чем при 200, и не ниже 0.95.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const INHERIT: f64 = 1.0;
const STEPS: usize = 50_000;

struct Form {
    strain_a: bool,
    damage: f64,
}

fn run(n: usize) -> f64 {
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
        let life_b = 1.0 / aging_mortality(Q, RATE, P, FLOOR, LAMBDA, INHERIT * mean_b);
        let total_life = life_a + life_b;

        for i in 0..pop.len() {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, pop[i].damage);
            let survive = (-mu).exp();
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u > survive {
                let pick = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
                let newcomer_a = pick * total_life < life_a;
                let parent_damage = if newcomer_a { 0.0 } else { mean_b };
                let inherit = if newcomer_a { 0.0 } else { INHERIT };
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
    println!("{:>8} {:>10}", "size", "share A");
    let mut rows = Vec::new();
    for n in [200usize, 500, 1000, 2000, 5000] {
        let share = run(n);
        println!("{n:>8} {share:>10.3}");
        rows.push((n, share));
    }

    println!();
    let mut bad = 0;

    let last = rows[rows.len() - 1].1;
    let a = last > 0.95 && rows.windows(2).all(|w| w[1].1 >= w[0].1 - 0.02);
    println!("  {} (a) the share rises and settles above 0.95: {last:.3}", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let spread_first = (rows[1].1 - rows[0].1).abs();
    let spread_last = (rows[4].1 - rows[3].1).abs();
    let b = spread_last <= spread_first;
    println!(
        "  {} (b) the spread between neighbours does not grow: {spread_first:.3} at the start, {spread_last:.3} at the end",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = last > rows[0].1 && last >= 0.95;
    println!("  {} (c) 5000 gives more than 200: {last:.3} against {:.3}", if c { "ok   " } else { "WRONG" }, rows[0].1);
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
