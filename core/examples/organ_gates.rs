//! The gate itself, printed: why does the last part of a sixteen-part chain starve when the parts in front read 1?
//!
//! `FINDING-285` left this unexplained. The prediction there was that one of the forward gates is not exactly one.
//! So print the gate applied to each part, not just its integrity.

use medium_core::organ::{Chain, Part};

const Q_MIN: f64 = 0.2;

fn main() {
    let d = 0.05;
    for n in [8usize, 16] {
        let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, d, 1.0)).collect();
        let mut u = vec![d; n];
        u[n - 1] = 2.0 * d * Q_MIN;
        let mut c = Chain::new(parts, Q_MIN, 10.0);

        println!("n = {n}: the gate applied to each part on the last step before death (or step 1000)");
        for step in 1..=100_000 {
            let alive = c.step(&u);
            if step == 1000 || !alive {
                let gates = &c.last_gates;
                let first_bad = gates.iter().position(|g| *g < 0.999_999);
                println!(
                    "  step {step}: alive {alive}, first gate below 1 at {first_bad:?}, gate[last - 1] = {:.6}, gate[last] = {:.6}",
                    gates[n - 2],
                    gates[n - 1]
                );
                println!(
                    "  gates: {}",
                    gates
                        .iter()
                        .take(8)
                        .map(|g| format!("{g:.4}"))
                        .collect::<Vec<_>>()
                        .join(" ")
                );
                if !alive {
                    println!("  killed at {:?}", c.killed_at);
                    break;
                }
            }
        }
        println!();
    }
}
