//! # `Proportional` splits one `income` per cell, and the split adds up
//!
//! `core/src/life.rs` claims:
//!
//! > the total taken from a cell never exceeds `income` however many organisms
//! > stand on it -- that is the structural difference from the sequential
//! > protocol, where the total is `k * income`.
//!
//! ## The defect this test was written for
//!
//! `share_counts` was built once before the loop and never decremented as
//! organisms ate, so an organism that ate before the crowd grew ate at the old
//! `k`. Measured on the pre-fix code: A eats alone on cell 0 (`k = 1`, takes
//! `income`), B moves onto cell 0 during the same step, B eats at `k = 2`
//! (takes `income / 2`). Total: `1.5 * income` from one cell.
//!
//! The fix gives each cell a budget of one `income` and hands out
//! `remaining / not_yet_eaten`, decrementing both as organisms eat.
//!
//! ## Why the measurement is `Sample::taken`
//!
//! The field regrows once per step, so `before + regen - after` counts the
//! regrowth as "taken" on a cell nobody ate from. Measuring the level gave a
//! false `taken = 1.0` on the untouched cell and hid the real defect.
//!
//! NOTE: the Lean runtime aborts the process on `panic!`, so failures are
//! reported by returning `Err`, not by `assert!`.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{ShareProtocol, World};

fn world_proportional() -> World {
    let mut world = World::default();
    world.share = ShareProtocol::Proportional;
    world.income = 1.0;
    world.maintenance_cost = 0.0;
    world.damage_rate = 0.0;
    world.repair_cost = 0.0;
    world.capacity = 1000.0;
    world
}

/// Control (`silent`): two organisms on one cell, both `Stay`.
///
/// Nobody moves, so the crowd never changes mid-step. The parts must add up to
/// exactly one `income`, and each organism must get exactly half of it. This is
/// the test that caught the first version of the fix, which handed out 0.5 and
/// then 0.25 because the budget shrank but the crowd did not.
#[test]
fn stay_proportional_splits_income_evenly() -> Result<(), String> {
    let field = Field::new(1, 10.0, 1.0).ok_or("field is None")?;
    let mut life =
        Life::spawn_even(world_proportional(), field, 2, 5.0, 0.0, Policy::Stay, 1, 0)
            .ok_or("life is None")?;

    life.advance().ok_or("advance returned None")?;

    let samples = life.samples();
    let total: f64 = samples.iter().map(|s| s.taken).sum();
    println!("Stay: total taken = {total:.6} (income 1.0)");
    for s in &samples {
        println!("  slot {}: taken {:.6}", s.slot, s.taken);
    }

    if (total - 1.0).abs() > 1e-9 {
        return Err(format!(
            "Stay: total taken {total}, expected exactly income 1.0 -- with no \
             movement the split must be an exact division of one income"
        ));
    }
    for s in &samples {
        if (s.taken - 0.5).abs() > 1e-9 {
            return Err(format!(
                "Stay: slot {} took {}, expected 0.5 (income / 2)",
                s.slot, s.taken
            ));
        }
    }
    Ok(())
}

/// The regression (`fires`): the crowd grows mid-step.
///
/// A stands on the rich cell 0, B on the poor cell 1. A eats first, then B
/// moves onto cell 0 and eats. Before the fix this took `1.5 * income` from
/// cell 0; now the cell's budget caps it at `income`.
#[test]
fn crowd_growing_mid_step_keeps_total_within_income() -> Result<(), String> {
    let mut world = world_proportional();
    world.read_budget = 3;

    // Cell 0 rich, cell 1 poor: a `Sighted` organism on cell 1 moves to 0.
    let field = Field::alternating(2, 10.0, 0.0, 1.0).ok_or("field is None")?;
    let mut life =
        Life::spawn_at(world, field, &[0, 1], 5.0, 0.0, Policy::Sighted, 1, 0)
            .ok_or("life is None")?;

    life.advance().ok_or("advance returned None")?;

    let samples = life.samples();
    let total: f64 = samples.iter().map(|s| s.taken).sum();
    for s in &samples {
        println!(
            "slot {}: cell {} (was {}), direction {}, taken {:.6}",
            s.slot, s.cell, s.prev_cell, s.direction, s.taken
        );
    }
    println!("total taken = {total:.6} (income 1.0)");

    // The scenario has to actually happen, or the test says nothing.
    let moved = samples.iter().any(|s| s.cell != s.prev_cell);
    if !moved {
        return Err(
            "void: nobody moved, so the crowd never grew -- the scenario did \
             not happen and this run says nothing"
                .to_string(),
        );
    }

    if total > 1.0 + 1e-9 {
        return Err(format!(
            "total taken {total} exceeds income 1.0 -- the per-cell budget is \
             not being decremented"
        ));
    }
    Ok(())
}

/// `specific`: the sequential protocol is untouched by this fix.
///
/// Under `Sequential` the total is `k * income` by design, so the same
/// scenario must still take more than one `income`. If this test started
/// failing, the fix would have leaked into the other protocol.
#[test]
fn sequential_still_takes_k_times_income() -> Result<(), String> {
    let mut world = world_proportional();
    world.share = ShareProtocol::Sequential;
    world.read_budget = 3;

    let field = Field::alternating(2, 10.0, 0.0, 1.0).ok_or("field is None")?;
    let mut life =
        Life::spawn_at(world, field, &[0, 1], 5.0, 0.0, Policy::Sighted, 1, 0)
            .ok_or("life is None")?;

    life.advance().ok_or("advance returned None")?;

    let total: f64 = life.samples().iter().map(|s| s.taken).sum();
    println!("Sequential: total taken = {total:.6} (income 1.0)");

    if total <= 1.0 + 1e-9 {
        return Err(format!(
            "Sequential: total taken {total} <= income 1.0 -- the proportional \
             fix leaked into the sequential protocol, which must still take \
             k * income"
        ));
    }
    Ok(())
}
