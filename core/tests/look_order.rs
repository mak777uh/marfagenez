//! The look order is a parameter of the world, and it changes the outcome.
//!
//! `Policy::Memory` reads its cell and updates the memory. The order -- read then
//! eat, or eat then read -- was never written down, and two runs that differed
//! only in it hashed the same. This file pins three things:
//!
//!   1. the default is the historical order, so no committed number moves;
//!   2. the two orders produce different traces (the parameter reaches the
//!      simulation, and the hash says so);
//!   3. the difference is not noise: `look-then-eat` keeps more organisms alive
//!      on an alternating field, on every seed tried.
//!
//! (3) is a measurement, not a law. It is here so that a change to the memory
//! rule has to face the number it moves, and so that "the order does not matter"
//! cannot be asserted again without failing a test.

#![cfg(test)]

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{LookOrder, ShareProtocol, TieBreak, World};
use medium_core::trace::{record, Trace};

fn world(order: LookOrder) -> World {
    World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 1,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: order,
    }
}

fn run(order: LookOrder, seed: u64) -> Trace {
    let w = world(order);
    let f = Field::alternating(8, 2.4, 1.6, 0.8).expect("field");
    let mut life = Life::spawn_even(w, f, 40, 10.0, 0.0, Policy::Memory, seed, 300)
        .expect("population");
    record(&mut life, 200, 1)
}

#[test]
fn the_default_is_the_historical_order() {
    assert_eq!(World::default().look_order, LookOrder::LookThenEat);
    assert_eq!(LookOrder::default(), LookOrder::LookThenEat);
}

#[test]
fn the_order_is_in_the_trace_and_in_its_hash() {
    let a = run(LookOrder::LookThenEat, 1);
    let b = run(LookOrder::EatThenLook, 1);
    assert_eq!(a.look_order, "look-then-eat");
    assert_eq!(b.look_order, "eat-then-look");
    assert_ne!(
        a.hash, b.hash,
        "the two orders hashed the same: either the parameter did not reach the \
         simulation, or it is not folded into the hash"
    );
    assert!(
        a.to_json().contains("\"look_order\": \"look-then-eat\""),
        "the trace does not record the order it ran under"
    );
}

#[test]
fn look_then_eat_keeps_more_alive_on_an_alternating_field() {
    for seed in 1..=5u64 {
        let a = run(LookOrder::LookThenEat, seed);
        let b = run(LookOrder::EatThenLook, seed);
        let alive = |t: &Trace| -> usize {
            t.frames
                .last()
                .map(|f| f.samples.iter().filter(|s| s.alive).count())
                .unwrap_or(0)
        };
        assert!(
            alive(&a) > alive(&b),
            "seed {seed}: look-then-eat kept {} alive, eat-then-look kept {}. \
             The recorded measurement (docs/FINDING-142) says the first is larger \
             on every seed; if this fails, the finding is stale, not the test.",
            alive(&a),
            alive(&b)
        );
    }
}

#[test]
fn the_hash_of_the_old_two_argument_form_is_unchanged() {
    // A caller with no look order in hand must get the hash it got before the
    // parameter existed. `hash_with_protocol_and_tiebreak` passes "" for it.
    let t = run(LookOrder::LookThenEat, 1);
    let old = Trace::hash_with_protocol_and_tiebreak(&t.frames, "sequential", "left");
    let new = Trace::hash_with_world(&t.frames, "sequential", "left", "");
    assert_eq!(old, new);
}
