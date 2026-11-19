//! Потолок 2 из `MODEL-CEILINGS.md`: **излишек с пользой**. Впервые появляется **выбор** — тратить или сберегать.
//!
//! Форма получает доход и распределяет его: доля `alpha` идёт в починку (поднимает `q`, снижает смертность),
//! доля `1 - alpha` — в **запас**. Засуха случается с вероятностью `p` и длится `k` шагов: в ней дохода нет, и
//! починка берётся **из запаса**.
//!
//! PREDICTION, before the run (`q_min` не участвует в смерти; `mu = floor + rate*(1-q)^p_exponent + lambda*damage`,
//! доход 0.04, N = 400 сидов на точку, горизонт 5000 шагов):
//!   (a) **без засух** (p = 0) выгоднее всего тратить всё на починку: `alpha = 1` даёт наибольшую долю выживших;
//!   (b) полоса **исчезнет**, как только засуха станет **редкой и короткой** (`p = 0.001`, `k = 50`): оптимум уйдёт
//!       на `alpha = 1`, а разброс вырастет выше 30 %;
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
    // Does the band come from the drought being lethal, or is it a property of the metric?
    // PREDICTION: with RARE and SHORT droughts the band must vanish and alpha = 1 must win by a lot.
    let regimes = [
        ("без засух", 0.0, 0),
        ("смертельная (p = 0.02, k = 400)", 0.02, 400),
        ("редкая и короткая (p = 0.001, k = 50)", 0.001, 50),
    ];
    let mut summary = Vec::new();
    for (name, p_drought, len) in regimes {
        let mut rows = Vec::new();
        for alpha in [0.0, 0.25, 0.5, 0.75, 1.0] {
            rows.push((alpha, survival(alpha, p_drought, len)));
        }
        let best = rows.iter().cloned().fold((0.0, f64::MIN), |a, b| if b.1 > a.1 { b } else { a });
        let worst = rows.iter().cloned().fold((0.0, f64::MAX), |a, b| if b.1 < a.1 { b } else { a });
        let spread = (best.1 - worst.1) / best.1;
        println!("{name}:");
        for (alpha, life) in &rows {
            println!("  alpha {alpha:>4.2}: {life:>7.1}");
        }
        println!("  вершина {:.2}, разброс {:.0} %", best.0, spread * 100.0);
        summary.push((name, best.0, spread));
    }

    println!();
    let mut bad = 0;

    // (a) the lethal regime is the flattest
    let a = summary[1].2 < summary[0].2 && summary[1].2 < summary[2].2;
    println!(
        "  {} (a) полоса только у смертельной засухи: разбросы {:.0} % / {:.0} % / {:.0} %",
        if a { "ok   " } else { "WRONG" },
        summary[0].2 * 100.0,
        summary[1].2 * 100.0,
        summary[2].2 * 100.0
    );
    if !a {
        bad += 1;
    }

    // (b) with a rare short drought the optimum goes back to spending everything
    let b = summary[2].1 > 0.9;
    println!("  {} (b) при редкой засухе вершина снова на alpha = 1 ({:.2})", if b { "ok   " } else { "WRONG" }, summary[2].1);
    if !b {
        bad += 1;
    }

    // (c) and that regime is sharp, not flat
    let c = summary[2].2 > 0.3;
    println!("  {} (c) и выбор там острый: разброс {:.0} %", if c { "ok   " } else { "WRONG" }, summary[2].2 * 100.0);
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
