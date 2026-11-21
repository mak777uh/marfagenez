//! How much damage can be repaired, as a function of the price?
//!
//! The repair is all-or-nothing: the organism pays `damage * repair_cost` and, if it can pay, damage drops
//! to zero; if it cannot pay, the damage stays and the next step adds more. With energy `E` the boundary
//! is therefore `damage * repair_cost < E` — a line, not a fuzzy region. This file measures the boundary
//! in the real world instead of trusting the formula:
//!
//! * just below the line, damage is repaired;
//! * just above it, damage survives the step.
//!
//! What this file does **not** claim: that damage is recoverable indefinitely. A repair that costs more
//! than the income allows will eventually drain the reserve; the boundary here is one step's affordability.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

fn world(repair_cost: f64) -> World {
    World {
        income: 0.0,
        maintenance_cost: 0.0,
        repair_cost,
        damage_rate: 0.0,
        capacity: 10.0,
        read_budget: 0,
        ..World::default()
    }
}

/// One step from a given energy and damage; returns the damage after the step.
fn damage_after(energy: f64, damage: f64, repair_cost: f64) -> Option<f64> {
    let field = Field::new(1, 1.0, 0.0).expect("field");
    let organism = Organism::new(energy, damage).expect("organism");
    let one = Remembering::new(organism, 0, 0.0, 0.0, 8).expect("remembering");
    let mut life = Life::new_mixed(world(repair_cost), field, vec![one], vec![Policy::Stay], 3, 8)?;
    life.advance()?;
    let samples = life.samples();
    let alive = samples.iter().find(|s| s.alive)?;
    Some(alive.damage)
}

#[test]
fn the_boundary_is_the_price_line() {
    // energy 2, repair_cost 4: the line is damage = 0.5. Below it the repair is affordable.
    let below = damage_after(2.0, 0.4, 4.0).expect("alive");
    assert!(below < 1e-12, "below the line the damage must be repaired: {below}");

    // Above it the organism cannot pay and the damage stays.
    let above = damage_after(2.0, 0.6, 4.0).expect("alive");
    assert!(
        (above - 0.6).abs() < 1e-12,
        "above the line the damage must survive the step: {above}"
    );
}

#[test]
fn a_dearer_price_moves_the_boundary_down() {
    let cheap = damage_after(6.0, 0.6, 2.0).expect("alive");
    let dear = damage_after(6.0, 0.6, 12.0).expect("alive");
    assert!(cheap < 1e-12, "cheap repair fixes 0.6 of damage");
    assert!(
        (dear - 0.6).abs() < 1e-12,
        "the same damage is out of reach at a dearer price: {dear}"
    );
}

#[test]
fn print_the_recovery_map() {
    // Not an assertion: the map is the artifact. Run with `-- --nocapture`.
    println!("повреждение после шага (энергия 6.0, damage_rate 0)");
    print!("damage\\cost");
    for cost in [1.0, 2.0, 4.0, 6.0, 9.0] {
        print!(" {:>7.1}", cost);
    }
    println!();
    for damage in [0.2, 0.6, 0.9, 0.99] {
        print!("{:>11.1}", damage);
        for cost in [1.0, 2.0, 4.0, 6.0, 9.0] {
            match damage_after(6.0, damage, cost) {
                Some(d) => print!(" {:>7.1}", d),
                None => print!(" {:>7}", "мёртв"),
            }
        }
        println!();
    }
    println!();
    println!("линия: damage * cost = 6.0 (энергия шага)");
}
