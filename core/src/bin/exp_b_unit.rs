//! EXP-2026-4107: детерминированная фаза B — верификация k-out-of-m логики.
//!
//! Design: research/closure-world/DESIGN.md 13.2 (направление B) + 13.6 + 13.9
//! (порядок исполнения (2)); task EXP-2026-4107 v1. Модульная ремонтная подсистема:
//! R_t = min(R0, r0*n_t) * 1[n_t >= k], r0 = R0/k; m=3, k=2; delta_R = 0 —
//! отключения модулей только объявленные вмешательства (do-clamp), rescue
//! помечен external. Unit-test N=1: детерминированный режим, без статистики.
//!
//! Плечи: A-control (fixed R0, cost-yoked 3 условных модуля), B-1 sham,
//! B-2 knockout-1 (t*), B-3 knockout-2 (t**), rescue (t***), D-лестница при n=3
//! (диссоциация по D через абсолютный дефицит), ghost (учёт модулей в ledger
//! без влияния на capacity), placebo k_eff=1 (ступень обязана исчезнуть).
//!
//! Closed ledger: каждый шаг, каждый поток; баланс < 1e-12 (assert).
//! Чувствительность предрегистрирована: r0 >= (f_goal-q0)/T,
//! k_D >= ln((1-q0)/(1-f_goal))/T; при нарушении INSENSITIVE_BY_CONSTRUCTION, exit 3.

use medium_core::Rng;

const D0: f64 = 0.5;
const X_BASE: f64 = 1.0;
const F_GOAL: f64 = 0.95;
const WINDOW_T: usize = 40;
const BINARY_STEPS: usize = 10;
const K_D: f64 = 0.30;
const R0: f64 = 0.10;
const M_MODULES: usize = 3;
const K_MIN: usize = 2;
const R0_PER_MODULE: f64 = R0 / K_MIN as f64; // r_0 = R_0 / k
const COST_REPAIR_E: f64 = 0.2;
const COST_REPAIR_S: f64 = 0.2;
const MAINT_E_PER_MODULE: f64 = 0.01;
const RATION_E: f64 = 0.05;
const RATION_S: f64 = 0.05;
const STOCK_E0: f64 = 0.10;
const STOCK_S0: f64 = 0.10;
const STOCK_E_CAP: f64 = 1.0;
const STOCK_S_CAP: f64 = 1.0;
const NOISE_REL: f64 = 0.10;
const SEEDS: usize = 1;
const SEED_BASE: u64 = 5401;
const T_KO1: usize = 5;
const T_KO2: usize = 10;
const T_RESCUE: usize = 15;
const SCHEDULE_FINGERPRINT: &str = "t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2";

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum CapMode {
    Fixed,
    Modular { k_eff: usize },
    Ghost,
}

#[derive(Clone, Copy)]
struct ArmSpec {
    label: &'static str,
    cap: CapMode,
    d0: f64,
    ko1: bool,
    ko2: bool,
    rescue: bool,
    sham: bool,
}

#[derive(Clone, Copy)]
struct RunOut {
    aurd: f64,
    aurd_abs: f64,
    f_final: f64,
    f_at_ko2: f64,
    v_after_ko2: f64,
    v_after_rescue: f64,
    binary95: bool,
    t_reach95: usize,
    max_imbalance: f64,
    v_first: f64,
    n_final: usize,
}

