//! A phase diagram over damage and repair price, measured on the real world.
//!
//! Review 2026-11-21 (§3 "phase analysis"): thresholds had been measured one at a time, never as a map.
//! This file sweeps `damage_rate` against `repair_cost`, counts survivors after a fixed horizon, and
//! prints the map. Three qualitative facts are asserted, so the map cannot silently become noise:
//!
//! 1. no damage and no repair price -> everybody lives;
//! 2. upkeep above income -> nobody lives, whatever the damage;
//! 3. at a high damage rate, a dear repair kills more than a cheap one.
//!
//! What this file does **not** claim: that the boundaries are sharp. The grid is coarse on purpose; a
//! boundary between two cells is not located more precisely than the step between them.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

const STEPS: usize = 200;
const START_ENERGY: f64 = 5.0;
const ORGANISMS: usize = 3;

fn world(damage: f64, repair: f64, income: f64, maintenance: f64) -> World {
    World {
        income,
        maintenance_cost: maintenance,
        repair_cost: repair,
        damage_rate: damage,
        capacity: 10.0,
        read_budget: 0,
        ..World::default()
    }
}

fn survivors(w: World) -> usize {
    let field = Field::new(4, 1.0, 1.0).expect("field refilled every step");
    let mut life = Life::spawn_even(w, field, ORGANISMS, START_ENERGY, 0.0, Policy::Stay, 7, 16)
        .expect("life");
    for _ in 0..STEPS {
        life.advance().expect("advance");
    }
    life.samples().iter().filter(|s| s.alive).count()
}

#[test]
fn the_phase_map_has_the_three_expected_corners() {
    // 1. no damage, free repair: nobody dies.
    assert_eq!(
        survivors(world(0.0, 0.0, 1.0, 0.6)),
        ORGANISMS,
        "an undamaged world with free repair must keep everybody alive"
    );

    // 2. upkeep above income: nobody lives, even with no damage at all.
    assert_eq!(
        survivors(world(0.0, 0.0, 1.0, 1.2)),
        0,
        "upkeep above income must kill, whatever the damage"
    );

    // 3. high damage: a dear repair kills more than a cheap one.
    let cheap = survivors(world(0.2, 0.5, 1.0, 0.6));
    let dear = survivors(world(0.2, 4.0, 1.0, 0.6));
    assert!(
        dear <= cheap,
        "a dearer repair must not save more lives: cheap {cheap}, dear {dear}"
    );
}

#[test]
fn print_the_map() {
    // Not an assertion: the table is the artifact. Run with `-- --nocapture` to see it.
    let damages = [0.0, 0.01, 0.05, 0.2];
    let repairs = [0.0, 0.5, 1.5, 4.0];
    println!("выживших из {} через {} шагов (доход 1.0, содержание 0.6)", ORGANISMS, STEPS);
    print!("damage\\repair");
    for r in repairs {
        print!(" {:>6.1}", r);
    }
    println!();
    for d in damages {
        print!("{:>12.2}", d);
        for r in repairs {
            print!(" {:>6}", survivors(world(d, r, 1.0, 0.6)));
        }
        println!();
    }
}
