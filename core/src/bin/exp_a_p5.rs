//! EXP-2026-4104 (A-P5): плавная ремонтная способность -- нулевая модель для D-Q9.
//!
//! Design: research/closure-world/DESIGN.md 13.4 (A-P5) + 13.6 + 13.9 (ревизия
//! 2026-11-27); task EXP-2026-4104 v4 (base 072d0fd0). Направление A: фиксированная
//! capacity R_t = frac * R_0, лестница frac in {1.0, 0.5, 1/3, 0.0}. На ступени j
//! оплачивается содержание j условных модулей (предрегистрированное отображение
//! j = round(3*frac): 3, 2, 1, 0); правило оплаты отключённых модулей -- отдельное
//! плечо (disabled_free | disabled_pays). Кандидат C (обязательный контраст):
//! повреждаемая capacity dC/dt = (C0-C)/tau - gamma*D*C, карта бифуркаций по gamma.
//!
//! Closed ledger: каждый шаг, каждый поток (энергия, субстрат, обслуживание,
//! replacement [в A всегда 0], невостребованные остатки) записан; баланс
//! inflow - outflow - delta_stock - unclaimed == 0 проверяется на каждом шаге.
//!
//! Paired seeds: один RNG-поток на seed во всех плечах, ровно два uniform на шаг
//! в каждом плече -> потоки выровнены между плечами. Чувствительность
//! предрегистрирована: r_0 >= (f_goal - q_0)/T и k_D >= ln((1-q_0)/(1-f_goal))/T;
//! при нарушении драйвер печатает INSENSITIVE_BY_CONSTRUCTION и выходит с кодом 3.

use medium_core::Rng;

const D0: f64 = 0.5;
const X_BASE: f64 = 1.0;
const F_GOAL: f64 = 0.95;
const WINDOW_T: usize = 40;
const BINARY_STEPS: usize = 10;
const K_D: f64 = 0.30;
const R0: f64 = 0.10;
const R0_PER_MODULE: f64 = R0 / 3.0;
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
const C_TAU: f64 = 20.0;
const GAMMA_GRID: [f64; 9] = [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4];
const SEEDS: usize = 12;
const SEED_BASE: u64 = 5301;

/// Предрегистрированное отображение лестницы в число оплачиваемых модулей.
fn modules_for_frac(f: f64) -> usize {
    let j = (3.0 * f).round();
    if j < 0.0 { 0 } else { j as usize }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum PayRule { DisabledFree, DisabledPays }

impl PayRule {
    fn label(self) -> &'static str {
        match self { PayRule::DisabledFree => "disabled_free", PayRule::DisabledPays => "disabled_pays" }
    }
}

#[derive(Clone, Copy, PartialEq, Debug)]
enum CapacityMode {
    Fixed,
    Candidate { gamma: f64, tau: f64 },
}

#[derive(Clone, Copy)]
struct ArmSpec {
    label: &'static str,
    frac: f64,
    pay_rule: PayRule,
    cap: CapacityMode,
    j_pay_override: Option<usize>,
    k_d: f64,
    ration_scale: f64,
}

#[derive(Clone, Copy)]
struct RunOut {
    aurd: f64,
    dfdt_mean10: f64,
    f_final: f64,
    binary95: bool,
    t_reach95: usize,
    max_imbalance: f64,
    v_first: f64,
}

