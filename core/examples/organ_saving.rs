//! Потолок 2 из `MODEL-CEILINGS.md`: **излишек с пользой**. Впервые появляется **выбор** — тратить или сберегать.
//!
//! Форма получает доход и распределяет его: доля `alpha` идёт в починку (поднимает `q`, снижает смертность),
//! доля `1 - alpha` — в **запас**. Засуха случается с вероятностью `p` и длится `k` шагов: в ней дохода нет, и
//! починка берётся **из запаса**.
//!
//! PREDICTION, before the run (`q_min` не участвует в смерти; `mu = floor + rate*(1-q)^p_exponent + lambda*damage`,
//! доход 0.04, N = 400 сидов на точку, горизонт 5000 шагов):
//!   (a) **без засух** (p = 0) выгоднее всего тратить всё на починку: `alpha = 1` даёт наибольшую долю выживших;
//!   (b) **при смертельной засухе** (p = 0.02, k = 400) оптимум **сдвигается**: без запаса форма не переживает
//!       засуху, и «тратить всё» становится смертельной стратегией;
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
const SEEDS: usize = 400;

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
    let calm = best("без засух", 0.0, 0);
    let dry = best("смертельная засуха (p = 0.02, k = 400)", 0.02, 400);

    println!();
    let mut bad = 0;

    let a = calm.0 > 0.9;
    println!("  {} (a) без засух оптимум — тратить всё (alpha = {:.2})", if a { "ok   " } else { "WRONG" }, calm.0);
    if !a {
        bad += 1;
    }

    let b = dry.0 < calm.0 - 1e-9;
    println!(
        "  {} (b) при засухах оптимум сдвигается к сбережению (alpha {:.2} против {:.2})",
        if b { "ok   " } else { "WRONG" },
        dry.0,
        calm.0
    );
    if !b {
        bad += 1;
    }

    let c = dry.1 > 50.0 && calm.1 > 50.0;
    println!("  {} (c) оба режима вообще разрешимы (жизнь {:.0} и {:.0})", if c { "ok   " } else { "WRONG" }, calm.1, dry.1);
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
