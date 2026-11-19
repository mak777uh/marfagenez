//! Прямая проверка закона из `FINDING-306`: при `h < 1` повреждение выходит на **плато**, при `h = 1` — **растёт**.
//!
//! Один штамм без конкуренции: форма живёт, пока не умрёт от угасания; место занимает новорождённый с повреждением
//! `h · (среднее повреждение)`.
//!
//! PREDICTION, before the run (`q = 0.5`, `rate = 0.01`, `p = 2`, `floor = 0.0002`, `λ = 0.001`, `δ = 0.001`,
//! N = 2000, 200 000 шагов):
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
const N: usize = 2000;
const STEPS: usize = 200_000;
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
    let slow = run(0.9);
    let flat = run(1.0);

    println!("{:>12} {:>14} {:>14}", "шаг", "h = 0.9", "h = 1.0");
    for i in 0..SAMPLES {
        println!("{:>12} {:>14.3} {:>14.3}", (i + 1) * (STEPS / SAMPLES), slow[i], flat[i]);
    }

    println!();
    let mut bad = 0;

    // (a) at h = 0.9 the last increments are small
    let last_gain_09 = slow[SAMPLES - 1] - slow[SAMPLES - 2];
    let a = last_gain_09 < 0.15 * slow[SAMPLES - 1];
    println!(
        "  {} (a) h = 0.9 reaches a plateau: last gain {last_gain_09:.4} against level {:.3}",
        if a { "ok   " } else { "WRONG" },
        slow[SAMPLES - 1]
    );
    if !a {
        bad += 1;
    }

    // (b) at h = 1.0 it keeps growing and ends higher
    let last_gain_10 = flat[SAMPLES - 1] - flat[SAMPLES - 2];
    let b = last_gain_10 > 0.0 && flat[SAMPLES - 1] > slow[SAMPLES - 1];
    println!(
        "  {} (b) h = 1.0 keeps growing: last gain {last_gain_10:.4}, ends at {:.3}",
        if b { "ok   " } else { "WRONG" },
        flat[SAMPLES - 1]
    );
    if !b {
        bad += 1;
    }

    // (c) the ratio at the end is above two
    let ratio = flat[SAMPLES - 1] / slow[SAMPLES - 1].max(1e-9);
    let c = ratio > 2.0;
    println!("  {} (c) the ratio at the end is {ratio:.2}", if c { "ok   " } else { "WRONG" });
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
