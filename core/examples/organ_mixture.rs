//! Две независимые величины: целость `q` защищает от распада, запас `w` — от голода.
//!
//! `DESIGN-two-quantities.md`. Доход делится: доля `beta` в целость, `1-beta` в запас. Смерть наступает двумя
//! независимыми способами.
//!
//! PREDICTION, before the run (доход 0.04, распад 0.05, `w_need = 0.5`, засуха ест 0.02 в шаг, 800 сидов):
//!   (a) оптимум `beta` лежит **внутри** (не 0 и не 1) при каждой частоте засух;
//!   (b) оптимум **сдвигается влево** с ростом частоты засух: больше запас → меньше `beta`;
//!   (c) сдвиг **плавный**: между тремя частотами нет скачков больше половины шага свипа.

use medium_core::Rng;

const INCOME: f64 = 0.04;
const D: f64 = 0.05;
const FLOOR: f64 = 0.0002;
const RATE: f64 = 0.01;
const P_EXP: f64 = 2.0;
const W_NEED: f64 = 0.5;
const STARVE: f64 = 0.05;
const DROUGHT_COST: f64 = 0.02;
const DROUGHT_LEN: usize = 100;
const HORIZON: usize = 3000;
const SEEDS: usize = 800;

fn one(beta: f64, drought_p: f64, seed: u64) -> usize {
    let mut rng = Rng::new(seed);
    let mut q = 1.0_f64;
    let mut w = W_NEED;
    let mut drought_left = 0usize;

    for step in 1..=HORIZON {
        if drought_left > 0 {
            drought_left -= 1;
        } else if drought_p > 0.0 {
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u < drought_p {
                drought_left = DROUGHT_LEN;
            }
        }
        let dry = drought_left > 0;

        // integrity
        q *= 1.0 - D;
        let repair = (beta * INCOME).min(1.0 - q).max(0.0);
        q = (q + repair).min(1.0);
        if q >= 1.0 - 1e-12 {
            q = 1.0;
        }

        // store
        w += (1.0 - beta) * INCOME;
        if dry {
            w = (w - DROUGHT_COST).max(0.0);
        }

        // two independent causes of death
        let mu_q = FLOOR + RATE * (1.0 - q).clamp(0.0, 1.0).powf(P_EXP);
        let mu_w = STARVE * (1.0 - (w / W_NEED).min(1.0)).max(0.0);
        let survive = (-(mu_q + mu_w)).exp();
        let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
        if u > survive {
            return step;
        }
    }
    HORIZON
}

fn mean_life(beta: f64, drought_p: f64) -> f64 {
    let mut total = 0.0;
    for seed in 0..SEEDS as u64 {
        total += one(beta, drought_p, seed + 1) as f64;
    }
    total / SEEDS as f64
}

fn main() {
    let betas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0];
    let rates = [0.001, 0.005, 0.02];
    println!("{:>7} {:>10} {:>10} {:>10}", "beta", "засуха 0.1%", "0.5%", "2%");
    let mut table = Vec::new();
    for beta in betas {
        let row: Vec<f64> = rates.iter().map(|r| mean_life(beta, *r)).collect();
        println!(
            "{beta:>7.1} {:>10.1} {:>10.1} {:>10.1}",
            row[0], row[1], row[2]
        );
        table.push((beta, row));
    }

    println!();
    let mut bad = 0;

    // the optimum for each drought rate
    let mut optima = Vec::new();
    for (j, _) in rates.iter().enumerate() {
        let best = table
            .iter()
            .max_by(|a, b| a.1[j].partial_cmp(&b.1[j]).unwrap())
            .unwrap();
        optima.push(best.0);
    }
    println!("оптимумы: {optima:?}");

    let a = optima.iter().all(|b| *b > 0.0 && *b < 1.0);
    println!("  {} (a) оптимум внутри при каждой частоте засух", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = optima.windows(2).all(|w| w[1] <= w[0]);
    println!("  {} (b) оптимум сдвигается влево с ростом засух", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    // (c) and the shift is gradual: no jump beyond half a sweep step
    let c = optima.windows(2).all(|w| (w[1] - w[0]).abs() <= 0.1 + 1e-9);
    println!("  {} (c) сдвиг плавный (шаг свипа 0.2)", if c { "ok   " } else { "WRONG" });
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