/// Одно плечо: WINDOW_T шагов, закрытый ledger, ровно 2 uniform на шаг.
/// step_rows: если Some, туда пишутся строки шагового CSV (без заголовка).
fn run_arm(spec: &ArmSpec, seed: u64, mut step_rows: Option<&mut Vec<String>>) -> RunOut {
    let mut rng = Rng::new(seed);
    let mut d = D0;
    let mut e = STOCK_E0;
    let mut s = STOCK_S0;
    let mut c = match spec.cap { CapacityMode::Fixed => spec.frac * R0, CapacityMode::Candidate { .. } => R0 };
    let j_func = if spec.j_pay_override.is_some() { modules_for_frac(1.0) } else { modules_for_frac(spec.frac) };
    let j_pay = match spec.j_pay_override {
        Some(j) => j,
        None => match spec.pay_rule { PayRule::DisabledFree => j_func, PayRule::DisabledPays => 3 },
    };
    let mut aurd_sum = 0.0;
    let mut dfdt_sum = 0.0;
    let mut dfdt_n = 0usize;
    let mut f_prev = 0.0f64;
    let mut binary95 = false;
    let mut t_reach95 = 0usize;
    let mut max_imbalance = 0.0f64;
    let mut v_first = 0.0f64;
    for t in 0..WINDOW_T {
        let u_e = rng.uniform();
        let u_s = rng.uniform();
        let e_in = RATION_E * spec.ration_scale * (1.0 + NOISE_REL * (2.0 * u_e - 1.0));
        let s_in = RATION_S * spec.ration_scale * (1.0 + NOISE_REL * (2.0 * u_s - 1.0));
        // 1) приток с кэпом: излишек = невостребованный остаток (ledger)
        let e_add = (STOCK_E_CAP - e).min(e_in).max(0.0);
        let e_unc = e_in - e_add;
        let s_add = (STOCK_S_CAP - s).min(s_in).max(0.0);
        let s_unc = s_in - s_add;
        let e_before = e; let s_before = s;
        e += e_add; s += s_add;
        // 2) capacity текущего шага
        let cap_now = match spec.cap { CapacityMode::Fixed => spec.frac * R0, CapacityMode::Candidate { .. } => c };
        // 3) обслуживание j_pay модулей (энергия); недоплаченное -- долг, capability в A не меняется
        let maint_need = j_pay as f64 * MAINT_E_PER_MODULE;
        let maint_e = maint_need.min(e);
        let maint_short = maint_need - maint_e;
        e -= maint_e;
        // 4) ремонт: min(спрос, capacity, энергия, субстрат, потребность)
        let demand = spec.k_d * d;
        let v = demand.min(cap_now).min(e / COST_REPAIR_E).min(s / COST_REPAIR_S).min(d).max(0.0);
        if t == 0 { v_first = v; }
        d -= v;
        e -= v * COST_REPAIR_E;
        s -= v * COST_REPAIR_S;
        let repl = 0.0f64; // направление A: replacement-потока нет
        // 5) кандидат C: восстановление capacity к C0 с tau, повреждение gamma*D*C (не ledger-поток)
        if let CapacityMode::Candidate { gamma, tau } = spec.cap {
            c += (R0 - c) / tau - gamma * d * c;
            if c < 0.0 { c = 0.0; }
        }
        // 6) метрики
        let x = X_BASE - d;
        let f = (D0 - d) / D0;
        let dfdt = if t == 0 { f } else { f - f_prev };
        if t >= 1 && t <= BINARY_STEPS { dfdt_sum += dfdt; dfdt_n += 1; }
        aurd_sum += d / D0;
        if t == BINARY_STEPS { binary95 = f >= F_GOAL; }
        if t_reach95 == 0 && f >= F_GOAL { t_reach95 = t; }
        f_prev = f;
        // 7) закрытый ledger: баланс по обоим запасам
        let imb_e = (e_before + e_in) - (e + e_unc + maint_e + v * COST_REPAIR_E);
        let imb_s = (s_before + s_in) - (s + s_unc + v * COST_REPAIR_S + repl);
        let imb = if imb_e.abs() > imb_s.abs() { imb_e } else { imb_s };
        if imb.abs() > max_imbalance { max_imbalance = imb.abs(); }
        assert!(imb.abs() < 1e-12, "ledger imbalance at t={t}: {imb}");
        if let Some(rows) = step_rows.as_mut() {
            rows.push(format!("{},{},{},{},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.12}",
                spec.label, spec.frac, spec.pay_rule.label(), seed, t, u_e, u_s, e_in, s_in,
                e_unc, s_unc, maint_e, maint_short, v, d, e, s, c, cap_now, f, dfdt, imb));
        }
    }
    RunOut {
        aurd: aurd_sum / WINDOW_T as f64,
        dfdt_mean10: if dfdt_n > 0 { dfdt_sum / dfdt_n as f64 } else { 0.0 },
        f_final: f_prev,
        binary95,
        t_reach95,
        max_imbalance,
        v_first,
    }
}

