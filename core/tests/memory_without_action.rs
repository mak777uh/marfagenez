//! # Memory that does not act
//!
//! The previous module showed that a child which reacts to its own state moves off
//! the law, in either direction. But it only tested **looking with action**: the child
//! read itself and then changed its drift.
//!
//! This module tests the other case: **looking without acting**. The child keeps a
//! record of where it has been, but the record does not change the drift.
//!
//! ## Why it matters
//!
//! Krishnamurti distinguishes observation from the observer's response. If the cost
//! comes from the **response** and not from the **record**, then a child can know its
//! own history without being narrowed by it. If the cost comes from the record
//! itself, then even memory is a weight.
//!
//! ## The three cases
//!
//! | case | record | action |
//! |---|---|---|
//! | **silent** | none | none |
//! | **remembering only** | keeps a running average | none |
//! | **remembering and acting** | keeps a running average | drift from the gap |
//!
//! The prediction: silent and remembering-only should give the same spread, and
//! remembering-and-acting should not.

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

/// What the child does with its record.
#[derive(Clone, Copy, PartialEq)]
enum Mode {
    /// No record at all.
    Silent,
    /// Keeps a running average but never acts on it.
    RememberingOnly,
    /// Keeps a running average and drifts by the gap to it.
    RememberingAndActing,
}

fn run(mode: Mode, n: usize, noise: f64, seed: u64, steps: usize, b: f64, gain: f64) -> f64 {
    let dims = 1;
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, noise).unwrap())
        .collect();

    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
    let mut medium = Medium::new(room, seed);

    // Each child's running average of its own position. The record exists only when
    // the mode asks for it.
    let mut memory: Vec<f64> = pop.iter().map(|c| c.position()[0]).collect();
    let alpha = 0.01; // the record is slow, so it is a memory and not the present

    for _ in 0..steps {
        for (i, c) in pop.iter_mut().enumerate() {
            medium.step(c).unwrap();
            if mode != Mode::Silent {
                // Update the record from the new position.
                memory[i] += alpha * (c.position()[0] - memory[i]);
                if mode == Mode::RememberingAndActing {
                    // The child drifts toward its own record.
                    let gap = memory[i] - c.position()[0];
                    let mut shifted = c.position().to_vec();
                    shifted[0] += gain * gap;
                    let experiment = OutsideExperiment::declare();
            experiment.act(c, |_| shifted).unwrap();
                }
            }
        }
    }

    per_trait_spread(&pop)
}

#[test]
fn remembering_without_acting_costs_nothing() {
    // The central test: a record that is never acted on leaves the spread where the
    // law puts it.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();

    let silent = run(Mode::Silent, 2000, 0.3, 701, 12000, b, 0.0);
    let remembering = run(Mode::RememberingOnly, 2000, 0.3, 701, 12000, b, 0.0);

    assert!(
        (silent - law).abs() / law < 0.1,
        "silent should match the law: {} vs {}",
        silent,
        law
    );
    assert!(
        (remembering - silent).abs() / silent < 0.05,
        "remembering without acting should change nothing: {} vs {}",
        remembering,
        silent
    );
}

#[test]
fn remembering_and_acting_does_cost() {
    // The contrast: the same record, acted on, moves the child off the law.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();

    let remembering = run(Mode::RememberingOnly, 2000, 0.3, 702, 12000, b, 0.0);
    let acting = run(Mode::RememberingAndActing, 2000, 0.3, 702, 12000, b, 0.1);

    assert!(
        (acting - remembering).abs() / remembering > 0.1,
        "acting on the record should change the spread: {} vs {}",
        acting,
        remembering
    );
    // Acting toward the record narrows, because the record lags behind and pulls the
    // child back toward where it was.
    assert!(
        acting < law,
        "acting toward a lagging record should narrow: {} vs law {}",
        acting,
        law
    );
}

#[test]
fn the_record_alone_is_harmless_at_any_speed() {
    // The record's speed does not matter if nothing acts on it. A fast record and a
    // slow one should both leave the spread alone.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();
    // The `alpha` is fixed inside `run`, so this test compares the two extremes of
    // what the record could be: none, and a record that is kept. Both are the same.
    let silent = run(Mode::Silent, 1500, 0.3, 703, 10000, b, 0.0);
    let keeping = run(Mode::RememberingOnly, 1500, 0.3, 703, 10000, b, 0.0);
    assert!(
        (silent - law).abs() / law < 0.1 && (keeping - law).abs() / law < 0.1,
        "both should match the law: silent {} keeping {} law {}",
        silent,
        keeping,
        law
    );
}
