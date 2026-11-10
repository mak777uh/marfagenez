//! Population-level tests for the child and the cycle.
//!
//! The laws in `docs/VISION.md` are about **populations**, not about one child:
//! `spread = B/√3` is the spread of many children in one room, not the spread of one
//! child's traits. A single child with one trait is a point, and a point has no
//! spread.
//!
//! This module builds populations, runs them through the medium, and checks the laws
//! against what comes out.

#![cfg(test)]

use medium_core::child::{Child, Medium, OutsideReading};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

/// A population of `n` children in one room, each with its own noise.
fn population(shape: Shape, b: f64, d: usize, n: usize, noise: f64, seed: u64) -> Vec<Child> {
    let mut rng = medium_core::Rng::new(seed);
    (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..d).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect()
}

fn run_all(room: Room, pop: &mut [Child], steps: usize, seed: u64) {
    let mut medium = Medium::new(room, seed);
    for c in pop.iter_mut() {
        medium.run(c, steps).unwrap();
    }
}

/// The per-trait spread of a population: for each trait, the spread across children,
/// averaged over traits.
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
fn population_in_a_box_reaches_the_law_spread() {
    // The law `spread = B/sqrt(3)` for a filled box.
    let b = 3.0;
    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
    let mut pop = population(Shape::Box, b, 1, 4000, 0.3, 11);
    run_all(room, &mut pop, 8000, 11);

    let spread = per_trait_spread(&pop);
    let expected = b / 3.0_f64.sqrt();
    let rel = (spread - expected).abs() / expected;
    assert!(
        rel < 0.08,
        "population spread {} vs law {} (rel {})",
        spread,
        expected,
        rel
    );
}

#[test]
fn box_population_keeps_spread_as_dims_grow() {
    // The law `box_keeps_every_trait`: B/sqrt(3) for every d.
    let b = 3.0;
    let mut spreads = Vec::new();
    for d in [1, 4, 8] {
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), d).unwrap();
        let mut pop = population(Shape::Box, b, d, 2000, 0.3, 21);
        run_all(room, &mut pop, 6000, 21);
        spreads.push(per_trait_spread(&pop));
    }
    let first = spreads[0];
    for s in &spreads {
        assert!(
            (s - first).abs() / first < 0.1,
            "box spread changed with d: {:?}",
            spreads
        );
    }
}

#[test]
fn ball_population_is_squeezed_as_dims_grow() {
    // The law `ball_squeezes_traits`: the whole-child bound is divided among traits.
    let b = 3.0;
    let mut spreads = Vec::new();
    for d in [1, 4, 8] {
        let room = Room::new(Shape::Ball, HalfWidth::new(b).unwrap(), d).unwrap();
        let mut pop = population(Shape::Ball, b, d, 2000, 0.3, 31);
        run_all(room, &mut pop, 6000, 31);
        spreads.push(per_trait_spread(&pop));
    }
    assert!(
        spreads[0] > spreads[1] && spreads[1] > spreads[2],
        "ball did not squeeze: {:?}",
        spreads
    );
}

#[test]
fn population_without_noise_keeps_its_initial_difference() {
    // A correction found while writing this test.
    //
    // The expectation was that a population with no noise would collapse to a point,
    // because "noise is the only source of width". That is wrong in a specific and
    // instructive way: noise is the only source of **new** width, not of width as
    // such. Children that start apart, with the same drift and no noise, stay apart
    // forever — reflection is an isometry, so it never brings them together.
    //
    // What noise does is let a population that starts **together** become different.
    // Without it, a population that starts together stays together.
    let b = 3.0;
    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();

    // Started apart, no noise: the difference is preserved.
    let mut apart = population(Shape::Box, b, 1, 500, 0.0, 41);
    let before = per_trait_spread(&apart);
    run_all(room.clone(), &mut apart, 4000, 41);
    let after = per_trait_spread(&apart);
    assert!(
        (after - before).abs() / before < 0.05,
        "without noise the initial spread should be preserved, {} -> {}",
        before,
        after
    );

    // Started together, no noise: they stay together.
    let room2 = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
    let mut together: Vec<Child> = (0..500).map(|_| Child::new(vec![0.0], 0.0, 0.0).unwrap()).collect();
    run_all(room2, &mut together, 4000, 42);
    let spread = per_trait_spread(&together);
    assert!(
        spread < 1e-9,
        "a population that starts together and has no noise must stay together, got {}",
        spread
    );
}

#[test]
fn medium_keeps_every_child_inside() {
    for shape in [Shape::Box, Shape::Ball] {
        let room = Room::new(shape, HalfWidth::new(3.0).unwrap(), 4).unwrap();
        let mut pop = population(shape, 3.0, 4, 200, 0.5, 51);
        let mut medium = Medium::new(room, 51);
        for c in pop.iter_mut() {
            medium.run(c, 2000).unwrap();
            assert!(
                medium.room().contains(c.position()),
                "the medium let a child out of a {:?} room",
                shape
            );
        }
    }
}

#[test]
fn outside_reading_is_not_part_of_the_medium() {
    // The reading exists, and it is a separate type built by a caller outside.
    // The medium itself has no method that returns one.
    let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
    let mut medium = Medium::new(room, 61);
    let mut child = Child::born(1, 0.0, 0.3).unwrap();
    medium.run(&mut child, 100).unwrap();
    let reading = OutsideReading::of(&child).unwrap();
    assert_eq!(reading.n, 1);
    assert!(reading.spread.is_finite());
}
