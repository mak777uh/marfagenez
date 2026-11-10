//! # The optimum answer time
//!
//! The race law says a room that answers in one step always wins the race. The
//! slow-answer test found something the law does not predict: **too slow is also
//! unstable**.
//!
//! | period | instability |
//! |---|---|
//! | 1 | 0.0322 |
//! | 10 | 0.0321 |
//! | 50 | **0.0311** |
//! | 200 | 0.0379 |
//! | 800 | **0.0466** |
//!
//! There is a minimum in between. This module finds it and asks why.

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

/// Instability of the last quarter: the standard deviation of the spread over time.
fn instability(period: usize, steps: usize, seed: u64) -> f64 {
    let dims = 1;
    let n = 600;
    let noise = 0.3;
    let k = 2.5;
    let b_min = 0.5;
    let b_max = 3.0;

    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| {
            let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
            Child::new(traits, 0.0, noise).unwrap()
        })
        .collect();

    let initial = Room::new(Shape::Box, HalfWidth::new(b_min).unwrap(), dims).unwrap();
    let mut medium = Medium::new(initial, seed);
    let mut history = Vec::new();
    let mut current_b = b_min;

    for step in 0..steps {
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

    let tail = &history[history.len() * 3 / 4..];
    let mean = tail.iter().sum::<f64>() / tail.len() as f64;
    let var = tail.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / tail.len() as f64;
    var.sqrt()
}

#[test]
fn there_is_an_optimum_period() {
    // Sweep the period and find where the instability is smallest.
    let periods = [1usize, 5, 10, 20, 50, 100, 200, 400, 800];
    let mut results: Vec<(usize, f64)> = periods
        .iter()
        .map(|&p| (p, instability(p, 40000, 401)))
        .collect();

    let min = results
        .iter()
        .cloned()
        .min_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
        .unwrap();

    // The optimum must be interior: not the fastest, not the slowest.
    assert!(
        min.0 > periods[0] && min.0 < periods[periods.len() - 1],
        "the optimum should be interior, got {:?} from {:?}",
        min,
        results
    );

    // And too slow must be worse than the optimum.
    let slowest = results[results.len() - 1].1;
    assert!(
        slowest > min.1,
        "too slow should be less stable than the optimum: slowest {} optimum {}",
        slowest,
        min.1
    );

    results.sort_by_key(|r| r.0);
    println!("period -> instability: {:?}", results);
}

#[test]
fn too_fast_and_too_slow_fail_for_different_reasons() {
    // Too fast: the room chases the children (the race law).
    // Too slow: the room's answer is based on a stale state, so it over-corrects.
    //
    // Measure: with a very slow period, does the room's width oscillate?
    let period = 800;
    let dims = 1;
    let n = 600;
    let noise = 0.3;

    let mut rng = medium_core::Rng::new(402);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, noise).unwrap())
        .collect();

    let initial = Room::new(Shape::Box, HalfWidth::new(0.5).unwrap(), dims).unwrap();
    let mut medium = Medium::new(initial, 402);
    let mut widths = Vec::new();

    for step in 0..40000 {
        if step % period == 0 {
            let s = per_trait_spread(&pop);
            let b = (2.5 * s).clamp(0.5, 3.0);
            widths.push(b);
            let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
            medium.set_room(room);
        }
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
    }

    // The room's width should move a lot: it over-corrects on stale data.
    let mean = widths.iter().sum::<f64>() / widths.len() as f64;
    let var = widths.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / widths.len() as f64;
    let width_std = var.sqrt();
    assert!(
        width_std > 0.1,
        "a very slow room should oscillate in width, got std {}",
        width_std
    );
}
