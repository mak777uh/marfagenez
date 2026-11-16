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
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, ShareProtocol, World};

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

/// `fires`: the share is counted over the LIVING, so a death frees it.
///
/// `Life::advance_with` fills `share_counts` from `r.organism.is_alive()` only
/// (`core/src/life.rs:334-345`) and hands out `remaining / k`, where `k` is the
/// number of not-yet-eaten LIVE organisms on the cell
/// (`core/src/life.rs:618-630`). A dead organism is skipped by the `continue`
/// at the top of the loop, so from the step after a death the survivors divide
/// one `income` among fewer mouths. This test pins that number: it fails if
/// `share_counts` is built over every slot instead of the live ones.
///
/// The world makes the death inevitable and the rescue visible with no repair
/// and no damage: `income = 1.0`, `maintenance = 0.6`. Two organisms split the
/// income, so each nets `0.5 - 0.6 = -0.1` per step; the weak one
/// (`energy = 0.5`) dies within the first few steps, the strong one
/// (`energy = 5.0`) would die around the fiftieth. After the weak one's death
/// the survivor eats the whole `income` and nets `+0.4`, so it lives.
///
/// The injected defect (`share_counts` over all slots, dead included) keeps
/// `k = 2` for ever: the survivor takes `0.5`, nets `-0.1`, and dies around
/// the fiftieth step. The `taken > income / 2` assertion is what catches it.
#[test]
fn a_dead_organism_frees_its_share() -> Result<(), String> {
    let mut world = world_proportional();
    world.maintenance_cost = 0.6;
    world.damage_rate = 0.0;
    world.repair_cost = 0.0;
    world.capacity = 1000.0;

    let field = Field::new(1, 10.0, 1.0).ok_or("field is None")?;
    let weak = Remembering::new(
        Organism::healthy(0.5).ok_or("weak is None")?,
        0,
        0.0,
        0.0,
        0,
    )
    .ok_or("weak remembering is None")?;
    let strong = Remembering::new(
        Organism::healthy(5.0).ok_or("strong is None")?,
        0,
        0.0,
        0.0,
        0,
    )
    .ok_or("strong remembering is None")?;
    let mut life = Life::new(world, field, vec![weak, strong], Policy::Stay, 1, 0)
        .ok_or("life is None")?;

    // One record per step: (step, taken per slot, alive per slot).
    let mut steps: Vec<(usize, [f64; 2], [bool; 2])> = Vec::new();
    for _ in 0..200 {
        if life.advance().is_none() {
            break;
        }
        let mut taken = [0.0f64; 2];
        let mut alive = [false; 2];
        for s in life.samples() {
            if s.slot < 2 {
                taken[s.slot] = s.taken;
                alive[s.slot] = s.alive;
            }
        }
        steps.push((life.step(), taken, alive));
        if !alive[0] && !alive[1] {
            break;
        }
    }

    let weak_death = steps
        .iter()
        .position(|(_, _, a)| !a[0])
        .ok_or("the weak organism never died: the scenario did not happen")?;
    if let Some(sd) = steps.iter().position(|(_, _, a)| !a[1]) {
        return Err(format!(
            "the strong organism died at step {} (the weak died at step {}): \
             the dead organism still occupies its share, so k never fell",
            steps[sd].0, steps[weak_death].0
        ));
    }
    if steps.len() < 100 {
        return Err(format!(
            "the run is only {} steps long: the strong organism used to die \
             around step 50 in this world, so a short run cannot show the rescue",
            steps.len()
        ));
    }
    if steps[weak_death].0 > 20 {
        return Err(format!(
            "the weak organism died at step {}, expected within the first few \
             steps: the world is not the one this test describes",
            steps[weak_death].0
        ));
    }

    // While both are alive the split is exact: 0.5 + 0.5 = income.
    for (step, taken, _) in &steps[..=weak_death] {
        let sum = taken[0] + taken[1];
        if (taken[1] - 0.5).abs() > 1e-12 || (sum - 1.0).abs() > 1e-12 {
            return Err(format!(
                "step {}: while both are alive the split must be 0.5 + 0.5 = \
                 1.0, got {} + {} = {}",
                step, taken[0], taken[1], sum
            ));
        }
    }
    // After the death one income goes to one mouth: the share is freed.
    let after: Vec<f64> = steps[weak_death + 1..]
        .iter()
        .map(|(_, taken, _)| taken[1])
        .collect();
    if after.is_empty() {
        return Err("there is no step after the weak organism's death".to_string());
    }
    for got in &after {
        if (got - 1.0).abs() > 1e-12 {
            return Err(format!(
                "after the death the survivor must take the whole income 1.0, \
                 got {got}"
            ));
        }
    }
    let rise = after[0] - 0.5;
    if after[0] <= 0.5 {
        return Err(format!(
            "the survivor takes {} after the death, not more than income/2 = \
             0.5: the dead organism still counts in share_counts",
            after[0]
        ));
    }
    println!(
        "weak died at step {}; survivor's share rose by {:.6} (0.5 -> {:.6}); \
         the survivor is alive at step {} (it would have died around 50 without \
         the freed share)",
        steps[weak_death].0,
        rise,
        after[0],
        steps[steps.len() - 1].0
    );
    Ok(())
}
