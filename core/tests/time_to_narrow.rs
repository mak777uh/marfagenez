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
                let experiment = OutsideExperiment::declare();
            experiment.act(c, |_| shifted).unwrap();
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
    //
    // That correction is also wrong, and this test used to assert it. Re-measured
    // (2026-11-12, seed 1501, n = 1200, noise 0.3, threshold 0.9):
    //
    // | push | B/mu | (B-law)/mu | measured |
    // |---|---|---|---|
    // | 0.020 | 150 | 63 | 110 |
    // | 0.050 | 60 | 25 | 32 |
    // | 0.100 | 30 | 13 | 12 |
    //
    // The corrected estimate is worse than the naive one at push 0.02 (63 vs 150,
    // measured 110) and at push 0.05 (25 vs 60, measured 32). It is only closer at
    // push 0.1, and that is the case where the two predictions are closest together.
    // So neither formula is the law, and the "corrected" one was fitted to three
    // numbers from one seed. What the data does support:
    //
    //   * the time falls as the push grows, roughly as `1/mu`;
    //   * the product `mu * t*` is not constant (2.20, 1.60, 1.20), so the law is not
    //     `t* = const/mu` either;
    //   * the naive `B/mu` is an upper bound in all three rows.
    //
    // The honest claim is the bound, not the estimate.
    let b = 3.0;
    let noise = 0.3;
    let law = b / 3.0_f64.sqrt();
    let mut rows = Vec::new();

    for push in [0.02, 0.05, 0.1] {
        let measured = time_to_narrow(push, 1200, noise, 1501, 80000, b, 0.9)
            .expect("every push should narrow");
        rows.push((push, measured));
    }

    println!("push -> B/mu, (B-law)/mu, measured");
    for (push, m) in &rows {
        println!(
            "  {:.3} -> {:.0}, {:.0}, measured {}",
            push,
            b / push,
            (b - law) / push,
            m
        );
    }

    // The naive estimate is an upper bound.
    for (push, m) in &rows {
        let naive = b / push;
        assert!(
            (*m as f64) < naive,
            "the push should narrow sooner than B/mu for push {}: measured {} naive {:.0}",
            push,
            m,
            naive
        );
    }
    // The time falls strictly as the push grows.
    for w in rows.windows(2) {
        assert!(
            w[0].1 > w[1].1,
            "a stronger push should narrow sooner: {} at {} vs {} at {}",
            w[0].1,
            w[0].0,
            w[1].1,
            w[1].0
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
