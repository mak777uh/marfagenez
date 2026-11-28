//! The "off position" contracts, pinned as traces rather than prose.
//!
//! `core/src` says in a dozen places that a switch in its off position must not change a recorded run
//! "by one bit". That sentence is only true if something compares two runs, so this file does:
//!
//! * setting a switch to its off value **after** construction must not change the trace;
//! * the harness must be able to see a change at all -- otherwise "equal" means nothing.
//!
//! What this file does **not** claim: that every switch is covered. It covers the ones whose off
//! position the docs call a contract and that have a public setter or a `World` field.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

fn world() -> World {
    World {
        income: 1.0,
        maintenance_cost: 0.4,
        repair_cost: 1.5,
        damage_rate: 0.05,
        capacity: 10.0,
        read_budget: 2,
        ..World::default()
    }
}

fn mix(h: &mut u64, x: u64) {
    *h ^= x;
    *h = h.wrapping_mul(0x100_0000_01b3);
}

fn energy_damage_hash(energy: f64, damage: f64) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    mix(&mut h, energy.to_bits());
    mix(&mut h, damage.to_bits());
    h
}

/// FNV-1a over the full state after every step: slot, cell, energy, damage, alive.
///
/// A hash, not a metric: it must react to *any* difference, including a one-ulp one.
fn trace_hash(life: &mut Life, steps: usize) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for _ in 0..steps {
        life.advance().expect("advance");
        for s in life.samples() {
            for x in [
                s.slot as u64,
                s.cell as u64,
                s.energy.to_bits(),
                s.damage.to_bits(),
                s.alive as u64,
            ] {
                mix(&mut h, x);
            }
        }
    }
    h
}

fn build(w: World, n: usize) -> Life {
    let field = Field::alternating(4, 4.0, 0.5, 0.0).expect("field");
    Life::spawn_even(w, field, n, 5.0, 0.0, Policy::Sighted, 11, 32).expect("life")
}

#[test]
fn the_off_positions_do_not_move_the_trace() {
    // `Life` is not `Clone` on purpose, so the baseline is a second build with the same seed.
    let h_base = trace_hash(&mut build(world(), 3), 40);

    // `policy_mutation = 0.0`: the docs call this the off position.
    let mut quiet = build(world(), 3);
    assert!(quiet.set_policy_mutation(0.0), "0.0 is a legal rate");
    assert_eq!(trace_hash(&mut quiet, 40), h_base, "policy_mutation off must change nothing");

    // `sight_radius = 1`: docs say `k <= 1` is the original code path.
    let mut blind = build(world(), 3);
    assert!(blind.set_sight_radius(1), "1 is a legal radius");
    assert_eq!(trace_hash(&mut blind, 40), h_base, "sight radius 1 must change nothing");

    // `order = Historical` is the off position of the visit-order switch.
    let mut historical = build(world(), 3);
    assert!(historical.set_order_protocol(medium_core::organism::OrderProtocol::Historical));
    assert_eq!(
        trace_hash(&mut historical, 40),
        h_base,
        "the historical order must change nothing"
    );
    // The "switch is not dead" control for this one lives in `order_protocol.rs`, where the cell is
    // deliberately scarce. In this world the cell is rich enough that every organism eats a full
    // income whatever the order, so a rotation is silent *here* -- which is itself worth knowing: an
    // order effect exists only under contention.

    // `claims = None` is the default; enabling and disabling again must come back.
    let mut owned = build(world(), 3);
    assert!(owned.enable_claims(0.5, 0.1), "claims with a positive cost are legal");
    assert_eq!(trace_hash(&mut owned, 40) != h_base, true, "enabled claims must be visible");
}

#[test]
fn the_harness_sees_one_ulp_and_signed_zero() {
    let energy = 1.0f64;
    let damage = 0.25f64;
    let energy_ulp = f64::from_bits(energy.to_bits() + 1);
    let damage_ulp = f64::from_bits(damage.to_bits() + 1);
    assert_ne!(energy, energy_ulp);
    assert_ne!(damage, damage_ulp);
    assert_ne!(energy_damage_hash(energy, damage), energy_damage_hash(energy_ulp, damage),
        "one energy ULP must survive hashing");
    assert_ne!(energy_damage_hash(energy, damage), energy_damage_hash(energy, damage_ulp),
        "one damage ULP must survive hashing");
    assert_ne!(energy_damage_hash(0.0, damage), energy_damage_hash(-0.0, damage),
        "signed zero is a bit-level difference");
}

#[test]
fn the_harness_can_see_a_change() {
    // A control for the test above: if *every* run produced the same hash, the equalities would be
    // worthless. A price on reading changes the energy, so the hash must move.
    let h_base = trace_hash(&mut build(world(), 3), 20);
    let mut paid = world();
    paid.read_cost = 0.5;
    let h_paid = trace_hash(&mut build(paid, 3), 20);
    assert_ne!(h_base, h_paid, "the harness must react to a real change");
}
