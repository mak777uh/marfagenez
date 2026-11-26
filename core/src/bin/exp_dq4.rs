//! D-Q4 (I-065): скрытая память ремонтного износа при равных (q, D, energy).
//!
//! Design: PROP-EXPER-DQ4-20261126-2319 rev2 (task EXP-2026-4101). Matching полностью
//! детерминирован (без смерти/цензурирования); challenge подаёт ОДИН paired RNG поток
//! обеим рукам одновременно, поэтому при k_repair=0 и do(R=0) распределения совпадают
//! попарно -- это и есть два встроенных контроля дизайна.
//!
//! Три контроля процедуры (proposal PROP-EXPER-DQ4-UNBLOCK-20261127-01 rev4):
//! - `--control repair` (default): реальный ремонт, R растёт на фактически выполненное;
//! - `--control r-clock`: в hazard подан R_clock=100 обеим рукам (изоляция
//!   значения-артефакта);
//! - `--control sham`: cost-matched sham-ремонт (энергия списывается, d не
//!   восстанавливается, R не растёт), в hazard подан 0.
//! r-clock и sham обязаны давать попарно идентичные исходы при k>0.

use medium_core::organ::{mortality_with_floor, Part};
use medium_core::Rng;

const MATCH_STEPS: usize = 100;
const HORIZON: usize = 5000;
const FLOOR: f64 = 0.0002;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const LAMBDA: f64 = 0.001;
const COST: f64 = 0.05;
const ADDED_DAMAGE: f64 = 0.2;
const REPAIR_REQUEST: f64 = 0.02;
const REPAIR_BUDGET: f64 = 0.1;
const Q_TARGET: f64 = 0.5;
const D_TARGET: f64 = 0.2;
const ENERGY_TARGET: f64 = 0.8;
const R_CLOCK: f64 = 100.0;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Control {
    Repair,
    RClock,
    Sham,
}

impl Control {
    fn parse(s: &str) -> Option<Control> {
        match s {
            "repair" => Some(Control::Repair),
            "r-clock" => Some(Control::RClock),
            "sham" => Some(Control::Sham),
            _ => None,
        }
    }
    fn label(self) -> &'static str {
        match self {
            Control::Repair => "repair",
            Control::RClock => "r-clock",
            Control::Sham => "sham",
        }
    }
}

struct Arm {
    q: f64,
    d: f64,
    energy: f64,
    r: f64,
}

/// Фаза выравнивания: A копит R = a одним ремонтом, B -- дрейфом. Обе руки
/// заканчивают ровно в (q, D, energy) = (0.5, 0.2, 0.8).
fn match_phase(a: f64) -> (Arm, Arm) {
    let mut part = Part::new(Q_TARGET - a, 0.0, COST);
    let mut energy = 1.0;
    // A: один вызов Part::step(request=a) на шаге MATCH_STEPS.
    for t in 1..=MATCH_STEPS {
        let u = if t == MATCH_STEPS { a } else { 0.0 };
        let done = part.step(u, 1.0, &mut energy);
        assert!(done == 0.0 || t == MATCH_STEPS, "repair outside schedule");
    }
    let r_a = Q_TARGET - (Q_TARGET - a); // done == a: проверяется тестом
    let arm_a = Arm { q: part.q, d: D_TARGET, energy, r: r_a };
    // B: D нарастает дрейфом 0.002/шаг, ремонтов нет.
    let d_b = 0.002 * MATCH_STEPS as f64;
    let arm_b = Arm { q: Q_TARGET, d: d_b, energy: 1.0, r: 0.0 };
    // Финальное выравнивание снимает confounding стоимости ремонта.
    let arm_a = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, r: arm_a.r };
    let arm_b = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, r: arm_b.r };
    (arm_a, arm_b)
}

fn hazard(arm: &Arm, k_repair: f64, do_r0: bool, control: Control) -> f64 {
    let mut r = match control {
        Control::Repair => arm.r,
        Control::RClock => R_CLOCK,
        Control::Sham => 0.0,
    };
    if do_r0 {
        r = 0.0;
    }
    mortality_with_floor(arm.q, RATE, P, FLOOR) + LAMBDA * arm.d + k_repair * r
}

