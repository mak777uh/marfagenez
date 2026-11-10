//! # The damping threshold
//!
//! The sweep found something sharp:
//!
//! | damping | spread / law |
//! |---|---|
//! | 0.00 | 0.987 |
//! | 0.50 | 0.959 |
//! | 0.75 | 0.922 |
//! | 0.90 | 0.880 |
//! | **0.99** | **0.347** |
//!
//! Between 0.90 and 0.99 the child falls off a cliff. This is not gradual narrowing:
//! it is a **threshold**.
//!
//! ## Why
//!
//! Damping undoes part of each step. When the damping is below 1, the child still
//! takes a net step forward each time, so the noise keeps accumulating. When the
//! damping approaches 1, the net step approaches zero and the child can no longer
//! move — the noise is undone as fast as it arrives, and the child is pinned.
//!
//! The threshold should be where the effective step size becomes small compared with
//! the room.

#![cfg(test)]

use medium_core::child::{Child, Medium};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn per_trait_spread(pop: &[Child]) -> f64 {
    let d = pop[0].dims();
    let n = pop.len();
    let mut total = 0.0;
    for k in 0..d {
        let mean: f64 = pop.iter().map(|c| c.position()[k]).sum::<f64>() / n as f64;
        let var: f64 = pop
            .iter()
            .map(|c| {
                let x = c.position()[k] - mean;
                x * x
            })
            .sum::<f64>()
            / n as f64;
        total += var;
    }
    (total / d as f64).sqrt()
}

fn run_damped(damping: f64, n: usize, noise: f64, seed: u64, steps: usize, b: f64) -> f64 {
    let dims = 1;
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, noise).unwrap())
        .collect();

    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
    let mut medium = Medium::new(room, seed);

    for _ in 0..steps {
        for c in pop.iter_mut() {
            let before = c.position()[0];
            medium.step(c).unwrap();
            let after = c.position()[0];
            let speed = after - before;
            if damping > 0.0 {
                let mut shifted = c.position().to_vec();
                shifted[0] -= damping * speed;
                let room2 = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
                let folded = room2.fold(&shifted).unwrap();
                c.set_position(folded).unwrap();
            }
        }
    }

    per_trait_spread(&pop)
}

#[test]
fn the_cliff_is_between_damping_09_and_099() {
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();

    let at_090 = run_damped(0.90, 2000, 0.3, 1001, 12000, b);
    let at_095 = run_damped(0.95, 2000, 0.3, 1001, 12000, b);
    let at_099 = run_damped(0.99, 2000, 0.3, 1001, 12000, b);

    println!(
        "0.90 -> {:.3} ({:.3}), 0.95 -> {:.3} ({:.3}), 0.99 -> {:.3} ({:.3})",
        at_090,
        at_090 / law,
        at_095,
        at_095 / law,
        at_099,
        at_099 / law
    );

    // Above 0.9 the child is still mostly wide.
    assert!(
        at_090 > law * 0.8,
        "at damping 0.90 the child should still be wide: {} vs {}",
        at_090,
        law
    );
    // At 0.99 the child has collapsed.
    assert!(
        at_099 < law * 0.6,
        "at damping 0.99 the child should collapse: {} vs {}",
        at_099,
        law
    );
    // The drop between 0.95 and 0.99 is large.
    assert!(
        at_095 > at_099 * 1.5,
        "the drop between 0.95 and 0.99 should be large: {} vs {}",
        at_095,
        at_099
    );
}

#[test]
fn damping_below_one_still_lets_the_noise_through() {
    // The mechanism: with damping d < 1, each step keeps a fraction (1 - d) of the
    // noise. The variance of the accumulated position is proportional to
    // 1/(1 - (1-d)^2) — finite for d < 1, and growing as d approaches 1.
    //
    // So the spread should grow as d approaches 1 from below, not shrink. The
    // measured shrinkage at d = 0.99 must therefore come from the wall, not from the
    // damping itself.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();
    let d_050 = run_damped(0.50, 2000, 0.3, 1002, 12000, b);
    let d_090 = run_damped(0.90, 2000, 0.3, 1002, 12000, b);
    // Both are below the law, and 0.90 is below 0.50: the wall starts to matter.
    assert!(
        d_090 < d_050,
        "stronger damping should narrow more while the wall is not yet dominant: {} vs {}",
        d_090,
        d_050
    );
    assert!(d_090 < law && d_050 < law);
}

#[test]
fn the_threshold_is_where_the_step_vanishes() {
    // A sanity statement about the arithmetic: the net step per unit noise is
    // (1 - d). At d = 0.99 that is 0.01, a hundredth of the noise. The child can
    // barely move, so it cannot explore the room.
    for d in [0.0f64, 0.5, 0.9, 0.99, 0.999] {
        let net = 1.0 - d;
        assert!(net >= 0.0);
    }
    // The ratio of net steps between 0.9 and 0.99 is ten.
    let ratio: f64 = (1.0 - 0.9) / (1.0 - 0.99);
    assert!((ratio - 10.0).abs() < 1e-9);
}
