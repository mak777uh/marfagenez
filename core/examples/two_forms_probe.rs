//! What does a two-form world do? A first look, with numbers instead of assertions.
//!
//! `Life::new_mixed` gives each organism its own policy. This example prints what
//! actually happens in a handful of two-form worlds, so the claims can be checked
//! against the printed numbers rather than against a test that cannot run its panic
//! machinery in this environment.

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
            let o = Organism::new(5.0, 0.0).expect("valid organism");
            Remembering::new(o, c, w.income, 0.0, 32).expect("valid remembering")
        })
        .collect()
}

fn run(policies: Vec<Policy>, steps: usize) -> (u64, usize, Vec<usize>) {
    let mut life = Life::new_mixed(
        world(),
        Field::alternating(6, 3.0, 1.0, 0.9).expect("field"),
        organisms(&[1, 4]),
        policies,
        7,
        32,
    )
    .expect("built");
    for _ in 0..steps {
        life.advance();
    }
    let c = life.census();
    let cells: Vec<usize> = life.samples().iter().map(|s| s.cell).collect();
    (c.moves, c.alive, cells)
}

fn main() {
    let cases: Vec<(&str, Vec<Policy>)> = vec![
        ("stay + stay", vec![Policy::Stay, Policy::Stay]),
        ("stay + sighted", vec![Policy::Stay, Policy::Sighted]),
        ("stay + random", vec![Policy::Stay, Policy::Random]),
        ("sighted + sighted", vec![Policy::Sighted, Policy::Sighted]),
    ];
    for (name, policies) in cases {
        let (moves, alive, cells) = run(policies.clone(), 20);
        println!(
            "{name:20} moves={moves:3} alive={alive} cells={cells:?} policies={policies:?}"
        );
    }
}
