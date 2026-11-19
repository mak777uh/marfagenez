//! F3/F4: где избыток покупает жизнь, а где всё ещё пропадает — с **полом старения**.
//!
//! Первый прогон `organ_surplus_life` показал неожиданное: при `yield >= 2` обе части достигают `q = 1.0`, а
//! `μ(1) = 0`, то есть форма **бессмертна**. Значит у угасания есть поглощающее состояние, и его надо назвать.
//!
//! Пол старения: `μ = floor + rate·(1−q)²`. Целая форма всё равно умирает, но медленно.
//!
//! Полная починка требует прихода `d_a + d_b = 0.10`, то есть `yield·0.05 ≥ 0.10` ⇒ `yield ≥ 2`. Значит
//! **градиент живёт ниже 2**, а выше — снова насыщение.
//!
//! PREDICTION, before the run (`rate = 0.01`, `p = 2`, `floor = 0.0002`, `d = 0.05`):
//!   (a) средняя жизнь **растёт плавно** от `yield = 1.0` к 2.0 — ступеньки нет;
//!   (b) выше 2.0 жизнь **насыщается** на `1/floor = 5000`;
//!   (c) при `yield = 1.5` жизнь **между** крайними значениями — избыток работает.

use medium_core::organ::{expected_life_with_floor, Flow, Part, RepairMode};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const STEPS: usize = 200_000;

fn settled_q(yield_rate: f64) -> Option<f64> {
    let mut f = Flow::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    f.yield_rate = yield_rate;
    f.repair_mode = RepairMode::Fill;
    for _ in 0..STEPS {
        if !f.step() {
            return None;
        }
    }
    Some(f.a.q.min(f.b.q))
}

fn main() {
    println!("{:>7} {:>8} {:>12} {:>12}", "yield", "q", "mu", "mean life");
    let mut rows = Vec::new();
    for y in [1.0, 1.25, 1.5, 1.75, 2.0, 3.0] {
        match settled_q(y) {
            Some(q) => {
                let life = expected_life_with_floor(q, RATE, P, FLOOR);
                let mu = 1.0 / life;
                println!("{y:>7.2} {q:>8.4} {mu:>12.6} {life:>12.0}");
                rows.push((y, q, life));
            }
            None => {
                println!("{y:>7.2} {:>8} {:>12} {:>12}", "die", "-", "-");
                rows.push((y, f64::NAN, 0.0));
            }
        }
    }

    println!();
    let mut bad = 0;

    let a = rows.windows(2).all(|w| w[1].2 >= w[0].2);
    println!("  {} (a) life rises smoothly with the surplus", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let top = rows[rows.len() - 1].2;
    let b = (top - 1.0 / FLOOR).abs() < 2.0;
    println!("  {} (b) above yield 2 it saturates at 1/floor = {:.0}: {top:.0}", if b { "ok   " } else { "WRONG" }, 1.0 / FLOOR);
    if !b {
        bad += 1;
    }

    let mid = rows.iter().find(|r| (r.0 - 1.5).abs() < 1e-9).unwrap().2;
    let c = mid > rows[0].2 && mid < top;
    println!("  {} (c) at yield 1.5 life is in between: {mid:.0}", if c { "ok   " } else { "WRONG" });
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
