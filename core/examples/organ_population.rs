//! Сходится ли доля штамма при росте популяции? `FINDING-303` показал, что при 200 формах доля A 0.790, а при 2000 —
//! 0.990. Значит вопрос не в конкретном числе, а в том, **есть ли предел**.
//!
//! PREDICTION, before the run (`FINDING-304` §конец, `q = 0.5`, 50 000 шагов, размеры 200 / 1000 / 5000):
//!   (a) при `inherit = 0.5` и **5000** форм доля A вырастет до **0.85–0.97**: малое преимущество тоже вытесняет;
//!   (b) доля растёт с размером и при малом `inherit`;
//!   (c) при каждом размере большее `inherit` даёт **не меньшую** долю.

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
    println!("{:>8} {:>12} {:>12}", "size", "share (0.5)", "share (1.0)");
    let mut rows = Vec::new();
    for n in [200usize, 1000, 5000] {
        let half = run(0.5, n);
        let full = run(1.0, n);
        println!("{n:>8} {half:>12.3} {full:>12.3}");
        rows.push((n, half, full));
    }

    println!();
    let mut bad = 0;

    // (a) a small advantage also evicts once the population is large
    let half_big = rows[rows.len() - 1].1;
    let a = half_big > 0.85;
    println!("  {} (a) at 5000 a mild advantage (0.5) already evicts: {half_big:.3}", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    // (b) and it grows with the size, as at inherit 1.0
    let b = rows.windows(2).all(|w| w[1].1 >= w[0].1 - 0.02);
    println!(
        "  {} (b) the mild advantage grows with the size: {:?}",
        if b { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 * 1000.0).round() / 1000.0)).collect::<Vec<_>>()
    );
    if !b {
        bad += 1;
    }

    // (c) the bigger advantage still wins more at every size
    let c = rows.iter().all(|r| r.2 >= r.1);
    println!("  {} (c) the bigger advantage wins more at every size", if c { "ok   " } else { "WRONG" });
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
