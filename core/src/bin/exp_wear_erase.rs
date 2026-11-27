//! EXP-2026-4106 (мост FINDING-457 N3): стирание износа в середине жизни.
//!
//! Протокол 457 (как в exp_wear_vec.rs): match-фаза выравнивает (q, D, energy)
//! обеих рук = (0.5, 0.2, 0.8); A копит износ a=0.2 одним ремонтом, B -- нет;
//! challenge: +0.2 damage, ремонт по расписанию (шаги 100..1000, request 0.02,
//! budget 0.1 -> ровно 5 ремонтов, бюджет исчерпан к шагу 500), смерть при
//! u < hazard = mortality_with_floor(q,0.01,2.0,0.0002) + 0.001*D + 0.001*R.
//! Paired RNG: один поток на пару, обе руки.
//!
//! Интервенция (external, ledger): на шаге t_erase обнулить накопленный износ R
//! руки, сохранив (q, D, energy). Стирание применяется обеим рукам (у B это
//! no-op: R=0) для симметрии ledger.
//!
//! Точки стирания (предрегистрированы; обе не зависят от текущего damage):
//! - ERASE_MID = 221: «середина жизни по медиане контрольной ветки» (спека):
//!   медиана lifeB = 221 по 4800 primary-парам завершённого EXP-2026-4105
//!   (cell scalar/repair; ветка B не зависит от клетки). К шагу 221 сделано
//!   2 ремонта -> стирается 0.24 из 0.3; после стирания износ дорастает на
//!   0.06 к шагу 500 -> полный коллапс НЕ предсказываем, только сдвиг к нулю.
//! - ERASE_STEP = 600: после конца ремонтного окна (бюджет исчерпан на 500):
//!   стирается весь износ 0.3 и больше не растёт -> для пар, где A жива на 600,
//!   дальнейшие исходы совпадают байт-в-байт.
//! - erand: 600 + ((seed+pair) mod 4)*100 -- момент задан (seed,pair), не
//!   состоянием (контроль независимости от damage).
//!
//! Предсказания (до прогона):
//! - P1 (primary, причинный): erase600, пары с lifeA >= 600:
//!   (lifeA, censA) == (lifeB, censB) байт-в-байт.
//! - P2: erase600 DeltaT90 > base DeltaT90 (сдвиг к нулю; смерти до 600
//!   необратимы, нуля не предсказываем).
//! - P3: erase221 DeltaT90 > base DeltaT90 (частичное стирание 0.24/0.3);
//!   lifeA <= lifeB поточечно (доминирование сохраняется: дорост 0.06 >= 0).
//! - P4: sham600 == base байт-в-байт на всех парах (метка без эффекта).
//! - P5: base: lifeA <= lifeB поточечно, DeltaT90 < 0 (репликация 457,
//!   окно [-90,-10] как в 4105).
//! - P6: erand: поточечный коллапс при своём t_erase; доля коллапса не
//!   зависит от момента; deferred-сиды -- подтверждение без настройки.
//! - Фальсификация: если стирание (обе точки) не сдвигает DeltaT90 и полный
//!   коллапс не наступает -- носитель памяти 457 НЕ износ R; линия ломается.

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
const A_PRIMARY: f64 = 0.2;
const K_SCALAR: f64 = 0.001;
const ERASE_MID: usize = 221;
const ERASE_STEP: usize = 600;
const SEED_BASE: u64 = 5501;
const PRIMARY_SEEDS: usize = 12;
const DEFERRED_SEEDS: usize = 8;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Cell { Base, Erase, EraseMid, Sham, Erand }

impl Cell {
    fn label(self) -> &'static str {
        match self {
            Cell::Base => "base",
            Cell::Erase => "erase600",
            Cell::EraseMid => "erase221",
            Cell::Sham => "sham600",
            Cell::Erand => "erand",
        }
    }
}

/// Шаг интервенции для носителя (None -- носитель не трогаем).
fn erase_step_for(cell: Cell, seed: u64, pair: u64) -> Option<usize> {
    match cell {
        Cell::Base => None,
        Cell::Erase => Some(ERASE_STEP),
        Cell::EraseMid => Some(ERASE_MID),
        // sham: только ledger-метка, wear сохраняется
        Cell::Sham => None,
        // erand: случайный момент из отдельного (seed,pair)-потока (аудит
        // 28.11.2026: прежняя формула была детерминированной сбалансированной
        // сеткой 600/700/800/900, а не случайным моментом)
        Cell::Erand => Some(erandom_moment(seed, pair)),
    }
}

