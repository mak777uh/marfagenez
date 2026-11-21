//! Births: the second arm of the feedback.
//!
//! `docs/FINDING-152.md` measured one direction of the population feedback --
//! a death frees a share -- and said the missing half was that nobody is born.
//! `World::max_population`, `World::birth_threshold` and `World::birth_cost`
//! add that half, and this file pins the six properties the model must keep:
//!
//! 1. a birth moves energy and never creates it;
//! 2. the default is "no births", so the population never grows;
//! 3. with births on, the population reaches `max_population` and stops there;
//! 4. a child takes the parent's cell and the **parent's** policy (not the first one);
//! 5. a dead slot is reused before the `Vec` grows;
//! 6. `World::validate` refuses a nonsense birth parameter.
//!
//! What this file does **not** claim: that a child is a descendant. The policy is
//! inherited, the organisation is not: there is no gene, no heritable structure, and the
//! child starts as a slot copy on the parent's cell with `birth_cost` energy. It is slot
//! reproduction, not evolution. See `docs/FINDING-153.md`.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::Organism;
use medium_core::organism::{LookOrder, ShareProtocol, TieBreak, World};

/// A world where the only event in a step is a birth.
///
/// No income, no maintenance, no damage: the reserve cannot move except by a
/// birth, so the energy sum is a test of the birth itself and not of the
/// arithmetic around it.
fn quiet_world(birth_threshold: f64, birth_cost: f64, max_population: usize) -> World {
    World {
        income: 0.0,
        maintenance_cost: 0.0,
        repair_cost: 1.5,
        damage_rate: 0.0,
        capacity: 10.0,
        read_budget: 0,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        birth_threshold,
        birth_cost,
        max_population,
        // Reading is free (the default) in this arm.
        read_cost: 0.0,
        read_period: 1,
        look_on_shortfall: false,
    }
}

fn total_energy(life: &Life) -> f64 {
    life.samples()
        .iter()
        .filter(|s| s.alive)
        .map(|s| s.energy)
        .sum()
}

#[test]
fn a_birth_moves_energy_and_does_not_create_it() {
    // One organism with 5.0 in a world where nothing else can change a reserve:
    // no income, no maintenance, no damage. A birth must leave the sum where
    // it was, because the parent pays exactly what the child receives.
    let world = quiet_world(1.0, 2.0, 8);
    let field = Field::new(1, 1.0, 0.0).unwrap();
    let mut life = Life::spawn_even(world, field, 1, 5.0, 0.0, Policy::Stay, 1, 300).unwrap();

    let before = total_energy(&life);
    assert_eq!(before, 5.0, "the starting reserve is what was asked for");

    life.advance().unwrap();

    let after = total_energy(&life);
    let census = life.census();
    assert_eq!(census.alive, 2, "one parent should have made one child");
    assert!(
        (after - before).abs() < 1e-12,
        "energy must be moved, not created: before {before}, after {after}, \
         difference {}",
        after - before
    );

    // The split is exactly the price: the parent keeps what it had minus
    // `birth_cost`, the child is born with `birth_cost`.
    let mut energies: Vec<f64> = life
        .samples()
        .iter()
        .filter(|s| s.alive)
        .map(|s| s.energy)
        .collect();
    energies.sort_by(|a, b| a.partial_cmp(b).unwrap());
    assert_eq!(energies, vec![2.0, 3.0], "5.0 splits as 3.0 + 2.0");
}

#[test]
fn births_are_off_by_default_so_the_population_never_grows() {
    // `World::default()` must keep the historical model: no births, so the
    // number of slots never rises above the number of organisms that were
    // spawned. The energy is generous on purpose -- every organism is rich
    // enough to breed if the switch were on, and it still must not.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.01,
        capacity: 10.0,
        read_budget: 0,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        ..Default::default()
    };
    // The defaults ARE the contract.
    assert_eq!(world.max_population, 0, "0 means births are off");
    assert_eq!(
        world.birth_threshold,
        f64::INFINITY,
        "an unreachable threshold is the second 'off'"
    );
    assert_eq!(world.birth_cost, 0.0);

    let field = Field::new(8, 2.0, 0.8).unwrap();
    let mut life = Life::spawn_even(world, field, 4, 5.0, 0.0, Policy::Stay, 7, 300).unwrap();
    assert_eq!(life.census().total, 4);

    for step in 0..200 {
        life.advance().unwrap();
        let census = life.census();
        assert_eq!(
            census.total, 4,
            "the population grew at step {step}: total = {}",
            census.total
        );
        assert!(census.alive <= 4, "more alive than were ever spawned");
    }
    assert_eq!(life.census().alive, 4, "nobody should have died here either");
}

#[test]
fn the_population_grows_to_max_population_and_not_above() {
    let world = quiet_world(1.0, 1.0, 6);
    // A quiet field with room for six: the cells are only a place to stand.
    let field = Field::new(64, 1.0, 0.0).unwrap();
    let mut life = Life::spawn_even(world, field, 2, 5.0, 0.0, Policy::Stay, 3, 300).unwrap();

    for step in 0..40 {
        life.advance().unwrap();
        let census = life.census();
        assert!(
            census.alive <= 6,
            "alive = {} above max_population = 6 at step {step}",
            census.alive
        );
    }

    let census = life.census();
    assert_eq!(census.alive, 6, "the population should reach the cap");
    assert_eq!(
        census.total, 6,
        "the Vec must not grow past the cap: total = {}",
        census.total
    );
}

