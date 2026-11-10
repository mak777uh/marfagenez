//! # A long life in a silent medium
//!
//! The medium is now structurally silent: it can only drift-and-noise and fold. So
//! every experiment below is **about** the medium, not a violation of it.
//!
//! ## The question
//!
//! The filling time is `(B/σ)²`. For `B = 3`, `σ = 0.3` that is 100 steps. For
//! `B = 30` it is 10 000. A child in a wide room needs a long time before its range
//! is available.
//!
//! This module asks: **what does a child experience at the start of a wide life**,
//! before the room is filled? Is it narrow, and for how long?
//!
//! ## Why it matters
//!
//! If the room is wide but the child starts narrow, then for the first `(B/σ)²` steps
//! the child is in a wide room but does not have the range the room allows. A wide
//! room is not the same as a wide life — the life has to fill it.

#![cfg(test)]

use medium_core::child::{Child, Medium};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn spread_of(pop: &[Child]) -> f64 {
    let n = pop.len();
    let mean: f64 = pop.iter().map(|c| c.position()[0]).sum::<f64>() / n as f64;
    (pop.iter()
        .map(|c| {
            let x = c.position()[0] - mean;
            x * x
        })
        .sum::<f64>()
        / n as f64)
        .sqrt()
}

/// Fills a room and records the spread at a few checkpoints.
fn fill_curve(b: f64, sigma: f64, n: usize, seed: u64, checkpoints: &[usize]) -> Vec<(usize, f64)> {
    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
    let mut medium = Medium::new(room, seed);
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, sigma).unwrap())
        .collect();

    let mut out = Vec::new();
    let max = *checkpoints.iter().max().unwrap();
    for step in 1..=max {
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
        if checkpoints.contains(&step) {
            out.push((step, spread_of(&pop)));
        }
    }
    out
}

#[test]
fn a_wide_room_starts_narrow() {
    // A room of half-width 30 with noise 0.3 needs (30/0.3)^2 = 10 000 steps to fill.
    // At step 100 — the filling time for B = 3 — the child in the wide room is still
    // narrow.
    let sigma: f64 = 0.3;
    let wide = 30.0;
    let narrow = 3.0;

    let wide_curve = fill_curve(wide, sigma, 800, 7001, &[100, 1000, 10000]);
    let narrow_curve = fill_curve(narrow, sigma, 800, 7002, &[100]);

    let wide_at_100 = wide_curve[0].1;
    let wide_law = wide / 3.0_f64.sqrt();
    let narrow_at_100 = narrow_curve[0].1;
    let narrow_law = narrow / 3.0_f64.sqrt();

    println!(
        "wide room at 100 steps: {:.2} of {:.2} law ({:.1}%)",
        wide_at_100,
        wide_law,
        100.0 * wide_at_100 / wide_law
    );
    println!(
        "narrow room at 100 steps: {:.2} of {:.2} law ({:.1}%)",
        narrow_at_100,
        narrow_law,
        100.0 * narrow_at_100 / narrow_law
    );

    // The narrow room is nearly full at 100 steps.
    assert!(
        narrow_at_100 / narrow_law > 0.9,
        "the narrow room should be nearly full at 100 steps: {} vs {}",
        narrow_at_100,
        narrow_law
    );
    // The wide room is far from full.
    assert!(
        wide_at_100 / wide_law < 0.5,
        "the wide room should still be far from full at 100 steps: {} vs {}",
        wide_at_100,
        wide_law
    );
}

#[test]
fn the_wide_room_fills_eventually() {
    // The same room, given its own filling time.
    let sigma: f64 = 0.3;
    let wide = 30.0;
    let curve = fill_curve(wide, sigma, 800, 7003, &[100, 1000, 10000]);
    let law = wide / 3.0_f64.sqrt();

    let at_100 = curve[0].1;
    let at_1000 = curve[1].1;
    let at_10000 = curve[2].1;

    println!(
        "wide room: 100 -> {:.2} ({:.0}%), 1000 -> {:.2} ({:.0}%), 10000 -> {:.2} ({:.0}%)",
        at_100,
        100.0 * at_100 / law,
        at_1000,
        100.0 * at_1000 / law,
        at_10000,
        100.0 * at_10000 / law
    );

    // Monotone growth toward the law.
    assert!(at_100 < at_1000, "the spread should grow: {} vs {}", at_100, at_1000);
    assert!(at_1000 < at_10000, "the spread should grow: {} vs {}", at_1000, at_10000);
    // And it reaches most of the law by its own filling time.
    assert!(
        at_10000 / law > 0.85,
        "the wide room should be mostly full by 10000 steps: {} vs {}",
        at_10000,
        law
    );
}

#[test]
fn the_first_steps_are_the_same_whatever_the_room() {
    // At the very start the room does not matter: the child has not reached the wall.
    // So two children in very different rooms have the same spread for a while.
    let sigma: f64 = 0.3;
    let small = fill_curve(3.0, sigma, 800, 7004, &[10]);
    let big = fill_curve(30.0, sigma, 800, 7004, &[10]);

    let rel = (small[0].1 - big[0].1).abs() / small[0].1;
    println!(
        "at 10 steps: small room {:.3}, big room {:.3} (rel {:.3})",
        small[0].1, big[0].1, rel
    );
    assert!(
        rel < 0.15,
        "at the start the room should not matter: {} vs {} (rel {})",
        small[0].1,
        big[0].1,
        rel
    );
}

#[test]
fn a_wide_room_needs_a_long_life_to_be_wide() {
    // The quantitative statement: the time to reach 90% of the law scales as (B/σ)^2.
    let sigma: f64 = 0.3;
    let mut times = Vec::new();
    for b in [3.0, 6.0, 12.0] {
        let predicted = (b / sigma).powi(2) as usize;
        // Search for the step where the spread reaches 90% of the law.
        let law = b / 3.0_f64.sqrt();
        let checkpoints: Vec<usize> = (1..=predicted * 2).step_by((predicted / 20).max(1)).collect();
        let curve = fill_curve(b, sigma, 600, 7005, &checkpoints);
        let reached = curve
            .iter()
            .find(|(_, s)| *s >= law * 0.9)
            .map(|(t, _)| *t);
        times.push((b, predicted, reached));
    }

    println!("B -> predicted (B/s)^2, measured 90%");
    for (b, predicted, reached) in &times {
        println!("  {:.0} -> {}, measured {:?}", b, predicted, reached);
    }

    // Every room reaches 90% within twice its predicted filling time.
    for (b, predicted, reached) in &times {
        let r = reached.expect("the room should fill within twice the prediction");
        assert!(
            r <= predicted * 2,
            "room {} should fill within {} steps, took {}",
            b,
            predicted * 2,
            r
        );
    }
    // And the times grow with the room.
    let t0 = times[0].2.unwrap();
    let t2 = times[2].2.unwrap();
    assert!(
        t2 > t0 * 4,
        "a room four times wider should take much longer: {} vs {}",
        t2,
        t0
    );
}
