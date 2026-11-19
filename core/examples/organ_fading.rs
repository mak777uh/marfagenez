//! F1 из `DESIGN-fading.md`: средняя жизнь при постоянном `q` равна `1/μ(q)`.
//!
//! PREDICTION, before the run (`rate = 0.01`, `p = 2`, `q` = 0.9 / 0.5 / 0.2 / 0.05, 4000 сидов на точку):
//!   (a) выборочная средняя совпадёт с `1/μ(q)` в пределах 5 %;
//!   (b) средняя жизнь **падает** с понижением `q`;
//!   (c) разница между `q = 0.9` и `q = 0.2` будет в **64 раза** (0.0001 против 0.0064 по смертности).

use medium_core::organ::{expected_life, mortality, sample_life};
use medium_core::Rng;

const RATE: f64 = 0.01;
const P: f64 = 2.0;
const SEEDS: usize = 4000;
const HORIZON: usize = 2_000_000;

fn main() {
    println!("{:>6} {:>12} {:>14} {:>12} {:>8}", "q", "mu", "predicted life", "sampled life", "error");
    let mut rows = Vec::new();
    for q in [0.9, 0.5, 0.2, 0.05] {
        let mu = mortality(q, RATE, P);
        let predicted = expected_life(q, RATE, P);
        let mut total = 0.0_f64;
        let mut counted = 0;
        for seed in 0..SEEDS {
            let mut rng = Rng::new(seed as u64 + 1);
            if let Some(steps) = sample_life(&mut rng, q, RATE, P, HORIZON) {
                total += steps as f64;
                counted += 1;
            }
        }
        let sampled = if counted > 0 { total / counted as f64 } else { f64::NAN };
        let err = (sampled - predicted).abs() / predicted * 100.0;
        println!("{q:>6.2} {mu:>12.6} {predicted:>14.1} {sampled:>12.1} {err:>7.1}%");
        rows.push((q, mu, predicted, sampled, err, counted));
    }

    println!();
    let mut bad = 0;

    let a = rows.iter().all(|r| r.4 < 5.0);
    println!("  {} (a) sampled life matches 1/mu within 5%", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = rows.windows(2).all(|w| w[1].3 < w[0].3);
    println!("  {} (b) life falls as q falls", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let ratio = rows[0].3 / rows[2].3;
    let c = (ratio - 64.0).abs() < 8.0;
    println!(
        "  {} (c) the ratio between q = 0.9 and q = 0.2 is about 64: {ratio:.1}",
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
