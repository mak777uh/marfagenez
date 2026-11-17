//! A rich patch inside a poor medium: is there now a reason to search?
//!
//! `FINDING-204` showed the gradient medium choosing weakly, and named the reason to
//! doubt it: when food is plentiful anywhere, no behaviour is better and walkers
//! dominate. The last step of the line is therefore not another mechanism but another
//! medium - islands of plenty in a poor sea.
//!
//!   poor 1.65, rich 3.0, regrowth 0.99, income 1.0, upkeep 0.6
//!   twenty-four cells, one rich cell every eight, cap twenty-four (crowding on)
//!
//! The survivability condition from `FINDING-203` holds for both levels:
//! `1.65 - 1.0/0.99 = 0.64 > 0.6` and `3.0 - 1.01 = 1.99 > 0.6`.
//!
//! PREDICTION, before the run:
//!   (a) every world keeps a population;
//!   (b) in the island world `Sighted` holds a larger share than in the poor uniform
//!       world, because a rich island is reachable only by walking toward a richer
//!       neighbour;
//!   (c) `Random` loses share in the island world compared with the poor uniform one.
//!
//! If (b) fails, the last honest answer is that a medium without a notion of region
//! cannot reward searching, and the line closes there.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, World};

const INCOME: f64 = 1.0;
const UPKEEP: f64 = 0.6;
const REGROW: f64 = 0.99;
const CELLS: usize = 24;

fn world() -> World {
    World {
        income: INCOME,
        maintenance_cost: UPKEEP,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 3,
        max_population: 24,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

fn run(field: Field, mutation: f64, steps: usize) -> ([usize; 5], usize) {
    let organisms: Vec<Remembering> = (0..CELLS)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, INCOME, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(),
        field,
        organisms,
        vec![Policy::Random; CELLS],
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
    let steps = 2000;
    let mutation = 0.30;
    println!(
        "{:<20} {:>5} {:>7} {:>8} {:>7} {:>8} {:>6}",
        "world", "stay", "random", "remember", "memory", "sighted", "alive"
    );
    for (name, field) in [
        (
            "uniform-poor",
            Field::new(CELLS, 1.65, REGROW).expect("field"),
        ),
        (
            "uniform-rich",
            Field::new(CELLS, 3.0, REGROW).expect("field"),
        ),
        (
            "islands (1 in 8)",
            Field::peaks(CELLS, 3.0, 1.65, REGROW, 8).expect("field"),
        ),
        (
            "islands (1 in 4)",
            Field::peaks(CELLS, 3.0, 1.65, REGROW, 4).expect("field"),
        ),
        (
            "islands mut 0.10",
            Field::peaks(CELLS, 3.0, 1.65, REGROW, 8).expect("field"),
        ),
    ] {
        let m = if name.ends_with("0.10") { 0.10 } else { mutation };
        let (c, alive) = run(field, m, steps);
        println!(
            "{name:<20} {:>5} {:>7} {:>8} {:>7} {:>8} {alive:>6}",
            c[0], c[1], c[2], c[3], c[4]
        );
    }
}
