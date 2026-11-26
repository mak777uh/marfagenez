//! D-Q5 (I-039/I-049): идентифицируемость показателя скорости на градуированном исходе.
//!
//! Design: PROP-EXPER-DQ5-20261126-2319 rev2 (task EXP-2026-4102). Генератор намеренно
//! НЕ содержит механизма, где скорость действует независимо от интеграла D: mortality
//! зависит только от текущего D(t)=min(L, v*t). Ожидаемый исход — dose-only модель
//! не уступает полной; это проверка идентифицируемости, а не доказательство степени.
//!
//! Контракты процедуры (proposal PROP-EXPER-DQ5-DRIVER-FIX-20261127-01, published):
//! - `--mode ramp|constant` (default ramp): constant-режим подаёт D(t) = dose/H
//!   константой каждый шаг — тот же аналитический dose (specific control);
//! - `--sham`: q0 фиксирован 0.5, RNG draw потребляется тем же (placebo control);
//! - `--details`: по-организменные строки organism,q0,death_step,censored (reproduce);
//! - CSV summary: L,v,seed,mode,sham,n,survivors,dose; seed — фактический (4201+).

use medium_core::organ::mortality_with_floor;
use medium_core::Rng;

const H: usize = 1000;
const FLOOR: f64 = 0.0002;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const LAMBDA: f64 = 0.001;
const N: usize = 200;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Mode {
    Ramp,
    Constant,
}

impl Mode {
    fn parse(s: &str) -> Option<Mode> {
        match s {
            "ramp" => Some(Mode::Ramp),
            "constant" => Some(Mode::Constant),
            _ => None,
        }
    }
    fn label(self) -> &'static str {
        match self {
            Mode::Ramp => "ramp",
            Mode::Constant => "constant",
        }
    }
}

/// Аналитическая площадь под D(t): доза за H шагов (непрерывный интеграл).
pub fn dose(l: f64, v: f64, h: usize) -> f64 {
    let h = h as f64;
    if l <= v * h {
        l * h - l * l / (2.0 * v)
    } else {
        v * h * h / 2.0
    }
}

/// D(t) в шаге t по режиму: ramp = min(L, v*t); constant = dose/H на каждом шаге.
fn d_at(l: f64, v: f64, t: usize, mode: Mode, h: usize) -> f64 {
    match mode {
        Mode::Ramp => l.min(v * t as f64),
        Mode::Constant => dose(l, v, h) / h as f64,
    }
}

/// q0: обычный 0.45+0.10*u; sham фиксирует 0.5, потребляя тот же draw u.
fn q0_from(u: f64, sham: bool) -> f64 {
    if sham {
        0.5
    } else {
        0.45 + 0.10 * u
    }
}

/// Одна ячейка x один seed: выжившие из N; при details заполняет по-организменные строки.
fn run_cell(
    l: f64,
    v: f64,
    seed: u64,
    mode: Mode,
    sham: bool,
    details: &mut Vec<(usize, f64, usize, bool)>,
) -> usize {
    let mut rng = Rng::new(seed);
    let mut alive = 0;
    for o in 0..N {
        let u0 = rng.uniform();
        let q = q0_from(u0, sham);
        let mut ok = true;
        let mut death_step = H;
        for t in 1..=H {
            let d = d_at(l, v, t, mode, H);
            let mu = mortality_with_floor(q, RATE, P, FLOOR) + LAMBDA * d;
            if rng.uniform() < mu {
                ok = false;
                death_step = t;
                break;
            }
        }
        details.push((o, q, death_step, ok));
        if ok {
            alive += 1;
        }
    }
    alive
}

