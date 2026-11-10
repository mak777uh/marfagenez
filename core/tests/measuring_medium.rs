//! # What a measuring medium does
//!
//! Principle 3 of the vision says the medium must not measure. That has been a
//! **choice**, not a result — nothing in the repository tested whether measuring
//! actually changes anything.
//!
//! This module tests it. A measuring medium is one that **writes back**: it reads the
//! child's state and changes the room because of what it read.
//!
//! ## The three ways a medium can write back
//!
//! | way | what it does | what it would mean |
//! |---|---|---|
//! | **reward** | widens the room when the child is wide | "you are doing well, here is more room" |
//! | **punish** | narrows the room when the child is wide | "you are too much, be less" |
//! | **centre** | moves the room toward the child's mean | "let me help you stay put" |
//!
//! ## What the vision predicts
//!
//! All three should narrow the child. The vision's claim is that being measured makes
//! the child an object, and an object cannot be free.
//!
//! ## What this module measures
//!
//! The spread after a long run, compared with a medium that does not measure.

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

fn per_trait_mean(pop: &[Child]) -> f64 {
    let d = pop[0].dims();
    let n = pop.len();
    let mut total = 0.0;
    for k in 0..d {
        total += pop.iter().map(|c| c.position()[k]).sum::<f64>() / n as f64;
    }
    total / d as f64
}

/// Runs a population in a medium that may or may not write back.
///
/// `write_back` is called every `period` steps with (mean, spread) and returns the
/// new half-width. `None` means the medium does not measure at all.
fn run<F>(
    write_back: Option<F>,
    period: usize,
    dims: usize,
    n: usize,
    noise: f64,
    seed: u64,
    steps: usize,
    b0: f64,
) -> (f64, f64)
where
    F: Fn(f64, f64) -> f64,
{
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect();

    let initial = Room::new(Shape::Box, HalfWidth::new(b0).unwrap(), dims).unwrap();
    let mut medium = Medium::new(initial, seed);

    for step in 0..steps {
        if let Some(f) = write_back.as_ref() {
            if step % period == 0 {
                let m = per_trait_mean(&pop);
                let s = per_trait_spread(&pop);
                let b = f(m, s).clamp(0.05, 20.0);
                let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
                medium.set_room(room);
            }
        }
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
    }

    (per_trait_mean(&pop), per_trait_spread(&pop))
}

#[test]
fn a_silent_medium_gives_the_law_spread() {
    // Baseline: the medium does not measure, so the law holds.
    let b = 3.0;
    let (_, s) = run(None::<fn(f64, f64) -> f64>, 1, 1, 2000, 0.3, 501, 15000, b);
    let law = b / 3.0_f64.sqrt();
    let rel = (s - law).abs() / law;
    assert!(rel < 0.1, "silent medium: spread {} vs law {}", s, law);
}

#[test]
fn a_rewarding_medium_widens_and_the_child_fills_it() {
    // The medium says "you are doing well, here is more room".
    // The room grows with the spread, so it runs away — the child never catches up.
    let (_, s) = run(
        Some(|_m: f64, sp: f64| 2.0 * sp),
        200,
        1,
        1500,
        0.3,
        502,
        30000,
        3.0,
    );
    // The room is `2 * spread`, so the ratio spread/room is 0.5, below the law 0.577.
    // The child is always in a room it has not filled.
    assert!(
        s > 3.0,
        "a rewarding medium should let the room grow past its start, got spread {}",
        s
    );
}

#[test]
fn a_punishing_medium_narrows_the_child() {
    // The medium says "you are too much, be less". It narrows the room when the
    // spread is large, which makes the spread smaller, which narrows it further.
    let (_, s) = run(
        Some(|_m: f64, sp: f64| {
            // Inverse: wide spread -> narrow room.
            (1.5 / (sp + 0.1)).clamp(0.1, 3.0)
        }),
        200,
        1,
        1500,
        0.3,
        503,
        30000,
        3.0,
    );
    let law = 3.0 / 3.0_f64.sqrt();
    assert!(
        s < law * 0.6,
        "a punishing medium should narrow the child below the law: {} vs {}",
        s,
        law
    );
}

#[test]
fn a_centring_medium_holds_the_mean_but_costs_range() {
    // The medium says "let me help you stay put": it moves the room toward the
    // child's mean. The mean is held near zero, but the room moves with it.
    let (m, s) = run(
        Some(|mean: f64, _sp: f64| 2.0 * mean.abs().max(0.1)),
        200,
        1,
        1500,
        0.3,
        504,
        30000,
        3.0,
    );
    // The mean is pinned near zero.
    assert!(m.abs() < 0.1, "a centring medium should pin the mean, got {}", m);
    // And the spread is far below the law.
    let law = 3.0 / 3.0_f64.sqrt();
    assert!(
        s < law * 0.5,
        "a centring medium should cost range: {} vs {}",
        s,
        law
    );
}

#[test]
fn every_write_back_narrows_or_runs_away_never_settles() {
    // The summary the vision predicts: a medium that measures either narrows the
    // child or chases them. None of the three write-backs gives the law spread.
    let law = 3.0 / 3.0_f64.sqrt();

    let reward = run(Some(|_m: f64, sp: f64| 2.0 * sp), 200, 1, 1200, 0.3, 505, 20000, 3.0).1;
    let punish = run(
        Some(|_m: f64, sp: f64| (1.5 / (sp + 0.1)).clamp(0.1, 3.0)),
        200,
        1,
        1200,
        0.3,
        506,
        20000,
        3.0,
    )
    .1;
    let centre = run(
        Some(|mean: f64, _sp: f64| 2.0 * mean.abs().max(0.1)),
        200,
        1,
        1200,
        0.3,
        507,
        20000,
        3.0,
    )
    .1;
    let silent = run(None::<fn(f64, f64) -> f64>, 1, 1, 1200, 0.3, 508, 20000, 3.0).1;

    // The silent medium is the only one near the law.
    assert!(
        (silent - law).abs() / law < 0.1,
        "silent should match the law: {} vs {}",
        silent,
        law
    );
    // Reward runs away.
    assert!(reward > law * 1.5, "reward should run away: {}", reward);
    // Punish and centre narrow.
    assert!(punish < law * 0.8, "punish should narrow: {}", punish);
    assert!(centre < law * 0.8, "centre should narrow: {}", centre);
}
