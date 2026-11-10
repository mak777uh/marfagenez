//! # How much room does a common push spend?
//!
//! The previous module showed that a common push moves the mean toward the wall, and
//! the wall then narrows the child. This module asks **how long** that takes.
//!
//! ## The prediction
//!
//! A constant push `μ` per step moves the mean by `μ · t` after `t` steps. The mean
//! reaches the wall `B` after
//!
//! $$t^* = \frac{B}{\mu}$$
//!
//! steps. So the room is spent in `B/μ` steps, whatever the noise.
//!
//! ## Why it matters
//!
//! This is the **time** a child has before a common push costs them their range. If
//! the push is small, the time is long; if the push is large, the time is short. The
//! noise does not enter the formula at all — which is the surprising part, because
//! noise is what fills the room.
//!
//! ## The test
//!
//! Run the same push at several strengths and measure when the spread starts to fall
//! below the law. Compare with `B/μ`.

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

/// Runs a common push and returns the step at which the spread first falls below
/// `threshold` times the law, or `None` if it never does.
fn time_to_narrow(
    push: f64,
    n: usize,
    noise: f64,
    seed: u64,
    max_steps: usize,
    b: f64,
    threshold: f64,
) -> Option<usize> {
    let dims = 1;
    let law = b / 3.0_f64.sqrt();
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, noise).unwrap())
        .collect();

    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
    let mut medium = Medium::new(room, seed);

    // Fill the room first, with no push. The filling time is (B/sigma)^2; without
    // this warm-up the population starts narrow and the threshold is already crossed
    // at step 0.
    let warmup = ((b / noise).powi(2) as usize).max(2000);
    for _ in 0..warmup {
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
    }

    for step in 0..max_steps {
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
            if push != 0.0 {
                let mut shifted = c.position().to_vec();
                shifted[0] += push;
                let room2 = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
                let folded = room2.fold(&shifted).unwrap();
                c.set_position(folded).unwrap();
            }
        }
        {
            let s = per_trait_spread(&pop);
            if s < law * threshold {
                return Some(step);
            }
        }
    }
    None
}

#[test]
fn the_room_is_spent_sooner_than_b_over_mu() {
    // A correction found while writing this test.
    //
    // The prediction was `t* = B/mu`: the mean reaches the wall after `B/mu` steps.
    // The measurement says otherwise:
    //
    // | push | predicted B/mu | measured |
    // |---|---|---|
    // | 0.10 | 30 | 11 |
    // | 0.05 | 60 | 32 |
    // | 0.02 | 150 | 83 |
    //
    // The measured time is about half the prediction. The reason: the spread starts to
    // fall before the mean reaches the wall. The wall begins to bite when the mean is
    // within about one spread of it, and the spread is `B/sqrt(3)`, so the mean only
    // has to travel `B - B/sqrt(3) = 0.42 B` before the narrowing starts.
    //
    // The corrected estimate is `t* = (B - B/sqrt(3)) / mu`.
    let b = 3.0;
    let noise = 0.3;
    let law = b / 3.0_f64.sqrt();
    let mut rows = Vec::new();

    for push in [0.02, 0.05, 0.1] {
        let predicted = (b - law) / push;
        let measured = time_to_narrow(push, 1200, noise, 1501, 80000, b, 0.9);
        rows.push((push, predicted, measured));
    }

    println!("push -> corrected (B-law)/mu, measured");
    for (push, predicted, measured) in &rows {
        match measured {
            Some(m) => println!("  {:.3} -> {:.0}, measured {}", push, predicted, m),
            None => println!("  {:.3} -> {:.0}, never narrowed", push, predicted),
        }
    }

    // The corrected estimate should be closer than the naive one.
    for (push, predicted, measured) in &rows {
        let m = measured.expect("every push should narrow") as f64;
        let naive = b / push;
        let err_corrected = (m - predicted).abs() / m;
        let err_naive = (m - naive).abs() / m;
        assert!(
            err_corrected < err_naive,
            "the corrected estimate should be closer for push {}: measured {} corrected {:.0} naive {:.0}",
            push,
            m,
            predicted,
            naive
        );
    }
}

#[test]
fn the_noise_does_enter_the_time() {
    // A correction. The prediction was that the noise does not enter `t* = B/mu`,
    // because the narrowing is caused by the mean reaching the wall.
    //
    // The measurement says the noise does matter: with low noise the child narrows
    // sooner (27 steps) than with high noise (52 steps), at the same push.
    //
    // The reason: the wall starts to bite when the mean is within about one spread of
    // it. A larger spread means the mean is already closer to the wall at the start,
    // so the narrowing begins sooner — the opposite of what "noise does not enter"
    // would suggest.
    let b = 3.0;
    let push = 0.05;
    let low = time_to_narrow(push, 1200, 0.1, 1502, 80000, b, 0.9).unwrap();
    let high = time_to_narrow(push, 1200, 0.5, 1502, 80000, b, 0.9).unwrap();

    println!("low noise: {}, high noise: {}", low, high);

    // The two differ: the noise is in the time.
    assert!(
        low != high,
        "the noise should change the time: low {} high {}",
        low,
        high
    );
    // And the difference is substantial, not a rounding artefact.
    let ratio = (low as f64).max(high as f64) / (low as f64).min(high as f64);
    assert!(
        ratio > 1.3,
        "the noise should change the time substantially: low {} high {} ratio {}",
        low,
        high,
        ratio
    );
}

#[test]
fn a_zero_push_never_narrows() {
    // Sanity: without a push the spread stays at the law, so the threshold is never
    // crossed.
    let b = 3.0;
    let never = time_to_narrow(0.0, 1200, 0.3, 1503, 20000, b, 0.9);
    assert!(never.is_none(), "without a push the child should not narrow");
}
