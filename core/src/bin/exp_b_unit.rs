//! EXP-2026-4107: deterministic verification of k-out-of-m repair logic.
//!
//! R_t = min(R0, r0*n_t) * 1[n_t >= k], r0 = R0/k, m=3, k=2.
//! Scheduled do-clamp events are independent of target damage. Rescue is an
//! explicit external module inflow. Fixed-capacity cost-yoked A arms follow the
//! same module/cost/external-stock schedule as the corresponding B arm.
//!
//! This is an N=1 instrument test, not a statistical test of direction B.
//! Floats use shortest round-trip formatting; trajectory hashes consume raw
//! f64 bits. Maintenance debt is accrual-only because repayment/default were
//! not preregistered.

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
const R0_PER_MODULE: f64 = R0 / K_MIN as f64;
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

pub const RAW_HEADER: &str = "arm,k_eff,d0,seed,aurd,aurd_abs,f_final,f_at_ko2,v_after_ko2,v_after_rescue,binary95_10,t_reach95,max_imbalance,v_first,n_final,aurd_observed,aurd_abs_observed,f_at_death,maint_short_total,maint_debt,rescue_in_total,external_rescue_stock,failed_module_stock,observed_steps,alive,death_step,death_cause,horizon_censored,state_hash,trajectory_hash";
pub const STEPS_HEADER: &str = "arm,seed,step,n_t,event,u_e,u_s,e_in,s_in,e_unc,s_unc,maint_e,maint_short,v,d,e,s,cap_now,f,imbalance,maint_debt,debt_imbalance,module_in,module_out,module_imbalance,failed_module_in,failed_module_stock,failed_module_imbalance,external_rescue_stock,rescue_stock_imbalance,d_before,e_before,s_before,alive,death_cause";

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
    cost_yoked: bool,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum DeathCause {
    None,
    Energy,
    Damage,
}

