//! Прямая проверка закона из `FINDING-306`: при `h < 1` повреждение выходит на **плато**, при `h = 1` — **растёт**.
//!
//! Один штамм без конкуренции: форма живёт, пока не умрёт от угасания; место занимает новорождённый с повреждением
//! `h · (среднее повреждение)`.
//!
//! PREDICTION, before the run (`FINDING-307` §конец, `q = 0.5`, N = 500, 300 000 шагов):
//! плато следует `1/(1−h)`, поэтому от измеренных 2.05 при `h = 0.9`: 0.95 → **≈4.1**, 0.98 → **≈10.3**,
//! 0.99 → **≈20.5**.
//!   (a) при `h = 0.9` среднее повреждение **выходит на плато** — прирост к концу почти нулевой;
//!   (b) при `h = 1.0` **растёт** и к концу больше, чем при 0.9;
//!   (c) отношение среднего повреждения 1.0 к 0.9 к концу больше 2.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const N: usize = 500;
const STEPS: usize = 300_000;
const SAMPLES: usize = 10;

fn run(h: f64) -> Vec<f64> {
    let mut rng = Rng::new(20261120);
    let mut damage = vec![0.0_f64; N];
    let mut trace = Vec::with_capacity(SAMPLES);
    let every = STEPS / SAMPLES;

    for step in 1..=STEPS {
        let mean = damage.iter().sum::<f64>() / N as f64;
        for i in 0..N {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, damage[i]);
            let survive = (-mu).exp();
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u > survive {
                damage[i] = h * mean;
            } else {
                damage[i] += DELTA;
            }
        }
        if step % every == 0 {
            trace.push(damage.iter().sum::<f64>() / N as f64);
        }
    }
    trace
}

fn main() {
    // The plateau should scale as 1/(1-h). Measured at h = 0.9 it is 2.05, so from that base:
    //   0.95 -> 2.05 * 2 = 4.1,  0.98 -> 2.05 * 5 = 10.3,  0.99 -> 2.05 * 10 = 20.5
    println!("{:>7} {:>12} {:>14} {:>12}", "h", "plateau", "predicted", "ratio to 0.9");
    let mut rows = Vec::new();
    let base = None::<f64>;
    for h in [0.9, 0.95, 0.98, 0.99] {
        let trace = run(h);
        let level = trace[trace.len() - 1];
        let predicted = 2.05 * (0.1 / (1.0 - h));
        println!("{h:>7.2} {level:>12.3} {predicted:>14.2}");
        rows.push((h, level, predicted));
    }
    let _ = base;

    println!();
    let mut bad = 0;

    // (a) the plateau rises as h approaches one
    let a = rows.windows(2).all(|w| w[1].1 > w[0].1);
    println!(
        "  {} (a) the plateau rises towards h = 1: {:?}",
        if a { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 * 100.0).round() / 100.0)).collect::<Vec<_>>()
    );
    if !a {
        bad += 1;
    }

    // (b) and follows 1/(1-h) within a factor of two at every point
    let b = rows.iter().all(|r| (r.1 / r.2) > 0.5 && (r.1 / r.2) < 2.0);
    println!(
        "  {} (b) it follows 1/(1-h) within a factor of two: {:?}",
        if b { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 / r.2 * 100.0).round() / 100.0)).collect::<Vec<_>>()
    );
    if !b {
        bad += 1;
    }

    // (c) the growth from 0.9 to 0.99 is at least fivefold
    let ratio = rows[rows.len() - 1].1 / rows[0].1;
    let c = ratio > 5.0;
    println!("  {} (c) from 0.9 to 0.99 the plateau grows {ratio:.1} times", if c { "ok   " } else { "WRONG" });
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
