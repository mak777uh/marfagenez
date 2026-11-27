//! D-Q6: численные показатели полюса death-reset (PROP-EXPER-DQ6-20261126-2319 rev2).
//!
//! Q-023 закрыт аналитически: D* ~ x^(-1/2), |dD*/dh| ~ x^(-1/2)^..., T_life ~ x^(1/2),
//! x = 1-h. Этот драйвер меряет числа: плато при h<1, рост при h=1, T_life по событиям
//! reset. Механика как в examples/organ_damage_drift.rs (FINDING-306/307), параметризована.
//!
//! Контракты процедуры (proposal PROP-EXPER-DQ6-DRIVER-FIX-20261127-01, published):
//! - sample_steps = {steps/8, steps/4, steps/2, steps} (при steps=800000: 100k..800k);
//! - CSV: фактические seed (4301+);
//! - `--details`: журнал событий reset (event,h,seed,ordinal,step) -- seed-level T_life
//!   восстановим из интервалов;
//! - `--control none|cap|sham` (default none): cap -- клэмп damage на 1.0;
//!   sham -- экзогенные reset-ы по baseline-смертности (без вклада damage), тот же
//!   темп-механизм, отвязанный от состояния.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const CAP: f64 = 1.0;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Control {
    None,
    Cap,
    Sham,
}

impl Control {
    fn parse(s: &str) -> Option<Control> {
        match s {
            "none" => Some(Control::None),
            "cap" => Some(Control::Cap),
            "sham" => Some(Control::Sham),
            _ => None,
        }
    }
    fn label(self) -> &'static str {
        match self {
            Control::None => "none",
            Control::Cap => "cap",
            Control::Sham => "sham",
        }
    }
}

/// Применяет один переход повреждения. Reset использует среднее ДО обновления шага,
/// рассчитанное вызывающим кодом; helper нужен и драйверу, и точному unit-тесту.
fn transition_damage(damage: &mut f64, reset: bool, h: f64, mean_before_step: f64,
                     control: Control) {
    if reset {
        let target = h * mean_before_step;
        *damage = if control == Control::Cap { target.min(CAP) } else { target };
    } else {
        *damage += DELTA;
        if control == Control::Cap {
            *damage = (*damage).min(CAP);
        }
    }
}

/// Расписание семплов по спеке задачи: {steps/8, steps/4, steps/2, steps}.
pub fn build_sample_steps(steps: usize) -> Vec<usize> {
    let e = steps / 8;
    let mut v = vec![e, 2 * e, 4 * e, steps];
    v.retain(|&s| s >= 1 && s <= steps);
    v.sort();
    v.dedup();
    v
}

