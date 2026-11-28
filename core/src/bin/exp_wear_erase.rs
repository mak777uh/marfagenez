//! EXP-2026-4106: causal midlife erasure of repair wear.
//!
//! The match phase aligns (q, D, energy) = (0.5, 0.2, 0.8). Arm A carries
//! repair wear 0.2 and arm B carries none. During challenge both arms receive
//! the same damage, repair schedule and paired random numbers.
//!
//! Registered cells: base, erase600, erase221, sham600, erand and silent.
//! Erasure changes only wear. The silent cell removes the wear term from the
//! hazard and is the mechanism-off control. The sham cell records the event
//! without changing wear.
//!
//! P3 (erase221 - base DeltaT90) is the sole primary scientific contrast.
//! P1/P4/silent/ledger are instrument gates. P6 is a landmark description:
//! survival to erasure and collapse given erasure are reported separately.

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

pub const CSV_HEADER: &str = "cell,cohort,seed,pair,t_erase,event_status,applied,wearA_before,wearA_after,wearB_before,wearB_after,qA_event,dA_event,eA_event,qB_event,dB_event,eB_event,state_hash,lifeA,censA,lifeB,censB";

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Cell {
    Base,
    Erase,
    EraseMid,
    Sham,
    Erand,
    Silent,
}

impl Cell {
    const ALL: [Cell; 6] = [
        Cell::Base,
        Cell::Erase,
        Cell::EraseMid,
        Cell::Sham,
        Cell::Erand,
        Cell::Silent,
    ];

