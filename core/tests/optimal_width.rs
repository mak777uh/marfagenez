//! # How wide should the room be? — a correction
//!
//! The first version of this module predicted an **optimum** width
//! `B* = σ√T`, where the room is exactly as wide as the child can fill in time.
//!
//! The measurement found no optimum. The spread grows with `B` all the way to
//! `B = 128`, and then stops growing. The correct law is a **saturation**:
//!
//!     spread(t, B) = min( σ√t,  B/√3 )
//!
//! * Below the saturation width the wall binds and the spread is `B/√3`.
//! * Above it the child never reaches the wall and the spread is `σ√t` — the free
//!   random walk's spread, whatever the room.
//!
//! The saturation width is where the two meet:
//!
//!     σ√t = B/√3  ⇒  B_sat = √3 · σ√t
//!
//! ## Why there is no optimum
//!
//! A wider room never gives *less* range. It gives the same range once the child
//! stops reaching the wall. So the choice of width is not a trade-off: **any room at
//! least `B_sat` wide is as good as any other**, and a narrower one caps the range.

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

fn final_spread(b: f64, sigma: f64, n: usize, seed: u64, steps: usize) -> f64 {
    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
    let mut medium = Medium::new(room, seed);
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, sigma).unwrap())
        .collect();
    for _ in 0..steps {
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
        }
    }
    spread_of(&pop)
}

#[test]
fn the_spread_saturates_at_the_free_walk() {
    // Above the saturation width the spread stops growing and equals sigma*sqrt(t).
    let sigma = 0.3;
    let steps = 1000;
    let free = sigma * (steps as f64).sqrt();

    let at_32 = final_spread(32.0, sigma, 600, 9201, steps);
    let at_64 = final_spread(64.0, sigma, 600, 9201, steps);
    let at_128 = final_spread(128.0, sigma, 600, 9201, steps);

    println!(
        "B=32 {:.3}, B=64 {:.3}, B=128 {:.3}, free walk sigma*sqrt(t) {:.3}",
        at_32, at_64, at_128, free
    );

    // All three are the same: the wall is no longer reached.
    let rel_32_128 = (at_32 - at_128).abs() / at_128;
    assert!(
        rel_32_128 < 0.05,
        "above saturation the width should not matter: {} vs {}",
        at_32,
        at_128
    );
    // And they equal the free walk's spread.
    let rel_free = (at_128 - free).abs() / free;
    assert!(
        rel_free < 0.15,
        "the saturated spread should be sigma*sqrt(t): {} vs {}",
        at_128,
        free
    );
}

#[test]
fn below_saturation_the_wall_binds() {
    // Below the saturation width the spread is the wall's law, B/sqrt(3).
    let sigma = 0.3;
    let steps = 1000;
    for b in [1.0, 2.0, 4.0, 8.0] {
        let s = final_spread(b, sigma, 600, 9202, steps);
        let law = b / 3.0_f64.sqrt();
        let rel = (s - law).abs() / law;
        println!("B={:.0}: {:.3} vs law {:.3} (rel {:.3})", b, s, law, rel);
        assert!(
            rel < 0.12,
            "below saturation the spread should be the law: B={} {} vs {}",
            b,
            s,
            law
        );
    }
}

#[test]
fn the_saturation_width_matches_the_formula() {
    // B_sat = sqrt(3) * sigma * sqrt(t).
    let sigma = 0.3;
    let steps = 1000;
    let b_sat = 3.0_f64.sqrt() * sigma * (steps as f64).sqrt();
    println!("predicted B_sat = {:.2}", b_sat);

    // Just below: the wall binds, so the spread is below the free walk.
    let below = final_spread(b_sat * 0.6, sigma, 600, 9203, steps);
    // Just above: the wall does not bind, so the spread is the free walk.
    let above = final_spread(b_sat * 1.6, sigma, 600, 9203, steps);

    let free = sigma * (steps as f64).sqrt();
    println!(
        "below ({:.1}): {:.3}, above ({:.1}): {:.3}, free {:.3}",
        b_sat * 0.6,
        below,
        b_sat * 1.6,
        above,
        free
    );

    assert!(
        below < free * 0.9,
        "below saturation the wall should bind: {} vs free {}",
        below,
        free
    );
    assert!(
        above > free * 0.85,
        "above saturation the spread should reach the free walk: {} vs {}",
        above,
        free
    );
}

#[test]
fn a_wider_room_never_gives_less_range() {
    // The statement that replaces "there is an optimum": the spread is monotone in the
    // width. A wider room never hurts.
    let sigma = 0.3;
    let steps = 1000;
    let widths = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0];
    let mut prev = 0.0;
    for b in widths {
        let s = final_spread(b, sigma, 600, 9204, steps);
        println!("B={:5.0} -> {:.3}", b, s);
        assert!(
            s >= prev - 0.1,
            "a wider room should not give less range: B={} gave {} after {}",
            b,
            s,
            prev
        );
        prev = s;
    }
}
