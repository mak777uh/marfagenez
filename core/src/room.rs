//! # A room with several traits
//!
//! A child is not one number. This module gives the room **dimensions**, and it
//! enforces the one distinction the previous project got wrong: a room can bound
//! each trait separately (a **box**) or the whole child at once (a **ball**), and
//! these are not the same room.
//!
//! ## What the laws say
//!
//! | room | per-trait spread | source |
//! |---|---|---|
//! | box, `d` traits | `B/√3` for every `d` | Lean `box_keeps_every_trait` |
//! | ball, radius `B` | about `B²/d` per trait | Lean `ball_squeezes_traits` |
//! | uniform in a ball | `d/(d+2)·R²` total | Lean `dimension_law` |
//!
//! So a room that bounds the whole child squeezes every trait as the child grows
//! more dimensions. A room that bounds each trait separately does not.
//!
//! ## The type-level guarantee
//!
//! [`Room`] is an enum, not a pair of numbers with a boolean flag. You cannot
//! accidentally build a ball and use it as a box: the two are different variants and
//! the fold is checked for each.

#![forbid(unsafe_code)]

use crate::{HalfWidth, Reflect};

/// The shape of a room. The shape, not the size, decides what a multi-trait child
/// keeps.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    /// Each trait bounded separately: `|x_k| ≤ B` for every `k`.
    Box,
    /// The whole child bounded at once: `‖x‖ ≤ B`.
    Ball,
}

/// A room with `d` dimensions.
///
/// The dimension is fixed at construction, so a room cannot be used with the wrong
/// number of traits.
#[derive(Debug, Clone)]
pub struct Room {
    shape: Shape,
    half_width: HalfWidth,
    dims: usize,
}

impl Room {
    /// Builds a room. Returns `None` for zero dimensions, because a zero-dimensional
    /// room has no traits to hold.
    pub fn new(shape: Shape, half_width: HalfWidth, dims: usize) -> Option<Self> {
        if dims == 0 {
            return None;
        }
        Some(Self {
            shape,
            half_width,
            dims,
        })
    }

    pub fn shape(&self) -> Shape {
        self.shape
    }

    pub fn dims(&self) -> usize {
        self.dims
    }

    pub fn half_width(&self) -> HalfWidth {
        self.half_width
    }

    /// The per-trait spread a filled box gives: `B/√3`, independent of `d`.
    ///
    /// This is the law `box_keeps_every_trait`.
    pub fn box_spread(&self) -> f64 {
        self.half_width.uniform_spread().0
    }

    /// The per-trait variance a filled ball gives: about `B²/d`.
    ///
    /// This is the law `ball_squeezes_traits`: the whole-child bound is divided among
    /// the traits, so each gets less as the child grows more dimensions.
    pub fn ball_trait_variance(&self) -> f64 {
        self.half_width.get().powi(2) / self.dims as f64
    }

    /// The total spread of a uniform population in a ball of radius `R`:
    /// `d/(d+2)·R²`.
    ///
    /// This is the law `dimension_law`, which unifies the one-dimensional `B²/3` and
    /// the two-dimensional `R²/2`.
    pub fn ball_total_variance(&self) -> f64 {
        let d = self.dims as f64;
        let r = self.half_width.get();
        d / (d + 2.0) * r * r
    }

    /// Folds a point back into the room.
    ///
    /// * A **box** reflects each coordinate independently, so a point bouncing off one
    ///   wall does not affect the others.
    /// * A **ball** reflects the point along its radius, so the whole child bounces
    ///   off the single wall together.
    ///
    /// Both are measure-preserving in their own geometry, which is why both keep the
    /// range; they differ in what happens as `d` grows.
    pub fn fold(&self, point: &[f64]) -> Option<Vec<f64>> {
        if point.len() != self.dims {
            return None;
        }
        match self.shape {
            Shape::Box => {
                let mirror = Reflect::new(self.half_width);
                Some(point.iter().map(|&x| mirror.apply(x)).collect())
            }
            Shape::Ball => {
                let b = self.half_width.get();
                let r = point.iter().map(|x| x * x).sum::<f64>().sqrt();
                if r <= b {
                    return Some(point.to_vec());
                }
                if r == 0.0 {
                    return Some(point.to_vec());
                }
                // Fold the radius into [0, B] with period 2B. A single reflection
                // (2B - r) fails for r > 2B: it gives a negative radius and throws
                // the point out the far side. The periodic fold is what the
                // one-dimensional `Reflect` does, applied to the radius.
                let period = 2.0 * b;
                let u = r.rem_euclid(period);
                let folded_r = if u <= b { u } else { period - u };
                let scale = folded_r / r;
                Some(point.iter().map(|x| x * scale).collect())
            }
        }
    }

