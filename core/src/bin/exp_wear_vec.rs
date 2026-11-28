//! EXP-2026-4105 (мост FINDING-457 N2): вектор износа вместо скаляра.
//!
//! Протокол 457 (exp_dq4.rs, SUB-EXP-2026-4101-1): match-фаза выравнивает (q, D, energy)
//! обеих рук; A копит износ ремонтом a, B -- нет; challenge: +0.2 damage, ремонт по
//! расписанию (шаги 100..1000, request 0.02, budget 0.1), смерть при u < hazard =
//! mortality(q) + lambda*D + k(wear). Paired RNG: один поток на пару, обе руки.
//!
//! Предрегистрация 4105 (до прогона):
//! - Чувствительности компонентов k_j = (0.0005, 0.0010, 0.0015); K_SCALAR = 0.001
//!   как в первичной ячейке 457 (a=0.2).
//! - Профили pi (сумма 1): uniform (1/3,1/3,1/3); c1/c2/c3 -- весь износ на
//!   компоненте 1/2/3; mA..mF -- перестановки смешанного (1/2,1/3,1/6).
//!   k_eff(pi) = sum_j k_j*pi_j; слагаемые суммируются в каноническом порядке
//!   (по убыванию) -> вырожденные перестановки дают байт-равный k_eff.
//! - Сумма износа векторных плеч равна скаляру (sum pi = 1); рост износа в
//!   challenge идёт по тому же профилю pi. При фиксированном pi компоненты
//!   движутся lockstep, поэтому это векторное представление, но не независимая
//!   компонентная динамика; отдельная регрессия компонент не идентифицируется.
//! - Предсказания: (P1) c2 == scalar байт-в-байт (k_eff == K_SCALAR точно);
//!   (P2) lifeA: c3 <= scalar <= c1 на одном потоке (поточечное доминирование
//!   hazard); (P3) mB == mC и mD == mE байт-равны (вырожденность по k_eff);
//!   (P4) нулевые контроли silent/do-r0/r-clock/sham -- попарно идентичные
//!   исходы; (P5) порядок |dT90| монотонен по k_eff (анализ; primary-сиды
//!   5401..5412, deferred 5413..5420 -- только подтверждение, без настройки).
//! - Фальсификация: permutation не меняет прогноз -> память скалярна; векторная
//!   форма теряет силу -> износ не декомпозируется.

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
const A_PRIMARY: f64 = 0.2;

const K_SCALAR: f64 = 0.001;
const K_COMPONENTS: [f64; 3] = [0.0005, 0.0010, 0.0015];
const SEED_BASE: u64 = 5401;
const PRIMARY_SEEDS: usize = 12;
const DEFERRED_SEEDS: usize = 8;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Form { Scalar, Vector }

impl Form {
    fn label(self) -> &'static str { match self { Form::Scalar => "scalar", Form::Vector => "vector" } }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Control { Repair, Silent, DoR0, RClock, Sham }

impl Control {
    fn parse(s: &str) -> Option<Control> {
        match s {
            "repair" => Some(Control::Repair),
            "silent" => Some(Control::Silent),
            "do-r0" => Some(Control::DoR0),
            "r-clock" => Some(Control::RClock),
            "sham" => Some(Control::Sham),
            _ => None,
        }
    }
    fn label(self) -> &'static str {
        match self {
            Control::Repair => "repair",
            Control::Silent => "silent",
            Control::DoR0 => "do-r0",
            Control::RClock => "r-clock",
            Control::Sham => "sham",
        }
    }
}

/// Канонический k_eff: слагаемые по убыванию -> вырожденные профили байт-равны.
fn keff(profile: [f64; 3]) -> f64 {
    let mut t = [
        K_COMPONENTS[0] * profile[0],
        K_COMPONENTS[1] * profile[1],
        K_COMPONENTS[2] * profile[2],
    ];
    t.sort_by(|a, b| b.partial_cmp(a).unwrap());
    t[0] + t[1] + t[2]
}

/// Предрегистрированные профили распределения износа.
fn profiles() -> Vec<(&'static str, [f64; 3])> {
    let third = 1.0 / 3.0;
    let sixth = 1.0 / 6.0;
    vec![
        ("uniform", [third, third, third]),
        ("c1", [1.0, 0.0, 0.0]),
        ("c2", [0.0, 1.0, 0.0]),
        ("c3", [0.0, 0.0, 1.0]),
        ("mA", [0.5, third, sixth]),
        ("mB", [0.5, sixth, third]),
        ("mC", [third, 0.5, sixth]),
        ("mD", [third, sixth, 0.5]),
        ("mE", [sixth, 0.5, third]),
        ("mF", [sixth, third, 0.5]),
    ]
}

#[derive(Clone, Copy, PartialEq, Debug)]
enum Wear {
    Scalar(f64),
    Vector([f64; 3]),
}

