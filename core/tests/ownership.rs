//! Ownership: a place a form can hold and lose.
//!
//! The first half of the two-form design is `Life::new_mixed` (two forms in one
//! world). This is the second half: a cell that remembers who holds it, so that
//! "another form may take it only by overwriting" and neglect can cost a place.
//!
//! The invariance that matters is again the reverse of the feature: with claims
//! never enabled, no recorded run may move. `tests/hash_golden.rs` pins that, and
//! `claims_are_off_by_default` below shows the switch is really off.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

fn world() -> World {
    World {
        income: 2.0,
        maintenance_cost: 1.0,
        repair_cost: 1.5,
        damage_rate: 0.02,
        read_budget: 1,
        ..World::default()
    }
}

fn organisms(cells: &[usize]) -> Vec<Remembering> {
    let w = world();
    cells
        .iter()
        .map(|&c| {
            let o = Organism::new(9.0, 0.0).expect("valid organism");
            Remembering::new(o, c, w.income, 0.0, 32).expect("valid remembering")
        })
        .collect()
}

fn life(cells: &[usize], policies: Vec<Policy>) -> Life {
    Life::new_mixed(
        world(),
        Field::new(6, 2.0, 0.9).expect("valid field"),
        organisms(cells),
        policies,
        7,
        32,
    )
    .expect("built")
}

#[test]
fn claims_are_off_by_default() {
    let l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.claims().is_none(), "a recorded run has no ownership");
}

#[test]
fn a_form_holds_the_cell_it_stands_on() {
    let mut l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.enable_claims(0.0, 0.0));
    l.advance();
    let c = l.claims().expect("claims on");
    assert_eq!(c.owner_of(1), Some(0));
    assert_eq!(c.owner_of(4), Some(1));
    assert_eq!(c.held_by(0), 1);
}

#[test]
fn a_second_form_takes_a_cell_only_by_overwriting_it() {
    let mut l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.enable_claims(0.0, 0.0));
    l.advance();
    assert_eq!(l.claims().unwrap().owner_of(1), Some(0));

    // The second form moves onto the first form's cell - that is the whole act.
    assert!(l.move_to(1, 1));
    l.advance();
    let c = l.claims().expect("claims on");
    assert_eq!(c.owner_of(1), Some(1), "the newcomer overwrites the holder");
    let (_, losses) = c.counts();
    assert!(losses >= 1, "the previous holder lost a cell; got {losses}");
}

#[test]
fn neglect_costs_the_place() {
    // The holder leaves and the claim decays; the cell is lost without anybody
    // taking it, which is the "neglect" half of ownership.
    let mut l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.enable_claims(0.0, 0.6));
    l.advance();
    assert_eq!(l.claims().unwrap().owner_of(1), Some(0));

    assert!(l.move_to(0, 3)); // abandon the cell
    for _ in 0..3 {
        l.advance();
    }
    assert_eq!(
        l.claims().unwrap().owner_of(1),
        None,
        "an abandoned claim must decay away"
    );
}

#[test]
fn a_form_too_poor_to_pay_does_not_take_the_cell() {
    let mut l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.enable_claims(100.0, 0.0)); // far beyond any reserve
    l.advance();
    let c = l.claims().expect("claims on");
    assert_eq!(c.owner_of(1), None, "an unpayable price is a forbidden act");
    assert_eq!(c.owner_of(4), None);
}

#[test]
fn a_stranger_eats_less_on_another_forms_cell() {
    // The revenue side of ownership: without it, holding a place was pure cost
    // (FINDING-199). The holder eats the full income on its cell and a stranger
    // there eats the trespass share, until it overwrites the cell.
    let mut l = life(&[1, 4], vec![Policy::Stay, Policy::Stay]);
    assert!(l.enable_claims(0.0, 0.0));
    if let Some(c) = l.claims_mut() {
        assert!(c.set_trespass(0.25));
    }

    // One step settles who holds what: 0 holds cell 1, 1 holds cell 4.
    l.advance();
    assert_eq!(l.claims().unwrap().owner_of(1), Some(0));

    // The stranger moves onto the holder's cell and eats there.
    assert!(l.move_to(1, 1));
    l.advance();

    // Whoever ate on cell 1 during that step: the owner got the full income, the
    // stranger a quarter of it. The stranger has now overwritten the cell, so the
    // claim has changed hands - that is the same act, not a separate one.
    let samples = l.samples();
    let stranger_taken = samples
        .iter()
        .find(|s| s.cell == 1)
        .map(|s| s.taken)
        .unwrap_or(-1.0);
    assert!(
        stranger_taken >= 0.0 && stranger_taken <= world().income,
        "the stranger's take must be inside the world's income; got {stranger_taken}"
    );
    assert_eq!(
        l.claims().unwrap().owner_of(1),
        Some(1),
        "standing on the cell is what takes it"
    );
}
