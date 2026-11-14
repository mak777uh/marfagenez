// EXP-79: why does a sighted organism on a poor cell stand still when both
// neighbours are richer?
//
// EXP-78 ran `--layout even` with 40 cells and n = 40 -- one organism per
// cell -- on an alternating field, and every arm froze at occ = 1 1 1 ...
// with `moving = 0`. With n = 80 the same field froze at occ = 2 1 2 1 ...
// with 60 alive. The policy says a poor cell's organism must move: its
// level is 1.35 and both neighbours are 2.15, so `best > here`.
//
// This file lived as `core/src/_exp79_test.rs`, which no `mod` declared, so
// it never compiled and never ran. It is a test, not library code: it moved
// here, where `cargo test` finds it.
//
// These four assertions separate the possible causes. They are the arms of
// `checks/exp79_why_the_poor_cell_organism_stands_still.py`; the test name
// is what that script greps for, so keep the `assert!` messages starting
// with the arm letter.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{Organism, World};

#[test]
fn exp79_the_poor_cell_organism_decides_to_move() {
    // A. A free move must not be refused. `spend` is the gate in
    //    `Life::advance`: `if direction != 0 && r.organism.spend(cost)`.
    //    If `spend(0.0)` returned false, every `move_cost = 0` arm in the
    //    project would be a population that silently cannot move.
    let mut o = Organism::healthy(10.0).expect("healthy organism");
    let before = o.energy();
    let paid = o.spend(0.0);
    assert!(
        paid,
        "A_spend_zero_is_true: spend(0.0) returned false, so a free move is \
         refused and every move_cost = 0 arm measures the refusal, not the \
         policy"
    );
    assert_eq!(o.energy(), before, "A: spend(0.0) must not change energy");

    // B. And it must still refuse a move it cannot pay for.
    let mut poor = Organism::healthy(0.3).expect("healthy organism");
    let refused = poor.spend(0.5);
    assert!(
        !refused,
        "B_spend_more_than_there_is_is_false: spend(0.5) with 0.3 energy \
         returned true"
    );
    assert_eq!(poor.energy(), 0.3, "B: a refused spend must not change energy");

    // C. The decision itself. One organism on cell 1 of a four-cell
    //    alternating field: cell 1 is poor (1.6), cells 0 and 2 are rich
    //    (2.4). `Sighted` reads both neighbours and must step toward one.
    let world = World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.05,
        capacity: 10.0,
        read_budget: 3,
        ..World::default()
    };
    let field = Field::alternating(4, 2.4, 1.6, 0.8).expect("alternating field");
    let mut life = Life::spawn(world, field, 1, 10.0, 0.0, Policy::Sighted, 1, 100000)
        .expect("one organism");
    assert!(life.move_to(0, 1), "C: organism 0 should move to cell 1");
    assert_eq!(life.samples()[0].cell, 1, "C: starts on the poor cell");

    let samples = life.samples();
    let start = samples[0].cell;
    life.advance().expect("one step");
    let after_step = life.samples();
    let d = after_step[0].direction;
    assert_ne!(
        d, 0,
        "C_poor_cell_organism_moves: on a poor cell (1.35) with two rich \
         neighbours (2.15) the sighted policy chose direction 0. The \
         policy in life.rs is not 'step toward the richer neighbour'."
    );
    assert_ne!(
        after_step[0].cell, start,
        "C: the direction was {} but the cell did not change, so the move \
         was refused after the decision",
        d
    );

    // D. The charge is the parameter and nothing else. The same start with
    //    move_cost 0.05 must end 0.05 lower in energy than arm C.
    //
    //    The tank must not hide the charge. In arm C the organism starts
    //    full (10.0 = capacity), earns 1.0 and pays 0.6, so the step ends
    //    +0.4 and the cap at 10.0 swallows any move cost: both arms end at
    //    exactly 10.0 and the charge is invisible. A first version of this
    //    arm asserted the difference anyway and failed with
    //    "free arm ended at 10, paid arm at 10, difference 0 instead of
    //    0.05". Income is therefore set equal to maintenance here, so the
    //    only thing that can move the energy is the move.
    let tight = World {
        income: 1.0,
        maintenance_cost: 1.0,
        ..world
    };
    let mut free_life = Life::spawn(
        tight,
        Field::alternating(4, 2.4, 1.6, 0.8).expect("field"),
        1,
        10.0,
        0.0,
        Policy::Sighted,
        1,
        100000,
    )
    .expect("one organism");
    assert!(free_life.move_to(0, 1), "D: organism 0 should move to cell 1");
    free_life.advance().expect("one step");
    let free_energy = free_life.samples()[0].energy;

    let mut paid_life = Life::spawn(
        tight,
        Field::alternating(4, 2.4, 1.6, 0.8).expect("field"),
        1,
        10.0,
        0.05,
        Policy::Sighted,
        1,
        100000,
    )
    .expect("one organism");
    assert!(paid_life.move_to(0, 1), "D: organism 0 should move to cell 1");
    paid_life.advance().expect("one step");
    let paid_energy = paid_life.samples()[0].energy;

    assert!(
        (free_energy - paid_energy - 0.05).abs() < 1e-12,
        "D_move_cost_is_charged_exactly: free arm ended at {}, paid arm at \
         {}, difference {} instead of 0.05",
        free_energy,
        paid_energy,
        free_energy - paid_energy
    );
}