fn run_arm(spec: &ArmSpec, seed: u64, mut step_rows: Option<&mut Vec<String>>) -> RunOut {
    let mut rng = Rng::new(seed);
    let d0 = spec.d0;
    let mut d = d0;
    let mut e = STOCK_E0;
    let mut s = STOCK_S0;
    let mut n: usize = M_MODULES;
    let mut aurd_sum = 0.0;
    let mut aurd_abs_sum = 0.0;
    let mut f_prev = 0.0f64;
    let mut f_at_ko2 = 0.0f64;
    let mut v_after_ko2 = 0.0f64;
    let mut v_after_rescue = 0.0f64;
    let mut binary95 = false;
    let mut t_reach95 = 0usize;
    let mut max_imbalance = 0.0f64;
    let mut v_first = 0.0f64;
    for t in 0..WINDOW_T {
        // 0) вмешательства: расписание предрегистрировано, от damage не зависит
        let mut event = "";
        if spec.ko1 && t == T_KO1 { n = n.saturating_sub(1); event = "ko1"; }
        if spec.ko2 && t == T_KO2 { n = n.saturating_sub(1); event = "ko2"; }
        if spec.rescue && t == T_RESCUE { n += 1; event = "rescue"; }
        if spec.sham && t == T_KO1 { event = "sham"; }
        let u_e = rng.uniform();
        let u_s = rng.uniform();
        let e_in = RATION_E * (1.0 + NOISE_REL * (2.0 * u_e - 1.0));
        let s_in = RATION_S * (1.0 + NOISE_REL * (2.0 * u_s - 1.0));
        // 1) приток с кэпом; излишек — невостребованный остаток (ledger)
        let e_add = (STOCK_E_CAP - e).min(e_in).max(0.0);
        let e_unc = e_in - e_add;
        let s_add = (STOCK_S_CAP - s).min(s_in).max(0.0);
        let s_unc = s_in - s_add;
        let e_before = e; let s_before = s;
        e += e_add; s += s_add;
        // 2) capacity шага
        let cap_now = match spec.cap {
            CapMode::Fixed | CapMode::Ghost => R0,
            CapMode::Modular { k_eff } => if n >= k_eff { R0.min(R0_PER_MODULE * n as f64) } else { 0.0 },
        };
        // 3) обслуживание: A-control платит за 3 (cost-yoked), модульные — за активные
        let j_pay = match spec.cap { CapMode::Fixed => M_MODULES, _ => n };
        let maint_need = j_pay as f64 * MAINT_E_PER_MODULE;
        let maint_e = maint_need.min(e);
        let maint_short = maint_need - maint_e;
        e -= maint_e;
        // 4) ремонт: min(спрос, capacity, энергия, субстрат, потребность)
        let demand = K_D * d;
        let v = demand.min(cap_now).min(e / COST_REPAIR_E).min(s / COST_REPAIR_S).min(d).max(0.0);
        if t == 0 { v_first = v; }
        if t == T_KO2 { f_at_ko2 = f_prev; }
        if t >= T_KO2 { v_after_ko2 += v; }
        if t >= T_RESCUE { v_after_rescue += v; }
        d -= v;
        e -= v * COST_REPAIR_E;
        s -= v * COST_REPAIR_S;
        // 5) метрики
        let f = (d0 - d) / d0;
        aurd_sum += d / d0;
        aurd_abs_sum += d;
        if t == BINARY_STEPS { binary95 = f >= F_GOAL; }
        if t_reach95 == 0 && f >= F_GOAL { t_reach95 = t; }
        // 6) closed ledger
        let imb_e = (e_before + e_in) - (e + e_unc + maint_e + v * COST_REPAIR_E);
        let imb_s = (s_before + s_in) - (s + s_unc + v * COST_REPAIR_S);
        let imb = if imb_e.abs() > imb_s.abs() { imb_e } else { imb_s };
        if imb.abs() > max_imbalance { max_imbalance = imb.abs(); }
        assert!(imb.abs() < 1e-12, "ledger imbalance at t={t}: {imb}");
        if let Some(rows) = step_rows.as_mut() {
            rows.push(format!("{},{},{},{},{},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.12}",
                spec.label, seed, t, n, event, u_e, u_s, e_in, s_in, e_unc, s_unc,
                maint_e, maint_short, v, d, e, s, cap_now, f, imb));
        }
        f_prev = f;
    }
    RunOut { aurd: aurd_sum / WINDOW_T as f64, aurd_abs: aurd_abs_sum / WINDOW_T as f64, f_final: f_prev, f_at_ko2, v_after_ko2, v_after_rescue, binary95, t_reach95, max_imbalance, v_first, n_final: n }
}

