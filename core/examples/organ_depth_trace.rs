//! A trajectory of the chain, part by part - the lesson of `FINDING-281` and `282` applied before any formula.
//!
//! Twice in this line I derived a formula for the mechanism I MEANT to write rather than the one in the code: a gate
//! that was always one, and a depth law that only counted the last part. Both would have shown themselves in a single
//! trajectory. So: print the parts first.
//!
//! PREDICTION, before the run (three parts, all decay 0.05, `q_min = 0.2`, `u_front` around the point where the chain
//! holds or fails):
//!   (a) the FIRST part to fall below the threshold is the **middle** one, not the last - the middle is already
//!       gated by the front while having to hold the last;
//!   (b) the front part settles at `u_front/d` and the middle at `q_front * u_mid / d`, so the middle's equilibrium
//!       is **lower** than the front's;
//!   (c) the last part's equilibrium is `q_front * q_mid * u_last / d` - three factors, which is why depth costs.

use medium_core::organ::{Chain, Part};

const Q_MIN: f64 = 0.2;
const DECAY: f64 = 0.05;

fn main() {
    for u_front in [0.020, 0.035] {
        println!("u_front = {u_front:.3}");
        println!("{:>7} {:>9} {:>9} {:>9} {:>8}", "step", "q[0]", "q[1]", "q[2]", "alive");
        let parts: Vec<Part> = (0..3).map(|_| Part::new(1.0, DECAY, 1.0)).collect();
        let mut chain = Chain::new(parts, Q_MIN, 10.0);
        // the last is held at twice its need; the middle and front at what is being tested
        let u = [u_front, u_front, 2.0 * DECAY * Q_MIN];
        for step in 1..=60_000 {
            let alive = chain.step(&u);
            if step % 5_000 == 0 || !alive {
                println!(
                    "{step:>7} {:>9.4} {:>9.4} {:>9.4} {:>8}",
                    chain.parts[0].q, chain.parts[1].q, chain.parts[2].q, alive
                );
            }
            if !alive {
                println!("  fell at index {:?}", chain.killed_at);
                break;
            }
        }
        println!();
    }
}
