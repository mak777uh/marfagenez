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
use medium_core::organism::{Organism, World};

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
    // The exact boundary is NOT tested as survivable. `sustains` now uses the
    // same strict affordability relation as repair (`price < energy`), so at
    // exact equality it returns false. `docs/FINDING-148.md` records the older
    // arithmetic `<=` formulation and the three floating-point equality cases;
    // this test pins the executable side of the first one.
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
    // point: `sustains` answers "the per-step price is payable on every step",
    // and "not for 500 steps" is not the same claim. The horizon here is
    // chosen to outlast the reserve.
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
fn capacity_does_not_rescue_an_unpayable_per_step_repair() {
    // Same economics, different tank sizes: the verdict of the *per-step*
    // test must not move. This is not a claim that capacity is irrelevant --
    // `docs/FINDING-148.md` and `tests/sustainability.rs`'s
    // `the_cadence_condition_of_finding_145_is_not_the_boundary_of_life`
    // show that the cap sets the largest deferred payment;
    // `dr = 0.03` below is in the per-step branch, where the cap cannot help.
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
// The limit of the predicate: `sustains` is a per-step price test, and a big
// enough reserve postpones the failure of the per-step arithmetic past any
// short horizon -- and, when the payment is deferred, the reserve is what pays.
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

// ---------------------------------------------------------------------------
// The limit of `sustains` itself. `docs/FINDING-148.md` measured the criterion
//
//     alive <=> dr*rc <= s OR (rc <= K*s AND rc < capacity + s)
//
// so a predicate that asks only the first disjunct is a price test. The two
// tests below are the points where that shows. They are the gate for the doc
// comment on `sustains`: if it is ever rewritten back into "the boundary of
// life", or if the predicate is swapped for the cadence condition of
// `FINDING-145`, they fail.
// ---------------------------------------------------------------------------

#[test]
fn sustains_is_false_at_exact_repair_price_and_is_not_life_boundary() {
    // `dr = 0.03` is a tooth of the damage clock (`K = 34`, so the cadence
    // edge is 34*0.4 = 13.6), and `rc = 0.4/0.03` makes the per-step price
    // exactly the step's surplus: `dr*rc == 0.4` in doubles. `sustains()` must
    // use the same strict relation as repair and therefore return `false`.
    //
    // Starting from a zero reserve the organism holds exactly `k*0.4` after
    // `k` steps and is charged exactly `k*0.4` for the damage it carries, so
    // the strict test `price < energy` in step 4 is false on every step: no
    // repair is ever paid. The damage reaches 1.0 at step 34 with the tank at
    // the cap, because one deferred repair costs `rc = 13.33...` and the cap
    // allows `capacity + surplus = 10.4`. The predicate says the price is not
    // strictly affordable; the organism dies of damage.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 13.333333333333334,
        damage_rate: 0.03,
        capacity: 10.0,
        ..World::default()
    };
    let surplus = world.income - world.maintenance_cost;
    assert_eq!(
        world.damage_rate * world.repair_cost,
        surplus,
        "the point is the exact equality `dr*rc == surplus`, not a near miss"
    );
    assert!(
        !world.sustains(),
        "strict affordability must reject exact equality: {} == {}",
        surplus,
        world.damage_rate * world.repair_cost
    );

    let mut organism = Organism::healthy(0.0).expect("a zero reserve is a legal state");
    let mut steps = 0;
    while organism.step(&world, world.income) {
        steps += 1;
        assert!(steps < 10_000, "it must die of damage, not live on");
    }
    assert!(
        organism.damage() >= 1.0,
        "the cause must be damage, got damage = {}",
        organism.damage()
    );
    assert!(
        organism.energy() >= world.capacity - 1e-12,
        "and not starvation: the reserve at death is {} of {}",
        organism.energy(),
        world.capacity
    );
    assert!(
        world.repair_cost > world.capacity + surplus,
        "one deferred repair must cost more than the deepest reserve: {} > {}",
        world.repair_cost,
        world.capacity + surplus
    );

    // The same world, the same predicate, a full tank: it lives, because the
    // per-step payment is now strictly cheaper than the reserve. What decides
    // is the reserve the organism carries, which is exactly what `sustains`
    // does not look at.
    assert!(
        survives(world, 500),
        "from a full tank the same world lives -- the predicate is not the boundary"
    );
}

