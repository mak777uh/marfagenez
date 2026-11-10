//! # A reaction that is the same for everyone
//!
//! The reaction law (`laws/Reaction.lean`) says any reaction with `g ≠ 0` changes the
//! step, and therefore the spread. But it says nothing about **which** part of the
//! spread it changes.
//!
//! This module tests the distinction that matters for a child:
//!
//! * a reaction that depends on the **child's own state** differs from child to child,
//!   so it changes the spread;
//! * a reaction that is the **same for everyone** shifts all children together, so it
//!   changes the mean and leaves the spread alone.
//!
//! ## Why this matters
//!
//! If a common reaction leaves the spread alone, then a medium can push everyone in
//! the same direction without narrowing anyone. That would be a way to act on a child
//! without costing range — and it would contradict the simple reading of the reaction
//! law.
//!
//! ## The prediction
//!
//! | reaction | depends on | predicted effect |
//! |---|---|---|
//! | common | nothing | mean moves, spread unchanged |
//! | own state | the child | spread changes |
//! | own speed | the child | spread changes |

#![cfg(test)]

use medium_core::boundary::OutsideExperiment;
use medium_core::child::{Child, Medium};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn moments(pop: &[Child]) -> (f64, f64) {
    let d = pop[0].dims();
    let n = pop.len();
    let mut total_mean = 0.0;
    let mut total_var = 0.0;
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
        total_mean += mean;
        total_var += var;
    }
    (total_mean / d as f64, (total_var / d as f64).sqrt())
}

/// What the reaction depends on.
#[derive(Clone, Copy, PartialEq)]
enum Kind {
    /// No reaction at all.
    None,
    /// The same push for every child, whatever its state.
    Common(f64),
    /// A pull toward zero, proportional to the child's own position.
    OwnState(f64),
    /// Damping proportional to the child's own step.
    OwnSpeed(f64),
}

fn run(kind: Kind, n: usize, noise: f64, seed: u64, steps: usize, b: f64) -> (f64, f64) {
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

            let extra = match kind {
                Kind::None => 0.0,
                Kind::Common(push) => push,
                Kind::OwnState(gain) => gain * (-after),
                Kind::OwnSpeed(damping) => -damping * step,
            };
            if extra != 0.0 {
                let mut shifted = c.position().to_vec();
                shifted[0] += extra;
                let experiment = OutsideExperiment::declare();
            experiment.act(c, |_| shifted).unwrap();
            }
        }
    }

    moments(&pop)
}

#[test]
fn a_common_reaction_moves_the_mean_and_narrows_through_the_wall() {
    // A correction found while writing this test.
    //
    // The hypothesis was that a common push — the same for every child — shifts
    // everyone together and leaves the spread alone. That is true only when there is
    // no wall nearby. With a wall at B = 3 the push moves the mean toward it, and the
    // wall does the narrowing.
    //
    // The far-wall case is tested in `common_reaction_wall.rs`, where the spread is
    // indeed unchanged. Here the wall is close, so the spread must fall.
    let b = 3.0;
    let law = b / 3.0_f64.sqrt();
    let (m_none, s_none) = run(Kind::None, 2000, 0.3, 1301, 12000, b);
    let (m_common, s_common) = run(Kind::Common(0.02), 2000, 0.3, 1301, 12000, b);

    println!(
        "none: mean {:.3} spread {:.3} | common: mean {:.3} spread {:.3} | law {:.3}",
        m_none, s_none, m_common, s_common, law
    );

    // The mean moved upward.
    assert!(
        m_common > m_none + 0.2,
        "a common push should move the mean: {} vs {}",
        m_common,
        m_none
    );
    // With a near wall the spread falls: the wall does the narrowing.
    assert!(
        s_common < s_none * 0.95,
        "with a near wall the common push should narrow: {} vs {}",
        s_common,
        s_none
    );
}

#[test]
fn an_own_state_reaction_changes_the_spread() {
    // The contrast: a reaction that depends on the child differs between children.
    let b = 3.0;
    let (_, s_none) = run(Kind::None, 2000, 0.3, 1302, 12000, b);
    let (_, s_own) = run(Kind::OwnState(0.05), 2000, 0.3, 1302, 12000, b);
    assert!(
        (s_own - s_none).abs() / s_none > 0.1,
        "an own-state reaction should change the spread: {} vs {}",
        s_own,
        s_none
    );
}

#[test]
fn an_own_speed_reaction_changes_the_spread() {
    let b = 3.0;
    let (_, s_none) = run(Kind::None, 2000, 0.3, 1303, 12000, b);
    let (_, s_speed) = run(Kind::OwnSpeed(0.5), 2000, 0.3, 1303, 12000, b);
    assert!(
        (s_speed - s_none).abs() / s_none > 0.02,
        "an own-speed reaction should change the spread: {} vs {}",
        s_speed,
        s_none
    );
}

#[test]
fn a_common_reaction_cannot_go_far_before_the_wall_stops_it() {
    // A common push moves everyone up until the wall. Then the wall holds them, and
    // the spread collapses against it — not because the reaction narrowed them, but
    // because the wall did.
    let b = 3.0;
    let (m_strong, s_strong) = run(Kind::Common(0.5), 2000, 0.3, 1304, 12000, b);
    let law = b / 3.0_f64.sqrt();
    println!(
        "strong common push: mean {:.3} spread {:.3} (law {:.3})",
        m_strong, s_strong, law
    );
    // Everyone is pressed against the upper wall.
    assert!(
        m_strong > b * 0.5,
        "a strong common push should move the mean far up: {}",
        m_strong
    );
    // And the spread has collapsed against the wall.
    assert!(
        s_strong < law * 0.7,
        "the wall should collapse the spread: {} vs law {}",
        s_strong,
        law
    );
}