/// Один прогон: (семплы (шаг, Dbar, events_so_far), всего событий, лог событий
/// (ordinal, step)). При cap damage клэмпится на CAP; при sham reset-ы экзогенные
/// (baseline-смертность без damage-вклада), отвязанные от состояния.
pub fn run_with_control(
    h: f64,
    n: usize,
    steps: usize,
    seed: u64,
    sample_steps: &[usize],
    control: Control,
    event_log: &mut Vec<(usize, usize)>,
) -> (Vec<(usize, f64, usize)>, usize) {
    let mut rng = Rng::new(seed);
    let mut damage = vec![0.0_f64; n];
    let mut events = 0_usize;
    let mut out = Vec::new();
    let mut si = 0_usize;
    for step in 1..=steps {
        let mean = damage.iter().sum::<f64>() / n as f64;
        for d in damage.iter_mut() {
            let mu = match control {
                Control::Sham => aging_mortality(Q, RATE, P, FLOOR, LAMBDA, 0.0),
                _ => aging_mortality(Q, RATE, P, FLOOR, LAMBDA, *d),
            };
            let survive = (-mu).exp();
            let reset = rng.uniform() > survive;
            transition_damage(d, reset, h, mean, control);
            if reset {
                events += 1;
                event_log.push((events, step));
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

/// Обёртка без контролов и лога (тесты/смоук, обратная совместимость).
pub fn run(h: f64, n: usize, steps: usize, seed: u64, sample_steps: &[usize]) -> (Vec<(usize, f64, usize)>, usize) {
    let mut log = Vec::new();
    run_with_control(h, n, steps, seed, sample_steps, Control::None, &mut log)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut h_list = vec![0.99_f64, 0.995, 0.998, 0.999, 0.9995];
    let mut controls = vec![0.9_f64, 0.95, 0.98, 1.0];
    let mut n = 100_usize;
    let mut steps = 800_000_usize;
    let mut seed_base = 4301_u64;
    let mut seeds = 12_usize;
    let mut control = Control::None;
    let mut details = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--h" => { i += 1; h_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--controls" => { i += 1; controls = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--n" => { i += 1; n = args[i].parse().unwrap(); }
            "--steps" => { i += 1; steps = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--control" => {
                i += 1;
                control = Control::parse(&args[i]).unwrap_or_else(|| {
                    eprintln!("unknown control: {} (none|cap|sham)", args[i]);
                    std::process::exit(2);
                });
            }
            "--details" => { details = true; }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    let uniq = build_sample_steps(steps);
    println!("control,h,seed,sample_step,Dbar,events_so_far");
    for &h in h_list.iter().chain(controls.iter()) {
        for s in 0..seeds {
            let seed = seed_base + s as u64;
            let mut event_log: Vec<(usize, usize)> = Vec::new();
            let (rows, _events) = run_with_control(h, n, steps, seed, &uniq, control, &mut event_log);
            for (step, dbar, ev) in rows {
                println!("{},{h},{seed},{step},{dbar:.6},{ev}", control.label());
            }
            if details {
                for (ordinal, step) in event_log {
                    println!("event,{},{h},{seed},{ordinal},{step}", control.label());
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sample_schedule_matches_spec() {
        // спека: {100000, 200000, 400000, 800000} при steps=800000.
        assert_eq!(build_sample_steps(800_000), vec![100_000, 200_000, 400_000, 800_000]);
        assert_eq!(build_sample_steps(8_000), vec![1_000, 2_000, 4_000, 8_000]);
    }

    #[test]
    fn cap_clamps_damage() {
        // cap: Dbar никогда не превышает CAP (сигма eps на шаг).
        let steps = 60_000_usize;
        let sched = build_sample_steps(steps);
        let mut log = Vec::new();
        let (rows, _) = run_with_control(1.0, 100, steps, 13, &sched, Control::Cap, &mut log);
        assert!(!rows.is_empty());
        for (_, dbar, _) in &rows {
            assert!(*dbar <= CAP + 1e-9, "cap violated: {dbar}");
        }
    }

    #[test]
    fn sham_resets_are_exogenous_and_deterministic() {
        // sham: reset-ы идут по baseline-смертности (без damage-вклада), события есть,
        // прогон детерминирован по seed.
        let steps = 60_000_usize;
        let sched = build_sample_steps(steps);
        let mut log1 = Vec::new();
        let (rows1, ev1) = run_with_control(0.99, 100, steps, 17, &sched, Control::Sham, &mut log1);
        assert!(ev1 > 0, "sham produced no exogenous resets");
        assert_eq!(log1.len(), ev1);
        let mut log2 = Vec::new();
        let (rows2, ev2) = run_with_control(0.99, 100, steps, 17, &sched, Control::Sham, &mut log2);
        assert_eq!((rows1, ev1), (rows2, ev2), "sham must be deterministic");
    }

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
    fn reset_uses_exact_pre_step_population_mean() {
        let mean_before_step = 0.4_f64;
        let h = 0.75_f64;
        let mut damage = 0.123_f64;
        transition_damage(&mut damage, true, h, mean_before_step, Control::None);
        assert!((damage - 0.3).abs() < 1e-15,
            "reset must be h * mean_before_step, got {damage}");

        let mut capped = 0.123_f64;
        transition_damage(&mut capped, true, 2.0, 0.6, Control::Cap);
        assert_eq!(capped, CAP, "cap control must clamp the exact reset target");
        let mut passthrough = 0.123_f64;
        transition_damage(&mut passthrough, true, 2.0, mean_before_step, Control::Cap);
        assert!((passthrough - 0.8).abs() < 1e-15,
            "cap must not clamp a below-cap reset target, got {passthrough}");
    }

    #[test]
    fn non_reset_step_adds_one_damage_increment() {
        let mut damage = 0.2_f64;
        transition_damage(&mut damage, false, 0.9, 0.4, Control::None);
        assert!((damage - (0.2 + DELTA)).abs() < 1e-15);
    }

    #[test]
    fn reset_events_are_journalled_with_steps() {
        // лог событий несёт (ordinal, step): seed-level T_life восстановим.
        let mut log = Vec::new();
        let (_, ev) = run_with_control(0.99, 20, 5_000, 3, &[5_000], Control::None, &mut log);
        assert!(ev > 0, "no reset events in 5000 steps");
        assert_eq!(log.len(), ev);
        assert!(log.iter().all(|(o, s)| *o >= 1 && *s >= 1 && *s <= 5_000));
        let steps_sorted = log.iter().map(|(_, s)| *s).collect::<Vec<_>>();
        assert!(steps_sorted.windows(2).all(|w| w[0] <= w[1]), "event steps must be non-decreasing");
    }
}
