//! A step-by-step look at the puzzling case: `u_skin = 0.006` lives although the arithmetic says the core should be
//! starved. When an explanation and a measurement disagree, print the trajectory instead of deriving a third formula.
//!
//! The arithmetic: with the skin's equilibrium at `u_s/d_s = 0.3`, the gate is 0.3, the core's repair is
//! `0.3*0.02 = 0.006`, its decay at the threshold would be `0.05*0.2 = 0.01`, so the core should sink and die.

use medium_core::organ::{Organism, Part};

const Q_MIN: f64 = 0.2;

fn main() {
    for u_skin in [0.004, 0.006] {
        println!("u_skin = {u_skin}");
        println!("{:>8} {:>10} {:>10} {:>10} {:>8}", "step", "q_skin", "q_core", "energy", "gate");
        let skin = Part::new(1.0, 0.02, 1.0);
        let core = Part::new(1.0, 0.05, 2.0);
        let mut o = Organism::new(skin, core, Q_MIN, 10.0);
        let u_core = 4.0 * 0.05 * Q_MIN;
        for step in 1..=20_000 {
            let gate = o.skin.q.powf(1.0).min(1.0);
            let alive = o.step(u_skin, u_core, 1.0, 0.5);
            if step % 2000 == 0 || !alive {
                println!(
                    "{step:>8} {:>10.4} {:>10.4} {:>10.2} {:>8.4}",
                    o.skin.q, o.core.q, o.energy, gate
                );
            }
            if !alive {
                break;
            }
        }
        println!();
    }
}
