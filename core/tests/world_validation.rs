//! # `World` must reject values that make the model meaningless
//!
//! `World` has `pub` fields and no constructor, so any caller can build a world
//! whose parameters are `NaN`, infinite or negative. The arithmetic does not
//! fail loudly on those: it silently produces an organism that cannot die.
//!
//! ## The defect this test was written for
//!
//! With `maintenance_cost = NaN`:
//!
//! 1. `energy -= NaN` makes `energy` NaN;
//! 2. `NaN.min(capacity)` returns `capacity`, because `f64::min` returns the
//!    non-NaN argument when exactly one side is NaN -- so the NaN is silently
//!    erased, not propagated;
//! 3. `.max(0.0)` leaves it at `capacity`;
//! 4. the death test `energy <= 0.0` is `false` for a real number, so the
//!    organism survives on a full tank forever, paying nothing.
//!
//! `income = NaN` is the mirror image: `resource.min(NaN)` returns `resource`,
//! so the organism drains a cell completely instead of at the income rate.
//! A negative `maintenance_cost` is free survival by construction.
//!
//! ## What the fix is
//!
//! `World::validate()` returns `Err` naming the first bad field, and `Life`
//! refuses to be built from an invalid world. The fields stay `pub` because 26
//! call sites build `World { .. , read_period: 1, }` literals; the validation lives at the point
//! where a world starts driving a simulation.
//!
//! NOTE: the Lean runtime aborts the process on `panic!`, so failures are
//! reported by returning `Err`, not by `assert!`.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{Organism, World};

/// `silent`: the default world is valid and stays valid.
#[test]
fn default_world_is_valid() -> Result<(), String> {
    let world = World::default();
    match world.validate() {
        Ok(()) => Ok(()),
        Err(e) => Err(format!("default world rejected: {e}")),
    }
}

/// `fires`: `maintenance_cost = NaN` is rejected, and would have been fatal.
#[test]
fn nan_maintenance_is_rejected() -> Result<(), String> {
    let mut world = World::default();
    world.maintenance_cost = f64::NAN;

    // Show the defect is real, not hypothetical: drive one organism and see it
    // survive a step it should not survive.
    let mut org = Organism::new(0.1, 0.0).ok_or("organism is None")?;
    let survived = org.step(&world, 0.0);
    println!(
        "NaN maintenance: energy {:.6}, alive {}, survived {}",
        org.energy(),
        org.is_alive(),
        survived
    );
    if !survived {
        return Err(
            "the NaN world did not produce an immortal organism -- the defect \
             this test guards is gone, so the guard may be unnecessary"
                .to_string(),
        );
    }

    match world.validate() {
        Ok(()) => Err(
            "World::validate accepted maintenance_cost = NaN -- an organism \
             with no upkeep cannot die"
                .to_string(),
        ),
        Err(e) => {
            println!("rejected as expected: {e}");
            Ok(())
        }
    }
}

/// `fires`: `Life` refuses to start from an invalid world.
#[test]
fn life_refuses_invalid_world() -> Result<(), String> {
    let mut world = World::default();
    world.maintenance_cost = f64::NAN;

    let field = Field::new(1, 10.0, 1.0).ok_or("field is None")?;
    match Life::spawn_even(world, field, 1, 5.0, 0.0, Policy::Stay, 1, 0) {
        Some(_) => Err(
            "Life::spawn_even accepted a world with maintenance_cost = NaN; \
             the simulation must refuse to start rather than produce an \
             immortal organism"
                .to_string(),
        ),
        None => Ok(()),
    }
}

/// `specific`: the other bad fields are rejected too, and each names itself.
#[test]
fn each_bad_field_is_named() -> Result<(), String> {
    let cases: [(&str, fn(&mut World), &str); 6] = [
        ("income", |w| w.income = f64::NAN, "income"),
        ("income negative", |w| w.income = -1.0, "income"),
        ("maintenance negative", |w| w.maintenance_cost = -0.5, "maintenance_cost"),
        ("damage_rate infinite", |w| w.damage_rate = f64::INFINITY, "damage_rate"),
        ("repair_cost negative", |w| w.repair_cost = -1.0, "repair_cost"),
        ("capacity zero", |w| w.capacity = 0.0, "capacity"),
    ];

    for (label, mutate, field_name) in cases {
        let mut world = World::default();
        mutate(&mut world);
        match world.validate() {
            Ok(()) => {
                return Err(format!("World::validate accepted {label}"));
            }
            Err(e) => {
                println!("{label}: {e}");
                if !e.contains(field_name) {
                    return Err(format!(
                        "{label}: error does not name `{field_name}`, so the \
                         caller cannot tell which field to fix: {e}"
                    ));
                }
            }
        }
    }
    Ok(())
}

/// `specific`: a world that is merely *unviable* is still valid.
///
/// `income <= maintenance_cost` means nothing can live, but that is a
/// scientific finding, not a malformed input. `validate` must not conflate the
/// two: `is_viable` answers the modelling question, `validate` answers the
/// "is this a number" question.
#[test]
fn unviable_world_is_still_valid() -> Result<(), String> {
    let mut world = World::default();
    world.income = 0.1;
    world.maintenance_cost = 0.6;

    if world.is_viable() {
        return Err("world should be unviable".to_string());
    }
    match world.validate() {
        Ok(()) => Ok(()),
        Err(e) => Err(format!(
            "an unviable but well-formed world was rejected: {e} -- \
             unviability is a finding, not a malformed input"
        )),
    }
}
