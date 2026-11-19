//! Why does a sixteen-part chain fail with full repair? Print the parts.

use medium_core::organ::{Chain, Part};

const Q_MIN: f64 = 0.2;

fn main() {
    for n in [8usize, 16] {
        let d = 0.05;
        let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, d, 1.0)).collect();
        let mut u = vec![d; n];
        u[n - 1] = 2.0 * d * Q_MIN;
        let mut c = Chain::new(parts, Q_MIN, 10.0);
        println!("n = {n}");
        println!("{:>7} {:>8} {:>8} {:>8} {:>8}", "step", "q[0]", "q[1]", "q[n/2]", "q[last]");
        let mut died = None;
        for step in 1..=100_000 {
            let alive = c.step(&u);
            if step == 10 || step == 1000 || step == 100_000 || !alive {
                println!(
                    "{step:>7} {:>8.4} {:>8.4} {:>8.4} {:>8.4}",
                    c.parts[0].q,
                    c.parts[1].q,
                    c.parts[n / 2].q,
                    c.parts[n - 1].q
                );
            }
            if !alive {
                died = c.killed_at;
                break;
            }
        }
        println!("  killed at {:?}", died);
        println!();
    }
}
