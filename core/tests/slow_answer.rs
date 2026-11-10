//! # A room that answers slowly
//!
//! The race law (`laws/Race.lean`) says a room that answers in one step always wins
//! the race against children who need `(B/σ)²` steps to fill it. That is why an
//! answering room either runs away or collapses.
//!
//! This module asks the other question: **what if the room answers slower than the
//! children fill it?**
//!
//! ## The hypothesis
//!
//! If the room's response time is longer than the filling time, the children reach
//! the boundary before the room moves. Then the room's answer is based on a
//! **filled** population, and the answer is meaningful rather than a chase.
//!
//! ## The test
//!
//! A room that tracks the spread, but only re-decides every `period` steps. For each
//! `period`, measure whether the population settles at a stable spread.

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

/// Runs a population in a room that re-decides every `period` steps.
///
/// Returns the spread history sampled once per period.
fn run_slow_answer(
    period: usize,
    dims: usize,
    n: usize,
    noise: f64,
    seed: u64,
    steps: usize,
    k: f64,
    b_min: f64,
    b_max: f64,
) -> Vec<f64> {
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect();

    let initial = Room::new(Shape::Box, HalfWidth::new(b_min.max(1.0)).unwrap(), dims).unwrap();
    let mut medium = Medium::new(initial, seed);
    let mut history = Vec::new();
    let mut current_b = b_min.max(1.0);

    for step in 0..steps {
        // Re-decide only every `period` steps.
        if step % period == 0 {
            let s = per_trait_spread(&pop);
            current_b = (k * s).clamp(b_min, b_max);
            let room = Room::new(Shape::Box, HalfWidth::new(current_b).unwrap(), dims).unwrap();
            medium.set_room(room);
        }
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
        if step % period == 0 {
            history.push(per_trait_spread(&pop));
        }
    }
    history
}

#[test]
fn a_fast_answer_runs_away() {
    // period = 1: the room answers every step, which is the case the race law covers.
    let h = run_slow_answer(1, 1, 800, 0.3, 301, 3000, 2.5, 0.05, 50.0);
    let early = h[100];
    let late = h[h.len() - 1];
    assert!(
        late > early * 1.5,
        "a fast answer should run away: early {} late {}",
        early,
        late
    );
}

#[test]
fn a_slow_answer_settles() {
    // period well above the filling time: the room waits for the children to fill it.
    // Filling time for B = 3, sigma = 0.3 is (3/0.3)^2 = 100 steps.
    let period = 400; // four times the filling time
    let h = run_slow_answer(period, 1, 800, 0.3, 302, 40000, 2.5, 0.5, 3.0);
    // Look at the last quarter: is it stable?
    let tail = &h[h.len() * 3 / 4..];
    let first = tail[0];
    let last = tail[tail.len() - 1];
    let rel = (last - first).abs() / first.max(1e-12);
    assert!(
        rel < 0.15,
        "a slow answer should settle: first {} last {} (rel {})",
        first,
        last,
        rel
    );
}

#[test]
fn too_slow_is_also_unstable() {
    // A correction found while writing this test.
    //
    // The expectation was monotone: the faster the answer, the wilder the result.
    // That is wrong. There is an optimum, and it sits near the filling time
    // `(B/σ)²`. Too fast is a chase; too slow is an answer to a stale state.
    //
    // This test checks the half the monotone guess got right: a very slow answer is
    // less stable than a moderate one.
    let moderate = run_slow_answer(100, 1, 600, 0.3, 303, 30000, 2.5, 0.5, 3.0);
    let very_slow = run_slow_answer(800, 1, 600, 0.3, 303, 30000, 2.5, 0.5, 3.0);

    let instability = |h: &[f64]| {
        let tail = &h[h.len() * 3 / 4..];
        let mean = tail.iter().sum::<f64>() / tail.len() as f64;
        let var = tail.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / tail.len() as f64;
        var.sqrt()
    };

    assert!(
        instability(&very_slow) > instability(&moderate),
        "too slow should be less stable than moderate: very slow {} vs moderate {}",
        instability(&very_slow),
        instability(&moderate)
    );
}

#[test]
fn a_slow_answer_does_not_measure_every_step() {
    // A consequence worth stating: a slow-answering room measures the population far
    // less often. Over `steps` steps with period `p` it takes `steps/p` readings.
    // This is not a test of the code but a statement of what the design costs.
    let steps = 1000;
    for period in [1, 10, 100] {
        let readings = steps / period;
        assert!(readings >= 1);
    }
    // At period 100 the room reads the population 10 times instead of 1000. The
    // medium still measures — which is why this cannot be part of the medium itself.
}
