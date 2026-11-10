//! # A child that measures itself
//!
//! The previous module showed that a **medium** which measures harms the child. This
//! module asks the other question: what happens when the **child** measures itself?
//!
//! ## Why this is different
//!
//! A measuring medium is a violation of principle 3. A self-measuring child is not:
//! the medium still does not measure, and the boundary is still constant. The
//! measuring is **inside** the child.
//!
//! Krishnamurti's claim (P261): *"the moment I am aware that I am aware, I am not
//! aware — the observer destroys the observation."* If that is true, a child that
//! watches its own state should behave differently from one that does not.
//!
//! ## The three kinds of self-measurement
//!
//! | kind | what the child does with the reading |
//! |---|---|
//! | **none** | does not look at itself |
//! | **compare** | pushes itself toward where it thinks it should be |
//! | **avoid** | pushes itself away from where it is |
//!
//! ## What the vision predicts
//!
//! All three self-measuring kinds should cost the child something. The one that does
//! not look keeps the law.

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

/// A child with a self-reading. `self_read` maps the child's own position to an
/// extra drift, which is what "reacting to your own state" means.
fn run<F>(
    self_read: Option<F>,
    dims: usize,
    n: usize,
    noise: f64,
    seed: u64,
    steps: usize,
    b: f64,
    gain: f64,
) -> f64
where
    F: Fn(f64) -> f64,
{
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect();

    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
    let mut medium = Medium::new(room, seed);

    for _ in 0..steps {
        for c in pop.iter_mut() {
            if let Some(f) = self_read.as_ref() {
                // The child reads its own first trait and adds a drift.
                let x = c.position()[0];
                let extra = gain * f(x);
                // Apply the extra drift by stepping with a shifted noise: the child
                // moves by `extra` on top of the medium's step.
                medium.step(c).unwrap();
                let mut shifted = c.position().to_vec();
                shifted[0] += extra;
                // The experiment acts on the child, named as what it is.
                let experiment = OutsideExperiment::declare();
                experiment.act(c, |_| shifted).unwrap();
            } else {
                medium.step(c).unwrap();
            }
        }
    }

    per_trait_spread(&pop)
}

#[test]
fn a_child_that_does_not_look_keeps_the_law() {
    let b = 3.0;
    let s = run(None::<fn(f64) -> f64>, 1, 2000, 0.3, 601, 12000, b, 0.0);
    let law = b / 3.0_f64.sqrt();
    let rel = (s - law).abs() / law;
    assert!(rel < 0.1, "a child that does not look: {} vs law {}", s, law);
}

#[test]
fn a_child_that_compares_itself_narrows() {
    // The child pushes itself toward zero ("I should be more centred").
    // That is a pull toward a point, which contracts the population.
    let b = 3.0;
    let s = run(Some(|x: f64| -x), 1, 2000, 0.3, 602, 12000, b, 0.05);
    let law = b / 3.0_f64.sqrt();
    assert!(
        s < law * 0.8,
        "comparing itself should narrow the child: {} vs law {}",
        s,
        law
    );
}

#[test]
fn a_child_that_avoids_itself_widens() {
    // The child pushes itself away from where it is ("I do not want to be here").
    // That is a push away from a point, which spreads the population.
    let b = 3.0;
    let s = run(Some(|x: f64| x), 1, 2000, 0.3, 603, 12000, b, 0.05);
    let law = b / 3.0_f64.sqrt();
    assert!(
        s > law * 1.1,
        "avoiding itself should widen the child: {} vs law {}",
        s,
        law
    );
}

#[test]
fn self_measurement_costs_whatever_direction_it_takes() {
    // The summary: any self-reading that changes the drift moves the child off the
    // law. Only not looking keeps it.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();
    let none = run(None::<fn(f64) -> f64>, 1, 1500, 0.3, 604, 10000, b, 0.0);
    let toward = run(Some(|x: f64| -x), 1, 1500, 0.3, 605, 10000, b, 0.05);
    let away = run(Some(|x: f64| x), 1, 1500, 0.3, 606, 10000, b, 0.05);

    assert!(
        (none - law).abs() / law < 0.1,
        "not looking should keep the law: {} vs {}",
        none,
        law
    );
    assert!(
        (toward - law).abs() / law > 0.15,
        "looking toward should move off the law: {} vs {}",
        toward,
        law
    );
    assert!(
        (away - law).abs() / law > 0.15,
        "looking away should move off the law: {} vs {}",
        away,
        law
    );
}
