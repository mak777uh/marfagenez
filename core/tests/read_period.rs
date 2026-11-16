//! `World::read_period`: a `Memory` organism may skip a look.
//!
//! FINDING-156 ended on one sentence: "the memory in this implementation does
//! not replace perception -- it reads the same two neighbours `sighted` reads,
//! so the price of a look falls on both equally". `read_period` is the model
//! change that gives the memory something to replace: a remembering organism
//! samples the world every `read_period`-th step and acts on the memory in
//! between, paying neither a read nor `read_cost`.
//!
//! The contract under test:
//!
//! * `read_period = 1` is "look every step" and changes nothing: not one frame,
//!   not one bit of the hash;
//! * `read_period > 1` reads about four times less at 4, and the paid bill
//!   shrinks with it;
//! * `0` is refused: that switch is `read_budget = 0`, which means something
//!   else.
//!
//! `Sighted` is deliberately not periodic (it has no memory to act on). One
//! test pins that its frames do not move when the period is set.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;
use medium_core::trace::{record, Trace};

/// A world where the only thing that moves energy is a **neighbour** read: no
/// income, no maintenance, no damage, no movement cost. The own cell read costs
/// a look from the budget but never energy, so every joule missing from the
/// reserve is a look at a neighbour.
fn quiet(read_cost: f64, read_period: usize) -> World {
    World {
        income: 0.0,
        maintenance_cost: 0.0,
        repair_cost: 0.0,
        damage_rate: 0.0,
        capacity: 1_000.0,
        read_budget: 3,
        read_cost,
        read_period,
        ..World::default()
    }
}

/// How many neighbour reads a `Memory` organism made in `steps` steps, read off
/// the energy it paid at `read_cost = 0.05`.
fn neighbour_reads(period: usize, steps: usize) -> f64 {
    let field = Field::alternating(40, 2.0, 0.2, 0.0).unwrap();
    let mut life = Life::spawn_at(
        quiet(0.05, period),
        field,
        &[12],
        100.0,
        0.0,
        Policy::Memory,
        5,
        1_000,
    )
    .unwrap();
    for _ in 0..steps {
        life.advance();
    }
    let spent = 100.0 - life.samples()[0].energy;
    spent / 0.05
}

#[test]
fn a_period_of_one_changes_nothing_in_the_hash() {
    // The hash rule: the period is appended only above 1, so at 1 the hash is
    // the one `hash_with_world` produced before the field existed. This is the
    // same contract `read_cost = 0.0` and the birth switch follow.
    let field = Field::alternating(20, 2.0, 0.2, 0.8).unwrap();
    let mut life = Life::spawn_at(
        quiet(0.0, 1),
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
    let with_one = Trace::hash_with_births(
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
    let with_four = Trace::hash_with_births(
        &trace.frames,
        "sequential",
        "left",
        "look-then-eat",
        0,
        f64::INFINITY,
        0.0,
        0.0,
        4,
        false,
    );
    assert_eq!(before, with_one, "read_period = 1 moved the hash");
    assert_ne!(
        before, with_four,
        "a sampling period must not collide with looking every step"
    );
}

#[test]
fn a_period_of_four_reads_about_four_times_less() {
    // 12 sampled steps x 2 neighbours = 24 reads at period 1; at period 4 the
    // samples are steps 0, 4 and 8 (three of them), so 6 reads. The start is
    // cell 12 of 40, so no sample is taken at the edge where one neighbour is
    // missing and the count would be less clean.
    let one = neighbour_reads(1, 12);
    let four = neighbour_reads(4, 12);
    assert!((one - 24.0).abs() < 1e-9, "period 1 read {one} neighbours");
    assert!((four - 6.0).abs() < 1e-9, "period 4 read {four} neighbours");
    assert!(
        (one / four - 4.0).abs() < 1e-9,
        "the ratio must be the period: {one} / {four}"
    );
}

#[test]
fn a_priced_period_four_pays_less_than_period_one() {
    // The point of the parameter: the memory buys fewer looks, and at a
    // positive price that is a smaller bill, not the same one under another
    // name. `read_cost = 0` is the free case where the bill is zero either way.
    let one = neighbour_reads(1, 12) * 0.05;
    let four = neighbour_reads(4, 12) * 0.05;
    assert!(four > 0.0, "period 4 must still read sometimes");
    assert!(
        four < one,
        "period 4 paid {four}, period 1 paid {one}: the period must save money"
    );

    let free_field = Field::alternating(40, 2.0, 0.2, 0.0).unwrap();
    let mut life = Life::spawn_at(
        quiet(0.0, 4),
        free_field,
        &[12],
        100.0,
        0.0,
        Policy::Memory,
        5,
        1_000,
    )
    .unwrap();
    for _ in 0..12 {
        life.advance();
    }
    assert_eq!(
        life.samples()[0].energy,
        100.0,
        "at read_cost = 0 a read can cost no energy"
    );
}

#[test]
fn a_skipped_step_spends_nothing() {
    // One step at period 4 samples (step 0) and pays two neighbour reads; the
    // next step does not sample, so it must pay nothing at all. This is the
    // mechanism itself, not a ratio: a skipped look is not a cheaper look, it
    // is no look.
    let field = Field::alternating(40, 2.0, 0.2, 0.0).unwrap();
    let mut life = Life::spawn_at(
        quiet(0.05, 4),
        field,
        &[12],
        100.0,
        0.0,
        Policy::Memory,
        5,
        1_000,
    )
    .unwrap();
    life.advance();
    let after_sampled = life.samples()[0].energy;
    assert!(
        (100.0 - after_sampled - 2.0 * 0.05).abs() < 1e-9,
        "the sampling step must pay two looks, energy is {after_sampled}"
    );
    life.advance();
    assert_eq!(
        life.samples()[0].energy,
        after_sampled,
        "a skipped step must pay nothing"
    );
}

#[test]
fn sighted_does_not_sample() {
    // `Sighted` has no memory, so its frames must not move when a period is
    // set: the period is not a cheaper sighted policy, it is a memory policy.
    let field = |_| Field::alternating(40, 2.0, 0.2, 0.8).unwrap();
    let mut one = Life::spawn_at(
        quiet(0.0, 1),
        field(0.0),
        &[12],
        5.0,
        0.1,
        Policy::Sighted,
        7,
        300,
    )
    .unwrap();
    let mut four = Life::spawn_at(
        quiet(0.0, 4),
        field(0.0),
        &[12],
        5.0,
        0.1,
        Policy::Sighted,
        7,
        300,
    )
    .unwrap();
    let a = record(&mut one, 40, 1);
    let b = record(&mut four, 40, 1);
    assert_eq!(a.frames, b.frames, "read_period leaked into `sighted`");
}

#[test]
fn validate_refuses_a_period_of_zero() {
    let mut world = World::default();
    assert_eq!(world.read_period, 1, "looking every step is the default");
    assert!(world.validate().is_ok(), "1 is a valid period");

    world.read_period = 4;
    assert!(world.validate().is_ok(), "4 is a valid period");

    world.read_period = 0;
    assert!(
        world.validate().is_err(),
        "a period of zero is not 'never look': that is read_budget = 0"
    );

    world.read_period = World::MAX_READ_PERIOD + 1;
    assert!(
        world.validate().is_err(),
        "a period beyond the cap is a stopped clock, not a sampling policy"
    );
}
