//! Does a form that RETURNS to its own place live longer than one that does not?
//!
//! `FINDING-200` gave ownership teeth: a stranger on another form's cell eats only a
//! trespass share. That makes holding a place worth something, and it makes a
//! testable claim out of Neill's "ownership creates care": a form that comes back to
//! its own cell should live longer than one that does not - but **only because of the
//! claim**, not because memory is generally good. Everything in this project says
//! memory is not generally good, so the control matters more than the effect.
//!
//! PREDICTION, before the run:
//!   (a) with trespass 1.0 (ownership changes nothing) the returning form is NOT
//!       reliably better than the wanderer - that is the baseline;
//!   (b) with trespass 0.50 and 0.25 the returning form lives LONGER, because it
//!       spends its meals on cells where it is the holder and eats the full income;
//!   (c) the gain grows as the stranger's share falls, since that is the price of
//!       eating somewhere else.
//!
//! If (b) holds only together with (a) - no gain without ownership, gain with it - the
//! difference is attributable to the claim and not to the policy.
//!
//! The "returning" policy is the existing `Memory`, which steps back toward the best
//! cell it has seen. No new behaviour is written for this experiment.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const MAINT: f64 = 1.7911;

fn world(income: f64) -> World {
    World {
        income,
        maintenance_cost: MAINT,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 1,
        ..World::default()
    }
}

fn organisms(cells: &[usize]) -> Vec<Remembering> {
    cells
        .iter()
        .map(|&c| {
            let o = Organism::new(5.0, 0.0).expect("valid organism");
            Remembering::new(o, c, 2.0, 0.0, 64).expect("valid remembering")
        })
        .collect()
}

/// Returns (lifetime of the returning form, lifetime of the wanderer).
fn run(policies: [Policy; 2], trespass: f64, steps: usize) -> (usize, usize) {
    let mut life = Life::new_mixed(
        world(1.83),
        Field::new(6, 3.0, 0.99).expect("valid field"),
        organisms(&[1, 4]),
        vec![policies[0], policies[1]],
        7,
        64,
    )
    .expect("built");
    life.enable_claims(0.05, 0.0);
    if let Some(c) = life.claims_mut() {
        c.set_trespass(trespass);
    }
    let mut l0 = steps;
    let mut l1 = steps;
    let mut seen0 = false;
    let mut seen1 = false;
    for step in 0..steps {
        life.advance();
        let s = life.samples();
        if let Some(a) = s.first() {
            if !a.alive && !seen0 {
                l0 = step + 1;
                seen0 = true;
            }
        }
        if let Some(b) = s.get(1) {
            if !b.alive && !seen1 {
                l1 = step + 1;
                seen1 = true;
            }
        }
        if seen0 && seen1 {
            break;
        }
    }
    (l0, l1)
}

fn main() {
    let steps = 4000;
    println!("{:>9} {:>12} {:>10} {:>8}", "trespass", "returns", "wanders", "ratio");
    for trespass in [1.0, 0.5, 0.25, 0.0] {
        let (ret, wan) = run([Policy::Memory, Policy::Random], trespass, steps);
        let ratio = ret as f64 / wan as f64;
        println!("{trespass:>9.2} {ret:>12} {wan:>10} {ratio:>8.2}");
    }
    println!();
    println!("control: the same pair with the roles swapped (returns vs stays)");
    for trespass in [1.0, 0.25] {
        let (ret, st) = run([Policy::Memory, Policy::Stay], trespass, steps);
        println!("{trespass:>9.2} returning={ret:>6} staying={st:>6}");
    }
}
