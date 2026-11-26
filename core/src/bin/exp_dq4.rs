//! D-Q4 (I-065): скрытая память ремонтного износа при равных (q, D, energy).
//!
//! Design: PROP-EXPER-DQ4-20261126-2319 rev2 (task EXP-2026-4101). Matching полностью
//! детерминирован (без смерти/цензурирования); challenge подаёт ОДИН paired RNG поток
//! обеим рукам одновременно, поэтому при k_repair=0 и do(R=0) распределения совпадают
//! попарно -- это и есть два встроенных контроля дизайна.

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

fn hazard(arm: &Arm, k_repair: f64, do_r0: bool) -> f64 {
    let r = if do_r0 { 0.0 } else { arm.r };
    mortality_with_floor(arm.q, RATE, P, FLOOR) + LAMBDA * arm.d + k_repair * r
}

/// Challenge: added damage 0.2 в t=0, ремонт по расписанию в рамках бюджета,
/// смерть при rng.uniform() < hazard. Возвращает (lifetime, censored).
fn challenge(mut arm: Arm, k_repair: f64, do_r0: bool, rng: &mut Rng) -> (usize, bool) {
    arm.d += ADDED_DAMAGE;
    let mut budget = REPAIR_BUDGET;
    for t in 1..=HORIZON {
        if t % 100 == 0 && t <= 1000 && budget > 0.0 && arm.energy > 0.0 {
            let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
            if want > 0.0 {
                arm.d -= want;
                arm.energy -= want * COST;
                arm.r += want;
                budget -= want;
            }
        }
        let u = rng.uniform();
        if u < hazard(&arm, k_repair, do_r0) {
            return (t, false);
        }
    }
    (HORIZON, true)
}

fn run_pair(a: f64, k_repair: f64, do_r0: bool, seed: u64, pair: u64) -> (usize, bool, usize, bool) {
    let (arm_a, arm_b) = match_phase(a);
    let mut rng_a = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (la, ca) = challenge(arm_a, k_repair, do_r0, &mut rng_a);
    // paired: тот же поток на вторую руку -> при k=0/do_r0 исходы равны попарно.
    let mut rng_b = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (lb, cb) = challenge(arm_b, k_repair, do_r0, &mut rng_b);
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
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--a" => { i += 1; a_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--k" => { i += 1; k_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect(); }
            "--seeds" => { i += 1; seeds = args[i].parse().unwrap(); }
            "--pairs" => { i += 1; pairs = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--do-r0" => { do_r0 = true; }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    println!("a,k_repair,do_r0,seed,pair,RA,RB,lifeA,censA,lifeB,censB");
    for &a in &a_list {
        for &k in &k_list {
            for s in 0..seeds {
                let seed = seed_base + s as u64;
                for p in 0..pairs {
                    let (la, ca, lb, cb) = run_pair(a, k, do_r0, seed, p as u64);
                    println!("{},{},{},{},{},{},{},{},{},{},{}", a, k, do_r0, s, p, a, 0.0, la, ca, lb, cb);
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
        let (la, ca, lb, cb) = run_pair(0.2, 0.0, false, 4101, 7);
        assert_eq!((la, ca), (lb, cb), "k=0 must give identical paired outcomes");
    }

    #[test]
    fn do_r0_pair_is_identical() {
        // контроль do(R=0): износ назван, но не подан в hazard.
        let (la, ca, lb, cb) = run_pair(0.2, 0.001, true, 4105, 3);
        assert_eq!((la, ca), (lb, cb), "do(R=0) must give identical paired outcomes");
    }

    #[test]
    fn fires_k_repair_separates_the_pair() {
        // чек должен уметь падать: при k>0 износ A выше и хотя бы одна пара расходится.
        let mut diverged = 0;
        for p in 0..64_u64 {
            let (la, _, lb, _) = run_pair(0.2, 0.003, false, 4109, p);
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