impl DeathCause {
    fn label(self) -> &'static str {
        match self {
            DeathCause::None => "none",
            DeathCause::Energy => "energy",
            DeathCause::Damage => "damage",
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct RunOut {
    aurd: f64,
    aurd_observed: f64,
    aurd_abs: f64,
    aurd_abs_observed: f64,
    f_final: f64,
    f_at_death: f64,
    f_at_ko2: f64,
    v_after_ko2: f64,
    v_after_rescue: f64,
    binary95: bool,
    t_reach95: usize,
    max_imbalance: f64,
    v_first: f64,
    n_final: usize,
    maint_short_total: f64,
    maint_debt: f64,
    rescue_in_total: usize,
    external_rescue_stock: usize,
    failed_module_stock: usize,
    observed_steps: usize,
    alive: bool,
    death_step: Option<usize>,
    death_cause: DeathCause,
    horizon_censored: bool,
    state_hash: u64,
    trajectory_hash: u64,
}

fn csv_num(value: f64) -> String {
    // Rust's Display uses a shortest round-trip representation for f64.
    format!("{value}")
}

fn hash_u64(hash: &mut u64, value: u64) {
    for byte in value.to_le_bytes() {
        *hash ^= u64::from(byte);
        *hash = hash.wrapping_mul(0x100000001b3);
    }
}

fn hash_f64(hash: &mut u64, value: f64) {
    hash_u64(hash, value.to_bits());
}

/// Unpaid maintenance becomes explicit debt. Repayment/default are outside
/// this preregistered instrument test, so debt does not alter capacity.
fn pay_maintenance(e: &mut f64, debt: &mut f64, need: f64) -> (f64, f64, f64) {
    let paid = need.min(*e).max(0.0);
    *e -= paid;
    let short = need - paid;
    *debt += short;
    (paid, short, *debt)
}

fn run_arm(spec: &ArmSpec, seed: u64, step_rows: Option<&mut Vec<String>>) -> RunOut {
    run_arm_with_ration_scale(spec, seed, 1.0, step_rows)
}

fn run_arm_with_ration_scale(
    spec: &ArmSpec,
    seed: u64,
    ration_scale: f64,
    mut step_rows: Option<&mut Vec<String>>,
) -> RunOut {
    let mut rng = Rng::new(seed);
    let d0 = spec.d0;
    let mut d = d0;
    let mut e = STOCK_E0;
    let mut s = STOCK_S0;
    let mut n: usize = M_MODULES;
    let mut external_rescue_stock = if spec.rescue { 1 } else { 0 };
    let mut failed_module_stock = 0usize;
    let mut rescue_in_total = 0usize;
    let mut aurd_sum = 0.0;
    let mut aurd_abs_sum = 0.0;
    let mut f_prev = 0.0f64;
    let mut f_at_death = 0.0f64;
    let mut f_at_ko2 = 0.0f64;
    let mut v_after_ko2 = 0.0;
    let mut v_after_rescue = 0.0;
    let mut binary95 = false;
    let mut t_reach95 = 0usize;
    let mut max_imbalance = 0.0f64;
    let mut v_first = 0.0;
    let mut maint_debt = 0.0;
    let mut maint_short_total = 0.0;
    let mut alive = e > 0.0 && d < 1.0;
    let mut death_step = if alive { None } else { Some(0) };
    let mut death_cause = if alive {
        DeathCause::None
    } else if e <= 0.0 {
        DeathCause::Energy
    } else {
        DeathCause::Damage
    };
    let mut observed_steps = 0usize;
    let mut trajectory_hash = 0xcbf2_9ce4_8422_2325u64;

    for t in 0..WINDOW_T {
        if !alive {
            break;
        }
        observed_steps += 1;

        // 0) Scheduled interventions, independent of target damage.
        let n_before = n;
        let rescue_stock_before = external_rescue_stock;
        let failed_stock_before = failed_module_stock;
        let mut module_in = 0usize;
        let mut module_out = 0usize;
        let mut event = "";
        if spec.ko1 && t == T_KO1 && n > 0 {
            n -= 1;
            module_out += 1;
            event = "ko1";
        }
        if spec.ko2 && t == T_KO2 && n > 0 {
            n -= 1;
            module_out += 1;
            event = "ko2";
        }
        if spec.rescue && t == T_RESCUE {
            if external_rescue_stock > 0 && n < M_MODULES {
                n += 1;
                external_rescue_stock -= 1;
                module_in += 1;
                rescue_in_total += module_in;
                event = "rescue";
            } else {
                event = "rescue_unavailable";
            }
        }
        if spec.sham && t == T_KO1 {
            event = "sham";
        }
        failed_module_stock += module_out;

        // 1) Seeded resource inflow with explicit unrequested remainder.
        let u_e = rng.uniform();
        let u_s = rng.uniform();
        let e_in = RATION_E * ration_scale * (1.0 + NOISE_REL * (2.0 * u_e - 1.0));
        let s_in = RATION_S * ration_scale * (1.0 + NOISE_REL * (2.0 * u_s - 1.0));
        let e_add = (STOCK_E_CAP - e).min(e_in).max(0.0);
        let s_add = (STOCK_S_CAP - s).min(s_in).max(0.0);
        let e_unc = e_in - e_add;
        let s_unc = s_in - s_add;
        let e_ledger_before = e;
        let s_ledger_before = s;
        let debt_before = maint_debt;
        e += e_add;
        s += s_add;

        // 2) Capacity and 3) maintenance. Cost-yoked fixed-capacity arms pay
        // for the same active-module schedule as their B counterpart.
        let cap_now = match spec.cap {
            CapMode::Fixed | CapMode::Ghost => R0,
            CapMode::Modular { k_eff } => {
                if n >= k_eff {
                    R0.min(R0_PER_MODULE * n as f64)
                } else {
                    0.0
                }
            }
        };
        let j_pay = match spec.cap {
            CapMode::Fixed if !spec.cost_yoked => M_MODULES,
            _ => n,
        };
        let maint_need = j_pay as f64 * MAINT_E_PER_MODULE;
        let (maint_e, maint_short, debt_now) = pay_maintenance(&mut e, &mut maint_debt, maint_need);
        maint_short_total += maint_short;

        // 4) Repair. d/e/s before are the values available to repair.
        let d_before = d;
        let e_before = e;
        let s_before = s;
        let demand = K_D * d;
        let v = demand
            .min(cap_now)
            .min(e / COST_REPAIR_E)
            .min(s / COST_REPAIR_S)
            .min(d)
            .max(0.0);
        if t == 0 {
            v_first = v;
        }
        if t == T_KO2 {
            f_at_ko2 = f_prev;
        }
        if t >= T_KO2 {
            v_after_ko2 += v;
        }
        if t >= T_RESCUE {
            v_after_rescue += v;
        }
        d -= v;
        e -= v * COST_REPAIR_E;
        s -= v * COST_REPAIR_S;

        // 5) Canonical death after energy and repair; death is absorbing.
        if e <= 0.0 || d >= 1.0 {
            alive = false;
            death_step = Some(t);
            death_cause = if e <= 0.0 {
                DeathCause::Energy
            } else {
                DeathCause::Damage
            };
        }

        // 6) Metrics. A fixed-window metric is NaN after death.
        let f = (d0 - d) / d0;
        aurd_sum += d / d0;
        aurd_abs_sum += d;
        if t == BINARY_STEPS {
            binary95 = alive && f >= F_GOAL;
        }
        if t_reach95 == 0 && alive && f >= F_GOAL {
            t_reach95 = t;
        }
        if !alive {
            f_at_death = f;
        }

        // 7) Closed energy/substrate/debt/module/rescue ledgers.
        let imb_e = (e_ledger_before + e_in)
            - (e + e_unc + maint_e + v * COST_REPAIR_E);
        let imb_s = (s_ledger_before + s_in) - (s + s_unc + v * COST_REPAIR_S);
        let debt_imb = maint_debt - (debt_before + maint_short);
        let module_imb =
            n_before as f64 + module_in as f64 - module_out as f64 - n as f64;
        let failed_module_imb =
            failed_stock_before as f64 + module_out as f64 - failed_module_stock as f64;
        let rescue_stock_imb =
            rescue_stock_before as f64 - module_in as f64 - external_rescue_stock as f64;
        let imb = imb_e
            .abs()
            .max(imb_s.abs())
            .max(debt_imb.abs())
            .max(module_imb.abs())
            .max(failed_module_imb.abs())
            .max(rescue_stock_imb.abs());
        if imb > max_imbalance {
            max_imbalance = imb;
        }
        assert!(imb < 1e-12, "ledger imbalance at t={t}: {imb}");

        // Hash dynamics from raw bits; event labels and cosmetic ledger fields
        // are excluded so matched cost/capacity trajectories can be compared.
        for value in [n as u64] {
            hash_u64(&mut trajectory_hash, value);
        }
        for value in [cap_now, d, e, s, v, f, maint_e, maint_short] {
            hash_f64(&mut trajectory_hash, value);
        }

        if let Some(rows) = step_rows.as_mut() {
            rows.push(format!(
                "{label},{seed},{step},{n},{event},{u_e},{u_s},{e_in},{s_in},{e_unc},{s_unc},{maint_e},{maint_short},{v},{d},{e},{s},{cap_now},{f},{imb},{debt_now},{debt_imb},{module_in},{module_out},{module_imb},{failed_module_in},{failed_module_stock},{failed_module_imb},{external_rescue_stock},{rescue_stock_imb},{d_before},{e_before},{s_before},{alive},{death_cause}",
                label = spec.label,
                seed = seed,
                step = t,
                n = n,
                event = event,
                u_e = csv_num(u_e),
                u_s = csv_num(u_s),
                e_in = csv_num(e_in),
                s_in = csv_num(s_in),
                e_unc = csv_num(e_unc),
                s_unc = csv_num(s_unc),
                maint_e = csv_num(maint_e),
                maint_short = csv_num(maint_short),
                v = csv_num(v),
                d = csv_num(d),
                e = csv_num(e),
                s = csv_num(s),
                cap_now = csv_num(cap_now),
                f = csv_num(f),
                imb = csv_num(imb),
                debt_now = csv_num(debt_now),
                debt_imb = csv_num(debt_imb),
                module_in = module_in,
                module_out = module_out,
                module_imb = csv_num(module_imb),
                failed_module_in = module_out,
                failed_module_stock = failed_module_stock,
                failed_module_imb = csv_num(failed_module_imb),
                external_rescue_stock = external_rescue_stock,
                rescue_stock_imb = csv_num(rescue_stock_imb),
                d_before = csv_num(d_before),
                e_before = csv_num(e_before),
                s_before = csv_num(s_before),
                alive = alive as u8,
                death_cause = death_cause.label(),
            ));
        }
        f_prev = f;
    }

    let mut state_hash = 0xcbf2_9ce4_8422_2325u64;
    hash_u64(&mut state_hash, n as u64);
    for value in [d, e, s, maint_debt] {
        hash_f64(&mut state_hash, value);
    }
    hash_u64(&mut state_hash, external_rescue_stock as u64);
    hash_u64(&mut state_hash, failed_module_stock as u64);

    RunOut {
        aurd: if alive {
            aurd_sum / WINDOW_T as f64
        } else {
            f64::NAN
        },
        aurd_observed: if observed_steps > 0 {
            aurd_sum / observed_steps as f64
        } else {
            f64::NAN
        },
        aurd_abs: if alive {
            aurd_abs_sum / WINDOW_T as f64
        } else {
            f64::NAN
        },
        aurd_abs_observed: if observed_steps > 0 {
            aurd_abs_sum / observed_steps as f64
        } else {
            f64::NAN
        },
        f_final: if alive { f_prev } else { f64::NAN },
        f_at_death: if alive { f64::NAN } else { f_at_death },
        f_at_ko2,
        v_after_ko2,
        v_after_rescue,
        binary95,
        t_reach95,
        max_imbalance,
        v_first,
        n_final: n,
        maint_short_total,
        maint_debt,
        rescue_in_total,
        external_rescue_stock,
        failed_module_stock,
        observed_steps,
        alive,
        death_step,
        death_cause,
        horizon_censored: alive,
        state_hash,
        trajectory_hash,
    }
}

fn build_arms() -> Vec<ArmSpec> {
    let mk = |label: &'static str,
              cap: CapMode,
              d0: f64,
              ko1: bool,
              ko2: bool,
              rescue: bool,
              sham: bool,
              cost_yoked: bool| ArmSpec {
        label,
        cap,
        d0,
        ko1,
        ko2,
        rescue,
        sham,
        cost_yoked,
    };
    vec![
        mk("A-control", CapMode::Fixed, D0, false, false, false, false, false),
        mk("B1-sham", CapMode::Modular { k_eff: K_MIN }, D0, false, false, false, true, false),
        mk("B2-ko1", CapMode::Modular { k_eff: K_MIN }, D0, true, false, false, false, false),
        mk("B3-ko2", CapMode::Modular { k_eff: K_MIN }, D0, true, true, false, false, false),
        mk("rescue", CapMode::Modular { k_eff: K_MIN }, D0, true, true, true, false, false),
        mk("A-B2-cost", CapMode::Fixed, D0, true, false, false, false, true),
        mk("A-B3-cost", CapMode::Fixed, D0, true, true, false, false, true),
        mk("A-rescue-cost", CapMode::Fixed, D0, true, true, true, false, true),
        mk("D-half", CapMode::Modular { k_eff: K_MIN }, D0 / 2.0, false, false, false, false, false),
        mk("D-third", CapMode::Modular { k_eff: K_MIN }, 1.0 / 6.0, false, false, false, false, false),
        mk("ghost", CapMode::Ghost, D0, true, true, false, false, true),
        mk("placebo-k1", CapMode::Modular { k_eff: 1 }, D0, true, true, false, false, false),
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
            "--seeds" => {
                i += 1;
                seeds = args[i].parse().unwrap();
            }
            "--seed-base" => {
                i += 1;
                seed_base = args[i].parse().unwrap();
            }
            "--steps-out" => {
                i += 1;
                steps_path = Some(args[i].clone());
            }
            other => {
                eprintln!("unknown arg: {other}");
                std::process::exit(2);
            }
        }
        i += 1;
    }

    let q0 = X_BASE - D0;
    let need_r0 = (F_GOAL - q0) / WINDOW_T as f64;
    let need_kd = ((1.0 - q0) / (1.0 - F_GOAL)).ln() / WINDOW_T as f64;
    eprintln!("schedule: {SCHEDULE_FINGERPRINT}");
    eprintln!(
        "sensitivity: r0={} need={} kD={} need={}",
        csv_num(R0_PER_MODULE),
        csv_num(need_r0),
        csv_num(K_D),
        csv_num(need_kd)
    );
    if R0_PER_MODULE < need_r0 || K_D < need_kd {
        println!(
            "INSENSITIVE_BY_CONSTRUCTION r0={} need={} kD={} need={}",
            csv_num(R0_PER_MODULE),
            csv_num(need_r0),
            csv_num(K_D),
            csv_num(need_kd)
        );
        std::process::exit(3);
    }

    let arms = build_arms();
    let mut steps_all: Vec<String> = vec![STEPS_HEADER.to_string()];
    println!("{RAW_HEADER}");
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
            let k_eff = match spec.cap {
                CapMode::Modular { k_eff } => k_eff as f64,
                _ => -1.0,
            };
            let death_step = out.death_step.map(|s| s as i64).unwrap_or(-1);
            println!(
                "{arm},{k_eff},{d0},{seed},{aurd},{aurd_abs},{f_final},{f_at_ko2},{v_after_ko2},{v_after_rescue},{binary95},{t_reach95},{max_imbalance},{v_first},{n_final},{aurd_observed},{aurd_abs_observed},{f_at_death},{maint_short_total},{maint_debt},{rescue_in_total},{external_rescue_stock},{failed_module_stock},{observed_steps},{alive},{death_step},{death_cause},{horizon_censored},{state_hash:016x},{trajectory_hash:016x}",
                arm = spec.label,
                k_eff = k_eff,
                d0 = csv_num(spec.d0),
                seed = seed,
                aurd = csv_num(out.aurd),
                aurd_abs = csv_num(out.aurd_abs),
                f_final = csv_num(out.f_final),
                f_at_ko2 = csv_num(out.f_at_ko2),
                v_after_ko2 = csv_num(out.v_after_ko2),
                v_after_rescue = csv_num(out.v_after_rescue),
                binary95 = out.binary95 as u8,
                t_reach95 = out.t_reach95,
                max_imbalance = csv_num(out.max_imbalance),
                v_first = csv_num(out.v_first),
                n_final = out.n_final,
                aurd_observed = csv_num(out.aurd_observed),
                aurd_abs_observed = csv_num(out.aurd_abs_observed),
                f_at_death = csv_num(out.f_at_death),
                maint_short_total = csv_num(out.maint_short_total),
                maint_debt = csv_num(out.maint_debt),
                rescue_in_total = out.rescue_in_total,
                external_rescue_stock = out.external_rescue_stock,
                failed_module_stock = out.failed_module_stock,
                observed_steps = out.observed_steps,
                alive = out.alive as u8,
                death_step = death_step,
                death_cause = out.death_cause.label(),
                horizon_censored = out.horizon_censored as u8,
                state_hash = out.state_hash,
                trajectory_hash = out.trajectory_hash,
            );
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

    #[test]
    fn fnv1a64_matches_known_vector() {
        let mut hash = 0xcbf2_9ce4_8422_2325u64;
        for byte in b"hello" {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(0x100000001b3);
        }
        assert_eq!(hash, 0xa430_d846_80aa_bd0b);
    }

    #[test]
    fn live_f_at_death_is_nan() {
        let out = run_arm(&build_arms()[0], SEED_BASE, None);
        assert!(out.alive);
        assert!(out.f_at_death.is_nan());
    }

    fn spec(
        label: &'static str,
        cap: CapMode,
        d0: f64,
        ko1: bool,
        ko2: bool,
        rescue: bool,
        sham: bool,
    ) -> ArmSpec {
        ArmSpec {
            label,
            cap,
            d0,
            ko1,
            ko2,
            rescue,
            sham,
            cost_yoked: false,
        }
    }

    fn arm(label: &'static str) -> ArmSpec {
        build_arms()
            .into_iter()
            .find(|a| a.label == label)
            .unwrap()
    }

    #[test]
    fn ledger_closes_every_step_and_registered_arms_survive() {
        for s in build_arms() {
            let out = run_arm(&s, SEED_BASE, None);
            assert!(out.max_imbalance < 1e-12, "{} imbalance {}", s.label, out.max_imbalance);
            assert!(out.alive, "registered arm {} died: {:?}", s.label, out.death_cause);
            assert_eq!(out.observed_steps, WINDOW_T);
        }
    }

    #[test]
    fn a_control_equals_b1_by_trajectory_hash() {
        let a = run_arm(&arm("A-control"), SEED_BASE, None);
        let b1 = run_arm(&arm("B1-sham"), SEED_BASE, None);
        assert_eq!(a.trajectory_hash, b1.trajectory_hash);
        assert_eq!(a.state_hash, b1.state_hash);
    }

    #[test]
    fn cost_yoked_a_b2_equals_b2_by_trajectory_hash() {
        let a = run_arm(&arm("A-B2-cost"), SEED_BASE, None);
        let b2 = run_arm(&arm("B2-ko1"), SEED_BASE, None);
        assert_eq!(a.trajectory_hash, b2.trajectory_hash);
        assert_eq!(a.state_hash, b2.state_hash);
        assert_eq!(a.n_final, 2);
    }

    #[test]
    fn cost_yoked_a_b3_equals_ghost_by_trajectory_hash() {
        let a = run_arm(&arm("A-B3-cost"), SEED_BASE, None);
        let ghost = run_arm(&arm("ghost"), SEED_BASE, None);
        assert_eq!(a.trajectory_hash, ghost.trajectory_hash);
        assert_eq!(a.state_hash, ghost.state_hash);
        assert_eq!(ghost.failed_module_stock, 2);
    }

    #[test]
    fn cost_yoked_a_rescue_matches_rescue_resources_but_not_capacity() {
        let a = run_arm(&arm("A-rescue-cost"), SEED_BASE, None);
        let rescue = run_arm(&arm("rescue"), SEED_BASE, None);
        assert_ne!(a.trajectory_hash, rescue.trajectory_hash);
        assert_eq!(a.n_final, rescue.n_final);
        assert_eq!(a.rescue_in_total, rescue.rescue_in_total);
        assert_eq!(a.external_rescue_stock, rescue.external_rescue_stock);
        assert_eq!(a.failed_module_stock, rescue.failed_module_stock);
        assert_eq!(a.maint_debt.to_bits(), rescue.maint_debt.to_bits());
        assert_eq!(rescue.rescue_in_total, 1);
        assert_eq!(rescue.external_rescue_stock, 0);
    }

    #[test]
    fn b3_freezes_at_ko2() {
        let b3 = run_arm(&arm("B3-ko2"), SEED_BASE, None);
        assert_eq!(b3.v_after_ko2, 0.0);
        assert!((b3.f_final - b3.f_at_ko2).abs() < 1e-15);
        assert_eq!(b3.n_final, 1);
        assert_eq!(b3.failed_module_stock, 2);
    }

    #[test]
    fn rescue_strictly_between_b2_and_b3() {
        let b2 = run_arm(&arm("B2-ko1"), SEED_BASE, None);
        let b3 = run_arm(&arm("B3-ko2"), SEED_BASE, None);
        let r = run_arm(&arm("rescue"), SEED_BASE, None);
        assert!(r.v_after_rescue > 0.0);
        assert!(b2.aurd < r.aurd);
        assert!(r.aurd < b3.aurd);
        assert!(r.aurd - b2.aurd > 1e-6 && b3.aurd - r.aurd > 1e-6);
    }

    #[test]
    fn rescue_consumes_explicit_external_stock_and_failed_modules_are_accounted() {
        let mut rows = Vec::new();
        let out = run_arm(&arm("rescue"), SEED_BASE, Some(&mut rows));
        assert_eq!(out.rescue_in_total, 1);
        assert_eq!(out.external_rescue_stock, 0);
        assert_eq!(out.failed_module_stock, 2);
        assert_eq!(out.n_final, 2);
        assert!(out.max_imbalance < 1e-12);
        let header: Vec<&str> = STEPS_HEADER.split(',').collect();
        let rescue_row = rows
            .iter()
            .find(|row| row.split(',').nth(4) == Some("rescue"))
            .expect("rescue event");
        let fields: Vec<&str> = rescue_row.split(',').collect();
        let get = |name: &str| fields[header.iter().position(|h| *h == name).unwrap()];
        assert_eq!(get("module_in"), "1");
        assert_eq!(get("module_out"), "0");
        assert_eq!(get("failed_module_in"), "0");
        assert_eq!(get("external_rescue_stock"), "0");
        assert_eq!(get("failed_module_stock"), "2");
        let ko2_row = rows
            .iter()
            .find(|row| row.split(',').nth(4) == Some("ko2"))
            .expect("ko2 event");
        let fields: Vec<&str> = ko2_row.split(',').collect();
        let get = |name: &str| fields[header.iter().position(|h| *h == name).unwrap()];
        assert_eq!(get("module_out"), "1");
        assert_eq!(get("failed_module_in"), "1");
    }

    #[test]
    fn maintenance_shortfall_and_energy_death_are_explicit() {
        let mut e = 0.01;
        let mut debt = 0.0;
        let (paid, short, stock) = pay_maintenance(&mut e, &mut debt, 0.03);
        assert!((paid - 0.01).abs() < 1e-15);
        assert!((short - 0.02).abs() < 1e-15);
        assert!((stock - 0.02).abs() < 1e-15);
        assert_eq!(e, 0.0);

        let starved = spec("starved", CapMode::Modular { k_eff: K_MIN }, 0.01, false, false, false, false);
        let mut rows = Vec::new();
        let out = run_arm_with_ration_scale(&starved, SEED_BASE, 0.0, Some(&mut rows));
        assert!(!out.alive && out.death_cause == DeathCause::Energy);
        assert_eq!(out.observed_steps, rows.len());
        assert!(rows.len() < WINDOW_T);
        assert!(out.maint_debt > 0.0 && out.maint_short_total > 0.0);
        assert!((out.maint_debt - out.maint_short_total).abs() < 1e-15);
        assert!(out.aurd.is_nan() && out.f_final.is_nan());
        assert!(out.max_imbalance < 1e-12);
    }

    #[test]
    fn damage_death_is_absorbing_and_boundary_is_exact() {
        let dead = spec("dead", CapMode::Modular { k_eff: K_MIN }, 1.0, false, false, false, false);
        let mut rows = Vec::new();
        let out = run_arm(&dead, SEED_BASE, Some(&mut rows));
        assert!(!out.alive && out.death_cause == DeathCause::Damage);
        assert_eq!(out.death_step, Some(0));
        assert_eq!(out.observed_steps, 0);
        assert!(rows.is_empty());
        assert!(out.aurd.is_nan() && out.aurd_abs.is_nan() && out.f_final.is_nan());

        let just_below = f64::from_bits(1.0f64.to_bits() - 1);
        let live = spec("live", CapMode::Modular { k_eff: K_MIN }, just_below, false, false, false, false);
        let out = run_arm(&live, SEED_BASE, None);
        assert!(out.alive && out.death_cause == DeathCause::None);
        assert_eq!(out.observed_steps, WINDOW_T);
        assert!(out.horizon_censored);
    }

    #[test]
    fn d_ladder_abs_monotone_and_third_is_exact_sixth() {
        let full = run_arm(&arm("B1-sham"), SEED_BASE, None);
        let half = run_arm(&arm("D-half"), SEED_BASE, None);
        let third = run_arm(&arm("D-third"), SEED_BASE, None);
        assert_eq!(arm("D-third").d0, 1.0 / 6.0);
        assert!(full.aurd_abs > half.aurd_abs);
        assert!(half.aurd_abs > third.aurd_abs);
    }

    #[test]
    fn placebo_k1_keeps_nonzero_capacity() {
        let mut rows = Vec::new();
        let p = run_arm(&arm("placebo-k1"), SEED_BASE, Some(&mut rows));
        assert!(p.v_after_ko2 > 0.0);
        let after = rows
            .iter()
            .filter(|row| {
                let fields: Vec<&str> = row.split(',').collect();
                fields[2].parse::<usize>().unwrap() >= T_KO2
            })
            .map(|row| {
                let fields: Vec<&str> = row.split(',').collect();
                fields[17].parse::<f64>().unwrap()
            });
        assert!(after.into_iter().all(|cap| (cap - 0.05).abs() < 1e-15));
    }

    #[test]
    fn capacity_binds_first_step_on_full_damage() {
        let a = run_arm(&arm("A-control"), SEED_BASE, None);
        let half = run_arm(&arm("D-half"), SEED_BASE, None);
        assert!((a.v_first - R0).abs() < 1e-12);
        assert!(half.v_first < R0);
    }

    #[test]
    fn same_seed_repeat_has_identical_hashes_and_metrics() {
        for s in build_arms() {
            let a = run_arm(&s, SEED_BASE, None);
            let b = run_arm(&s, SEED_BASE, None);
            assert_eq!(a.trajectory_hash, b.trajectory_hash, "{}", s.label);
            assert_eq!(a.state_hash, b.state_hash, "{}", s.label);
            assert_eq!(a.aurd.to_bits(), b.aurd.to_bits(), "{}", s.label);
            assert_eq!(a.f_final.to_bits(), b.f_final.to_bits(), "{}", s.label);
        }
    }

    #[test]
    fn schedule_registered_and_ordered() {
        assert!(T_KO1 < T_KO2 && T_KO2 < T_RESCUE && T_RESCUE < WINDOW_T);
        assert_eq!(M_MODULES, 3);
        assert_eq!(K_MIN, 2);
        assert!((R0_PER_MODULE - R0 / 2.0).abs() < 1e-15);
    }

    #[test]
    fn sensitivity_conditions_hold_for_registered_params() {
        let q0 = X_BASE - D0;
        let need_r0 = (F_GOAL - q0) / WINDOW_T as f64;
        let need_kd = ((1.0 - q0) / (1.0 - F_GOAL)).ln() / WINDOW_T as f64;
        assert!(R0_PER_MODULE >= need_r0);
        assert!(K_D >= need_kd);
    }

    #[test]
    fn csv_number_preserves_one_ulp_and_signed_zero() {
        let one = 1.0f64;
        let next = f64::from_bits(one.to_bits() + 1);
        assert_ne!(csv_num(one), csv_num(next));
        assert_eq!(csv_num(-0.0), "-0");
        assert_eq!(csv_num(f64::NAN), "NaN");
    }
}