/// Случайный момент стирания erand: детерминирован (seed, pair), равномерен
/// в [600, 1000), независим от состояния руки и от paired-потока симуляции.
fn erandom_moment(seed: u64, pair: u64) -> usize {
    let mut m = Rng::new(seed ^ 0x5EED_BEEF ^ pair.wrapping_mul(0x9E37_79B9_7F4A_7C15));
    600 + (m.uniform() * 400.0) as usize
}

/// Ledger-колонка: 0 = вмешательства не было.
fn ledger_t_erase(cell: Cell, seed: u64, pair: u64) -> usize {
    match cell {
        Cell::Base => 0,
        Cell::Sham => ERASE_STEP,
        _ => erase_step_for(cell, seed, pair).unwrap(),
    }
}

struct Arm { q: f64, d: f64, energy: f64, wear: f64 }

/// External-вмешательство: стереть износ, (q, D, energy) не тронуты.
fn erase_wear(arm: &mut Arm) {
    arm.wear = 0.0;
}

/// Фаза выравнивания 457: A копит износ a одним ремонтом, B -- нет; обе руки
/// заканчивают ровно в (q, D, energy) = (0.5, 0.2, 0.8); износ A = a, B = 0.
fn match_phase(a: f64) -> (Arm, Arm) {
    let mut part = Part::new(Q_TARGET - a, 0.0, COST);
    let mut energy = 1.0;
    for t in 1..=MATCH_STEPS {
        let u = if t == MATCH_STEPS { a } else { 0.0 };
        let done = part.step(u, 1.0, &mut energy);
        assert!(done == 0.0 || t == MATCH_STEPS, "repair outside schedule");
    }
    let r_a = Q_TARGET - (Q_TARGET - a);
    let arm_a = Arm { q: part.q, d: D_TARGET, energy, wear: r_a };
    let d_b = 0.002 * MATCH_STEPS as f64;
    let arm_b = Arm { q: Q_TARGET, d: d_b, energy: 1.0, wear: 0.0 };
    let arm_a = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, wear: arm_a.wear };
    let arm_b = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, wear: arm_b.wear };
    (arm_a, arm_b)
}

fn hazard(arm: &Arm) -> f64 {
    mortality_with_floor(arm.q, RATE, P, FLOOR) + LAMBDA * arm.d + K_SCALAR * arm.wear
}

/// Challenge 457 с внешней интервенцией на erase_at.
fn challenge(mut arm: Arm, erase_at: Option<usize>, rng: &mut Rng)
    -> (usize, bool, bool, f64, f64) {
    arm.d += ADDED_DAMAGE;
    let mut budget = REPAIR_BUDGET;
    // intervention ledger (аудит 28.11.2026): applied, wear до/после события
    let mut applied = false;
    let mut w_before = 0.0_f64;
    let mut w_after = 0.0_f64;
    for t in 1..=HORIZON {
        if t % 100 == 0 && t <= 1000 && budget > 0.0 && arm.energy > 0.0 {
            let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
            if want > 0.0 {
                arm.energy -= want * COST;
                arm.d -= want;
                arm.wear += want;
                budget -= want;
            }
        }
        if erase_at == Some(t) {
            w_before = arm.wear;
            erase_wear(&mut arm);
            w_after = arm.wear;
            applied = true;
        }
        let u = rng.uniform();
        if u < hazard(&arm) {
            return (t, false, applied, w_before, w_after);
        }
    }
    (HORIZON, true, applied, w_before, w_after)
}

/// Полный прогон пары с intervention ledger:
/// (lifeA, censA, lifeB, censB, applied, wearA_before, wearA_after).
/// applied/wear -- по руке A (носитель); стирание симметрично обеим рукам,
/// у B это no-op (wear=0), ledger честен для обеих.
fn run_pair_full(cell: Cell, seed: u64, pair: u64)
    -> (usize, bool, usize, bool, bool, f64, f64) {
    let (arm_a, arm_b) = match_phase(A_PRIMARY);
    let erase = erase_step_for(cell, seed, pair);
    let mut rng_a = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (la, ca, applied, w_before, w_after) = challenge(arm_a, erase, &mut rng_a);
    let mut rng_b = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (lb, cb, _bap, _bwb, _bwa) = challenge(arm_b, erase, &mut rng_b);
    (la, ca, lb, cb, applied, w_before, w_after)
}

