//! Does an organism that can see an empty cell move into it?
//!
//! EXP-26 explained the empty cells at `n = 160` by claiming that `sighted` never
//! enters an empty cell in a uniform field, because an empty cell is not *richer*
//! than an occupied one -- it is the same. That is a claim about the decision
//! rule, and it can be tested without a population at all.
//!
//! Build a small field, put one organism where the question is, and print what it
//! decides. `Field::gradient` and `Field::moving` are the only public
//! constructors that set per-cell levels:
//!
//! * `equal`      -- `gradient(1.6, 1.6)`: all three cells 1.6, the neighbours are
//!                   exactly what the organism stands on;
//! * `richer`     -- `gradient(1.6, 3.2)`: the right neighbour is 3.2, plainly
//!                   better than the 2.4 underfoot;
//! * `enter-empty`-- `moving(3, 1.6, 0.0)`: cell 0 is 1.6, cells 1 and 2 are 0.0.
//!                   The organism stands on cell 0, so its only neighbour is empty.
//!                   **This is the question**: does it step into emptiness?
//! * `leave-empty`-- the same field, the organism on cell 1, so it stands on 0.0
//!                   and its left neighbour is 1.6. The reverse question: does it
//!                   leave emptiness?
//!
//! `read_budget` is 3, not 2. Seeing costs three reads -- the cell underfoot and
//! both neighbours -- and with a budget of 2 the right neighbour is never read,
//! so `Sighted` silently becomes "look left only". Measured: with 2, the `richer`
//! shape gave 0 instead of +1.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

fn world() -> World {
    World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.01,
        capacity: 10.0,
        read_budget: 3,
    }
}

/// One organism at `at` on `field`; return the direction it chooses.
fn decide(policy: Policy, field: Field, at: usize) -> i32 {
    let mut life = Life::spawn_even(world(), field, 1, 10.0, 0.05, policy, 7, 1000)
        .expect("one organism");
    life.move_to(0, at);
    life.advance().expect("step");
    life.samples()[0].direction
}

fn main() {
    let shapes: [(&str, Field, usize); 4] = [
        ("equal", Field::gradient(3, 1.6, 1.6, 0.5).unwrap(), 1),
        ("richer", Field::gradient(3, 1.6, 3.2, 0.5).unwrap(), 1),
        ("enter-empty", Field::moving(3, 1.6, 0.0, 0.5, 0.0).unwrap(), 0),
        ("leave-empty", Field::moving(3, 1.6, 0.0, 0.5, 0.0).unwrap(), 1),
    ];

    println!("policy     shape        here  left  right  ->  direction");
    for policy in [Policy::Stay, Policy::Random, Policy::Sighted] {
        for (label, field, at) in shapes.iter() {
            let here = field.level(*at);
            let left = if *at > 0 { field.level(at - 1) } else { f64::NAN };
            let right = if field.inside(at + 1) {
                field.level(at + 1)
            } else {
                f64::NAN
            };
            let d = decide(policy, field.clone(), *at);
            println!(
                "{:<10} {:<12} {:>4}  {:>4}  {:>5}  ->  {:+}",
                format!("{:?}", policy),
                label,
                fmt(here),
                fmt(left),
                fmt(right),
                d
            );
        }
    }
}

fn fmt(x: f64) -> String {
    if x.is_nan() {
        "--".to_string()
    } else {
        format!("{:.3}", x).trim_end_matches('0').trim_end_matches('.').to_string()
    }
}
