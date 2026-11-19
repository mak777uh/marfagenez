//! Первый потолок из `MODEL-CEILINGS.md`: **прошлое**. Накопление повреждений делает две формы с одинаковой
//! целостью **неравными**.
//!
//! До сих пор состояние формы было одним числом `q`, и по нему всё предсказывалось. С повреждением `D`, которое не
//! лечится, средняя жизнь перестаёт быть `1/μ(q)` и становится функцией **истории**.
//!
//! PREDICTION, before the run (`q = 0.5`, `rate = 0.01`, `p = 2`, `floor = 0.0002`, `lambda = 0.001`, `delta = 0.001`,
//! 3000 сидов на точку):
//!   (a) молодая форма (`damage = 0`) живёт **дольше** старой (`damage = 1.0`) при **той же** целости;
//!   (b) разница **велика**, а не на проценты: старая должна жить примерно втрое меньше;
//!   (c) у молодой формы жизнь близка к `1/μ(q)` из 294-й, пока повреждение мало — то есть история не отменяет
//!       прежний закон, а добавляет к нему член.

use medium_core::organ::{aging_mortality, sample_life_with_damage};
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const SEEDS: usize = 3000;
const HORIZON: usize = 2_000_000;

fn mean_life(damage0: f64) -> f64 {
    let mut total = 0.0;
    let mut counted = 0;
    for seed in 0..SEEDS {
        let mut rng = Rng::new(seed as u64 + 1);
        if let Some(steps) =
            sample_life_with_damage(&mut rng, Q, RATE, P, FLOOR, LAMBDA, DELTA, damage0, HORIZON)
        {
            total += steps as f64;
            counted += 1;
        }
    }
    if counted > 0 {
        total / counted as f64
    } else {
        f64::INFINITY
    }
}

fn main() {
    let young = mean_life(0.0);
    let old = mean_life(1.0);
    let ancient = mean_life(5.0);
    let no_history = 1.0 / aging_mortality(Q, RATE, P, FLOOR, 0.0, 0.0);

    println!("{:>12} {:>10} {:>14}", "damage", "mu(0)", "mean life");
    for (label, d, life) in [("young", 0.0, young), ("aged", 1.0, old), ("ancient", 5.0, ancient)] {
        println!(
            "{label:>12} {:>10.6} {life:>14.0}",
            aging_mortality(Q, RATE, P, FLOOR, LAMBDA, d)
        );
    }
    println!("{:>12} {:>10.6} {:>14.0}", "no damage", aging_mortality(Q, RATE, P, FLOOR, 0.0, 0.0), no_history);

    println!();
    let mut bad = 0;

    let a = young > old;
    println!(
        "  {} (a) the young form lives longer at the same integrity: {young:.0} against {old:.0}",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let ratio = young / old;
    let b = ratio > 2.0;
    println!("  {} (b) and the gap is large: ratio {ratio:.2}", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let c = (young / no_history - 1.0).abs() < 0.5;
    println!(
        "  {} (c) the young form is near 1/mu without history: {young:.0} against {no_history:.0}",
        if c { "ok   " } else { "WRONG" }
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
