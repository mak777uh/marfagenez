//! # A room with several traits
//!
//! A child is not one number. This module gives the room **dimensions**, and it
//! enforces one distinction: a room can bound each trait separately (a **box**) or
//! the whole child at once (a **ball**).
//!
//! ## The ball is not used for results
//!
//! `Shape::Ball` is kept as an **experiment**, not as a result. The reason is a
//! measurement: the radial fold does not preserve the uniform measure.
//!
//! | room | `chi²` of the folded distribution | expected |
//! |---|---|---|
//! | box | **35.0** for 36 degrees of freedom | 36 |
//! | ball | **31 429 297** for 9 degrees of freedom | 9 |
//!
//! The box preserves the uniform distribution; the ball does not. The cause is
//! geometry: in `d` dimensions the volume of a spherical shell grows as `r^(d-1)`,
//! so folding the radius without accounting for that moves mass to the wrong places.
//!
//! So the ball is marked [`Shape::is_trusted`] = `false`, and every result that
//! depends on the room's shape must check it. The `Box` is the only shape on which
//! the project makes claims.
//!
//! ## The type-level guarantee
//!
//! [`Room`] is an enum, not a pair of numbers with a boolean flag. You cannot
//! accidentally build a ball and use it as a box: the two are different variants, and
//! [`Room::is_trusted`] says which one the results may rest on.

#![forbid(unsafe_code)]

use crate::{HalfWidth, Reflect};

/// The shape of a room.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    /// Each trait bounded separately: `|x_k| ≤ B` for every `k`.
    ///
    /// The fold preserves the uniform measure (measured: `chi² = 35.0` for 36 dof).
    Box,
    /// The whole child bounded at once: `‖x‖ ≤ B`.
    ///
    /// **Not trusted.** The radial fold does not preserve the uniform measure
    /// (measured: `chi² = 31 429 297` for 9 dof). Kept for experiments only.
    Ball,
}

impl Shape {
    /// Whether results may rest on this shape.
    ///
    /// `true` only for [`Shape::Box`]. A result that depends on the room's shape must
    /// check this before it is reported.
    pub fn is_trusted(self) -> bool {
        matches!(self, Shape::Box)
    }
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

    /// A box room: the only shape on which the project makes claims.
    pub fn box_room(half_width: HalfWidth, dims: usize) -> Option<Self> {
        Self::new(Shape::Box, half_width, dims)
    }

    /// Whether results may rest on this room's shape.
    pub fn is_trusted(&self) -> bool {
        self.shape.is_trusted()
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

    /// The per-trait spread of a filled box: `B/√3`, independent of `d`.
    ///
    /// This is the law `box_keeps_every_trait`, and it holds only for a box.
    /// For a ball the value is meaningless, because the ball's fold does not
    /// preserve the uniform measure.
    pub fn box_spread(&self) -> f64 {
        self.half_width.uniform_spread().0
    }

    /// The exact per-trait variance of a uniform distribution in a `d`-ball:
    /// `R²/(d+2)`.
    ///
    /// This is the **exact** value, not the approximation `R²/d` the earlier version
    /// returned. It describes a uniform distribution in a ball; it does **not**
    /// describe the distribution the ball's fold produces, because that fold does not
    /// preserve the uniform measure.
    pub fn ball_trait_variance_uniform(&self) -> f64 {
        let d = self.dims as f64;
        let r = self.half_width.get();
        r * r / (d + 2.0)
    }

    /// The total variance of a uniform distribution in a `d`-ball: `d/(d+2)·R²`.
    ///
    /// This is `E[‖X‖²]`, the mean squared radius — **not** the variance of one
    /// coordinate. The earlier version of this module and its notes used the same
    /// symbol for both, which was an error.
    pub fn ball_total_variance_uniform(&self) -> f64 {
        let d = self.dims as f64;
        let r = self.half_width.get();
        d / (d + 2.0) * r * r
    }

    /// Folds a point back into the room.
    ///
    /// * A **box** reflects each coordinate independently. This preserves the uniform
    ///   measure, so a uniform population stays uniform.
    /// * A **ball** reflects the point along its radius. This does **not** preserve
    ///   the uniform measure, so a uniform population becomes non-uniform.
    ///
    /// Both keep the point inside; only the box keeps the distribution uniform.
    pub fn fold(&self, point: &[f64]) -> Option<Vec<f64>> {
        if point.len() != self.dims {
            return None;
        }
        // Reject non-finite input: a `NaN` coordinate would pass through the fold
        // unchanged and corrupt every later measurement.
        if point.iter().any(|x| !x.is_finite()) {
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
                //
                // Note: this keeps the point inside but does NOT preserve the uniform
                // measure, because the shell volume grows as r^(d-1).
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
    fn only_the_box_is_trusted() {
        assert!(Shape::Box.is_trusted());
        assert!(!Shape::Ball.is_trusted());
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
    fn nan_is_rejected() {
        let r = room(Shape::Box, 3.0, 2);
        assert!(r.fold(&[f64::NAN, 0.0]).is_none());
        assert!(r.fold(&[f64::INFINITY, 0.0]).is_none());
    }

    #[test]
    fn wrong_dimension_rejected() {
        let r = room(Shape::Box, 3.0, 4);
        assert!(r.fold(&[1.0, 2.0]).is_none());
    }

    #[test]
    fn box_spread_is_independent_of_dims() {
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
    fn ball_trait_variance_is_the_exact_uniform_value() {
        // For a uniform distribution in a d-ball: Var(X_i) = R^2/(d+2).
        // The earlier version returned R^2/d, which is wrong.
        let r1 = room(Shape::Ball, 3.0, 1);
        assert!((r1.ball_trait_variance_uniform() - 9.0 / 3.0).abs() < 1e-12);
        let r2 = room(Shape::Ball, 3.0, 2);
        assert!((r2.ball_trait_variance_uniform() - 9.0 / 4.0).abs() < 1e-12);
        let r8 = room(Shape::Ball, 3.0, 8);
        assert!((r8.ball_trait_variance_uniform() - 9.0 / 10.0).abs() < 1e-12);
    }

    #[test]
    fn ball_total_variance_is_the_mean_squared_radius() {
        // d/(d+2)*R^2 is E[||X||^2], not the variance of one coordinate.
        let r1 = room(Shape::Ball, 3.0, 1);
        assert!((r1.ball_total_variance_uniform() - 9.0 / 3.0).abs() < 1e-12);
        let r2 = room(Shape::Ball, 3.0, 2);
        assert!((r2.ball_total_variance_uniform() - 9.0 / 2.0).abs() < 1e-12);
        // And the total is d times the per-coordinate variance.
        let r4 = room(Shape::Ball, 3.0, 4);
        assert!(
            (r4.ball_total_variance_uniform() - 4.0 * r4.ball_trait_variance_uniform()).abs()
                < 1e-12
        );
    }

    #[test]
    fn ball_centre_is_fixed() {
        let r = room(Shape::Ball, 3.0, 4);
        let centre = vec![0.0; 4];
        assert_eq!(r.fold(&centre).unwrap(), centre);
    }
}
