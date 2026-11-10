//! # The brake has a plateau, then a cliff
//!
//! The sweep found a shape the prediction did not expect:
//!
//! | limit | spread / law |
//! |---|---|
//! | 5.00 | 1.010 |
//! | 1.00 | 1.008 |
//! | 0.50 | 1.003 |
//! | 0.20 | 0.970 |
//! | 0.10 | 0.946 |
//! | 0.05 | 0.945 |
//! | **0.01** | **0.619** |
//!
//! Two regimes: a **plateau** where the brake barely matters, and then a **cliff**
//! somewhere below 0.05. This is neither the gradual narrowing predicted nor the
//! cliff of damping — it is a plateau followed by a cliff.
//!
//! ## Why
//!
//! The brake cuts steps larger than `limit`. The typical step is the noise `σ = 0.3`.
//! While `limit` is above `σ`, almost no step is cut and the child is untouched. When
//! `limit` falls below `σ`, the brake starts cutting the ordinary noise, and the
//! child's motion shrinks with it.
//!
//! So the knee is at `limit ≈ σ`.

#![cfg(test)]

use medium_core::boundary::OutsideExperiment;
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

fn run_brake(limit: f64, n: usize, noise: f64, seed: u64, steps: usize, b: f64) -> f64 {
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
            let step = after - before;
            if step.abs() > limit {
                let excess = step - limit.copysign(step);
                let mut shifted = c.position().to_vec();
                shifted[0] -= excess;
                let experiment = OutsideExperiment::declare();
            experiment.act(c, |_| shifted).unwrap();
            }
        }
    }

    per_trait_spread(&pop)
}

#[test]
fn the_knee_is_at_the_noise_level() {
    let b = 3.0;
    let sigma = 0.3;
    let law = b / 3.0_f64.sqrt();

    // Above the noise level: the brake barely matters.
    let above = run_brake(0.5, 2000, sigma, 1201, 12000, b);
    assert!(
        (above - law).abs() / law < 0.05,
        "a brake above the noise should barely matter: {} vs law {}",
        above,
        law
    );

    // Just below the noise level: the brake starts to bite.
    let below = run_brake(0.2, 2000, sigma, 1202, 12000, b);
    assert!(
        below < law * 0.99,
        "a brake below the noise should bite: {} vs law {}",
        below,
        law
    );

    // Far below: the child is much narrower.
    let far = run_brake(0.01, 2000, sigma, 1203, 12000, b);
    assert!(
        far < law * 0.75,
        "a brake far below the noise should narrow a lot: {} vs law {}",
        far,
        law
    );
}

#[test]
fn the_plateau_ends_where_the_brake_starts_cutting_the_noise() {
    // Sweep finely around the noise level to find where the plateau ends.
    let b = 3.0;
    let sigma = 0.3;
    let law = b / 3.0_f64.sqrt();
    let mut rows = Vec::new();
    for limit in [1.0, 0.6, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.02, 0.01] {
        let s = run_brake(limit, 1500, sigma, 1204, 10000, b);
        rows.push((limit, s / law));
    }
    println!("limit -> spread/law  (noise = {})", sigma);
    for (l, r) in &rows {
        let marker = if (*l - sigma).abs() < 0.06 { "  <- noise level" } else { "" };
        println!("  {:.2} -> {:.3}{}", l, r, marker);
    }

    // The plateau: everything above the noise level is within 5% of the law.
    for (l, r) in &rows {
        if *l > sigma * 1.2 {
            assert!(
                (r - 1.0).abs() < 0.05,
                "above the noise the brake should not matter: limit {} gave {}",
                l,
                r
            );
        }
    }
    // The cliff: far below the noise the spread is well under the law.
    let last = rows[rows.len() - 1].1;
    assert!(last < 0.8, "far below the noise the spread should fall: {}", last);
}

#[test]
fn the_brake_never_pins_the_child_as_completely_as_damping() {
    // The contrast with damping: damping at d = 0.99 gives 0.349 of the law. A brake
    // at limit 0.01 gives about 0.62. The brake cuts the step; damping cuts the
    // motion. A cut step still lets the noise through on the next step.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();
    let brake = run_brake(0.01, 2000, 0.3, 1205, 12000, b);
    assert!(
        brake > law * 0.5,
        "a tight brake should leave more width than heavy damping: {} vs law {}",
        brake,
        law
    );
}
