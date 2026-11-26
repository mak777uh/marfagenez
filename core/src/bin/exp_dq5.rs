//! D-Q5 (I-039/I-049): идентифицируемость показателя скорости на градуированном исходе.
//!
//! Design: PROP-EXPER-DQ5-20261126-2319 rev2 (task EXP-2026-4201). Генератор намеренно
//! НЕ содержит механизма, где скорость действует независимо от интеграла D: mortality
//! зависит только от текущего D(t)=min(L, v*t). Ожидаемый исход — dose-only модель
//! не уступает полной; это проверка идентифицируемости, а не доказательство степени.

use medium_core::organ::mortality_with_floor;
use medium_core::Rng;

const H: usize = 1000;
const FLOOR: f64 = 0.0002;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const LAMBDA: f64 = 0.001;
const N: usize = 200;

/// Аналитическая площадь под D(t): доза за H шагов.
pub fn dose(l: f64, v: f64, h: usize) -> f64 {
    let h = h as f64;
    if l <= v * h {
        l * h - l * l / (2.0 * v)
    } else {
        v * h * h / 2.0
    }
}

/// Одна ячейка x один seed: сколько из N организмов дожили до H.
fn survivors(l: f64, v: f64, seed: u64) -> usize {
    let mut rng = Rng::new(seed);
    let mut alive = 0;
    for _ in 0..N {
        let q = 0.45 + 0.10 * rng.uniform();
        let mut ok = true;
        for t in 1..=H {
            let d = l.min(v * t as f64);
            let mu = mortality_with_floor(q, RATE, P, FLOOR) + LAMBDA * d;
            if rng.uniform() < mu {
                ok = false;
                break;
            }
        }
        if ok {
            alive += 1;
        }
    }
    alive
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut l_list = vec![0.1_f64, 0.2, 0.3, 0.4, 0.5];
    let mut v_list = vec![0.001_f64, 0.002, 0.004, 0.008, 0.016];
    let mut seed_base = 4209_u64;
    let mut seeds = 12_usize;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--L" => { i += 1; l_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--v" => { i += 1; v_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--phase" => {
                i += 1;
                match args[i].as_str() {
                    "dev" => { seed_base = 4201; seeds = 4; }
                    "pilot" => { seed_base = 4205; seeds = 4; }
                    "confirmatory" => { seed_base = 4209; seeds = 12; }
                    other => { eprintln!("unknown phase: {other}"); std::process::exit(2); }
                }
            }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    println!("L,v,seed,n,survivors,dose");
    for &l in &l_list {
        for &v in &v_list {
            let d = dose(l, v, H);
            for s in 0..seeds {
                let seed = seed_base + s as u64;
                let sv = survivors(l, v, seed);
                println!("{l},{v},{s},{N},{sv},{d}");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dose_formula_matches_continuous_integral() {
        // Формула дизайна — НЕПРЕРЫВНЫЙ интеграл площади под min(L, v*t), а не
        // дискретная сумма по шагам (та расходится с интегралом на v*t*/2 ~ L/2).
        // Сверяем с трапецией на мелкой сетке: чек должен уметь падать.
        for &(l, v) in &[(0.3_f64, 0.001_f64), (0.5_f64, 0.0004_f64), (0.2_f64, 0.016_f64)] {
            let h = 1000.0_f64;
            let steps = 100_000_u64;
            let dt = h / steps as f64;
            let mut area = 0.0_f64;
            for i in 0..steps {
                let t0 = i as f64 * dt;
                let t1 = t0 + dt;
                area += (l.min(v * t0) + l.min(v * t1)) / 2.0 * dt;
            }
            let analytic = dose(l, v, H);
            assert!((area - analytic).abs() < 1e-6 * h, "dose mismatch: {area} vs {analytic}");
        }
    }

    #[test]
    fn ramp_caps_at_l() {
        let v = 0.001_f64;
        let l = 0.3_f64;
        assert!((l.min(v * 300.0) - 0.3).abs() < 1e-12);
        assert!((l.min(v * 100.0) - 0.1).abs() < 1e-12);
    }

    #[test]
    fn same_seed_same_counts() {
        assert_eq!(survivors(0.2, 0.002, 4209), survivors(0.2, 0.002, 4209));
    }

    #[test]
    fn higher_load_kills_more() {
        // fires: смертность растёт с L при том же v.
        let lo = survivors(0.1, 0.004, 4210);
        let hi = survivors(0.5, 0.004, 4210);
        assert!(hi < lo, "L=0.5 must kill more than L=0.1: {hi} vs {lo}");
    }
}
