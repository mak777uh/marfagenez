//! A niche medium designed from the survivability condition, not from taste.
//!
//! `FINDING-203` failed because a poor cell below upkeep is a grave, not a niche. The
//! arithmetic that fixes it is one line, and it also constrains the whole design:
//!
//!   steady state of a standing form on a cell is `ceiling - take/regrow`,
//!   so a cell is survivable exactly when `ceiling - take/regrow > upkeep`.
//!
//! With income 1.0, upkeep 0.6 and regrow 0.99 that means `ceiling > 1.61` for every
//! cell. A rich half at 3.0 and a poor half at 1.8 are then both survivable, and the
//! rich half is worth more than twice as much - which is what a niche is: worse, not
//! fatal.
//!
//! PREDICTION, before the run:
//!   (a) all four worlds keep a population alive; if any is empty, the design is wrong
//!       again and the result says nothing about niches;
//!   (b) the gradient world's mix differs from BOTH uniform worlds - that is what
//!       "the medium chooses" means;
//!   (c) `Random` loses in the gradient world, because a walker averages the poor and
//!       the rich while a stayer on the rich end gets the rich.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const INCOME: f64 = 1.0;
const UPKEEP: f64 = 0.6;
const REGROW: f64 = 0.99;

fn world() -> World {
    World {
        income: INCOME,
        maintenance_cost: UPKEEP,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 2,
        max_population: 24,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

fn run(field: Field, cells: usize, mutation: f64, steps: usize) -> ([usize; 5], usize) {
    let organisms: Vec<Remembering> = (0..cells)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(),
        field,
        organisms,
        vec![Policy::Random; cells],
        11,
        32,
    )
    .expect("built");
    life.set_policy_mutation(mutation);
    for _ in 0..steps {
        life.advance();
    }
    (life.policy_census(), life.organisms_alive())
}

fn main() {
    let steps = 1500;
    let mutation = 0.30;
    let cells = 12;
    println!(
        "{:<16} {:>6} {:>6} {:>8} {:>6} {:>7} {:>6}",
        "world", "stay", "random", "remember", "memory", "sighted", "alive"
    );
    for (name, field) in [
        (
            "uniform-rich",
            Field::new(cells, 3.0, REGROW).expect("field"),
        ),
        (
            "uniform-poor",
            Field::new(cells, 1.65, REGROW).expect("field"),
        ),
        (
            "gradient",
            Field::gradient(cells, 1.65, 3.0, REGROW).expect("field"),
        ),
        (
            "gradient-mut10",
            Field::gradient(cells, 1.65, 3.0, REGROW).expect("field"),
        ),
    ] {
        let m = if name == "gradient-mut10" { 0.10 } else { mutation };
        let (c, alive) = run(field, cells, m, steps);
        println!(
            "{name:<16} {:>6} {:>6} {:>8} {:>6} {:>7} {alive:>6}",
            c[0], c[1], c[2], c[3], c[4]
        );
    }
}
