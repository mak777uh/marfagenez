//! At the cap a price is invisible in the state.
//!
//! Review 2026-11-21 (the "cap erases the price" note): with `clamp(energy, 0, E_max)` as the last
//! step, an organism that holds the cap and has a non-negative inflow ends the step at `E_max`
//! whatever it paid on the way. The cost happened -- it is a real transfer -- but the *state* after
//! the step cannot see it, so a measurement that reads only energy at the cap cannot price anything.
//!
//! This file uses `maintenance_cost` as the price because it is charged on every step,
//! unconditionally: no branch, no read budget, no policy. That keeps the test about the cap and not
//! about when a charge happens to be attempted.
//!
//! What this file does **not** claim: that the payment is fake. It is a transfer out of the reserve;
//! the claim is narrower -- at the cap it does not survive into the next state.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

fn world_with(maintenance: f64, income: f64) -> World {
    World {
        income,
        maintenance_cost: maintenance,
        repair_cost: 1.5,
        damage_rate: 0.0,
        capacity: 10.0,
        read_budget: 0,
        ..World::default()
    }
}

fn energies(w: World, start: f64, level: f64, steps: usize) -> Vec<f64> {
    let field = Field::new(2, level, 1.0).expect("field refilled to the level every step");
    let mut life = Life::spawn_even(w, field, 1, start, 0.0, Policy::Stay, 5, 16).expect("life");
    for _ in 0..steps {
        life.advance().expect("advance");
    }
    life.samples().iter().filter(|s| s.alive).map(|s| s.energy).collect()
}

#[test]
fn at_the_cap_the_upkeep_price_is_invisible() {
    // Rich cell, income 2.0, cap 10: `10 - 0.9 + 2.0` clamps back to 10, so a dearer world and a free
    // one end every step at the same energy. The upkeep was still paid: it left the reserve first.
    let free = energies(world_with(0.0, 2.0), 10.0, 5.0, 6);
    let dear = energies(world_with(0.9, 2.0), 10.0, 5.0, 6);
    assert_eq!(free.len(), 1, "one organism survives");
    assert!((free[0] - 10.0).abs() < 1e-12, "stays at the cap: {free:?}");
    assert_eq!(
        free, dear,
        "at the cap the upkeep does not survive into the state: free {free:?}, dear {dear:?}"
    );
}

#[test]
fn below_the_cap_the_same_price_is_visible() {
    // The control: same two worlds, a poor cell and a poor start. Now the upkeep is not clamped away.
    let free = energies(world_with(0.0, 0.2), 1.0, 0.2, 6);
    let dear = energies(world_with(0.1, 0.2), 1.0, 0.2, 6);
    assert_eq!(free.len(), 1, "the free organism survives");
    assert!(
        (free[0] - dear[0]).abs() > 1e-9,
        "below the cap the upkeep must show: free {free:?}, dear {dear:?}"
    );
}

#[test]
fn the_price_is_charged_even_at_the_cap() {
    // A stricter instrument than energy: an organism that cannot pay the upkeep dies even at the cap.
    // `income = 2`, `maintenance = 12`: every step costs more than the take, so the reserve falls from
    // the cap and the organism dies -- the price was real, it just needed more steps than one to
    // become visible in the state.
    let w = world_with(12.0, 2.0);
    let field = Field::new(2, 20.0, 1.0).expect("field");
    let mut life = Life::spawn_even(w, field, 1, 10.0, 0.0, Policy::Stay, 5, 16).expect("life");
    for _ in 0..30 {
        life.advance().expect("advance");
    }
    let alive = life.samples().iter().filter(|s| s.alive).count();
    assert_eq!(alive, 0, "a price above the inflow must kill, cap or no cap");
}
