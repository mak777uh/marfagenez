//! Two forms in one world.
//!
//! `Life::new` gives every organism the same policy, so "one world, two forms" was
//! not expressible: two `Life`s do not share a field and therefore cannot compete
//! for a cell. `Life::new_mixed` gives each organism its own policy.
//!
//! The invariance that matters is the reverse of the feature: the single-policy
//! constructor must keep producing exactly the dynamics it produced before, because
//! every recorded result in this project depends on it. That is pinned by
//! `tests/hash_golden.rs`; here the two-form case is shown to be *different*, which
//! is what proves the policy is really per organism.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

fn world() -> World {
    World {
        income: 2.0,
        maintenance_cost: 1.0,
        repair_cost: 1.5,
        damage_rate: 0.02,
        read_budget: 1,
        ..World::default()
    }
}

fn organisms(cells: &[usize]) -> Vec<Remembering> {
    let w = world();
    cells
        .iter()
        .map(|&c| {
            let o = Organism::new(5.0, 0.0).expect("valid organism");
            Remembering::new(o, c, w.income, 0.0, 32).expect("valid remembering")
        })
        .collect()
}

fn field() -> Field {
    Field::alternating(6, 3.0, 1.0, 0.9).expect("valid field")
}

#[test]
fn mixed_policies_are_accepted_and_reported_per_organism() {
    let life = Life::new_mixed(
        world(),
        field(),
        organisms(&[1, 4]),
        vec![Policy::Stay, Policy::Sighted],
        7,
        32,
    )
    .expect("two organisms, two policies");
    assert_eq!(life.policy(), Policy::Stay, "the first organism's policy");
    assert_eq!(life.policies(), &[Policy::Stay, Policy::Sighted]);
}

#[test]
fn a_mismatch_is_refused_rather_than_padded() {
    let refused = Life::new_mixed(
        world(),
        field(),
        organisms(&[1, 4]),
        vec![Policy::Stay],
        7,
        32,
    );
    assert!(
        refused.is_none(),
        "one policy for two organisms must be refused, not padded"
    );
}

#[test]
fn the_second_organism_actually_uses_its_own_policy() {
    // Same world, same start, same seed; the only difference is the second
    // organism's policy. A stayer never moves; a random walker does, so the move
    // counter differs. `Random` is used rather than `Sighted` because on this
    // field the sighted organism has no richer neighbour to step to - that is a
    // property of the field, not of the policy plumbing, and it belongs in a
    // field experiment rather than in a test of per-organism policies.
    let run = |second: Policy| {
        let mut life = Life::new_mixed(
            world(),
            field(),
            organisms(&[1, 4]),
            vec![Policy::Stay, second],
            7,
            32,
        )
        .expect("built");
        for _ in 0..20 {
            life.advance();
        }
        life.census().moves
    };
    let both_stay = run(Policy::Stay);
    let second_walks = run(Policy::Random);
    assert_eq!(both_stay, 0, "no stayer moves");
    assert!(
        second_walks > 0,
        "the random organism must move; got {second_walks}"
    );
}
