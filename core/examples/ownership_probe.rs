//! What does ownership actually do? Numbers, not assertions.
//!
//! Two forms on one line, claims switched on, and the questions the design asks:
//! how often does a cell change hands, and does a holder ever lose a cell to
//! neglect? With `Stay` forms on fixed cells nothing should change hands after the
//! first step; a walker should keep taking cells and losing them.

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

fn run(policies: Vec<Policy>, cost: f64, decay: f64, steps: usize) -> (u64, u64, usize, usize) {
    let mut life = Life::new_mixed(
        world(),
        Field::new(6, 2.0, 0.9).expect("valid field"),
        organisms(&[1, 4]),
        policies,
        7,
        32,
    )
    .expect("built");
    life.enable_claims(cost, decay);
    for _ in 0..steps {
        life.advance();
    }
    let c = life.claims().expect("claims on");
    let (takes, losses) = c.counts();
    (takes, losses, c.held_by(0), c.held_by(1))
}

fn main() {
    println!("{:<26} {:>6} {:>7} {:>7} {:>7}", "case", "takes", "losses", "held0", "held1");
    for (name, policies, cost, decay) in [
        ("stay+stay cost0 decay0", vec![Policy::Stay, Policy::Stay], 0.0, 0.0),
        ("stay+stay decay0.6", vec![Policy::Stay, Policy::Stay], 0.0, 0.6),
        ("stay+random cost0", vec![Policy::Stay, Policy::Random], 0.0, 0.0),
        ("stay+random decay0.6", vec![Policy::Stay, Policy::Random], 0.0, 0.6),
        ("stay+random cost0.1", vec![Policy::Stay, Policy::Random], 0.1, 0.0),
        ("stay+random cost2.0", vec![Policy::Stay, Policy::Random], 2.0, 0.0),
    ] {
        let (takes, losses, h0, h1) = run(policies, cost, decay, 20);
        println!("{name:<26} {takes:>6} {losses:>7} {h0:>7} {h1:>7}");
    }
}