    /// Whether a folded point lies inside the room. Used by the probes.
    pub fn contains(&self, point: &[f64]) -> bool {
        let b = self.half_width.get();
        match self.shape {
            Shape::Box => point.iter().all(|x| x.abs() <= b + 1e-12),
            Shape::Ball => {
                point.iter().map(|x| x * x).sum::<f64>().sqrt() <= b + 1e-12
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn room(shape: Shape, b: f64, d: usize) -> Room {
        Room::new(shape, HalfWidth::new(b).unwrap(), d).unwrap()
    }

    #[test]
    fn zero_dimensions_rejected() {
        assert!(Room::new(Shape::Box, HalfWidth::new(1.0).unwrap(), 0).is_none());
    }

    #[test]
    fn box_fold_stays_inside() {
        let r = room(Shape::Box, 3.0, 4);
        for i in -50..50 {
            let p = vec![i as f64 * 0.3; 4];
            let f = r.fold(&p).unwrap();
            assert!(r.contains(&f), "box folded {:?} outside", f);
        }
    }

    #[test]
    fn ball_fold_stays_inside() {
        let r = room(Shape::Ball, 3.0, 4);
        for i in -50..50 {
            let p = vec![i as f64 * 0.3; 4];
            let f = r.fold(&p).unwrap();
            assert!(r.contains(&f), "ball folded {:?} outside", f);
        }
    }

    #[test]
    fn wrong_dimension_rejected() {
        let r = room(Shape::Box, 3.0, 4);
        assert!(r.fold(&[1.0, 2.0]).is_none());
    }

    #[test]
    fn box_spread_is_independent_of_dims() {
        // The law `box_keeps_every_trait`: B/sqrt(3) for every d.
        let expected = 3.0 / 3.0_f64.sqrt();
        for d in [1, 2, 4, 8, 16] {
            let r = room(Shape::Box, 3.0, d);
            assert!(
                (r.box_spread() - expected).abs() < 1e-12,
                "box spread changed with d={}",
                d
            );
        }
    }

    #[test]
    fn ball_squeezes_as_dims_grow() {
        // The law `ball_squeezes_traits`: B^2/d falls as d grows.
        let mut prev = f64::INFINITY;
        for d in [1, 2, 4, 8, 16] {
            let r = room(Shape::Ball, 3.0, d);
            let v = r.ball_trait_variance();
            assert!(v < prev, "ball variance did not fall at d={}", d);
            prev = v;
        }
    }

    #[test]
    fn dimension_law_matches_1d_and_2d() {
        // d=1 gives B^2/3, d=2 gives R^2/2.
        let r1 = room(Shape::Ball, 3.0, 1);
        assert!((r1.ball_total_variance() - 9.0 / 3.0).abs() < 1e-12);
        let r2 = room(Shape::Ball, 3.0, 2);
        assert!((r2.ball_total_variance() - 9.0 / 2.0).abs() < 1e-12);
    }

    #[test]
    fn box_and_ball_differ_for_high_dims() {
        // A point at the corner of the box is outside the ball.
        let b = 3.0;
        let p = vec![2.9; 8]; // corner-ish
        let bx = room(Shape::Box, b, 8);
        let bl = room(Shape::Ball, b, 8);
        let fb = bx.fold(&p).unwrap();
        let fl = bl.fold(&p).unwrap();
        // The box leaves it (inside each coordinate); the ball folds it far in.
        assert!(bx.contains(&fb));
        assert!(bl.contains(&fl));
        let norm_b = fb.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_l = fl.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!(
            norm_b > norm_l,
            "the box should keep the corner further out than the ball"
        );
    }

    #[test]
    fn ball_centre_is_fixed() {
        let r = room(Shape::Ball, 3.0, 4);
        let centre = vec![0.0; 4];
        assert_eq!(r.fold(&centre).unwrap(), centre);
    }
}
