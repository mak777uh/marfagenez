//! Does holding a place pay for itself when existing costs almost as much as it earns?
//!
//! `FINDING-198` showed that ownership exists and can be lost, but that its price did
//! not bite: income 2.0 against upkeep 1.0 restored the reserve faster than takes
//! spent it, so 0.1 and 2.0 gave identical numbers.
//!
//! This puts the economy at the maintenance boundary of `FINDING-176`
//! (`income = maintenance + damage_rate * repair_cost` = 1.8211) and asks whether
//! holding a cell is worth anything there.
//!
//! PREDICTION, before the run:
//!   (a) at income 1.95 (well above the boundary) both forms live to the horizon and
//!       ownership changes nothing;
//!   (b) at income 1.83 (just above the boundary) the staying form still lives, because
//!       it pays no claim price - it never moves, so it never takes a cell;
//!   (c) the wandering form dies earlier once the price is positive, because every move
//!       is a take and a take costs energy that the boundary leaves no room for;
//!   (d) with decay on, the wanderer holds fewer cells at the end than without it.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

fn world(income: f64) -> World {
    World {
        income,
        maintenance_cost: 1.7911,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 1,
        ..World::default()
    }
}

fn organisms(cells: &[usize], energy: f64) -> Vec<Remembering> {
    cells
        .iter()
        .map(|&c| {
            let o = Organism::new(energy, 0.0).expect("valid organism");
            Remembering::new(o, c, 2.0, 0.0, 32).expect("valid remembering")
        })
        .collect()
}

struct Outcome {
    lifetime0: usize,
    lifetime1: usize,
    takes: u64,
    losses: u64,
    held0: usize,
    held1: usize,
}

fn run(
    income: f64,
    cost: f64,
    decay: f64,
    steps: usize,
    claims: bool,
    trespass: f64,
) -> Outcome {
    let mut life = Life::new_mixed(
        world(income),
        Field::new(6, 3.0, 0.99).expect("valid field"),
        organisms(&[1, 4], 5.0),
        vec![Policy::Stay, Policy::Random],
        7,
        32,
    )
    .expect("built");
    if claims {
        life.enable_claims(cost, decay);
        if let Some(c) = life.claims_mut() {
            c.set_trespass(trespass);
        }
    }
    let mut lifetime0 = steps;
    let mut lifetime1 = steps;
    let mut seen0 = false;
    let mut seen1 = false;
    for step in 0..steps {
        life.advance();
        let samples = life.samples();
        if let Some(s) = samples.first() {
            if !s.alive && !seen0 {
                lifetime0 = step + 1;
                seen0 = true;
            }
        }
        if let Some(s) = samples.get(1) {
            if !s.alive && !seen1 {
                lifetime1 = step + 1;
                seen1 = true;
            }
        }
        if seen0 && seen1 {
            break;
        }
    }
    let (takes, losses, held0, held1) = match life.claims() {
        Some(c) => {
            let (t, l) = c.counts();
            (t, l, c.held_by(0), c.held_by(1))
        }
        None => (0, 0, 0, 0),
    };
    Outcome { lifetime0, lifetime1, takes, losses, held0, held1 }
}

fn main() {
    println!(
        "{:<38} {:>9} {:>9} {:>6} {:>7} {:>6} {:>6}",
        "case", "stay", "random", "takes", "losses", "held0", "held1"
    );
    for (name, income, cost, decay, claims, trespass) in [
        ("1.83 no claims", 1.83, 0.0, 0.0, false, 1.0),
        ("1.83 claims, no trespass", 1.83, 0.05, 0.0, true, 1.0),
        ("1.83 claims, stranger 0.50", 1.83, 0.05, 0.0, true, 0.50),
        ("1.83 claims, stranger 0.25", 1.83, 0.05, 0.0, true, 0.25),
        ("1.83 claims, stranger 0.00", 1.83, 0.05, 0.0, true, 0.00),
        ("1.95 claims, stranger 0.25", 1.95, 0.05, 0.0, true, 0.25),
        ("1.83 stranger 0.25, decay 0.3", 1.83, 0.05, 0.3, true, 0.25),
    ] {
        let o = run(income, cost, decay, 20000, claims, trespass);
        println!(
            "{name:<38} {:>9} {:>9} {:>6} {:>7} {:>6} {:>6}",
            o.lifetime0, o.lifetime1, o.takes, o.losses, o.held0, o.held1
        );
    }
}