    fn label(self) -> &'static str {
        match self {
            Cell::Base => "base",
            Cell::Erase => "erase600",
            Cell::EraseMid => "erase221",
            Cell::Sham => "sham600",
            Cell::Erand => "erand",
            Cell::Silent => "silent",
        }
    }

    fn wear_hazard_enabled(self) -> bool {
        self != Cell::Silent
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum EventStatus {
    Applied,
    Sham,
    NotScheduled,
    NotDueDeath,
    Horizon,
}

impl EventStatus {
    fn label(self) -> &'static str {
        match self {
            EventStatus::Applied => "applied",
            EventStatus::Sham => "sham",
            EventStatus::NotScheduled => "not_scheduled",
            EventStatus::NotDueDeath => "not_due_death",
            EventStatus::Horizon => "horizon",
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct Arm {
    q: f64,
    d: f64,
    energy: f64,
    wear: f64,
}

#[derive(Clone, Copy, Debug)]
struct EventRecord {
    status: EventStatus,
    t_erase: usize,
    applied: bool,
    wear_a_before: f64,
    wear_a_after: f64,
    wear_b_before: f64,
    wear_b_after: f64,
    arm_a: Arm,
    arm_b: Arm,
    state_hash: u64,
}

#[derive(Clone, Copy, Debug)]
struct PairRecord {
    life_a: usize,
    cens_a: bool,
    life_b: usize,
    cens_b: bool,
    event: EventRecord,
}

/// Scheduled erasure time. Sham has a ledger marker but no erasure branch.
fn erase_step_for(cell: Cell, seed: u64, pair: u64) -> Option<usize> {
    match cell {
        Cell::Base | Cell::Silent => None,
        Cell::Erase => Some(ERASE_STEP),
        Cell::EraseMid => Some(ERASE_MID),
        Cell::Sham => Some(ERASE_STEP),
        Cell::Erand => Some(erandom_moment(seed, pair)),
    }
}

/// Deterministic pseudo-random moment from a stream separate from simulation.
fn erandom_moment(seed: u64, pair: u64) -> usize {
    let mut m = Rng::new(seed ^ 0x5EED_BEEF ^ pair.wrapping_mul(0x9E37_79B9_7F4A_7C15));
    600 + (m.uniform() * 400.0) as usize
}

fn ledger_t_erase(cell: Cell, seed: u64, pair: u64) -> usize {
    erase_step_for(cell, seed, pair).unwrap_or(0)
}

/// External do-operation: only wear changes; q, D and energy are untouched.
fn erase_wear(arm: &mut Arm) {
    arm.wear = 0.0;
}

/// Match phase from FINDING-457. Both arms end at exactly the same q/D/energy.
fn match_phase(a: f64) -> (Arm, Arm) {
    let mut part = Part::new(Q_TARGET - a, 0.0, COST);
    let mut energy = 1.0;
    for t in 1..=MATCH_STEPS {
        let u = if t == MATCH_STEPS { a } else { 0.0 };
        let done = part.step(u, 1.0, &mut energy);
        assert!(done == 0.0 || t == MATCH_STEPS, "repair outside schedule");
    }
    let wear_a = a;
    (
        Arm {
            q: Q_TARGET,
            d: D_TARGET,
            energy: ENERGY_TARGET,
            wear: wear_a,
        },
        Arm {
            q: Q_TARGET,
            d: D_TARGET,
            energy: ENERGY_TARGET,
            wear: 0.0,
        },
    )
}

fn hazard(arm: &Arm, wear_hazard_enabled: bool) -> f64 {
    mortality_with_floor(arm.q, RATE, P, FLOOR)
        + LAMBDA * arm.d
        + if wear_hazard_enabled {
            K_SCALAR * arm.wear
        } else {
            0.0
        }
}

fn repair_if_due(arm: &mut Arm, t: usize, budget: &mut f64) {
    if t % 100 == 0 && t <= 1000 && *budget > 0.0 && arm.energy > 0.0 {
        let want = REPAIR_REQUEST
            .min(*budget)
            .min(arm.d)
            .min(arm.energy / COST);
        if want > 0.0 {
            arm.energy -= want * COST;
            arm.d -= want;
            arm.wear += want;
            *budget -= want;
        }
    }
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

/// Hash the complete event state of both arms from raw f64 bits.
fn state_hash(a: Arm, b: Arm) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325;
    for value in [a.q, a.d, a.energy, a.wear, b.q, b.d, b.energy, b.wear] {
        hash_f64(&mut hash, value);
    }
    hash
}

fn event_record(
    status: EventStatus,
    t_erase: usize,
    applied: bool,
    wear_a_before: f64,
    wear_a_after: f64,
    wear_b_before: f64,
    wear_b_after: f64,
    arm_a: Arm,
    arm_b: Arm,
) -> EventRecord {
    EventRecord {
        status,
        t_erase,
        applied,
        wear_a_before,
        wear_a_after,
        wear_b_before,
        wear_b_after,
        arm_a,
        arm_b,
        state_hash: state_hash(arm_a, arm_b),
    }
}

/// Run one paired challenge in lockstep so the ledger snapshots both arms at
/// the same event/landmark, including when one arm dies first.
fn run_pair_full(cell: Cell, seed: u64, pair: u64) -> PairRecord {
    let (mut arm_a, mut arm_b) = match_phase(A_PRIMARY);
    arm_a.d += ADDED_DAMAGE;
    arm_b.d += ADDED_DAMAGE;
    let initial_a = arm_a;
    let initial_b = arm_b;
    let erase_at = erase_step_for(cell, seed, pair);
    let t_erase = ledger_t_erase(cell, seed, pair);
    let wear_hazard_enabled = cell.wear_hazard_enabled();
    let mut rng_a = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let mut rng_b = Rng::new(seed.wrapping_mul(1_000_003).wrapping_add(pair));
    let mut budget_a = REPAIR_BUDGET;
    let mut budget_b = REPAIR_BUDGET;
    let mut alive_a = true;
    let mut alive_b = true;
    let mut life_a = HORIZON;
    let mut life_b = HORIZON;
    let mut cens_a = true;
    let mut cens_b = true;
    let mut event: Option<EventRecord> = None;

    for t in 1..=HORIZON {
        if alive_a {
            repair_if_due(&mut arm_a, t, &mut budget_a);
        }
        if alive_b {
            repair_if_due(&mut arm_b, t, &mut budget_b);
        }

        if event.is_none() && erase_at == Some(t) {
            let before_a = arm_a;
            let before_b = arm_b;
            if cell != Cell::Sham {
                if alive_a {
                    erase_wear(&mut arm_a);
                }
                if alive_b {
                    erase_wear(&mut arm_b);
                }
            }
            event = Some(event_record(
                if cell == Cell::Sham {
                    EventStatus::Sham
                } else {
                    EventStatus::Applied
                },
                t_erase,
                cell != Cell::Sham,
                before_a.wear,
                arm_a.wear,
                before_b.wear,
                arm_b.wear,
                arm_a,
                arm_b,
            ));
        }

        let death_a = alive_a && rng_a.uniform() < hazard(&arm_a, wear_hazard_enabled);
        let death_b = alive_b && rng_b.uniform() < hazard(&arm_b, wear_hazard_enabled);
        if death_a {
            alive_a = false;
            life_a = t;
            cens_a = false;
        }
        if death_b {
            alive_b = false;
            life_b = t;
            cens_b = false;
        }

        if event.is_none() && erase_at.is_some() && (death_a || death_b) {
            event = Some(event_record(
                EventStatus::NotDueDeath,
                t_erase,
                false,
                arm_a.wear,
                arm_a.wear,
                arm_b.wear,
                arm_b.wear,
                arm_a,
                arm_b,
            ));
        }
        if !alive_a && !alive_b {
            break;
        }
    }

    let event = event.unwrap_or_else(|| {
        event_record(
            if erase_at.is_some() {
                EventStatus::Horizon
            } else {
                EventStatus::NotScheduled
            },
            t_erase,
            false,
            initial_a.wear,
            initial_a.wear,
            initial_b.wear,
            initial_b.wear,
            initial_a,
            initial_b,
        )
    });

    PairRecord {
        life_a,
        cens_a,
        life_b,
        cens_b,
        event,
    }
}

#[cfg(test)]
fn run_pair(cell: Cell, seed: u64, pair: u64) -> (usize, bool, usize, bool) {
    let out = run_pair_full(cell, seed, pair);
    (out.life_a, out.cens_a, out.life_b, out.cens_b)
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
            "--seeds" => {
                i += 1;
                primary = args[i].parse().unwrap();
            }
            "--deferred" => {
                i += 1;
                deferred = args[i].parse().unwrap();
            }
            "--seed-base" => {
                i += 1;
                seed_base = args[i].parse().unwrap();
            }
            "--pairs" => {
                i += 1;
                pairs = args[i].parse().unwrap();
            }
            other => {
                eprintln!("unknown arg: {other}");
                std::process::exit(2);
            }
        }
        i += 1;
    }

    println!("{CSV_HEADER}");
    for cell in Cell::ALL {
        for s in 0..(primary + deferred) {
            let seed = seed_base + s as u64;
            let cohort = if s < primary { "primary" } else { "deferred" };
            for p in 0..pairs {
                let out = run_pair_full(cell, seed, p as u64);
                let e = out.event;
                println!(
                    "{cell},{cohort},{seed},{pair},{t_erase},{status},{applied},{wear_a_before},{wear_a_after},{wear_b_before},{wear_b_after},{q_a},{d_a},{e_a},{q_b},{d_b},{e_b},{state_hash:016x},{life_a},{cens_a},{life_b},{cens_b}",
                    cell = cell.label(),
                    cohort = cohort,
                    seed = seed,
                    pair = p,
                    t_erase = e.t_erase,
                    status = e.status.label(),
                    applied = e.applied as u8,
                    wear_a_before = e.wear_a_before,
                    wear_a_after = e.wear_a_after,
                    wear_b_before = e.wear_b_before,
                    wear_b_after = e.wear_b_after,
                    q_a = e.arm_a.q,
                    d_a = e.arm_a.d,
                    e_a = e.arm_a.energy,
                    q_b = e.arm_b.q,
                    d_b = e.arm_b.d,
                    e_b = e.arm_b.energy,
                    state_hash = e.state_hash,
                    life_a = out.life_a,
                    cens_a = out.cens_a as u8,
                    life_b = out.life_b,
                    cens_b = out.cens_b as u8,
                );
            }
        }
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

    const SEEDS: [u64; 3] = [SEED_BASE, SEED_BASE + 3, SEED_BASE + 7];
    const PAIRS: [u64; 3] = [0, 17, 137];

    #[test]
    fn base_pointwise_life_a_le_life_b() {
        for seed in SEEDS {
            for pair in PAIRS {
                let (la, _ca, lb, _cb) = run_pair(Cell::Base, seed, pair);
                assert!(la <= lb, "base lifeA > lifeB at {seed}/{pair}: {la} > {lb}");
            }
        }
    }

    #[test]
    fn silent_mechanism_off_is_exactly_paired() {
        for seed in SEEDS {
            for pair in PAIRS {
                let (la, ca, lb, cb) = run_pair(Cell::Silent, seed, pair);
                assert_eq!((la, ca), (lb, cb), "silent wear term changed future at {seed}/{pair}");
            }
        }
    }

    #[test]
    fn unscheduled_cells_never_claim_a_death_event() {
        for cell in [Cell::Base, Cell::Silent] {
            for seed in SEEDS {
                for pair in PAIRS {
                    let out = run_pair_full(cell, seed, pair);
                    assert_eq!(out.event.status, EventStatus::NotScheduled);
                    assert!(!out.event.applied);
                    assert_eq!(out.event.t_erase, 0);
                }
            }
        }
    }

    #[test]
    fn erase600_collapses_paired_lives() {
        let mut checked = 0;
        let mut violations = Vec::new();
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
        assert!(checked > 0, "no surviving pair in 3x64 sample");
        assert!(violations.is_empty(), "no collapse: {}", violations.join("; "));
    }

    #[test]
    fn erase221_keeps_pointwise_order() {
        for seed in SEEDS {
            for pair in PAIRS {
                let (la, _ca, lb, _cb) = run_pair(Cell::EraseMid, seed, pair);
                assert!(la <= lb, "erase221 lifeA > lifeB at {seed}/{pair}");
            }
        }
    }

    #[test]
    fn erase221_is_partial_and_regrows_to_expected() {
        let (mut arm, _) = match_phase(A_PRIMARY);
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=221 {
            repair_if_due(&mut arm, t, &mut budget);
        }
        assert!((arm.wear - (A_PRIMARY + 2.0 * REPAIR_REQUEST)).abs() < 1e-12);
        erase_wear(&mut arm);
        for t in 222..=500 {
            repair_if_due(&mut arm, t, &mut budget);
        }
        assert!((arm.wear - 3.0 * REPAIR_REQUEST).abs() < 1e-12);
        assert_eq!(budget, 0.0);
    }

    #[test]
    fn sham_equals_base_outcomes_and_records_real_wear() {
        for seed in SEEDS {
            for pair in PAIRS {
                assert_eq!(run_pair(Cell::Base, seed, pair), run_pair(Cell::Sham, seed, pair));
                let sham = run_pair_full(Cell::Sham, seed, pair);
                if sham.event.status == EventStatus::Sham {
                    assert_eq!(sham.event.wear_a_before, sham.event.wear_a_after);
                    assert!(sham.event.wear_a_before > 0.0);
                }
            }
        }
    }

    #[test]
    fn erand_collapses_only_given_survival_to_event() {
        let mut checked = 0;
        let mut violations = Vec::new();
        for seed in SEEDS {
            for pair in 0..64u64 {
                let t_e = erase_step_for(Cell::Erand, seed, pair).unwrap();
                assert!((600..1000).contains(&t_e));
                let (la, ca, lb, cb) = run_pair(Cell::Erand, seed, pair);
                if la >= t_e {
                    if (la, ca) != (lb, cb) {
                        violations.push(format!("seed {seed} pair {pair} t {t_e}: {la}/{lb}"));
                    }
                    checked += 1;
                }
            }
        }
        assert!(checked > 0, "no surviving pair in 3x64 erand sample");
        assert!(violations.is_empty(), "erand no collapse: {}", violations.join("; "));
    }

    #[test]
    fn erase_preserves_q_d_energy_and_ledger_is_complete() {
        let mut arm = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.25 };
        erase_wear(&mut arm);
        assert_eq!(arm.q, 0.5);
        assert_eq!(arm.d, 0.3);
        assert_eq!(arm.energy, 0.7);
        assert_eq!(arm.wear, 0.0);

        for seed in SEEDS {
            for pair in 0..64u64 {
                let out = run_pair_full(Cell::Erase, seed, pair);
                if out.event.status == EventStatus::Applied {
                    assert_eq!(out.event.wear_a_after, 0.0);
                    assert_eq!(out.event.arm_a.q, out.event.arm_b.q);
                    assert_eq!(out.event.arm_a.d, out.event.arm_b.d);
                    assert_eq!(out.event.arm_a.energy, out.event.arm_b.energy);
                    assert_ne!(out.event.state_hash, 0);
                }
            }
        }
    }

    #[test]
    fn wear_at_600_is_full_budget() {
        let (mut arm, _) = match_phase(A_PRIMARY);
        arm.d += ADDED_DAMAGE;
        let mut budget = REPAIR_BUDGET;
        for t in 1..=500 {
            repair_if_due(&mut arm, t, &mut budget);
        }
        assert_eq!(budget, 0.0);
        assert!((arm.wear - (A_PRIMARY + REPAIR_BUDGET)).abs() < 1e-12);
        assert!(ERASE_STEP > 500);
        assert!(ERASE_MID < 500);
    }

    #[test]
    fn erand_moment_detached_from_state() {
        let mut moments = std::collections::HashSet::new();
        for seed in SEEDS {
            for pair in PAIRS {
                let t1 = erase_step_for(Cell::Erand, seed, pair).unwrap();
                let t2 = erase_step_for(Cell::Erand, seed, pair).unwrap();
                assert_eq!(t1, t2);
                assert!((600..1000).contains(&t1));
                moments.insert(t1);
            }
        }
        assert!(moments.len() > 4, "moments look like a fixed schedule: {moments:?}");
    }

    #[test]
    fn hazard_gap_is_exactly_the_wear_term() {
        let a = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.3 };
        let b = Arm { q: 0.5, d: 0.3, energy: 0.7, wear: 0.0 };
        assert!((hazard(&a, true) - hazard(&b, true) - K_SCALAR * 0.3).abs() < 1e-15);
        assert_eq!(hazard(&a, false), hazard(&b, false));
    }
}