impl Wear {
    fn zero(form: Form) -> Self {
        match form { Form::Scalar => Wear::Scalar(0.0), Form::Vector => Wear::Vector([0.0; 3]) }
    }

    fn total(self) -> f64 {
        match self {
            Wear::Scalar(v) => v,
            Wear::Vector(v) => v[0] + v[1] + v[2],
        }
    }

    fn add(&mut self, form: Form, profile: [f64; 3], amount: f64) {
        match (form, self) {
            (Form::Scalar, Wear::Scalar(v)) => *v += amount,
            (Form::Vector, Wear::Vector(v)) => {
                for j in 0..3 { v[j] += profile[j] * amount; }
            }
            _ => panic!("wear representation does not match form"),
        }
    }
}

struct Arm { q: f64, d: f64, energy: f64, wear: Wear }

fn vector_wear_hazard(wear: [f64; 3]) -> f64 {
    let mut terms = [
        K_COMPONENTS[0] * wear[0],
        K_COMPONENTS[1] * wear[1],
        K_COMPONENTS[2] * wear[2],
    ];
    // Канонический порядок делает перестановки профилей байт-равными.
    terms.sort_by(|a, b| b.partial_cmp(a).unwrap());
    terms[0] + terms[1] + terms[2]
}

fn wear_hazard(form: Form, wear: Wear, control: Control) -> f64 {
    match control {
        Control::Repair => match (form, wear) {
            (Form::Scalar, Wear::Scalar(v)) => K_SCALAR * v,
            (Form::Vector, Wear::Vector(v)) => vector_wear_hazard(v),
            _ => panic!("wear representation does not match form"),
        },
        // silent: механизм выключен (k_j не действуют), износ растёт как число
        Control::Silent => 0.0,
        // do(R=0): интервенция на носителе, износ растёт, в hazard не подан
        Control::DoR0 => 0.0,
        // r-clock: обеим рукам поданы часы 100 (векторная форма: (100,100,100))
        Control::RClock => match form {
            Form::Scalar => K_SCALAR * R_CLOCK,
            Form::Vector => (K_COMPONENTS[0] + K_COMPONENTS[1] + K_COMPONENTS[2]) * R_CLOCK,
        },
        // sham: cost-matched, износ не растёт и не подан
        Control::Sham => 0.0,
    }
}

/// Фаза выравнивания: A копит износ a одним ремонтом, B -- дрейфом. Обе руки
/// заканчивают ровно в (q, D, energy) = (0.5, 0.2, 0.8); износ A = a, B = 0.
fn match_phase(a: f64, form: Form, profile: [f64; 3]) -> (Arm, Arm) {
    let mut part = Part::new(Q_TARGET - a, 0.0, COST);
    let mut energy = 1.0;
    let mut repair_done = 0.0;
    for t in 1..=MATCH_STEPS {
        let u = if t == MATCH_STEPS { a } else { 0.0 };
        let done = part.step(u, 1.0, &mut energy);
        repair_done += done;
        assert!(done == 0.0 || t == MATCH_STEPS, "repair outside schedule");
    }
    let mut wear_a = Wear::zero(form);
    wear_a.add(form, profile, repair_done);
    let arm_a = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, wear: wear_a };
    let arm_b = Arm { q: Q_TARGET, d: D_TARGET, energy: ENERGY_TARGET, wear: Wear::zero(form) };
    (arm_a, arm_b)
}

fn hazard(arm: &Arm, form: Form, control: Control) -> f64 {
    mortality_with_floor(arm.q, RATE, P, FLOOR) + LAMBDA * arm.d + wear_hazard(form, arm.wear, control)
}

/// Challenge как в 457: +0.2 damage, ремонт по расписанию, смерть при u < hazard.
fn challenge(mut arm: Arm, form: Form, profile: [f64; 3], control: Control, rng: &mut Rng) -> (usize, bool) {
    arm.d += ADDED_DAMAGE;
    let mut budget = REPAIR_BUDGET;
    for t in 1..=HORIZON {
        if t % 100 == 0 && t <= 1000 && budget > 0.0 && arm.energy > 0.0 {
            let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
            if want > 0.0 {
                arm.energy -= want * COST;
                if control != Control::Sham {
                    arm.d -= want;
                    arm.wear.add(form, profile, want);
                }
                budget -= want;
            }
        }
        let u = rng.uniform();
        if u < hazard(&arm, form, control) {
            return (t, false);
        }
    }
    (HORIZON, true)
}

