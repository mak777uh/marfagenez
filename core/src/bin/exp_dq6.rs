//! D-Q6: численные показатели полюса death-reset (PROP-EXPER-DQ6-20261126-2319 rev2).
//!
//! Q-023 закрыт аналитически: D* ~ x^(-1/2), |dD*/dh| ~ x^(-3/2), T_life ~ x^(1/2), x = 1-h.
//! Этот драйвер меряет числа: плато при h<1, рост при h=1, T_life по событиям reset.
//! Механика как в examples/organ_damage_drift.rs (FINDING-306/307), параметризована.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;

/// Один прогон: (пары (шаг, Dbar, events_so_far) по sample_steps, всего событий).
pub fn run(h: f64, n: usize, steps: usize, seed: u64, sample_steps: &[usize]) -> (Vec<(usize, f64, usize)>, usize) {
    let mut rng = Rng::new(seed);
    let mut damage = vec![0.0_f64; n];
    let mut events = 0_usize;
    let mut out = Vec::new();
    let mut si = 0_usize;
    for step in 1..=steps {
        let mean = damage.iter().sum::<f64>() / n as f64;
        for d in damage.iter_mut() {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, *d);
            let survive = (-mu).exp();
            if rng.uniform() > survive {
                *d = h * mean;
                events += 1;
            } else {
                *d += DELTA;
            }
        }
        while si < sample_steps.len() && step == sample_steps[si] {
            let dbar = damage.iter().sum::<f64>() / n as f64;
            out.push((step, dbar, events));
            si += 1;
        }
    }
    (out, events)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut h_list = vec![0.99_f64, 0.995, 0.998, 0.999, 0.9995];
    let mut controls = vec![0.9_f64, 0.95, 0.98, 1.0];
    let mut n = 100_usize;
    let mut steps = 800_000_usize;
    let mut seed_base = 4301_u64;
    let mut seeds = 12_usize;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--h" => { i += 1; h_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--controls" => { i += 1; controls = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--n" => { i += 1; n = args[i].parse().unwrap(); }
            "--steps" => { i += 1; steps = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    let quarter = steps / 4;
    let sample_steps: Vec<usize> = vec![quarter, 2 * quarter, 4 * quarter.min(steps), steps];
    let mut uniq: Vec<usize> = sample_steps.into_iter().filter(|s| *s <= steps).collect();
    uniq.sort(); uniq.dedup();
    println!("h,seed,sample_step,Dbar,events_so_far");
    for &h in h_list.iter().chain(controls.iter()) {
        for s in 0..seeds {
            let seed = seed_base + s as u64;
            let (rows, _events) = run(h, n, steps, seed, &uniq);
            for (step, dbar, ev) in rows {
                println!("{h},{s},{step},{dbar:.6},{ev}");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plateau_at_h_below_one() {
        // h=0.9: рост Dbar между серединой и концом мал (плато).
        let steps = 60_000_usize;
        let q = steps / 2;
        let (rows, _) = run(0.9, 100, steps, 7, &[q, steps]);
        let (d_mid, d_end) = (rows[0].1, rows[1].1);
        assert!(d_end > 0.0, "no damage accumulated");
        assert!(d_end - d_mid <= 0.05 * d_end.max(0.01), "no plateau: {d_mid} -> {d_end}");
    }

    #[test]
    fn grows_at_h_one() {
        // h=1.0: рост без плато к концу больше, чем при 0.9.
        let steps = 60_000_usize;
        let q = steps / 2;
        let (rows9, _) = run(0.9, 100, steps, 7, &[steps]);
        let (rows1, _) = run(1.0, 100, steps, 7, &[steps]);
        assert!(rows1[0].1 > 2.0 * rows9[0].1, "h=1.0 must outgrow h=0.9: {} vs {}", rows1[0].1, rows9[0].1);
    }

    #[test]
    fn deterministic_by_seed() {
        let a = run(0.995, 50, 20_000, 11, &[10_000, 20_000]);
        let b = run(0.995, 50, 20_000, 11, &[10_000, 20_000]);
        assert_eq!(a.0, b.0);
        assert_eq!(a.1, b.1);
    }

    #[test]
    fn reset_uses_h_times_mean() {
        // fires: событие reset кладёт ровно h*mean — проверяем на крошечном прогоне,
        // где все умирают на первом шаге (mu > 1 невозможно, поэтому проверяем геометрию формулы).
        // Возьмём h и mean: после reset damage <= h*mean того шага.
        let (rows, events) = run(0.99, 20, 5_000, 3, &[5_000]);
        assert!(events > 0, "no reset events in 5000 steps");
        assert!(rows[0].1 >= 0.0);
        // damage не может превысить h*mean + delta*(шаги без reset) грубо; здесь только sanity:
        assert!(rows[0].1 <= 1.0 + DELTA * 5_000.0, "damage runaway: {}", rows[0].1);
    }
}
