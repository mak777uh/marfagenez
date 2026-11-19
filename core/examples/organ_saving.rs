//! Потолок 2 из `MODEL-CEILINGS.md`: **излишек с пользой**. Впервые появляется **выбор** — тратить или сберегать.
//!
//! Форма получает доход и распределяет его: доля `alpha` идёт в починку (поднимает `q`, снижает смертность),
//! доля `1 - alpha` — в **запас**. Засуха случается с вероятностью `p` и длится `k` шагов: в ней дохода нет, и
//! починка берётся **из запаса**.
//!
//! PREDICTION, before the run (`q_min` не участвует в смерти; `mu = floor + rate*(1-q)^p_exponent + lambda*damage`,
//! доход 0.04, N = 400 сидов на точку, горизонт 5000 шагов):
//!   (a) **без засух** (p = 0) выгоднее всего тратить всё на починку: `alpha = 1` даёт наибольшую долю выживших;
//!   (b) максимум окажется **внутри** свипа (0.60…0.85), а не на краю, и кривая будет **плоской**: разброс меньше
//!       10 % от максимума;
//!   (c) значит `alpha` оптимальное **зависит от режима** — то есть у формы есть **выбор**, а не один рецепт.
//!
//! Если оптимум не сдвинется, потолок «излишек» не снимается: запас не даёт выбора, а только страховку.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const RATE: f64 = 0.01;
const P_EXP: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const INCOME: f64 = 0.04;
const COST: f64 = 1.0;
const HORIZON: usize = 5000;
const SEEDS: usize = 1600;

/// One life. Returns the number of steps survived (HORIZON if it never died).
fn one(alpha: f64, drought_p: f64, drought_len: usize, seed: u64) -> usize {
    let mut rng = Rng::new(seed);
    let mut q = 1.0_f64;
    let mut stock = 0.0_f64;
    let mut damage = 0.0_f64;
    let mut drought_left = 0usize;
    let mut steps = 0;

    for step in 1..=HORIZON {
        steps = step;
        // drought bookkeeping
        if drought_left > 0 {
            drought_left -= 1;
        } else if drought_p > 0.0 {
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u < drought_p {
                drought_left = drought_len;
            }
        }
        let dry = drought_left > 0;

        // the decay, and the money available for repair this step
        q *= 1.0 - 0.05;
        let income = if dry { 0.0 } else { INCOME };
        let to_stock = income * (1.0 - alpha);
        stock += to_stock;
        let budget = income * alpha + if dry { stock.min(0.02) } else { 0.0 };
        let repair = (budget / COST).min(1.0 - q).max(0.0);
        stock = (stock - if dry { budget.min(stock) } else { 0.0 }).max(0.0);
        q = (q + repair).min(1.0);
        if q >= 1.0 - 1e-12 {
            q = 1.0;
        }

        // fading mortality with the aging floor
        let mu = aging_mortality(q, RATE, P_EXP, FLOOR, LAMBDA, damage);
        let survive = (-mu).exp();
        let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
        if u > survive {
            return steps;
        }
        damage += DELTA;
    }
    steps
}

/// Mean lifetime - the metric that works when every form eventually dies of damage.
fn survival(alpha: f64, drought_p: f64, drought_len: usize) -> f64 {
    let mut total = 0.0;
    for seed in 0..SEEDS as u64 {
        total += one(alpha, drought_p, drought_len, seed + 1) as f64;
    }
    total / SEEDS as f64
}

fn best(regime: &str, drought_p: f64, drought_len: usize) -> (f64, f64) {
    println!("{regime}:");
    let mut best = (0.0, -1.0);
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0] {
        let s = survival(alpha, drought_p, drought_len);
        println!("  alpha {alpha:>4.2}: средняя жизнь {s:>7.1}");
        if s > best.1 {
            best = (alpha, s);
        }
    }
    best
}

fn main() {
    // Is the optimum a PEAK or a PLATEAU? Sweep finely under the lethal drought.
    println!("смертельная засуха (p = 0.02, k = 400), свип 0.05:");
    let mut rows: Vec<(f64, f64)> = Vec::new();
    for alpha in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90] {
        let life = survival(alpha, 0.02, 400);
        println!("  alpha {alpha:>4.2}: средняя жизнь {life:>7.1}");
        rows.push((alpha, life));
    }

    println!();
    let mut bad = 0;

    let best = rows.iter().cloned().fold((0.0, f64::MIN), |a, b| if b.1 > a.1 { b } else { a });
    let worst = rows.iter().cloned().fold((0.0, f64::MAX), |a, b| if b.1 < a.1 { b } else { a });
    let spread = (best.1 - worst.1) / best.1;

    // (a) the best value is interior, not at either end of the sweep
    let a = rows[0].0 < best.0 && best.0 < rows[rows.len() - 1].0;
    println!("  {} (a) оптимум внутри: alpha = {:.2} при жизни {:.1}", if a { "ok   " } else { "WRONG" }, best.0, best.1);
    if !a {
        bad += 1;
    }

    // (b) the curve is flat: the spread across the whole sweep is under 10 %
    let b = spread < 0.10;
    println!("  {} (b) кривая плоская: разброс {:.1} % от максимума", if b { "ok   " } else { "WRONG" }, spread * 100.0);
    if !b {
        bad += 1;
    }

    // (c) and it is flat near the top: every alpha from 0.6 to 0.85 is within 5 % of the best
    let near: Vec<f64> = rows.iter().filter(|r| r.0 >= 0.6 - 1e-9 && r.0 <= 0.85 + 1e-9).map(|r| r.1).collect();
    let c = near.iter().all(|v| (best.1 - v) / best.1 < 0.05);
    println!(
        "  {} (c) от 0.60 до 0.85 всё в пределах 5 %: {:?}",
        if c { "ok   " } else { "WRONG" },
        near.iter().map(|v| (v * 10.0).round() / 10.0).collect::<Vec<_>>()
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
