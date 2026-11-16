//! The exit rule declared in `docs/FINDING-161.md`: a `Memory` organism may
//! look out of turn when the cell underfoot cannot pay the upkeep.
//!
//! The rule is a `World` switch, `look_on_shortfall`, off by default. These
//! tests pin the three things that make it a policy rather than a tweak:
//!
//! * off changes neither the behaviour nor the hash (`FINDING-161` says the
//!   wording was declared before the run, so the off position is the old run);
//! * on a **poor** cell the rule reads more, and the extra reads are counted
//!   by the energy they cost, not by the intent;
//! * on a **rich** cell the rule does not fire, so the schedule is untouched.
//!
//! `Sighted` is deliberately not covered: it has no memory to fall back on, so
//! "look out of turn" is meaningless for it.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{LookOrder, ShareProtocol, TieBreak, World};
use medium_core::trace::{record, Trace};

/// A world where the only things that move energy are the read price and the
/// maintenance: no income, no damage, no repair, no movement cost, no births.
/// Any difference between two such worlds is therefore the price of looking.
fn quiet(read_cost: f64, read_period: usize, look_on_shortfall: bool) -> World {
    World {
        income: 0.0,
        maintenance_cost: 0.6,
        repair_cost: 0.0,
        damage_rate: 0.0,
        capacity: 100.0,
        read_budget: 3,
        read_cost,
        read_period,
        look_on_shortfall,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        birth_threshold: f64::INFINITY,
        birth_cost: 0.0,
        max_population: 0,
    }
}

/// The energy of the only organism after `steps` steps.
fn energy_after(world: World, field: Field, start: usize, steps: usize) -> f64 {
    let mut life =
        Life::spawn_at(world, field, &[start], 20.0, 0.0, Policy::Memory, 7, 300).unwrap();
    for _ in 0..steps {
        life.advance();
    }
    life.samples()[0].energy
}

#[test]
fn the_switch_is_off_by_default_and_adds_nothing_to_the_hash() {
    assert!(
        !World::default().look_on_shortfall,
        "the rule must be off unless asked for, or every recorded run moves"
    );

    let field = Field::peaks(20, 2.0, 0.2, 0.8, 4).unwrap();
    let mut life = Life::spawn_at(
        quiet(0.05, 4, false),
        field,
        &[5],
        5.0,
        0.1,
        Policy::Memory,
        11,
        300,
    )
    .unwrap();
    let trace = record(&mut life, 40, 1);

    let before = Trace::hash_with_world(&trace.frames, "sequential", "left", "look-then-eat");
    let off = Trace::hash_with_births(
        &trace.frames,
        "sequential",
        "left",
        "look-then-eat",
        0,
        f64::INFINITY,
        0.0,
        0.0,
        1,
        false,
    );
    let on = Trace::hash_with_births(
        &trace.frames,
        "sequential",
        "left",
        "look-then-eat",
        0,
        f64::INFINITY,
        0.0,
        0.0,
        1,
        true,
    );
    assert_eq!(before, off, "look_on_shortfall = false moved the hash");
    assert_ne!(before, on, "the switch must not collide with the old schedule");
}

#[test]
fn a_poor_cell_makes_memory_look_out_of_turn() {
    // Every cell holds 0.4 and the upkeep is 0.6, so the rule fires on every
    // step. The own cell is free; each sample reads two neighbours at 1.0.
    // Off: samples at steps 0 and 4 of six -> 4 reads. On: six samples -> 12
    // reads. Maintenance is the same 0.6 per step on both arms, so the energy
    // difference is exactly the 8 extra reads.
    let poor = || Field::new(24, 0.4, 0.8).unwrap();
    let off = energy_after(quiet(1.0, 4, false), poor(), 12, 6);
    let on = energy_after(quiet(1.0, 4, true), poor(), 12, 6);

    assert!(on < off, "looking out of turn must cost the extra look: {off} vs {on}");
    let extra_reads = off - on;
    assert!(
        (extra_reads - 8.0).abs() < 1e-9,
        "expected 8 extra neighbour reads (4 samples x 2), got {extra_reads}"
    );
}

#[test]
fn a_rich_cell_keeps_the_schedule_and_the_hash() {
    // The level is 5.0 against an upkeep of 0.6, so `needs_look` is false on
    // every step and the flag cannot change anything -- not even one bit.
    let rich = || Field::new(24, 5.0, 0.8).unwrap();
    let off = energy_after(quiet(1.0, 4, false), rich(), 12, 6);
    let on = energy_after(quiet(1.0, 4, true), rich(), 12, 6);
    assert!(
        (off - on).abs() < 1e-12,
        "a rich cell must not make the rule fire: {off} vs {on}"
    );

    // A uniform field at 5.0: every cell is rich, so the two arms must agree
    // frame for frame as well as in the hash.
    let field = || Field::new(20, 5.0, 0.8).unwrap();
    let mut a = Life::spawn_at(
        quiet(0.05, 4, false),
        field(),
        &[3],
        5.0,
        0.1,
        Policy::Memory,
        5,
        300,
    )
    .unwrap();
    let mut b = Life::spawn_at(
        quiet(0.05, 4, true),
        field(),
        &[3],
        5.0,
        0.1,
        Policy::Memory,
        5,
        300,
    )
    .unwrap();
    // The full trace hash intentionally differs when the switch is true:
    // the parameter is folded in so two experiments cannot collide. What
    // must not move is the behaviour itself, so the frames are compared.
    assert_eq!(
        record(&mut a, 40, 1).frames,
        record(&mut b, 40, 1).frames,
        "a rich cell must leave every frame untouched"
    );
}
