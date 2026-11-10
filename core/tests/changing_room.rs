//! # Watching a population when the room changes
//!
//! The medium does not measure. This module does — from **outside**, and it never
//! feeds anything back. It exists so a person can see what happens when the room is
//! changed while children live in it.
//!
//! ## What we are looking for
//!
//! The laws describe a **filled** room: `spread = B/√3`. They say nothing about what
//! happens when `B` itself moves. Two questions:
//!
//! 1. If the room **narrows**, does the spread follow it down, and how fast?
//! 2. If the room **widens**, does the spread grow back, or is the old narrowness
//!    kept?
//!
//! ## Why it matters for a child
//!
//! A room that narrows and then widens is what a crisis looks like from outside: a
//! period of constraint, then release. The question is whether the release undoes the
//! constraint, or whether the constraint leaves a mark.

#![cfg(test)]

use medium_core::child::{Child, Medium};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

/// Runs a population in a room whose half-width changes over time.
///
/// `schedule` is a list of `(steps, half_width)` phases. The reading is taken at the
/// end of each phase, from outside.
fn run_changing(
    shape: Shape,
    dims: usize,
    n: usize,
    noise: f64,
    seed: u64,
    schedule: &[(usize, f64)],
) -> Vec<(f64, f64)> {
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect();

    let mut readings = Vec::new();
    for (steps, b) in schedule {
        let room = Room::new(shape, HalfWidth::new(*b).unwrap(), dims).unwrap();
        let mut medium = Medium::new(room, seed);
        for c in pop.iter_mut() {
            medium.run(c, *steps).unwrap();
        }
        readings.push((*b, per_trait_spread(&pop)));
    }
    readings
}

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

#[test]
fn narrowing_the_room_narrows_the_population() {
    // Fill a wide room, then narrow it. The spread should follow.
    let readings = run_changing(
        Shape::Box,
        1,
        3000,
        0.3,
        101,
        &[(6000, 5.0), (6000, 2.0), (6000, 1.0)],
    );
    let spreads: Vec<f64> = readings.iter().map(|(_, s)| *s).collect();
    assert!(
        spreads[0] > spreads[1] && spreads[1] > spreads[2],
        "narrowing should narrow the spread: {:?}",
        spreads
    );
    // And each should be near its own law value B/sqrt(3).
    for (b, s) in &readings {
        let law = b / 3.0_f64.sqrt();
        let rel = (s - law).abs() / law;
        assert!(rel < 0.15, "B={} spread {} vs law {} (rel {})", b, s, law, rel);
    }
}

#[test]
fn widening_the_room_lets_the_population_spread_again() {
    // The reverse: narrow, then widen. Does the spread come back?
    let readings = run_changing(
        Shape::Box,
        1,
        3000,
        0.3,
        102,
        &[(6000, 1.0), (6000, 3.0), (6000, 5.0)],
    );
    let spreads: Vec<f64> = readings.iter().map(|(_, s)| *s).collect();
    assert!(
        spreads[0] < spreads[1] && spreads[1] < spreads[2],
        "widening should let the spread grow back: {:?}",
        spreads
    );
}

#[test]
fn a_narrow_period_leaves_no_permanent_mark() {
    // The question that matters for a child: does a period of constraint leave a
    // permanent mark?
    //
    // Two populations: one that stayed in a wide room the whole time, one that was
    // narrowed and then released. After the same total time in the same wide room,
    // are they the same?
    let b_wide: f64 = 4.0;
    let total = 12000;

    let straight = run_changing(Shape::Box, 1, 3000, 0.3, 103, &[(total, b_wide)]);
    let detour = run_changing(
        Shape::Box,
        1,
        3000,
        0.3,
        103,
        &[(6000, 1.0), (total - 6000, b_wide)],
    );

    let s_straight = straight[0].1;
    let s_detour = detour[1].1;
    let rel = (s_straight - s_detour).abs() / s_straight.max(1e-12);
    assert!(
        rel < 0.1,
        "a narrow period should leave no permanent mark: straight {} vs detour {} (rel {})",
        s_straight,
        s_detour,
        rel
    );
}

#[test]
fn a_narrow_period_leaves_a_mark_when_it_is_too_short_to_recover() {
    // The complement: if the release is shorter than the filling time, the mark
    // remains.
    //
    // The filling time is `(B/σ)²` (the timescale law). For `B = 4`, `σ = 0.3` that is
    // about 178 steps. A release of 50 steps is well under it, so the population
    // cannot refill the room and the narrowness is still visible.
    let b_wide: f64 = 4.0;
    let sigma: f64 = 0.3;
    let fill = (b_wide / sigma).powi(2) as usize;
    assert!(fill > 100, "the test assumes a filling time above 100, got {}", fill);

    let (_, s_straight) = run_changing(Shape::Box, 1, 3000, sigma, 104, &[(20000, b_wide)])[0];
    let release = 50; // well under the filling time
    let detour = run_changing(
        Shape::Box,
        1,
        3000,
        sigma,
        104,
        &[(6000, 1.0), (release, b_wide)],
    );
    let s_detour = detour[1].1;
    assert!(
        s_detour < s_straight * 0.95,
        "a release of {} steps (filling time {}) should not refill the room: \
         straight {} vs detour {}",
        release,
        fill,
        s_straight,
        s_detour
    );
}

#[test]
fn ball_and_box_respond_differently_to_narrowing() {
    // A box narrows each trait; a ball narrows the whole child. With several traits
    // the ball should compress harder.
    let b_from = 4.0;
    let b_to = 1.5;
    let d = 6;

    let boxed = run_changing(Shape::Box, d, 1500, 0.3, 105, &[(4000, b_from), (4000, b_to)]);
    let balled = run_changing(Shape::Ball, d, 1500, 0.3, 105, &[(4000, b_from), (4000, b_to)]);

    let box_ratio = boxed[1].1 / boxed[0].1;
    let ball_ratio = balled[1].1 / balled[0].1;

    assert!(
        ball_ratio < box_ratio,
        "the ball should compress harder than the box: box ratio {} vs ball ratio {}",
        box_ratio,
        ball_ratio
    );
}
