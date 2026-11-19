//! F2 из `DESIGN-fading.md`: на месте старого порога **ступеньки нет**.
//!
//! Старая модель: форма жива, если `u >= need`, и мертва иначе — обрыв в одной точке. Угасание: форма садится на
//! `q* = u/d`, смертность `μ(q*)`, средняя жизнь `1/μ(q*)` — непрерывная функция дохода.
//!
//! PREDICTION, before the run (`rate = 0.01`, `p = 2`, `d = 0.05`, `need = 0.01 = d*q_min`):
//!   (a) у старого порога (`u/need = 1`) **ступеньки нет**: соседние точки по среднему времени жизни отличаются
//!       меньше чем вдвое;
//!   (b) старая модель в этой же точке имеет **обрыв**: жива при `u/need >= 1`, мертва при `< 1`;
//!   (c) средняя жизнь **растёт** с доходом на всём диапазоне.

use medium_core::organ::{expected_life, sample_life};
use medium_core::Rng;

const RATE: f64 = 0.01;
const P: f64 = 2.0;
const D: f64 = 0.05;
const NEED: f64 = 0.01; // d * q_min, q_min = 0.2
const SEEDS: usize = 2000;
const HORIZON: usize = 2_000_000;

fn mean_life(u: f64) -> f64 {
    let q = (u / D).min(1.0).max(0.0);
    let mut total = 0.0;
    let mut counted = 0;
    for seed in 0..SEEDS {
        let mut rng = Rng::new(seed as u64 + 1);
        if let Some(steps) = sample_life(&mut rng, q, RATE, P, HORIZON) {
            total += steps as f64;
            counted += 1;
        }
    }
    if counted > 0 {
        total / counted as f64
    } else {
        f64::NAN
    }
}

fn main() {
    println!("{:>8} {:>6} {:>10} {:>14} {:>12}", "u/need", "q*", "old model", "1/mu", "sampled life");
    let mut rows = Vec::new();
    for frac in [0.4, 0.7, 0.9, 1.0, 1.1, 1.5, 2.0, 2.4] {
        let u = frac * NEED;
        let q = (u / D).min(1.0).max(0.0);
        let old = frac >= 1.0;
        let predicted = expected_life(q, RATE, P);
        let sampled = mean_life(u);
        println!(
            "{frac:>8.1} {q:>6.2} {:>10} {predicted:>14.0} {sampled:>12.0}",
            if old { "alive" } else { "DEAD" }
        );
        rows.push((frac, old, predicted, sampled));
    }

    println!();
    let mut bad = 0;

    // (a) no step at the old threshold: the jump between 0.9 and 1.1 must stay under 2x
    let before = rows.iter().find(|r| (r.0 - 0.9).abs() < 1e-9).unwrap().3;
    let after = rows.iter().find(|r| (r.0 - 1.1).abs() < 1e-9).unwrap().3;
    let ratio = after / before;
    let a = ratio < 2.0;
    println!(
        "  {} (a) no step at the old threshold: {before:.0} -> {after:.0} (ratio {ratio:.2})",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    // (b) the old model does jump exactly there, by construction - and that is the contrast
    let b = rows.iter().all(|r| r.1 == (r.0 >= 1.0));
    println!("  {} (b) the old model jumps at u/need = 1", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    // (c) life rises with income across the whole sweep
    let c = rows.windows(2).all(|w| w[1].3 > w[0].3);
    println!("  {} (c) life rises with income everywhere", if c { "ok   " } else { "WRONG" });
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
