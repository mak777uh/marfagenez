//! The price of reading, and a field whose peaks are out of sight.
//!
//! `docs/FINDING-155.md` named two reasons the medium never asks a question
//! about memory: the field is uniform (the richest cell is always adjacent) and
//! reading is **free** (there is a budget on perception but no price for it).
//! Two independent reviews said the same in
//! `docs/REVIEW-emergence-notes-3.md` §1.3 and "Что остаётся сделать".
//!
//! These tests pin the two model changes that close those gaps:
//!
//! * `World::read_cost` -- what one **neighbour** read costs, with `0.0` as the
//!   contract "free", which must not move a single bit of a recorded run;
//! * `Field::peaks` -- one rich cell every `period` cells, so with `period >= 4`
//!   the next rich cell is outside the visible window.
//!
//! What is *not* tested here: that the price buys anything. That is the
//! experiment (`checks/exp_memory_cost.py`), not the unit test.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{LookOrder, ShareProtocol, TieBreak, World};
use medium_core::trace::{record, Trace};

/// A world where the **only** thing that moves energy is the read price: no
/// income, no maintenance, no damage, no movement cost, no births.
///
/// Any energy that disappears is therefore the price of looking, and nothing
/// else -- which is what makes the accounting below an assertion rather than a
/// coincidence.
fn quiet(read_cost: f64, read_budget: usize) -> World {
    World {
        income: 0.0,
        maintenance_cost: 0.0,
        repair_cost: 0.0,
        damage_rate: 0.0,
        capacity: 100.0,
        read_budget,
        read_cost,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        birth_threshold: f64::INFINITY,
        birth_cost: 0.0,
        max_population: 0,
        read_period: 1,
        look_on_shortfall: false,
    }
}

/// The energy of the only organism after `steps` steps.
fn energy_after(world: World, field: Field, start: usize, steps: usize) -> f64 {
    let mut life =
        Life::spawn_at(world, field, &[start], 5.0, 0.0, Policy::Sighted, 7, 300).unwrap();
    for _ in 0..steps {
        life.advance();
    }
    life.samples()[0].energy
}

#[test]
fn a_sighted_organism_pays_for_every_neighbour_it_reads() {
    // An alternating field, an interior start: both neighbours exist, so a
    // budget of 3 is one look at the own cell and two at the neighbours.
    // 10 steps x 2 neighbours x 0.05 = 1.0 from a reserve of 5.0.
    let field = |r| Field::alternating(24, 2.0, 0.2, r).unwrap();
    let free = energy_after(quiet(0.0, 3), field(0.0), 12, 10);
    let priced = energy_after(quiet(0.05, 3), field(0.0), 12, 10);
    assert!((free - 5.0).abs() < 1e-12, "free reads spent {free}");
    assert!(
        (free - priced - 1.0).abs() < 1e-12,
        "two priced neighbour reads per step over 10 steps must be 1.0, got {}",
        free - priced
    );
}

#[test]
fn a_budget_of_one_reads_no_neighbour_and_pays_nothing() {
    // The budget is spent on the own cell first, so `read_budget = 1` buys no
    // neighbour at all. The price is irrelevant there: this is the cell that
    // says the charge follows the *read*, not the parameter.
    let field = |r| Field::alternating(24, 2.0, 0.2, r).unwrap();
    let free = energy_after(quiet(0.0, 1), field(0.0), 12, 10);
    let priced = energy_after(quiet(0.5, 1), field(0.0), 12, 10);
    assert!((priced - free).abs() < 1e-12, "{free} against {priced}");
}

#[test]
fn an_unaffordable_read_is_not_taken() {
    // Cell 0 is the only rich cell, so the cell 1 organism has a rich LEFT
    // neighbour: a sighted organism that can see it steps left and eats.
    let field = |_r| Field::peaks(24, 2.0, 0.2, 0.0, 24).unwrap();

    // Free to look, but no energy at all: it still walks to the rich cell,
    // because looking costs nothing.
    let mut life = Life::spawn_at(quiet(0.0, 3), field(0.0), &[1], 0.0, 0.0, Policy::Sighted, 7, 300)
        .unwrap();
    for _ in 0..5 {
        life.advance();
    }
    assert_eq!(life.samples()[0].cell, 0, "a free look should find cell 0");

    // The same organism with a price and no energy does NOT read: it stays
    // where it is and does not go into debt to see.
    let mut life = Life::spawn_at(
        quiet(0.05, 3),
        field(0.0),
        &[1],
        0.0,
        0.0,
        Policy::Sighted,
        7,
        300,
    )
    .unwrap();
    for _ in 0..5 {
        life.advance();
    }
    let s = life.samples()[0];
    assert_eq!(s.cell, 1, "an unpayable look must not be taken");
    assert_eq!(s.energy, 0.0, "the price must not drive energy negative");
    assert!(s.energy >= 0.0);
}

