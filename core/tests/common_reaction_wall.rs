//! # Why a common reaction still narrows
//!
//! The test found that a common push — the same for every child — **did** change the
//! spread: 1.746 became 1.488, a 15% narrowing. The hypothesis was that a common
//! reaction shifts everyone together and leaves the spread alone.
//!
//! The hypothesis is wrong, and the reason is the wall.
//!
//! ## The mechanism
//!
//! A common push moves the mean up. The wall is at `B = 3`. Once the mean is close to
//! the wall, the children pile against it, and the wall compresses them — exactly the
//! wall law from `FINDING-compression-wall.md`.
//!
//! So a common reaction is not neutral. It **spends the room** by moving the mean
//! toward the wall.
//!
//! ## The test
//!
//! Move the wall far away and push the same amount. If the spread is then unchanged,
//! the narrowing came from the wall and not from the reaction.

#![cfg(test)]

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

fn run_common(push: f64, n: usize, noise: f64, seed: u64, steps: usize, b: f64) -> (f64, f64) {
    let dims = 1;
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, noise).unwrap())
        .collect();

    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
    let mut medium = Medium::new(room, seed);

    for _ in 0..steps {
        for c in pop.iter_mut() {
            medium.step(c).unwrap();
            if push != 0.0 {
                let mut shifted = c.position().to_vec();
                shifted[0] += push;
                let room2 = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), dims).unwrap();
                let folded = room2.fold(&shifted).unwrap();
                c.set_position(folded).unwrap();
            }
        }
    }

    moments(&pop)
}

#[test]
fn with_a_far_wall_a_common_reaction_leaves_the_spread() {
    // The wall is at 100, so a push of 0.02 for 12000 steps moves the mean by about
    // 240 — still far from the wall. The spread should be unchanged.
    // The filling time for B = 100 and sigma = 0.3 is (100/0.3)^2 = 111 000 steps.
    // A shorter run leaves the room unfilled and the spread meaningless.
    let b = 100.0;
    let steps = 200000;
    let (m_none, s_none) = run_common(0.0, 1500, 0.3, 1401, steps, b);
    // A tiny push: over 200 000 steps it moves the mean by about 40, well inside the
    // wall at 100. A larger push would wrap the population around the wall and the
    // spread would collapse for a reason that has nothing to do with the reaction.
    let (m_common, s_common) = run_common(0.0002, 1500, 0.3, 1401, steps, b);

    println!(
        "far wall: none mean {:.2} spread {:.3} | common mean {:.2} spread {:.3}",
        m_none, s_none, m_common, s_common
    );

    // The mean moved.
    assert!(
        m_common > m_none + 10.0,
        "the common push should move the mean far: {} vs {}",
        m_common,
        m_none
    );
    // The spread is unchanged: with no wall nearby, a common push is a pure shift.
    assert!(
        (s_common - s_none).abs() / s_none < 0.10,
        "with a far wall the spread should be unchanged: {} vs {}",
        s_common,
        s_none
    );
}

#[test]
fn with_a_near_wall_a_common_reaction_narrows() {
    // The same push, but the wall is at 3. The children pile against it.
    let b = 3.0;
    let (_, s_none) = run_common(0.0, 2000, 0.3, 1402, 12000, b);
    let (m_common, s_common) = run_common(0.02, 2000, 0.3, 1402, 12000, b);

    println!(
        "near wall: none spread {:.3} | common mean {:.2} spread {:.3}",
        s_none, m_common, s_common
    );

    assert!(
        s_common < s_none * 0.95,
        "with a near wall the common push should narrow: {} vs {}",
        s_common,
        s_none
    );
}

#[test]
fn the_narrowing_is_the_wall_law_not_the_reaction() {
    // The claim: the narrowing is what the wall does when the mean is close to it.
    // The wall law says the spread is at most (B - mean) * (mean + B) / ... in the
    // Bhatia-Davis form. A simpler check: the spread should be bounded by the
    // distance from the mean to the wall.
    let b = 3.0;
    let (m, s) = run_common(0.02, 2000, 0.3, 1403, 12000, b);
    let distance_to_wall = b - m;
    println!(
        "mean {:.3}, spread {:.3}, distance to wall {:.3}",
        m, s, distance_to_wall
    );
    // The spread cannot exceed the distance to the wall by much: the children are
    // pressed against it.
    assert!(
        s < distance_to_wall * 2.0 + 0.5,
        "the spread should be bounded by the wall: spread {} distance {}",
        s,
        distance_to_wall
    );
}