fn run_pair(a: f64, form: Form, profile: [f64; 3], control: Control, seed: u64, pair: u64) -> (usize, bool, usize, bool) {
    let (arm_a, arm_b) = match_phase(a, form, profile);
    let mut rng_a = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (la, ca) = challenge(arm_a, form, profile, control, &mut rng_a);
    let mut rng_b = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let (lb, cb) = challenge(arm_b, form, profile, control, &mut rng_b);
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
    println!("form,profile,control,k_eff,cohort,seed,pair,lifeA,censA,lifeB,censB");
    let profs = profiles();
    // 1) scalar-мост (457 первичная ячейка)
    for s in 0..(primary + deferred) {
        let seed = seed_base + s as u64;
        let cohort = if s < primary { "primary" } else { "deferred" };
        for p in 0..pairs {
            let (la, ca, lb, cb) = run_pair(A_PRIMARY, Form::Scalar, profs[0].1, Control::Repair, seed, p as u64);
            println!("scalar,scalar,repair,{:.7},{},{},{},{},{},{},{}",
                K_SCALAR, cohort, seed, p, la, ca as u8, lb, cb as u8);
        }
    }
    // 2) векторные профили, repair
    for (name, prof) in &profs {
        for s in 0..(primary + deferred) {
            let seed = seed_base + s as u64;
            let cohort = if s < primary { "primary" } else { "deferred" };
            for p in 0..pairs {
                let (la, ca, lb, cb) = run_pair(A_PRIMARY, Form::Vector, *prof, Control::Repair, seed, p as u64);
                println!("vector,{},{},{:.7},{},{},{},{},{},{},{}",
                    name, "repair", keff(*prof), cohort, seed, p, la, ca as u8, lb, cb as u8);
            }
        }
    }
    // 3) нулевые контроли на uniform
    for control in [Control::Silent, Control::DoR0, Control::RClock, Control::Sham] {
        for s in 0..(primary + deferred) {
            let seed = seed_base + s as u64;
            let cohort = if s < primary { "primary" } else { "deferred" };
            for p in 0..pairs {
                let (la, ca, lb, cb) = run_pair(A_PRIMARY, Form::Vector, profs[0].1, control, seed, p as u64);
                println!("vector,uniform,{},{:.7},{},{},{},{},{},{},{}",
                    control.label(), keff(profs[0].1), cohort, seed, p, la, ca as u8, lb, cb as u8);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn prof(name: &str) -> [f64; 3] {
        profiles().into_iter().find(|(n, _)| *n == name).unwrap().1
    }

    #[test]
    fn keff_c2_equals_scalar_exactly() {
        assert!(keff(prof("c2")) == K_SCALAR, "k_eff(c2) != K_SCALAR");
        assert!((keff(prof("uniform")) - K_SCALAR).abs() < 1e-15, "uniform k_eff far from scalar");
    }

    #[test]
    fn keff_ordering_and_degeneracies() {
        let (c1, ma, mb, mc) = (keff(prof("c1")), keff(prof("mA")), keff(prof("mB")), keff(prof("mC")));
        let (c2, md, me, mf, c3) = (keff(prof("c2")), keff(prof("mD")), keff(prof("mE")), keff(prof("mF")), keff(prof("c3")));
        assert!(c1 < ma && ma < mb, "c1<ma<mb failed");
        assert!(mb == mc, "mB != mC");
        assert!(mc < c2, "mC >= c2");
        assert!(c2 < md, "c2 >= mD");
        assert!(md == me, "mD != mE");
        assert!(me < mf && mf < c3, "mE<mf<c3 failed");
    }

    #[test]
    fn c2_lifetimes_equal_scalar() {
        for seed in [SEED_BASE, SEED_BASE + 3, SEED_BASE + 7] {
            for pair in [0_u64, 17, 199] {
                let sc = run_pair(A_PRIMARY, Form::Scalar, prof("uniform"), Control::Repair, seed, pair);
                let c2 = run_pair(A_PRIMARY, Form::Vector, prof("c2"), Control::Repair, seed, pair);
                assert_eq!((sc.0, sc.1, sc.2, sc.3), (c2.0, c2.1, c2.2, c2.3),
                    "c2 != scalar at seed {seed} pair {pair}");
            }
        }
    }

    #[test]
    fn pointwise_death_order_c3_scalar_c1() {
        for seed in [SEED_BASE, SEED_BASE + 5] {
            for pair in [0_u64, 42, 137] {
                let c3 = run_pair(A_PRIMARY, Form::Vector, prof("c3"), Control::Repair, seed, pair);
                let sc = run_pair(A_PRIMARY, Form::Scalar, prof("uniform"), Control::Repair, seed, pair);
                let c1 = run_pair(A_PRIMARY, Form::Vector, prof("c1"), Control::Repair, seed, pair);
                assert!(c3.0 <= sc.0 && sc.0 <= c1.0, "lifeA order violated: {} {} {} (seed {seed} pair {pair})", c3.0, sc.0, c1.0);
                assert!(sc.2 == c1.2 && c1.2 == c3.2, "lifeB differs across profiles");
            }
        }
    }

    #[test]
    fn degenerate_permutations_byte_equal() {
        for seed in [SEED_BASE, SEED_BASE + 2] {
            for pair in [0_u64, 91] {
                let mb = run_pair(A_PRIMARY, Form::Vector, prof("mB"), Control::Repair, seed, pair);
                let mc = run_pair(A_PRIMARY, Form::Vector, prof("mC"), Control::Repair, seed, pair);
                assert_eq!((mb.0, mb.1, mb.2, mb.3), (mc.0, mc.1, mc.2, mc.3), "mB != mC lifetimes");
                let md = run_pair(A_PRIMARY, Form::Vector, prof("mD"), Control::Repair, seed, pair);
                let me = run_pair(A_PRIMARY, Form::Vector, prof("mE"), Control::Repair, seed, pair);
                assert_eq!((md.0, md.1, md.2, md.3), (me.0, me.1, me.2, me.3), "mD != mE lifetimes");
            }
        }
    }

    #[test]
    fn null_controls_paired_identical() {
        for control in [Control::Silent, Control::DoR0, Control::RClock, Control::Sham] {
            for seed in [SEED_BASE + 1, SEED_BASE + 4] {
                let (la, ca, lb, cb) = run_pair(A_PRIMARY, Form::Vector, prof("uniform"), control, seed, 7);
                assert_eq!((la, ca), (lb, cb), "control {} not paired-identical", control.label());
            }
        }
    }

    #[test]
    fn do_r0_collapses_profile_differences() {
        // Интервенция do(R=0) убирает различие профилей: lifeA(c1) == lifeA(c3) == scalar.
        for seed in [SEED_BASE + 6, SEED_BASE + 9] {
            for pair in [0_u64, 23] {
                let c1 = run_pair(A_PRIMARY, Form::Vector, prof("c1"), Control::DoR0, seed, pair);
                let c3 = run_pair(A_PRIMARY, Form::Vector, prof("c3"), Control::DoR0, seed, pair);
                let sc = run_pair(A_PRIMARY, Form::Scalar, prof("uniform"), Control::DoR0, seed, pair);
                assert_eq!(c1.0, c3.0, "do-r0 c1 != c3");
                assert_eq!(c1.0, sc.0, "do-r0 c1 != scalar");
            }
        }
    }

    #[test]
    fn wear_sum_consistent_across_forms() {
        // Сумма износа A после challenge не зависит от формы/профиля (одинаковое расписание).
        let (arm_a, _) = match_phase(A_PRIMARY, Form::Vector, prof("uniform"));
        let mut rng = Rng::new(SEED_BASE);
        let mut arm = Arm { ..arm_a };
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=1000 {
            if t % 100 == 0 && budget > 0.0 {
                let want = REPAIR_REQUEST.min(budget).min(arm.d).min(arm.energy / COST);
                arm.d -= want; arm.energy -= want * COST;
                arm.wear.add(Form::Vector, prof("uniform"), want);
                budget -= want;
            }
            let _ = rng.uniform();
        }
        assert!((arm.wear.total() - (A_PRIMARY + REPAIR_BUDGET)).abs() < 1e-9,
            "wear sum mismatch: {}", arm.wear.total());
    }

    #[test]
    fn vector_wear_is_a_component_state_and_hazard_is_its_dot_product() {
        let profile = prof("mA");
        let (arm, _) = match_phase(A_PRIMARY, Form::Vector, profile);
        let Wear::Vector(components) = arm.wear else { panic!("vector arm must store components") };
        for j in 0..3 {
            assert!((components[j] - A_PRIMARY * profile[j]).abs() < 1e-15);
        }
        assert!((components[0] + components[1] + components[2] - A_PRIMARY).abs() < 1e-15);

        let c1 = wear_hazard(Form::Vector, Wear::Vector([0.2, 0.0, 0.0]), Control::Repair);
        let c2 = wear_hazard(Form::Vector, Wear::Vector([0.0, 0.2, 0.0]), Control::Repair);
        let scalar = wear_hazard(Form::Scalar, Wear::Scalar(0.2), Control::Repair);
        assert_ne!(c1, c2, "equal total wear in different components must not alias");
        assert_eq!(c2.to_bits(), scalar.to_bits(), "c2 must remain the exact scalar bridge");

        let (mb, _) = match_phase(A_PRIMARY, Form::Vector, prof("mB"));
        let (mc, _) = match_phase(A_PRIMARY, Form::Vector, prof("mC"));
        assert_eq!(wear_hazard(Form::Vector, mb.wear, Control::Repair).to_bits(),
            wear_hazard(Form::Vector, mc.wear, Control::Repair).to_bits(),
            "canonical summation must preserve permutation degeneracy");
    }
}
