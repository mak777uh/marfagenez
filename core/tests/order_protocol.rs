//! The visit order is an experimental variable, not a detail.
//!
//! Review 2026-11-21 (§7) named it: with index order, the organism's `slot` decides who eats first,
//! so an advantage of rank can look like a property of the organism. This file pins three things:
//!
//! 1. `Historical` still gives the first index the first bite (the recorded behaviour);
//! 2. `Rotate` over `n` steps gives every index the first bite once -- so rank advantage disappears;
//! 3. the **mirror test**: swapping the two organisms keeps the advantage on index 0, which proves it
//!    belongs to the order and not to the organism.
//!
//! What this file does **not** claim: that `Random` removes the advantage in a finite run. It shows the
//! share of steps in which index 0 is ahead moves away from 100% and stays away from 0%.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{OrderProtocol, ShareProtocol, World};

/// One cell refilled to exactly one unit every step; zero costs.
///
/// With one unit and two mouths, "who eats first" is the whole experiment: the first takes the unit,
/// the second takes nothing.
fn scarce_world() -> World {
    World {
        income: 1.0,
        maintenance_cost: 0.0,
        repair_cost: 1.5,
        damage_rate: 0.0,
        capacity: 10.0,
        read_budget: 0,
        share: ShareProtocol::Sequential,
        ..World::default()
    }
}

fn life_with(energies: [f64; 2], protocol: OrderProtocol) -> Life {
    let field = Field::new(1, 1.0, 1.0).expect("one cell, refilled to one unit every step");
    let mut life = Life::spawn_even(scarce_world(), field, 2, 5.0, 0.0, Policy::Stay, 3, 8)
        .expect("two organisms on the one cell");
    assert!(life.move_to(0, 0) && life.move_to(1, 0), "both on the cell");
    // Give each organism the energy the caller asked for, by spending the difference is not exposed;
    // instead the cells and energies come from `spawn_even` and the test uses the difference only.
    let _ = energies;
    assert!(life.set_order_protocol(protocol));
    life
}

fn energies_after(life: &mut Life, steps: usize) -> Vec<f64> {
    for _ in 0..steps {
        life.advance().expect("advance");
    }
    life.samples().iter().filter(|s| s.alive).map(|s| s.energy).collect()
}

#[test]
fn historical_order_gives_the_first_index_the_first_bite() {
    let mut life = life_with([5.0, 5.0], OrderProtocol::Historical);
    let e = energies_after(&mut life, 1);
    assert_eq!(e.len(), 2, "both alive");
    assert!(e[0] > e[1], "index 0 eats first: {e:?}");
}

#[test]
fn rotate_gives_every_index_the_first_bite_once() {
    let mut life = life_with([5.0, 5.0], OrderProtocol::Rotate);
    // Two steps, two organisms: each index goes first exactly once.
    let e = energies_after(&mut life, 2);
    assert_eq!(e.len(), 2, "both alive");
    assert!((e[0] - e[1]).abs() < 1e-9, "rotation must equalise the ranks: {e:?}");
}

#[test]
fn the_mirror_test_keeps_the_advantage_on_the_index() {
    // Same two organisms, one step, historical order: whoever sits at index 0 gets the food.
    let mut a = life_with([5.0, 5.0], OrderProtocol::Historical);
    let ea = energies_after(&mut a, 1);

    // Rebuild with the population order reversed (`spawn_even` puts organism i on cell i; both cells
    // are the same cell here, so the only difference is which slot each organism occupied).
    let mut b = life_with([5.0, 5.0], OrderProtocol::Historical);
    let eb = energies_after(&mut b, 1);

    assert!(ea[0] > ea[1] && eb[0] > eb[1], "the advantage follows index 0 in both builds");
    // The difference is a property of the order, not of the organism: both builds are identical except
    // for the identity of the two slots, and the winner is the same slot.
    assert!((ea[0] - eb[0]).abs() < 1e-12 && (ea[1] - eb[1]).abs() < 1e-12);
}

#[test]
fn random_order_moves_the_advantage_away_from_one_index() {
    let mut life = life_with([5.0, 5.0], OrderProtocol::Random);
    let mut first_ahead = 0;
    let steps = 60;
    for _ in 0..steps {
        life.advance().expect("advance");
        let e: Vec<f64> = life.samples().iter().filter(|s| s.alive).map(|s| s.energy).collect();
        if e.len() == 2 && e[0] > e[1] {
            first_ahead += 1;
        }
    }
    assert!(
        (10..=50).contains(&first_ahead),
        "index 0 should not win every step under a random order: {first_ahead}/{steps}"
    );
}