fn build_arms() -> Vec<ArmSpec> {
    let mut v = Vec::new();
    for frac in [1.0_f64, 0.5, 1.0 / 3.0, 0.0] {
        for pay in [PayRule::DisabledFree, PayRule::DisabledPays] {
            v.push(ArmSpec { label: "A", frac, pay_rule: pay, cap: CapacityMode::Fixed, j_pay_override: None, k_d: K_D, ration_scale: 1.0 });
        }
    }
    for j in [2_usize, 1] {
        v.push(ArmSpec { label: "yoked", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: Some(j), k_d: K_D, ration_scale: 1.0 });
    }
    v.push(ArmSpec { label: "target-off", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: None, k_d: 0.0, ration_scale: 1.0 });
    v.push(ArmSpec { label: "ration-half", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: None, k_d: K_D, ration_scale: 0.5 });
    for gamma in GAMMA_GRID {
        v.push(ArmSpec { label: "C", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Candidate { gamma, tau: C_TAU }, j_pay_override: None, k_d: K_D, ration_scale: 1.0 });
    }
    v
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
    // Предрегистрированная проверка чувствительности (13.6): r_0 и k_D достаточны.
    let q0 = X_BASE - D0;
    let need_r0 = (F_GOAL - q0) / WINDOW_T as f64;
    let need_kd = ((1.0 - q0) / (1.0 - F_GOAL)).ln() / WINDOW_T as f64;
    eprintln!("sensitivity: r0={:.6} need={:.6} kD={:.6} need={:.6}", R0_PER_MODULE, need_r0, K_D, need_kd);
    if R0_PER_MODULE < need_r0 || K_D < need_kd {
        println!("INSENSITIVE_BY_CONSTRUCTION r0={R0_PER_MODULE} need={need_r0} kD={K_D} need={need_kd}");
        std::process::exit(3);
    }
    let arms = build_arms();
    let mut steps_all: Vec<String> = Vec::new();
    steps_all.push("arm,frac,pay_rule,seed,step,u_e,u_s,e_in,s_in,e_unc,s_unc,maint_e,maint_short,v,d,e,s,c,cap_now,f,dfdt,imbalance".to_string());
    println!("arm,frac,pay_rule,gamma,tau,j_pay,seed,aurd,dfdt_mean10,f_final,binary95_10,t_reach95,max_imbalance,v_first");
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
            let (gamma, tau) = match spec.cap {
                CapacityMode::Candidate { gamma, tau } => (gamma, tau),
                CapacityMode::Fixed => (-1.0, -1.0),
            };
            let j_pay = match spec.j_pay_override {
                Some(j) => j,
                None => match spec.pay_rule { PayRule::DisabledFree => modules_for_frac(spec.frac), PayRule::DisabledPays => 3 },
            };
            println!("{},{:.4},{},{:.4},{:.2},{},{},{:.6},{:.6},{:.6},{},{},{:.12},{:.6}",
                spec.label, spec.frac, spec.pay_rule.label(), gamma, tau, j_pay, seed,
                out.aurd, out.dfdt_mean10, out.f_final, out.binary95 as u8, out.t_reach95, out.max_imbalance, out.v_first);
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

    fn arm(label: &'static str, frac: f64, pay: PayRule) -> ArmSpec {
        ArmSpec { label, frac, pay_rule: pay, cap: CapacityMode::Fixed, j_pay_override: None, k_d: K_D, ration_scale: 1.0 }
    }

    #[test]
    fn ledger_closes_every_step() {
        for spec in build_arms() {
            let out = run_arm(&spec, SEED_BASE, None);
            assert!(out.max_imbalance < 1e-12, "{} imbalance {}", spec.label, out.max_imbalance);
        }
    }

    #[test]
    fn ladder_is_monotone_and_zero_arm_frozen() {
        let full = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, None);
        let half = run_arm(&arm("A", 0.5, PayRule::DisabledFree), SEED_BASE, None);
        let third = run_arm(&arm("A", 1.0 / 3.0, PayRule::DisabledFree), SEED_BASE, None);
        let zero = run_arm(&arm("A", 0.0, PayRule::DisabledFree), SEED_BASE, None);
        assert!(full.aurd < half.aurd && half.aurd < third.aurd, "aurd not monotone: {} {} {}", full.aurd, half.aurd, third.aurd);
        assert!((zero.f_final - 0.0).abs() < 1e-12, "zero arm recovered: {}", zero.f_final);
        assert!((zero.aurd - 1.0).abs() < 1e-12, "zero arm aurd != 1: {}", zero.aurd);
        assert!((zero.v_first - 0.0).abs() < 1e-12, "zero arm repaired: {}", zero.v_first);
        assert!(full.binary95 && !half.binary95 && !third.binary95 && !zero.binary95, "binary95 grading unexpected");
    }

    #[test]
    fn capacity_binds_early_on_full_arm() {
        let mut rows = Vec::new();
        let out = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, Some(&mut rows));
        assert!((out.v_first - R0).abs() < 1e-12, "first step not capacity-bound: {}", out.v_first);
        assert!(rows.len() == WINDOW_T);
    }

    #[test]
    fn payment_rule_changes_ledger_not_recovery() {
        for seed in [SEED_BASE, SEED_BASE + 1, SEED_BASE + 2] {
            let free = run_arm(&arm("A", 0.5, PayRule::DisabledFree), seed, None);
            let pays = run_arm(&arm("A", 0.5, PayRule::DisabledPays), seed, None);
            assert!((free.aurd - pays.aurd).abs() < 1e-12, "payment rule changed recovery at seed {seed}");
        }
    }

    #[test]
    fn yoked_control_keeps_full_capability() {
        let yoked1 = ArmSpec { label: "yoked", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: Some(1), k_d: K_D, ration_scale: 1.0 };
        let plain = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, None);
        let yoked = run_arm(&yoked1, SEED_BASE, None);
        assert!((plain.aurd - yoked.aurd).abs() < 1e-12, "yoked control changed recovery");
        assert!((plain.f_final - yoked.f_final).abs() < 1e-12);
    }

    #[test]
    fn target_off_never_recovers() {
        let spec = ArmSpec { label: "target-off", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: None, k_d: 0.0, ration_scale: 1.0 };
        let out = run_arm(&spec, SEED_BASE, None);
        assert!((out.f_final - 0.0).abs() < 1e-12, "target-off recovered: {}", out.f_final);
        assert!(out.t_reach95 == 0);
    }

    #[test]
    fn candidate_c_gamma_zero_equals_full_arm() {
        let c0 = ArmSpec { label: "C", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Candidate { gamma: 0.0, tau: C_TAU }, j_pay_override: None, k_d: K_D, ration_scale: 1.0 };
        let plain = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, None);
        let c = run_arm(&c0, SEED_BASE, None);
        assert!((plain.aurd - c.aurd).abs() < 1e-12, "C gamma=0 != full arm: {} vs {}", plain.aurd, c.aurd);
        assert!((plain.f_final - c.f_final).abs() < 1e-12);
    }

    #[test]
    fn candidate_c_bifurcates_by_gamma() {
        let mut f_by_gamma = Vec::new();
        for gamma in GAMMA_GRID {
            let spec = ArmSpec { label: "C", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Candidate { gamma, tau: C_TAU }, j_pay_override: None, k_d: K_D, ration_scale: 1.0 };
            let out = run_arm(&spec, SEED_BASE, None);
            f_by_gamma.push((gamma, out));
        }
        let (g_lo, o_lo) = f_by_gamma[0];
        let (g_hi, o_hi) = f_by_gamma[GAMMA_GRID.len() - 1];
        assert!(g_lo == 0.0 && g_hi == 6.4);
        assert!(o_hi.f_final < o_lo.f_final - 0.3, "C collapse too weak: {} vs {}", o_hi.f_final, o_lo.f_final);
        assert!(o_hi.t_reach95 == 0, "collapsed C arm reached 95%");
        // монотонность не требуется (возможна немонотонность карты), но край обязан различаться.
    }

    #[test]
    fn deterministic_regime_seeds_nonbinding() {
        // Заявленное свойство регистрационного режима: ресурсы не binds, шум рациона
        // не влияет -> все 12 сидов дают идентичные строки. Нулевая модель A-P5
        // детерминирована по построению; сиды значимы будут в стохастическом B pilot.
        let first = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, None);
        for s in 1..SEEDS {
            let out = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE + s as u64, None);
            assert!((first.aurd - out.aurd).abs() < 1e-15, "seed {} changed outcome in deterministic regime", s);
            assert!((first.f_final - out.f_final).abs() < 1e-15);
        }
    }

    #[test]
    fn ration_bottleneck_control_bites() {
        // Контроль ресурсного bottleneck: при полном R0, но рациях x0.5, восстановление
        // обязано замедлиться (иначе контроль ничего не проверяет).
        let full = run_arm(&arm("A", 1.0, PayRule::DisabledFree), SEED_BASE, None);
        let half = ArmSpec { label: "ration-half", frac: 1.0, pay_rule: PayRule::DisabledFree, cap: CapacityMode::Fixed, j_pay_override: None, k_d: K_D, ration_scale: 0.5 };
        let out = run_arm(&half, SEED_BASE, None);
        assert!(out.aurd > full.aurd * 1.5, "ration bottleneck control does not bite: {} vs {}", out.aurd, full.aurd);
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
