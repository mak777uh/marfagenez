//! `World::is_viable` was necessary but not sufficient for survival.
//!
//! The tests here pin down what the real condition is, and -- just as
//! importantly -- record that the obvious guess was wrong. `PLAN-NEXT.md` §3 B2
//! claimed `capacity < maintenance_cost` was the counterexample. It is not: the
//! income lands in step 1 and the maintenance is paid in step 2, so the cap
//! applied in step 5 never decides whether the maintenance can be afforded.
//! That claim is tested here as `capacity_below_maintenance_is_survivable`, so
//! the wrong guess cannot come back as a "fix".

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

/// Run a single organism on a one-cell field for `steps` and report whether it
/// is alive at the end.
///
/// The field regrows fully each step (`regrow = 1.0`), so the only thing under
/// test is the world's arithmetic, not the resource dynamics.
fn survives_from(world: World, energy: f64, steps: usize) -> bool {
    let field = Field::new(1, 10.0, 1.0).expect("field");
    let mut life = match Life::spawn_even(world, field, 1, energy, 0.0, Policy::Stay, 1, 0) {
        Some(l) => l,
        None => return false,
    };
    for _ in 0..steps {
        life.advance();
    }
    life.census().alive > 0
}

/// The same, starting from a full tank.
///
/// A full tank is a large buffer, and it hides the difference between "sustains
/// forever" and "runs on the reserve for a while": a world that loses 0.0001
/// per step survives 500 steps from a tank of 10.0 no matter what the economics
/// say. The `fires` tests therefore use a long horizon, and the boundary tests
/// say explicitly what horizon they are claiming.
fn survives(world: World, steps: usize) -> bool {
    survives_from(world, world.capacity, steps)
}

// ---------------------------------------------------------------------------
// silent: on a healthy world the new predicate agrees with the old one.
// ---------------------------------------------------------------------------

#[test]
fn default_world_sustains_and_is_viable() {
    let world = World::default();
    assert!(
        world.is_viable(),
        "default world must fill faster than it leaks"
    );
    assert!(
        world.sustains(),
        "default world must also pay for its own repair"
    );
    assert!(
        survives(world, 500),
        "and an organism must actually survive there"
    );
}

// ---------------------------------------------------------------------------
// fires: the defect this test exists for. `is_viable` says yes, the organism
// dies of damage.
// ---------------------------------------------------------------------------

#[test]
fn cheap_income_but_expensive_repair_is_viable_but_does_not_sustain() {
    // Surplus per step: 1.0 - 0.5 = 0.5.
    // Repair price per step: 0.05 * 100.0 = 5.0.
    // The surplus can never buy the repair, so damage runs to 1.0.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.5,
        repair_cost: 100.0,
        damage_rate: 0.05,
        ..World::default()
    };

    assert!(
        world.is_viable(),
        "the tank does fill: this is the trap, not a typo"
    );
    assert!(
        !world.sustains(),
        "but one step's surplus cannot buy one step's repair"
    );
    assert!(
        !survives(world, 500),
        "and the organism must actually be dead -- otherwise the predicate \
         is a slogan, not a measurement"
    );
}

// ---------------------------------------------------------------------------
// specific: the boundary is non-strict, and `capacity` is not the condition.
// ---------------------------------------------------------------------------

#[test]
fn capacity_below_maintenance_is_survivable() {
    // `PLAN-NEXT.md` B2 claimed this world kills an organism in one step.
    // It does not. Income arrives in step 1, maintenance is paid in step 2, and
    // only step 5 applies the cap -- so `capacity < maintenance_cost` never
    // stops the maintenance from being paid.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.9,
        capacity: 0.5,
        ..World::default()
    };

    assert!(world.is_viable());
    assert!(world.sustains(), "surplus 0.1 >= repair 0.015");
    assert!(
        survives(world, 500),
        "the claimed counterexample is not one: the organism lives"
    );
}

#[test]
fn surplus_just_above_repair_price_survives() {
    // Surplus: 1.0 - 0.8 = 0.2. Repair price: 0.2 * 1.0 = 0.2.
    // A margin of 1e-6 is enough to make the strict test `price < energy` hold
    // on every step, so the steady state is real and not a rounding accident.
    //
    // The exact boundary is NOT tested as survivable, even though `sustains`
    // uses `>=`. At exact equality the step's arithmetic is `energy - price`
    // with both sides equal, and the result depends on the accumulated rounding
    // of the previous 500 steps: it survives or dies depending on the path, not
    // on the parameters. `sustains` answers the mathematical question; the
    // simulation answers the floating-point one, and they agree only away from
    // the boundary. This test pins the side where they do.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.8,
        repair_cost: 1.0,
        damage_rate: 0.2,
        ..World::default()
    };
    let with_margin = World {
        income: 1.0 + 1e-6,
        ..world
    };

    assert!(with_margin.sustains());
    assert!(
        survives(with_margin, 500),
        "a margin above the boundary must survive"
    );
}

#[test]
fn a_hair_below_the_boundary_kills() {
    // The same world with the surplus a hair below the repair price.
    // This is the `specific` half: the test above passes because of the
    // boundary, not because the predicate is always true.
    //
    // A deficit of 0.0001 per step is still a deficit. The reserve is `capacity`
    // = 10.0, so it takes more than 100_000 steps to run out -- which is the
    // point: `sustains` answers "indefinitely", and "not for 500 steps" is not
    // the same claim. The horizon here is chosen to outlast the reserve.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.8001,
        repair_cost: 1.0,
        damage_rate: 0.2,
        ..World::default()
    };

    assert!(!world.sustains());
    assert!(
        !survives(world, 200_000),
        "a permanent deficit of 0.0001 per step must end in death once the \
         reserve is gone -- if it does not, the reserve is not finite and \
         `sustains` is measuring the wrong thing"
    );
}

#[test]
fn capacity_does_not_change_sustainability() {
    // Same economics, different tank sizes: the verdict must not move.
    let base = World {
        income: 1.0,
        maintenance_cost: 0.5,
        repair_cost: 100.0,
        damage_rate: 0.05,
        ..World::default()
    };
    for capacity in [0.1, 0.5, 2.0, 10.0, 1000.0] {
        let world = World { capacity, ..base };
        assert!(
            !world.sustains(),
            "capacity {} must not rescue an unpayable repair",
            capacity
        );
        assert!(
            !survives(world, 500),
            "capacity {} must not rescue survival either",
            capacity
        );
    }
}

// ---------------------------------------------------------------------------
// The limit of the predicate: `sustains` is a long-run statement, and a big
// enough reserve postpones the failure past any short horizon.
// ---------------------------------------------------------------------------

#[test]
fn a_full_tank_can_outlive_a_short_horizon_even_when_the_world_does_not_sustain() {
    // Surplus 0.9, repair price 1.5: the world does not sustain.
    // But the organism starts with 10.0 in the tank, and each step it repairs
    // out of the reserve rather than out of the surplus. It survives until the
    // reserve is gone -- which is a long time, not forever.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.1,
        damage_rate: 1.0,
        ..World::default()
    };

    assert!(world.is_viable());
    assert!(
        !world.sustains(),
        "surplus 0.9 < repair price 1.5: no steady state exists"
    );
    assert!(
        survives(world, 10),
        "the reserve carries it for a while -- this is why `sustains` says \
         'indefinitely' and not 'next step'"
    );
    assert!(
        !survives(world, 5000),
        "but not forever: the reserve is finite"
    );
}