#[test]
fn a_zero_price_adds_nothing_to_the_dynamics_hash() {
    // The contract is about the hash, not about a test: `read_cost = 0.0` must
    // produce the same value `hash_with_world` produced before the field
    // existed, while a positive price is a different experiment and must not
    // collide with a free one that happens to share its frames.
    let world = quiet(0.0, 3);
    let field = Field::alternating(20, 2.0, 0.2, 0.8).unwrap();
    let mut life =
        Life::spawn_even(world, field, 6, 5.0, 0.1, Policy::Sighted, 11, 300).unwrap();
    let trace = record(&mut life, 40, 1);

    let before = Trace::hash_with_world(&trace.frames, "sequential", "left", "look-then-eat");
    let with_zero = Trace::hash_with_births(
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
    let with_price = Trace::hash_with_births(
        &trace.frames,
        "sequential",
        "left",
        "look-then-eat",
        0,
        f64::INFINITY,
        0.0,
        0.05,
        1,
        false,
    );
    assert_eq!(before, with_zero, "read_cost = 0.0 moved the hash");
    assert_ne!(before, with_price, "a price must not collide with free reading");
}

#[test]
fn peaks_puts_one_rich_cell_per_period() {
    let f = Field::peaks(12, 2.0, 0.2, 0.8, 3).unwrap();
    for i in 0..12 {
        let want = if i % 3 == 0 { 2.0 } else { 0.2 };
        assert!((f.level(i) - want).abs() < 1e-12, "cell {i}: {}", f.level(i));
    }
    // The *ceilings* moved with the levels: empty a rich and a poor cell, regrow
    // once, and they must climb toward 2.0 and 0.2 respectively -- not toward a
    // single `max_resource` for the whole field. That was the bug
    // `docs/FINDING-alternating-field-collapses.md` recorded.
    let mut f = Field::peaks(12, 2.0, 0.2, 0.8, 3).unwrap();
    for i in 0..12 {
        f.take(i, 10.0);
    }
    f.regrow_all();
    assert!((f.level(0) - 2.0 * 0.8).abs() < 1e-12, "rich: {}", f.level(0));
    assert!((f.level(1) - 0.2 * 0.8).abs() < 1e-12, "poor: {}", f.level(1));
}

#[test]
fn peaks_with_period_two_is_alternating_and_with_one_is_new() {
    // `alternating` delegates to `peaks(period = 2)`; the two must agree cell
    // for cell, or the delegation is a second place for them to disagree.
    let alt = Field::alternating(13, 3.0, 0.4, 0.5).unwrap();
    let two = Field::peaks(13, 3.0, 0.4, 0.5, 2).unwrap();
    for i in 0..13 {
        assert_eq!(alt.level(i), two.level(i), "cell {i}");
    }
    let flat = Field::new(13, 3.0, 0.5).unwrap();
    let one = Field::peaks(13, 3.0, 0.4, 0.5, 1).unwrap();
    for i in 0..13 {
        assert_eq!(flat.level(i), one.level(i), "cell {i}");
    }
    // No period is not "period one": `period = 0` has no meaning and is refused.
    assert!(Field::peaks(13, 3.0, 0.4, 0.5, 0).is_none());
    assert!(Field::peaks(13, 3.0, f64::NAN, 0.5, 4).is_none());
    assert!(Field::peaks(13, 3.0, -1.0, 0.5, 4).is_none());
}

#[test]
fn validate_refuses_a_negative_or_nan_read_cost() {
    let free = World::default();
    assert_eq!(free.read_cost, 0.0, "reading is free by default");
    assert!(free.validate().is_ok(), "0.0 is the allowed default");

    let mut priced = World::default();
    priced.read_cost = 0.05;
    assert!(priced.validate().is_ok(), "a price is a valid world");

    let mut bad = World::default();
    bad.read_cost = -0.01;
    assert!(bad.validate().is_err(), "a negative price is nonsense");

    let mut bad = World::default();
    bad.read_cost = f64::NAN;
    assert!(bad.validate().is_err(), "NaN is not a price");
}