/// Обёртка без details (тесты/смоук).
fn survivors(l: f64, v: f64, seed: u64, mode: Mode, sham: bool) -> usize {
    let mut det = Vec::new();
    run_cell(l, v, seed, mode, sham, &mut det)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut l_list = vec![0.1_f64, 0.2, 0.3, 0.4, 0.5];
    let mut v_list = vec![0.001_f64, 0.002, 0.004, 0.008, 0.016];
    let mut seed_base = 4209_u64;
    let mut seeds = 12_usize;
    let mut mode = Mode::Ramp;
    let mut sham = false;
    let mut details = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--L" => { i += 1; l_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--v" => { i += 1; v_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--mode" => {
                i += 1;
                mode = Mode::parse(&args[i]).unwrap_or_else(|| {
                    eprintln!("unknown mode: {} (ramp|constant)", args[i]);
                    std::process::exit(2);
                });
            }
            "--sham" => { sham = true; }
            "--details" => { details = true; }
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
    println!("L,v,seed,mode,sham,n,survivors,dose");
    for &l in &l_list {
        for &v in &v_list {
            let d = dose(l, v, H);
            for s in 0..seeds {
                let seed = seed_base + s as u64;
                let mut det: Vec<(usize, f64, usize, bool)> = Vec::new();
                let sv = run_cell(l, v, seed, mode, sham, &mut det);
                println!("{l},{v},{seed},{},{},{N},{sv},{d}", mode.label(), sham);
                if details {
                    for (o, q0, ds, cens) in det {
                        println!("detail,{l},{v},{seed},{},{},{o},{q0},{ds},{cens}", mode.label(), sham);
                    }
                }
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
    fn constant_mode_keeps_analytic_dose_per_step() {
        // specific control: constant-режим подаёт ровно dose/H на каждом шаге.
        for &(l, v) in &[(0.3_f64, 0.001_f64), (0.5_f64, 0.004_f64)] {
            for t in [1_usize, 500, 1000] {
                let dc = d_at(l, v, t, Mode::Constant, H);
                assert!((dc - dose(l, v, H) / H as f64).abs() < 1e-12,
                    "constant d({t}) = {dc}");
            }
            let dr_end = d_at(l, v, H, Mode::Ramp, H);
            assert!((dr_end - l.min(v * H as f64)).abs() < 1e-12);
        }
    }

    #[test]
    fn sham_fixes_q0_and_consumes_the_same_draw() {
        // placebo control: q0 = 0.5 при любом u; draw u потребляется одинаково.
        for u in [0.0_f64, 0.25, 0.999] {
            assert!((q0_from(u, true) - 0.5).abs() < 1e-12, "sham q0 must be 0.5");
            assert!((q0_from(u, false) - (0.45 + 0.10 * u)).abs() < 1e-12);
        }
        // sham меняет исход (q0=0.5 > 0.45+0.10u при малых u), но детерминирован.
        let a = survivors(0.3, 0.002, 4211, Mode::Ramp, true);
        let b = survivors(0.3, 0.002, 4211, Mode::Ramp, true);
        assert_eq!(a, b, "sham must be deterministic");
    }

    #[test]
    fn details_capture_q0_death_step_and_censoring() {
        let mut det: Vec<(usize, f64, usize, bool)> = Vec::new();
        let sv = run_cell(0.4, 0.004, 4213, Mode::Ramp, false, &mut det);
        assert_eq!(det.len(), N);
        assert_eq!(sv, det.iter().filter(|x| x.3).count());
        assert!(det.iter().all(|x| x.1 > 0.449 && x.1 < 0.56), "q0 out of range");
        assert!(det.iter().all(|x| x.2 >= 1 && x.2 <= H), "death_step out of horizon");
    }

    #[test]
    fn same_seed_same_counts() {
        assert_eq!(
            survivors(0.2, 0.002, 4209, Mode::Ramp, false),
            survivors(0.2, 0.002, 4209, Mode::Ramp, false)
        );
    }

    #[test]
    fn higher_load_kills_more() {
        // fires: смертность растёт с L при том же v.
        let lo = survivors(0.1, 0.004, 4210, Mode::Ramp, false);
        let hi = survivors(0.5, 0.004, 4210, Mode::Ramp, false);
        assert!(hi < lo, "L=0.5 must kill more than L=0.1: {hi} vs {lo}");
    }
}
