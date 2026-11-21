//! Is the room isotropic? A reflection test, not a picture.
//!
//! Review 2026-11-21 (§1A, "grid bias") warned that a lattice or a folding rule can give the medium a
//! preferred direction without anyone intending it. For this room the question has an exact form:
//! does folding treat `x` and `-x` alike, and does it commute with permuting the axes?
//!
//! What this file does **not** claim: that the *population* fills the room uniformly. That is a
//! measure-preservation question, asked elsewhere (`Shape::is_trusted`, the chi-square probes); this
//! file only checks that the map itself has no preferred direction.

use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn box_room(dims: usize) -> Room {
    Room::new(Shape::Box, HalfWidth::new(1.0).expect("positive half width"), dims).expect("room")
}

/// A deterministic spread of points, including outside the room and on the faces.
fn points(dims: usize) -> Vec<Vec<f64>> {
    let mut out = Vec::new();
    let coords = [-3.7, -1.0, -0.35, 0.0, 0.35, 1.0, 3.7];
    if dims == 2 {
        for &a in &coords {
            for &b in &coords {
                out.push(vec![a, b]);
            }
        }
    } else {
        for &a in &coords {
            out.push(vec![a, -a * 0.5, a * 1.5]);
        }
    }
    out
}

#[test]
fn the_box_fold_is_even_under_reflection() {
    let room = box_room(2);
    for p in points(2) {
        let neg: Vec<f64> = p.iter().map(|x| -x).collect();
        let a = room.fold(&p).expect("finite point folds");
        let b = room.fold(&neg).expect("finite point folds");
        for k in 0..2 {
            assert!(
                (a[k] + b[k]).abs() < 1e-12,
                "fold(-x) must be -fold(x): point {p:?}, axis {k}, got {a:?} and {b:?}"
            );
        }
    }
}

#[test]
fn the_box_fold_commutes_with_swapping_the_axes() {
    // A square room has no distinguished axis: folding then swapping must equal swapping then folding.
    let room = box_room(2);
    for p in points(2) {
        let folded = room.fold(&p).expect("folds");
        let swapped_first = room.fold(&[p[1], p[0]]).expect("folds");
        assert!((folded[0] - swapped_first[1]).abs() < 1e-12);
        assert!((folded[1] - swapped_first[0]).abs() < 1e-12);
    }
}

#[test]
fn the_ball_fold_is_even_under_reflection() {
    let room = Room::new(Shape::Ball, HalfWidth::new(1.0).expect("positive"), 2).expect("room");
    for p in points(2) {
        let neg: Vec<f64> = p.iter().map(|x| -x).collect();
        let a = room.fold(&p).expect("folds");
        let b = room.fold(&neg).expect("folds");
        for k in 0..2 {
            assert!((a[k] + b[k]).abs() < 1e-12, "ball fold must be even: {p:?}");
        }
    }
}

#[test]
fn the_reflection_test_is_not_vacuous() {
    // A control: an intentionally biased map `|x|` is even, so it would pass the test above --
    // the control must be a map that is NOT even. `x + 0.3` is such a map: it moves every point,
    // and `f(-x) != -f(x)` for x != 0. This proves the assertion can fail.
    let biased = |x: f64| x + 0.3;
    let x = 0.7;
    assert!(
        (biased(-x) + biased(x)).abs() > 1e-12,
        "the control map must break reflection symmetry, otherwise the test means nothing"
    );
}