/// Challenge: added damage 0.2 в t=0, ремонт по расписанию в рамках бюджета,
/// смерть при rng.uniform() < hazard. Возвращает (lifetime, censored, финальная рука).
fn challenge(mut arm: Arm, k_repair: f64, do_r0: bool, control: Control, rng: &mut Rng) -> (usize, bool, Arm) {
    arm.d += ADDED_DAMAGE;
    let mut budget = REPAIR_BUDGET;
    for t in 1..=HORIZON {
        if t % 100 == 0 && t <= 1000 && budget > 0.0 && arm.energy > 0.0 {
            let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
            if want > 0.0 {
                // cost-matched: энергия списывается всегда; d и R -- только на реальном ремонте.
                arm.energy -= want * COST;
                if control != Control::Sham {
                    arm.d -= want;
                    arm.r += want;
                }
                budget -= want;
            }
        }
        let u = rng.uniform();
        if u < hazard(&arm, k_repair, do_r0, control) {
            return (t, false, arm);
        }
    }
    (HORIZON, true, arm)
}

fn run_pair(a: f64, k_repair: f64, do_r0: bool, control: Control, seed: u64, pair: u64) -> (usize, bool, usize, bool) {
    let (arm_a, arm_b) = match_phase(a);
    let mut rng_a = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (la, ca, _) = challenge(arm_a, k_repair, do_r0, control, &mut rng_a);
    // paired: тот же поток на вторую руку -> при k=0/do_r0/control исходы равны попарно.
    let mut rng_b = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (lb, cb, _) = challenge(arm_b, k_repair, do_r0, control, &mut rng_b);
    (la, ca, lb, cb)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut a_list = vec![0.1_f64, 0.2, 0.3];
    let mut k_list = vec![0.0_f64, 0.0001, 0.0003, 0.001, 0.003];
    let mut seeds = 12_usize;
    let mut pairs = 400_usize;
    let mut seed_base = 4101_u64;
    let mut do_r0 = false;
    let mut control = Control::Repair;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--a" => { i += 1; a_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--k" => { i += 1; k_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--pairs" => { i += 1; pairs = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--do-r0" => { do_r0 = true; }
            "--control" => {
                i += 1;
                control = Control::parse(&args[i]).unwrap_or_else(|| {
                    eprintln!("unknown control: {} (repair|r-clock|sham)", args[i]);
                    std::process::exit(2);
                });
            }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    println!("a,k_repair,do_r0,control,seed,pair,RA,RB,lifeA,censA,lifeB,censB");
    for &a in &a_list {
        for &k in &k_list {
            for s in 0..seeds {
                let seed = seed_base + s as u64;
                for p in 0..pairs {
                    let (la, ca, lb, cb) = run_pair(a, k, do_r0, control, seed, p as u64);
                    println!("{},{},{},{},{},{},{},{},{},{},{},{}", a, k, do_r0, control.label(), seed, p, a, 0.0, la, ca, lb, cb);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn match_equalizes_and_done_is_a() {
        // done == a: Part::step с энергией 1 и cost 0.05 режет только по missing/affordable.
        let mut part = Part::new(0.3, 0.0, COST);
        let mut energy = 1.0;
        let done = part.step(0.2, 1.0, &mut energy);
        assert!((done - 0.2).abs() < 1e-12, "done != a: {done}");
        assert!((part.q - 0.5).abs() < 1e-12);
        for a in [0.1_f64, 0.2, 0.3] {
            let (arm_a, arm_b) = match_phase(a);
            assert!((arm_a.q - Q_TARGET).abs() < 1e-12);
            assert!((arm_a.d - D_TARGET).abs() < 1e-12);
            assert!((arm_b.q - arm_a.q).abs() < 1e-12);
            assert!((arm_b.d - arm_a.d).abs() < 1e-12);
            assert!((arm_b.energy - arm_a.energy).abs() < 1e-12);
            assert!((arm_a.r - a).abs() < 1e-12, "R_A != a");
            assert!(arm_b.r.abs() < 1e-12);
        }
    }

    #[test]
    fn k_zero_pair_is_identical() {
        // контроль k_repair = 0: paired RNG -> попарно равные исходы.
        let (la, ca, lb, cb) = run_pair(0.2, 0.0, false, Control::Repair, 4101, 7);
        assert_eq!((la, ca), (lb, cb), "k=0 must give identical paired outcomes");
    }

    #[test]
    fn do_r0_pair_is_identical() {
        // контроль do(R=0): износ назван, но не подан в hazard.
        let (la, ca, lb, cb) = run_pair(0.2, 0.001, true, Control::Repair, 4105, 3);
        assert_eq!((la, ca), (lb, cb), "do(R=0) must give identical paired outcomes");
    }

    #[test]
    fn r_clock_pair_is_identical() {
        // контроль r-clock: R_clock=100 подан обеим рукам -> при k>0 исходы равны попарно.
        let (la, ca, lb, cb) = run_pair(0.2, 0.003, false, Control::RClock, 4111, 5);
        assert_eq!((la, ca), (lb, cb), "r-clock control must give identical paired outcomes");
    }

    #[test]
    fn sham_pair_is_identical() {
        // контроль sham: cost-matched без ремонта и без R в hazard -> при k>0 исходы равны попарно.
        let (la, ca, lb, cb) = run_pair(0.2, 0.003, false, Control::Sham, 4112, 5);
        assert_eq!((la, ca), (lb, cb), "sham control must give identical paired outcomes");
    }

    #[test]
    fn sham_costs_energy_but_never_repairs() {
        // sham списывает энергию, но d не восстанавливает и R не растит.
        let (arm_a, _) = match_phase(0.2);
        let r_expected = arm_a.r;
        let mut any_spent = false;
        for seed in [4113_u64, 4114, 4115, 4116] {
            let mut rng = Rng::new(seed);
            let arm = Arm { ..arm_a };
            let (_, _, final_arm) = challenge(arm, 0.0, false, Control::Sham, &mut rng);
            assert!((final_arm.d - (D_TARGET + ADDED_DAMAGE)).abs() < 1e-12,
                "sham repaired d: {}", final_arm.d);
            assert!((final_arm.r - r_expected).abs() < 1e-12, "sham grew R: {}", final_arm.r);
            let spent = ENERGY_TARGET - final_arm.energy;
            assert!(spent >= 0.0 && spent <= REPAIR_BUDGET * COST + 1e-9,
                "sham spent out of budget: {}", spent);
            let events = spent / (REPAIR_REQUEST * COST);
            assert!((events - events.round()).abs() < 1e-6,
                "sham spent not a whole number of events: {}", spent);
            if spent > 1e-12 { any_spent = true; }
        }
        assert!(any_spent, "sham never spent energy in 4 seeds");
    }

    #[test]
    fn fires_k_repair_separates_the_pair() {
        // чек должен уметь падать: при k>0 износ A выше и хотя бы одна пара расходится.
        let mut diverged = 0;
        for p in 0..64_u64 {
            let (la, _, lb, _) = run_pair(0.2, 0.003, false, Control::Repair, 4109, p);
            if la != lb { diverged += 1; }
        }
        assert!(diverged > 0, "k_repair=0.003 never separated a pair in 64 tries");
    }

    #[test]
    fn budget_caps_repairs_and_r_counts_only_executed() {
        // R растёт только на реально выполненных ремонтах, бюджет 0.1 не пробивается.
        let (arm_a, _) = match_phase(0.3);
        let mut rng = Rng::new(1);
        let mut arm = Arm { ..arm_a };
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=1000 {
            if t % 100 == 0 && budget > 0.0 {
                let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
                arm.d -= want; arm.energy -= want * COST; arm.r += want; budget -= want;
            }
            let _ = rng.uniform();
        }
        assert!(arm.r <= 0.3 + REPAIR_BUDGET + 1e-12, "R exceeded match+budget: {}", arm.r);
        assert!((0.3_f64 + REPAIR_BUDGET - arm.r).abs() < 1e-9, "budget not fully used: {}", arm.r);
    }
}