fn run_pair(cell: Cell, seed: u64, pair: u64) -> (usize, bool, usize, bool) {
    let (la, ca, lb, cb, _, _, _) = run_pair_full(cell, seed, pair);
    (la, ca, lb, cb)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut primary = PRIMARY_SEEDS;
    let mut deferred = DEFERRED_SEEDS;
    let mut seed_base = SEED_BASE;
    let mut pairs = 400_usize;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--seeds" => { i += 1; primary = args[i].parse().unwrap(); }
            "--deferred" => { i += 1; deferred = args[i].parse().unwrap(); }
            "--seed-base" => { i += 1; seed_base = args[i].parse().unwrap(); }
            "--pairs" => { i += 1; pairs = args[i].parse().unwrap(); }
            other => { eprintln!("unknown arg: {other}"); std::process::exit(2); }
        }
        i += 1;
    }
    println!("cell,cohort,seed,pair,t_erase,applied,wearA_before,wearA_after,lifeA,censA,lifeB,censB");
    for cell in [Cell::Base, Cell::Erase, Cell::EraseMid, Cell::Sham, Cell::Erand] {
        for s in 0..(primary + deferred) {
            let seed = seed_base + s as u64;
            let cohort = if s < primary { "primary" } else { "deferred" };
            for p in 0..pairs {
                let (la, ca, lb, cb, applied, wb, wa) = run_pair_full(cell, seed, p as u64);
                println!("{},{},{},{},{},{},{},{},{},{},{},{}",
                    cell.label(), cohort, seed, p, ledger_t_erase(cell, seed, p as u64),
                    applied as u8, wb, wa,
                    la, ca as u8, lb, cb as u8);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SEEDS: [u64; 3] = [SEED_BASE, SEED_BASE + 3, SEED_BASE + 7];
    const PAIRS: [u64; 3] = [0, 17, 137];

    #[test]
    fn base_pointwise_lifeA_le_lifeB() {
        // P5: доминирование 457 -- износ A делает смерть A не позже B поточечно.
        for seed in SEEDS {
            for pair in PAIRS {
                let (la, _ca, lb, _cb) = run_pair(Cell::Base, seed, pair);
                assert!(la <= lb, "lifeA > lifeB at seed {seed} pair {pair}: {la} > {lb}");
            }
        }
    }

    #[test]
    fn erase600_collapses_paired_lives() {
        // P1: для пар, где рука A жива на 600, исходы совпадают байт-в-байт.
        // Аудит 28.11.2026: выборка 3 сида x 3 пары не даёт ни одной пары с
        // lifeA >= 600 (медиана жизни ~217), assert(checked>0) паниковал, а
        // паника в этом бине абортится (SIGSEGV) вместо честного FAILED.
        // Перебор пар 0..64, нарушения копим, одна паника в конце.
        let mut checked = 0;
        let mut violations: Vec<String> = Vec::new();
        for seed in SEEDS {
            for pair in 0..64u64 {
                let (la, ca, lb, cb) = run_pair(Cell::Erase, seed, pair);
                if la >= ERASE_STEP {
                    if (la, ca) != (lb, cb) {
                        violations.push(format!("seed {seed} pair {pair}: {la}/{lb}"));
                    }
                    checked += 1;
                }
            }
        }
        assert!(checked > 0, "no surviving pair in 3x64 sample; widen further");
        assert!(violations.is_empty(),
            "no collapse for {} pairs: {}", violations.len(), violations.join("; "));
    }

    #[test]
    fn erase221_keeps_pointwise_order() {
        // P3: частичное стирание сохраняет доминирование: дорост 0.06 >= 0.
        for seed in SEEDS {
            for pair in PAIRS {
                let (la, _ca, lb, _cb) = run_pair(Cell::EraseMid, seed, pair);
                assert!(la <= lb, "erase221 lifeA > lifeB at seed {seed} pair {pair}");
            }
        }
    }

    #[test]
    fn erase221_is_partial_and_regrows_to_expected() {
        // К 221 сделано 2 ремонта: стирается 0.24; дорост до 0.06 к шагу 500.
        let (arm_a, _) = match_phase(A_PRIMARY);
        let mut rng = Rng::new(SEED_BASE);
        let mut arm = Arm { ..arm_a };
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=221 {
            if t % 100 == 0 && budget > 0.0 {
                let want = REPAIR_REQUEST.min(budget).min(arm.d);
                arm.d -= want; arm.wear += want; budget -= want;
            }
            let _ = rng.uniform();
        }
        assert!((arm.wear - (A_PRIMARY + 2.0 * REPAIR_REQUEST)).abs() < 1e-9,
            "wear at 221 mismatch: {}", arm.wear);
        erase_wear(&mut arm);
        for t in 222..=500 {
            if t % 100 == 0 && budget > 0.0 {
                let want = REPAIR_REQUEST.min(budget).min(arm.d);
                arm.d -= want; arm.wear += want; budget -= want;
            }
            let _ = rng.uniform();
        }
        assert!((arm.wear - 3.0 * REPAIR_REQUEST).abs() < 1e-9,
            "regrowth to 500 mismatch: {}", arm.wear);
        assert_eq!(budget, 0.0);
    }

    #[test]
    fn sham_equals_base_byte() {
        // P4: ledger-метка без эффекта -- исходы идентичны base.
        for seed in SEEDS {
            for pair in PAIRS {
                let base = run_pair(Cell::Base, seed, pair);
                let sham = run_pair(Cell::Sham, seed, pair);
                assert_eq!(base, sham, "sham != base at seed {seed} pair {pair}");
                assert_eq!(ledger_t_erase(Cell::Sham, seed, pair), ERASE_STEP);
            }
        }
    }

    #[test]
    fn erand_collapses_paired_lives() {
        // P6: тот же коллапс при случайном из (seed,pair) моменте.
        // Момент равномерен в [600,1000), не сетка из 4 значений.
        let mut checked = 0;
        let mut violations: Vec<String> = Vec::new();
        for seed in SEEDS {
            for pair in 0..64u64 {
                let t_e = erase_step_for(Cell::Erand, seed, pair).unwrap();
                assert!((600..1000).contains(&t_e),
                    "erand moment out of range: {t_e}");
                let (la, ca, lb, cb) = run_pair(Cell::Erand, seed, pair);
                if la >= t_e {
                    if (la, ca) != (lb, cb) {
                        violations.push(format!(
                            "seed {seed} pair {pair} t {t_e}: {la}/{lb}"));
                    }
                    checked += 1;
                }
            }
        }
        assert!(checked > 0, "no surviving pair in 3x64 erand sample");
        assert!(violations.is_empty(),
            "erand no collapse for {} pairs: {}", violations.len(),
            violations.join("; "));
    }

    #[test]
    fn erase_preserves_q_d_energy() {
        // Интервенция трогает только носитель: (q, D, energy) не тронуты.
        let mut arm = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.25 };
        erase_wear(&mut arm);
        assert_eq!(arm.q, 0.5);
        assert_eq!(arm.d, 0.3);
        assert_eq!(arm.energy, 0.7);
        assert_eq!(arm.wear, 0.0);
    }

    #[test]
    fn wear_at_600_is_full_budget() {
        // К шагу 600 ремонтное окно закрыто: wear A = a + budget = 0.3 ровно.
        let (arm_a, _) = match_phase(A_PRIMARY);
        let mut rng = Rng::new(SEED_BASE);
        let mut arm = Arm { ..arm_a };
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=500 {
            if t % 100 == 0 && budget > 0.0 {
                let want = REPAIR_REQUEST.min(budget).min(arm.d);
                arm.d -= want; arm.wear += want; budget -= want;
            }
            let _ = rng.uniform();
        }
        assert_eq!(budget, 0.0, "budget not exhausted by step 500");
        assert!((arm.wear - (A_PRIMARY + REPAIR_BUDGET)).abs() < 1e-9,
            "wear at erase mismatch: {}", arm.wear);
        assert!(ERASE_STEP > 500, "erase must be after the repair window");
        assert!(ERASE_MID < 500, "erase-mid must be inside the repair window");
    }

    #[test]
    fn erand_moment_detached_from_state() {
        // Момент -- чистая функция (seed, pair): детерминизм, диапазон, и
        // СЛУЧАЙНОСТЬ (аудит: прежняя формула была сбалансированной сеткой).
        let mut moments = std::collections::HashSet::new();
        for seed in SEEDS {
            for pair in PAIRS {
                let t1 = erase_step_for(Cell::Erand, seed, pair).unwrap();
                let t2 = erase_step_for(Cell::Erand, seed, pair).unwrap();
                assert_eq!(t1, t2, "moment must be deterministic in (seed, pair)");
                assert!((600..1000).contains(&t1), "moment out of [600,1000): {t1}");
                moments.insert(t1);
            }
        }
        assert!(moments.len() > 4,
            "moments look like a fixed schedule: {moments:?}");
    }

    #[test]
    fn base_hazard_gap_carried_by_wear() {
        // При равных (q, D, energy) вся разница hazard -- износ: K_SCALAR * wear.
        let a = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.3 };
        let b = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.0 };
        assert!((hazard(&a) - hazard(&b) - K_SCALAR * 0.3).abs() < 1e-15,
            "hazard gap is not exactly K*wear");
    }
}
