//! # A room that answers the population
//!
//! So far the room changed on a schedule set from outside. This module asks what
//! happens when the room changes **in response to the children in it**.
//!
//! ## Why this is the dangerous case
//!
//! The previous project (`medium`) found that a self-referential wall either
//! collapses or runs away, and concluded that only a constant room holds. But that
//! conclusion was reached with a **point** on a line, not with a population of
//! children. With children there is a new fact: the population has its own noise,
//! and noise is a stabiliser.
//!
//! ## The three responses
//!
//! | response | rule | what it would mean |
//! |---|---|---|
//! | to the **spread** | `B = k · spread` | the room tracks how wide the children are |
//! | to the **mean** | `B = k · |mean|` | the room tracks where the children are |
//! | to the **count** | `B = k · n` | the room tracks how many there are |
//!
//! ## The principle this must respect
//!
//! The medium must not measure (principle 3). A room that answers the population
//! **is** measuring it. So this module is an **experiment outside the medium**, not a
//! feature of it: it exists to show what happens if one breaks the principle, not to
//! be used.

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

/// Runs a population in a room that answers the population each step.
///
/// `response` maps (mean, spread) to a half-width. The room is rebuilt every step.
/// Returns the spread history.
fn run_answering<F>(
    response: F,
    dims: usize,
    n: usize,
    noise: f64,
    seed: u64,
    steps: usize,
    b_min: f64,
    b_max: f64,
) -> Vec<f64>
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

    let mut history = Vec::new();
    let initial = Room::new(Shape::Box, HalfWidth::new(b_min.max(1.0)).unwrap(), dims).unwrap();
    // One Medium for the whole run, so the noise sequence is continuous. Rebuilding
    // it each step would restart the generator and the population would never fill
    // the room.
    let mut medium = Medium::new(initial, seed);
    for _ in 0..steps {
        let m = per_trait_mean(&pop);
        let s = per_trait_spread(&pop);
        let b = response(m, s).clamp(b_min, b_max);
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
        medium.set_room(room);
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
        history.push(per_trait_spread(&pop));
    }
    history
}

#[test]
fn room_answering_the_spread_runs_away() {
    // `B = 2.5 * spread`: every widening of the room permits more widening.
    // The old project found this and called it divergence. With children it still
    // diverges — noise does not save it, because the room grows faster than the
    // children can fill it.
    let h = run_answering(|_m, s| 2.5 * s, 1, 800, 0.3, 201, 3000, 0.05, 50.0);
    let early = h[100];
    let late = h[h.len() - 1];
    assert!(
        late > early * 1.5,
        "the room should run away: early {} late {}",
        early,
        late
    );
}

#[test]
fn room_answering_the_mean_collapses() {
    // `B = 2.5 * |mean|`: as the mean settles at zero the room closes, and the
    // children are squeezed with it.
    //
    // The collapse is fast — by step 100 the spread is already tiny. So the test
    // compares against the law value for the starting room, not against an early
    // sample of the collapse itself.
    let law_start = 3.0 / 3.0_f64.sqrt();
    let h = run_answering(|m, _s| 2.5 * m.abs(), 1, 800, 0.3, 202, 3000, 0.05, 50.0);
    let late = h[h.len() - 1];
    assert!(
        late < law_start * 0.1,
        "the room should collapse far below the law spread: late {} vs law {}",
        late,
        law_start
    );
}

#[test]
fn a_bounded_answer_settles() {
    // The correction from the old project: a response with a ceiling settles.
    // `B = clamp(2.5 * spread, 0.5, 3.0)`.
    let h = run_answering(|_m, s| 2.5 * s, 1, 800, 0.3, 203, 4000, 0.5, 3.0);
    let late = h[h.len() - 1];
    let law = 3.0 / 3.0_f64.sqrt();
    let rel = (late - law).abs() / law;
    assert!(
        rel < 0.15,
        "a bounded answer should settle at the ceiling's law: {} vs {} (rel {})",
        late,
        law,
        rel
    );
}

#[test]
fn a_constant_room_is_the_special_case() {
    // A constant room is a response that ignores its arguments. It should give the
    // same answer as before.
    let h = run_answering(|_m, _s| 3.0, 1, 800, 0.3, 204, 4000, 0.5, 10.0);
    let late = h[h.len() - 1];
    let law = 3.0 / 3.0_f64.sqrt();
    let rel = (late - law).abs() / law;
    assert!(
        rel < 0.1,
        "a constant room should give the law spread: {} vs {}",
        late,
        law
    );
}

#[test]
fn the_answer_is_slower_than_the_children() {
    // The reason an unbounded answer diverges: the room reacts in one step, but the
    // children need (B/sigma)^2 steps to fill it. The room always wins the race.
    //
    // Measured: with `B = 2.5 * spread`, the ratio `spread / B` should stay well
    // below the law value `1/sqrt(3) = 0.577`, because the room is always ahead.
    let h = run_answering(|_m, s| 2.5 * s, 1, 800, 0.3, 205, 2000, 0.05, 50.0);
    let late = h[h.len() - 1];
    let b_late = 2.5 * late;
    let ratio = late / b_late;
    assert!(
        ratio < 0.577,
        "the children should never fill a room that chases them: ratio {}",
        ratio
    );
}