#[test]
fn a_child_gets_the_parents_cell_and_the_parents_policy() {
    let world = quiet_world(1.0, 1.0, 4);
    let field = Field::new(4, 1.0, 0.0).unwrap();
    let mut life = Life::spawn_even(world, field, 1, 5.0, 0.0, Policy::Stay, 5, 300).unwrap();
    assert!(life.move_to(0, 2), "put the parent on cell 2");

    life.advance().unwrap();

    let samples = life.samples();
    assert_eq!(samples.len(), 2, "one birth, one new slot");
    for s in &samples {
        assert!(s.alive, "both should be alive");
        assert_eq!(
            s.cell, 2,
            "the child is born on the parent's cell, not on a random one"
        );
    }
    // The single-policy constructor gives one policy to everybody, so this run
    // cannot tell "parent's policy" from "population's first". The test below does.
    assert_eq!(life.policy(), Policy::Stay);
    for _ in 0..10 {
        life.advance().unwrap();
    }
    for s in life.samples() {
        assert!(s.alive, "the quiet world should let them live");
        assert_eq!(s.cell, 2, "`Stay` must keep the newborn where it was born");
    }
}

#[test]
fn a_dead_slot_is_reused_before_the_vec_grows() {
    // Two cells: cell 0 is rich and never runs dry in this run, cell 1 is
    // empty. The organism on the empty cell starves; the one on the rich cell
    // breeds. Once the poor organism is dead, the next birth must fill its
    // slot instead of appending a fourth one: a dead slot is a free slot, and
    // a `Vec` that keeps the graveyard beside the living is a leak.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.9,
        repair_cost: 1.5,
        damage_rate: 0.0,
        capacity: 10.0,
        read_budget: 0,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        // A threshold only a fed organism reaches, so the births are spread
        // out over time and one of them lands after the death.
        birth_threshold: 5.0,
        birth_cost: 0.5,
        max_population: 4, read_cost: 0.0,
        read_period: 1,
        look_on_shortfall: false,
    };
    let field = Field::alternating(2, 1.0e9, 0.0, 0.0).unwrap();
    let mut life = Life::spawn_even(world, field, 2, 5.0, 0.0, Policy::Stay, 11, 300).unwrap();
    assert!(life.move_to(0, 0), "the rich cell");
    assert!(life.move_to(1, 1), "the empty cell");

    for step in 0..40 {
        life.advance().unwrap();
        let census = life.census();
        assert!(
            census.total <= 4,
            "total = {} at step {step}: the Vec grew past max_population",
            census.total
        );
    }

    let census = life.census();
    assert_eq!(
        census.total, 4,
        "a dead slot should be reused, not appended beside: total = {}",
        census.total
    );
    assert_eq!(census.alive, 4, "four organisms should be alive");
}

#[test]
fn a_child_takes_the_parents_policy_not_the_populations_first() {
    // The rich organism (the only one that can afford a birth) sits at `rich_index`.
    // If the child copied `policies[0]`, the second case would fail: there the parent is
    // second in the vector and `policies[0]` belongs to the poor organism.
    fn child_policy(policies: Vec<Policy>, rich_index: usize) -> Policy {
        let world = quiet_world(1.0, 1.0, 4);
        let field = Field::new(4, 1.0, 0.0).unwrap();
        let energies = [5.0, 0.5];
        let cells = [0usize, 1usize];
        let mut organisms = Vec::new();
        for k in 0..2 {
            let o = Organism::new(energies[k], 0.0).unwrap();
            organisms.push(Remembering::new(o, cells[k], 0.0, 0.0, 300).unwrap());
        }
        if rich_index == 1 {
            // swap the energies so the second slot is the rich one
            let mut swapped = Vec::new();
            for k in 0..2 {
                let o = Organism::new(energies[1 - k], 0.0).unwrap();
                swapped.push(Remembering::new(o, cells[k], 0.0, 0.0, 300).unwrap());
            }
            organisms = swapped;
        }
        let mut life = Life::new_mixed(world, field, organisms, policies, 7, 300)
            .expect("two policies for two organisms");
        life.advance().unwrap();
        let got = life.policies();
        assert_eq!(got.len(), 3, "one birth, one new slot");
        got[2]
    }

    assert_eq!(
        child_policy(vec![Policy::Sighted, Policy::Memory], 0),
        Policy::Sighted,
        "the child inherits the parent's policy (parent first in the vector)"
    );
    assert_eq!(
        child_policy(vec![Policy::Memory, Policy::Sighted], 1),
        Policy::Sighted,
        "the child copies `policies[parent]`, not `policies[0]` (parent second)"
    );
}

#[test]
fn validate_refuses_a_nonsense_birth() {
    let good = quiet_world(1.0, 1.0, 4);
    assert!(good.validate().is_ok(), "a finite threshold is legal");
    assert!(
        quiet_world(f64::INFINITY, 0.0, 0).validate().is_ok(),
        "INFINITY is the sanctioned 'never'"
    );

    let mut bad = quiet_world(1.0, 1.0, 4);
    bad.birth_threshold = -1.0;
    assert!(bad.validate().is_err(), "a negative threshold is refused");
    bad.birth_threshold = f64::NAN;
    assert!(bad.validate().is_err(), "a NaN threshold is refused");
    bad.birth_threshold = f64::NEG_INFINITY;
    assert!(bad.validate().is_err(), "-INFINITY is not the 'never' default");

    let mut bad = quiet_world(1.0, 1.0, 4);
    bad.birth_cost = -0.5;
    assert!(bad.validate().is_err(), "a negative price is refused");
    bad.birth_cost = f64::NAN;
    assert!(bad.validate().is_err(), "a NaN price is refused");
    bad.birth_cost = f64::INFINITY;
    assert!(bad.validate().is_err(), "an infinite price is refused");
}
