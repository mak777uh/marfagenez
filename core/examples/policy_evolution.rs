//! Selection over a repertoire: does the policy mix change, and toward what?
//!
//! `docs/FORMS-LINE-CLOSED.md` names the one thing the forms line never had: the
//! repertoire was fixed, so nothing about a decision could be selected for. Births
//! existed and the child inherited the parent's policy, but with no variation there
//! was nothing to select.
//!
//! This starts a population of six random walkers, turns on births, deaths and a
//! mutation rate, and watches the policy census.
//!
//! PREDICTION, before the run:
//!   (a) with `policy_mutation = 0` the census never changes - no variation, nothing
//!       to select, the mix is frozen;
//!   (b) with mutation on, the census moves away from `Random`, because the economy
//!       kills wanderers on the maintenance boundary (`FINDING-199`);
//!   (c) the population sits at the cap, so the change is selection and not drift in
//!       a shrinking population.
//!
//! What this can and cannot show is stated in the file header of the finding: this is
//! selection over five written behaviours, not the emergence of a new one.

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
        capacity: 10.0,
        read_budget: 2,
        max_population: 12,
        birth_threshold: 6.0,
        birth_cost: 2.0,
        ..World::default()
    }
}

fn start_policy(p: Policy) -> Vec<Policy> {
    vec![p; 6]
}

fn run(mutation: f64, steps: usize) -> Vec<([usize; 5], usize)> {
    let cells = [0usize, 1, 2, 3, 4, 5];
    let organisms: Vec<Remembering> = cells
        .iter()
        .map(|&c| {
            let o = Organism::new(6.0, 0.0).expect("valid organism");
            Remembering::new(o, c, 2.0, 0.0, 32).expect("valid remembering")
        })
        .collect();
    let mut life = Life::new_mixed(
        world(),
        Field::new(6, 3.0, 0.99).expect("valid field"),
        organisms,
        start_policy(Policy::Random),
        11,
        32,
    )
    .expect("built");
    life.set_policy_mutation(mutation);

    let mut trace = Vec::new();
    for _ in 0..steps {
        life.advance();
        if life.step() % 200 == 0 {
            trace.push((life.policy_census(), life.organisms_alive()));
        }
    }
    trace
}

fn main() {
    let steps = 2000;
    for mutation in [0.0, 0.05, 0.30] {
        println!("--- mutation {mutation} ---");
        println!(
            "{:>6} {:>6} {:>6} {:>7} {:>6} {:>7} {:>8}",
            "step", "alive", "stay", "random", "rememb", "memory", "sighted"
        );
        for (i, (census, alive)) in run(mutation, steps).into_iter().enumerate() {
            println!(
                "{:>6} {:>6} {:>6} {:>7} {:>6} {:>7} {:>8}",
                (i + 1) * 200,
                alive,
                census[0],
                census[1],
                census[2],
                census[3],
                census[4]
            );
        }
        println!();
    }
}
