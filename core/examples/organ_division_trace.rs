//! Print the spiral: does mutual licensing collapse?

use medium_core::organ::{Division, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn main() {
    let mut d = Division::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    d.income = 10.0;
    println!("{:>7} {:>9} {:>9} {:>8}", "step", "q_a", "q_b", "alive");
    for step in 1..=200_000 {
        let alive = d.step(1.5 * D * Q_MIN);
        if [1usize, 10, 50, 200, 1000, 5000].contains(&step) || !alive {
            println!(
                "{step:>7} {:>9.4} {:>9.4} {:>8}",
                d.a.q, d.b.q, alive
            );
        }
        if !alive {
            println!("  killed first: {:?}", d.killed_first);
            break;
        }
    }
}
