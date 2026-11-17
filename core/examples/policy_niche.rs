//! Which economy selects which behaviour? The direction before the niche.
//!
//! `FINDING-202` showed that selection over the repertoire removes the worst and
//! establishes no best, because a homogeneous economy has no niche. The next step is a
//! medium with niches, and this is the measurement that has to come first: **does the
//! direction of selection actually depend on the economy?**
//!
//! Three worlds, same population, same mutation rate, same seed:
//!
//!   * `uniform-fast`  - one rich level, regrowth 0.99: standing never exhausts a cell,
//!     so walking is pure cost;
//!   * `uniform-slow`  - one rich level, regrowth 0.30: a cell takes several steps to
//!     recover, so walking may pay;
//!   * `peaks-slow`    - rich every second cell, regrowth 0.30: rich cells are scarce
//!     and slow, which is the classic patch case where a memory that returns should
//!     beat a random walk.
//!
//! PREDICTION:
//!   (a) in `uniform-fast` selection pushes away from `Random`, because moving costs
//!       and buys nothing;
//!   (b) in `peaks-slow` selection ALSO pushes away from `Random`, but toward the
//!       policies that return to a known cell (`Memory`, `Remember`) rather than
//!       toward `Stay`, because a rich cell there does exhaust;
//!   (c) the end-of-run mixes of the three worlds differ, which is what "the economy
//!       chooses" means.
//!
//! If (c) fails, the economy does not select anything and a niche world is pointless.

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
        read_budget: 2,
        max_population: 12,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

fn run(field: Field, income: f64, mutation: f64, steps: usize) -> [usize; 5] {
    let cells = 6;
    let organisms: Vec<Remembering> = (0..cells)
        .map(|c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, income, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(income),
        field,
        organisms,
        vec![Policy::Random; 6],
        11,
        32,
    )
    .expect("built");
    life.set_policy_mutation(mutation);
    for _ in 0..steps {
        life.advance();
    }
    life.policy_census()
}

fn main() {
    let steps = 1500;
    let mutation = 0.30;
    let header = "stay random remember memory sighted";
    println!("{:<14} {:>6} {:<34} alive", "world", "income", header);

    for (name, field, income) in [
        (
            "uniform-fast",
            Field::new(6, 3.0, 0.99).expect("field"),
            2.0,
        ),
        (
            "uniform-slow",
            Field::new(6, 3.0, 0.30).expect("field"),
            2.0,
        ),
        (
            "peaks-slow",
            Field::peaks(6, 4.0, 0.8, 0.30, 2).expect("field"),
            2.0,
        ),
        (
            "peaks-slow-hi",
            Field::peaks(6, 4.0, 0.8, 0.30, 2).expect("field"),
            3.0,
        ),
    ] {
        let census = run(field, income, mutation, steps);
        let total: usize = census.iter().sum();
        println!(
            "{name:<14} {income:>6.1} {:>6} {:>6} {:>8} {:>6} {:>7} {total:>5}",
            census[0], census[1], census[2], census[3], census[4]
        );
    }
}
