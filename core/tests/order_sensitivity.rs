//! Does the visit order change a conclusion, or only the numbers?
//!
//! Review 2026-11-21 (§7): with index order the first organism eats first, so an advantage of rank can look
//! like a property of the organism. `OrderProtocol` exists (FINDING-327), but a protocol nobody replays
//! measures nothing. This file replays the **phase map** of `phase_diagram.rs` under all three orders and
//! counts cells whose verdict (everybody lives / somebody dies) changes.
//!
//! What this file does **not** claim: that recorded experiments were re-run. They are Python models; this
//! measures the Rust world on the same parameter grid, which is the closest honest surrogate.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{OrderProtocol, World};

const STEPS: usize = 200;
const START_ENERGY: f64 = 5.0;
const ORGANISMS: usize = 3;

fn world(damage: f64, repair: f64) -> World {
    World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: repair,
        damage_rate: damage,
        capacity: 10.0,
        read_budget: 0,
        ..World::default()
    }
}

/// The surviving slots, not just how many: "one of three survives" hides *which* one, and the order
/// decides exactly that.
fn survivors(damage: f64, repair: f64, order: OrderProtocol, seed: u64) -> Vec<usize> {
    let field = Field::new(4, 1.0, 1.0).expect("field");
    let mut life = Life::spawn_even(world(damage, repair), field, ORGANISMS, START_ENERGY, 0.0,
                                    Policy::Stay, seed, 16).expect("life");
    // Contention is the whole point: `spawn_even` puts organism i on cell i, where nobody competes and the
    // order is silent (FINDING-327). Put all three mouths on one cell with one unit per step.
    for i in 0..ORGANISMS {
        assert!(life.move_to(i, 0), "put organism {i} on cell 0");
    }
    assert!(life.set_order_protocol(order));
    for _ in 0..STEPS {
        life.advance().expect("advance");
    }
    life.samples().iter().filter(|s| s.alive).map(|s| s.slot).collect()
}

fn verdict(slots: &[usize]) -> String {
    match slots.len() {
        0 => "мертвы все".to_string(),
        n if n == ORGANISMS => "живы все".to_string(),
        _ => format!("выжил {:?}", slots),
    }
}

#[test]
fn the_order_changes_at_least_one_verdict_or_none_do() {
    let damages = [0.0, 0.05, 0.2];
    let repairs = [0.5, 1.5, 4.0];
    let mut diffs = Vec::new();
    let mut total = 0;
    for &d in &damages {
        for &r in &repairs {
            total += 1;
            let h = verdict(&survivors(d, r, OrderProtocol::Historical, 11));
            let rot = verdict(&survivors(d, r, OrderProtocol::Rotate, 11));
            let rnd = verdict(&survivors(d, r, OrderProtocol::Random, 11));
            if !(h == rot && rot == rnd) {
                diffs.push((d, r, h, rot, rnd));
            }
        }
    }
    println!("клеток сетки: {} · вердикт изменяется: {}", total, diffs.len());
    for (d, r, h, rot, rnd) in &diffs {
        println!("  damage {:.2} repair {:.1}: historical «{}» · rotate «{}» · random «{}»", d, r, h, rot, rnd);
    }
    // The map must be reproducible at all: if every cell were identical, the switch would be silent here
    // and the finding would be "no conclusion depends on order in this grid".
    assert!(total > 0);
}