fn build_arms() -> Vec<ArmSpec> {
    let mk = |label: &'static str, cap: CapMode, d0: f64, ko1: bool, ko2: bool, rescue: bool, sham: bool| ArmSpec { label, cap, d0, ko1, ko2, rescue, sham };
    vec![
        mk("A-control", CapMode::Fixed, D0, false, false, false, false),
        mk("B1-sham", CapMode::Modular { k_eff: K_MIN }, D0, false, false, false, true),
        mk("B2-ko1", CapMode::Modular { k_eff: K_MIN }, D0, true, false, false, false),
        mk("B3-ko2", CapMode::Modular { k_eff: K_MIN }, D0, true, true, false, false),
        mk("rescue", CapMode::Modular { k_eff: K_MIN }, D0, true, true, true, false),
        mk("D-half", CapMode::Modular { k_eff: K_MIN }, D0 / 2.0, false, false, false, false),
        mk("D-third", CapMode::Modular { k_eff: K_MIN }, D0 / 3.0, false, false, false, false),
        mk("ghost", CapMode::Ghost, D0, true, true, false, false),
        mk("placebo-k1", CapMode::Modular { k_eff: 1 }, D0, true, true, false, false),
    ]
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut seeds = SEEDS;
    let mut seed_base = SEED_BASE;
    let mut steps_path: Option<String> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--steps-out" => { i += 1; steps_path = Some(args[i].clone()); }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    // Предрегистрированная проверка чувствительности (13.6)
    let q0 = X_BASE - D0;
    let need_r0 = (F_GOAL - q0) / WINDOW_T as f64;
    let need_kd = ((1.0 - q0) / (1.0 - F_GOAL)).ln() / WINDOW_T as f64;
    eprintln!("schedule: {SCHEDULE_FINGERPRINT}");
    eprintln!("sensitivity: r0={:.6} need={:.6} kD={:.6} need={:.6}", R0_PER_MODULE, need_r0, K_D, need_kd);
    if R0_PER_MODULE < need_r0 || K_D < need_kd {
        println!("INSENSITIVE_BY_CONSTRUCTION r0={R0_PER_MODULE} need={need_r0} kD={K_D} need={need_kd}");
        std::process::exit(3);
    }
    let arms = build_arms();
    let mut steps_all: Vec<String> = Vec::new();
    steps_all.push("arm,seed,step,n_t,event,u_e,u_s,e_in,s_in,e_unc,s_unc,maint_e,maint_short,v,d,e,s,cap_now,f,imbalance".to_string());
    println!("arm,k_eff,d0,seed,aurd,aurd_abs,f_final,f_at_ko2,v_after_ko2,v_after_rescue,binary95_10,t_reach95,max_imbalance,v_first,n_final");
    for spec in &arms {
        for s_i in 0..seeds {
            let seed = seed_base + s_i as u64;
            let (out, rows) = if steps_path.is_some() {
                let mut rows = Vec::new();
                let out = run_arm(spec, seed, Some(&mut rows));
                steps_all.extend(rows);
                (out, true)
            } else {
                (run_arm(spec, seed, None), false)
            };
            let _ = rows;
            let k_eff = match spec.cap { CapMode::Modular { k_eff } => k_eff as f64, _ => -1.0 };
            println!("{},{:.0},{:.4},{},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{},{},{:.12},{:.6},{}",
                spec.label, k_eff, spec.d0, seed,
                out.aurd, out.aurd_abs, out.f_final, out.f_at_ko2, out.v_after_ko2, out.v_after_rescue,
                out.binary95 as u8, out.t_reach95, out.max_imbalance, out.v_first, out.n_final);
        }
    }
    if let Some(path) = steps_path {
        std::fs::write(&path, steps_all.join("\n") + "\n").expect("steps-out write");
        eprintln!("steps written: {path}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec(label: &'static str, cap: CapMode, d0: f64, ko1: bool, ko2: bool, rescue: bool, sham: bool) -> ArmSpec {
        ArmSpec { label, cap, d0, ko1, ko2, rescue, sham }
    }
    fn b_spec(label: &'static str, ko1: bool, ko2: bool, rescue: bool, sham: bool) -> ArmSpec {
        spec(label, CapMode::Modular { k_eff: K_MIN }, D0, ko1, ko2, rescue, sham)
    }

    #[test]
    fn ledger_closes_every_step() {
        for s in build_arms() {
            let out = run_arm(&s, SEED_BASE, None);
            assert!(out.max_imbalance < 1e-12, "{} imbalance {}", s.label, out.max_imbalance);
        }
    }

    #[test]
    fn b1_equals_a_control() {
        let a = run_arm(&spec("A", CapMode::Fixed, D0, false, false, false, false), SEED_BASE, None);
        let b1 = run_arm(&b_spec("B1", false, false, false, true), SEED_BASE, None);
        assert!((a.aurd - b1.aurd).abs() < 1e-12, "aurd {} vs {}", a.aurd, b1.aurd);
        assert!((a.f_final - b1.f_final).abs() < 1e-12);
    }

    #[test]
    fn b2_equals_b1() {
        let b1 = run_arm(&b_spec("B1", false, false, false, true), SEED_BASE, None);
        let b2 = run_arm(&b_spec("B2", true, false, false, false), SEED_BASE, None);
        assert!((b1.aurd - b2.aurd).abs() < 1e-12, "knockout-1 changed recovery: {} vs {}", b1.aurd, b2.aurd);
        assert!((b1.f_final - b2.f_final).abs() < 1e-12);
        assert!(b2.n_final == 2);
    }

    #[test]
    fn b3_freezes_at_ko2() {
        let b3 = run_arm(&b_spec("B3", true, true, false, false), SEED_BASE, None);
        assert!(b3.v_after_ko2 == 0.0, "repair continued below k: {}", b3.v_after_ko2);
        assert!((b3.f_final - b3.f_at_ko2).abs() < 1e-15, "f moved during freeze: {} vs {}", b3.f_final, b3.f_at_ko2);
        assert!(b3.n_final == 1);
    }

    #[test]
    fn rescue_strictly_between_b2_and_b3() {
        let b2 = run_arm(&b_spec("B2", true, false, false, false), SEED_BASE, None);
        let b3 = run_arm(&b_spec("B3", true, true, false, false), SEED_BASE, None);
        let r = run_arm(&b_spec("R", true, true, true, false), SEED_BASE, None);
        assert!(r.v_after_rescue > 0.0, "rescue did not resume repair");
        assert!(b2.aurd < r.aurd, "rescue aurd not above B-2: {} vs {}", b2.aurd, r.aurd);
        assert!(r.aurd < b3.aurd, "rescue aurd not below B-3: {} vs {}", r.aurd, b3.aurd);
        assert!(r.aurd - b2.aurd > 1e-6 && b3.aurd - r.aurd > 1e-6, "step margins too small");
    }

    #[test]
    fn d_ladder_abs_monotone() {
        let full = run_arm(&b_spec("B1", false, false, false, true), SEED_BASE, None);
        let half = run_arm(&spec("D-half", CapMode::Modular { k_eff: K_MIN }, D0 / 2.0, false, false, false, false), SEED_BASE, None);
        let third = run_arm(&spec("D-third", CapMode::Modular { k_eff: K_MIN }, D0 / 3.0, false, false, false, false), SEED_BASE, None);
        assert!(full.aurd_abs > half.aurd_abs, "abs deficit not monotone: {} vs {}", full.aurd_abs, half.aurd_abs);
        assert!(half.aurd_abs > third.aurd_abs, "abs deficit not monotone: {} vs {}", half.aurd_abs, third.aurd_abs);
    }

    #[test]
    fn ghost_equals_b1() {
        let b1 = run_arm(&b_spec("B1", false, false, false, true), SEED_BASE, None);
        let g = run_arm(&spec("ghost", CapMode::Ghost, D0, true, true, false, false), SEED_BASE, None);
        assert!((b1.aurd - g.aurd).abs() < 1e-12, "ghost accounting changed recovery: {} vs {}", b1.aurd, g.aurd);
        assert!(g.n_final == 1, "ghost schedule not applied");
    }

    #[test]
    fn placebo_k1_no_zero_step() {
        let b3 = run_arm(&b_spec("B3", true, true, false, false), SEED_BASE, None);
        let p = run_arm(&spec("placebo", CapMode::Modular { k_eff: 1 }, D0, true, true, false, false), SEED_BASE, None);
        assert!(p.v_after_ko2 > 0.0, "placebo froze: {}", p.v_after_ko2);
        assert!(p.f_final > b3.f_final + 0.01, "placebo too close to B-3: {} vs {}", p.f_final, b3.f_final);
    }

    #[test]
    fn capacity_binds_first_step_on_full_damage() {
        let a = run_arm(&spec("A", CapMode::Fixed, D0, false, false, false, false), SEED_BASE, None);
        let half = run_arm(&spec("D-half", CapMode::Modular { k_eff: K_MIN }, D0 / 2.0, false, false, false, false), SEED_BASE, None);
        assert!((a.v_first - R0).abs() < 1e-12, "first step not capacity-bound: {}", a.v_first);
        assert!(half.v_first < R0, "demand did not bind on smaller damage: {}", half.v_first);
    }

    #[test]
    fn deterministic_seed_invariance() {
        for s in build_arms() {
            let o1 = run_arm(&s, SEED_BASE, None);
            let o2 = run_arm(&s, SEED_BASE + 1, None);
            assert!((o1.aurd - o2.aurd).abs() < 1e-15, "{} seed changed outcome in deterministic regime", s.label);
            assert!((o1.f_final - o2.f_final).abs() < 1e-15);
        }
    }

    #[test]
    fn schedule_registered_and_ordered() {
        assert!(T_KO1 < T_KO2 && T_KO2 < T_RESCUE && T_RESCUE < WINDOW_T);
        assert!(M_MODULES == 3 && K_MIN == 2);
        assert!((R0_PER_MODULE - R0 / 2.0).abs() < 1e-15);
    }

    #[test]
    fn sensitivity_conditions_hold_for_registered_params() {
        let q0 = X_BASE - D0;
        let need_r0 = (F_GOAL - q0) / WINDOW_T as f64;
        let need_kd = ((1.0 - q0) / (1.0 - F_GOAL)).ln() / WINDOW_T as f64;
        assert!(R0_PER_MODULE >= need_r0, "r0 {} < {}", R0_PER_MODULE, need_r0);
        assert!(K_D >= need_kd, "kD {} < {}", K_D, need_kd);
    }
}