#[test]
fn the_cadence_condition_of_finding_145_is_not_the_boundary_of_life() {
    // The counterexample of `docs/FINDING-148.md` O3, verbatim:
    // `dr = 0.03`, `income = 1.0`, `maint = 0.6`, `rc = 13.466666666666669`,
    // `capacity = 10`, `energy0 = 5`.
    //
    // FINDING-145's condition holds: `ceil(1/dr)*s = 34*0.4 = 13.6 >= 13.47`.
    // The per-step price is 0.404 > s = 0.4, so the payment is deferred; the
    // reserve at the repair test is at most `capacity + s = 10.4 < rc`, so the
    // payment is never made. The organism dies of damage at step 1284 holding
    // a full tank -- there is no starvation anywhere in this run.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 13.466666666666669,
        damage_rate: 0.03,
        capacity: 10.0,
        ..World::default()
    };
    let surplus = world.income - world.maintenance_cost;
    let cadence = 34.0 * surplus; // ceil(1/0.03) = 34 on this grid
    assert!(
        cadence >= world.repair_cost,
        "FINDING-145 must call this point alive: {} >= {}",
        cadence,
        world.repair_cost
    );
    assert!(
        !world.sustains(),
        "and `sustains` must already refuse it -- the per-step price {} > {}",
        world.damage_rate * world.repair_cost,
        surplus
    );
    assert!(
        world.repair_cost > world.capacity + surplus,
        "the deferred payment must cost more than the deepest reserve"
    );

    let mut organism = Organism::healthy(5.0).expect("five units of reserve");
    // `steps` counts successful steps, so the step that kills it is 1284 and
    // the loop stops with 1283 behind it. `rho_probe` reports the death step.
    let mut steps = 0;
    while organism.step(&world, world.income) {
        steps += 1;
        assert!(steps < 100_000, "it must die of damage, not live on");
    }
    assert_eq!(steps, 1283, "the measured lifetime of this point");
    assert!(organism.damage() >= 1.0, "the cause must be damage");
    assert!(
        organism.energy() >= world.capacity - 1e-12,
        "it dies holding the cap, not starving: {} of {}",
        organism.energy(),
        world.capacity
    );
}

// ---------------------------------------------------------------------------
// The comment is a claim, so it gets a gate of its own.
// ---------------------------------------------------------------------------

/// The doc comment on `World::sustains` must name the limit it was measured to
/// have, and must not drift back to the promise it was demoted from.
///
/// `cargo test` cannot read prose, so the source is included as text and the
/// `///` block immediately above `pub fn sustains` is checked. This is the
/// point of the gate: the two tests above pin the numbers the comment talks
/// about, and this one pins the sentence itself, so restoring "whether an
/// organism can live here indefinitely" -- or dropping the reference to the
/// finding that refuted it -- fails a test instead of surviving as a comment
/// nobody re-reads.
#[test]
fn the_doc_comment_on_sustains_names_the_limit_it_has() {
    const SOURCE: &str = include_str!("../src/organism.rs");

    let at = SOURCE
        .find("pub fn sustains(&self) -> bool")
        .expect("`sustains` must exist in organism.rs");
    let head: Vec<&str> = SOURCE[..at].lines().collect();
    // The contiguous `///` block immediately above the function, and nothing
    // else: `is_viable`'s documentation also mentions `sustains`.
    // The slice ends in the indentation of the `pub fn` line, so trailing
    // blank lines go first, then the contiguous `///` block is taken.
    let mut end = head.len();
    while end > 0 && head[end - 1].trim().is_empty() {
        end -= 1;
    }
    let mut start = end;
    for i in (0..end).rev() {
        if head[i].trim_start().starts_with("///") {
            start = i;
        } else {
            break;
        }
    }
    let doc = head[start..end].join("\n");
    assert!(
        doc.contains("per-step price"),
        "the comment must say which price the predicate tests:\n{}",
        doc
    );
    assert!(
        doc.contains("not the boundary of life"),
        "and that it is not the boundary:\n{}",
        doc
    );
    assert!(
        doc.contains("FINDING-148"),
        "the finding that measured the limit must be cited:\n{}",
        doc
    );
    assert!(
        doc.contains("FINDING-145"),
        "and so must the cadence condition it is not:\n{}",
        doc
    );
    assert!(
        doc.contains("capacity + surplus"),
        "the second half of the measured criterion must be named:\n{}",
        doc
    );
    assert!(
        !doc.contains("can live here indefinitely"),
        "the demoted promise is back; it was refuted by docs/FINDING-148.md:\n{}",
        doc
    );
}
