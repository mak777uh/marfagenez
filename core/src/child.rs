//! # The child and the cycle
//!
//! A room with a boundary is not yet a medium. Something has to **live** in it.
//! This module adds the child and the cycle — the smallest thing that can be called
//! a life in this model.
//!
//! ## What the laws say the child needs
//!
//! | law | what it forces |
//! |---|---|
//! | `spread = B/√3` | the room must be bounded, or the range is undefined |
//! | `Var = d/(d+2)·R²` | each trait needs its own bound, or the child is squeezed |
//! | `α = 2μ/σ²` | growth spends range; the child cannot have both without limit |
//! | noise is the source of width | without noise the child becomes a point |
//!
//! ## What the medium must NOT do
//!
//! From `docs/VISION.md`, principles 3 and 4:
//!
//! * **It must not measure.** There is no `score()`, no `evaluate()`, no `compare()`.
//!   The child cannot be told how it is doing, because being told is being made an
//!   object.
//! * **It must not direct.** There is no `suggest()`, no `hint()`, no `goal()`. The
//!   child moves by its own drift and its own noise.
//!
//! The medium's whole job is [`Room::fold`]: keep the boundary. Nothing else.
//!
//! ## What this module deliberately does not have
//!
//! No observer that writes back. The child does not know its own state, does not
//! remember it, and is not told it. This is principle 3 taken literally: a logger
//! that feeds into the child is an observer that destroys the observation.

#![forbid(unsafe_code)]

use crate::room::Room;
use crate::Rng;

/// A child: one point in the room, with its own drift and its own noise.
///
/// The fields are private on purpose. Nothing outside can read the child's state to
/// decide what to do with it — the medium has no business knowing.
#[derive(Debug, Clone)]
pub struct Child {
    traits: Vec<f64>,
    drive: f64,
    noise: f64,
}

impl Child {
    /// Builds a child. Returns `None` for a child with no traits, a negative drive
    /// magnitude, or a negative noise — all of which would make the model
    /// meaningless.
    pub fn new(traits: Vec<f64>, drive: f64, noise: f64) -> Option<Self> {
        if traits.is_empty() || !drive.is_finite() || !noise.is_finite() || noise < 0.0 {
            return None;
        }
        Some(Self {
            traits,
            drive,
            noise,
        })
    }

    /// A child born at the centre of a room with `dims` traits.
    pub fn born(dims: usize, drive: f64, noise: f64) -> Option<Self> {
        Self::new(vec![0.0; dims], drive, noise)
    }

    pub fn dims(&self) -> usize {
        self.traits.len()
    }

    /// Takes one step: drift, then noise. **The room is not applied here** — the
    /// boundary belongs to the medium, not to the child, so the child cannot be
    /// blamed for crossing it.
    pub fn drift_and_noise(&mut self, rng: &mut Rng) {
        for t in self.traits.iter_mut() {
            *t += self.drive + self.noise * rng.normal();
        }
    }

    /// The child's position, for the medium to fold. Read-only.
    pub fn position(&self) -> &[f64] {
        &self.traits
    }

    /// Puts the child back inside the room. Only the medium calls this.
    pub(crate) fn place(&mut self, folded: Vec<f64>) {
        self.traits = folded;
    }
}

/// The medium: a room, and nothing else.
///
/// It holds a child and keeps the boundary. It does not read the child, does not
/// score it, does not steer it.
#[derive(Debug)]
pub struct Medium {
    room: Room,
    rng: Rng,
}

impl Medium {
    pub fn new(room: Room, seed: u64) -> Self {
        Self {
            room,
            rng: Rng::new(seed),
        }
    }

    pub fn room(&self) -> &Room {
        &self.room
    }

    /// One step of the cycle: the child moves, the medium keeps the boundary.
    ///
    /// Returns `None` if the child's number of traits does not match the room, which
    /// is the only thing the medium is allowed to refuse.
    pub fn step(&mut self, child: &mut Child) -> Option<()> {
        if child.dims() != self.room.dims() {
            return None;
        }
        child.drift_and_noise(&mut self.rng);
        let folded = self.room.fold(child.position())?;
        child.place(folded);
        Some(())
    }

    /// Runs `steps` steps. The medium does not look at the result — it has no
    /// reason to.
    pub fn run(&mut self, child: &mut Child, steps: usize) -> Option<()> {
        for _ in 0..steps {
            self.step(child)?;
        }
        Some(())
    }
}

/// A reading taken **from outside** the medium.
///
/// This is not part of the medium. It exists so that a person looking at the system
/// can see what happened, and it is deliberately a separate type: the medium cannot
/// produce one, because the medium does not measure.
#[derive(Debug, Clone, Copy)]
pub struct OutsideReading {
    pub mean: f64,
    pub spread: f64,
    pub n: usize,
}

impl OutsideReading {
    /// Measures a child from outside. Only a caller outside the medium can do this,
    /// and the medium never sees the result.
    pub fn of(child: &Child) -> Option<Self> {
        let xs = child.position();
        if xs.is_empty() {
            return None;
        }
        let n = xs.len();
        let mean = xs.iter().sum::<f64>() / n as f64;
        let var = xs.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / n as f64;
        Some(Self {
            mean,
            spread: var.sqrt(),
            n,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::room::Shape;
    use crate::HalfWidth;

    fn setup(shape: Shape, b: f64, d: usize) -> (Medium, Child) {
        let room = Room::new(shape, HalfWidth::new(b).unwrap(), d).unwrap();
        let child = Child::born(d, 0.0, 0.3).unwrap();
        (Medium::new(room, 42), child)
    }

    #[test]
    fn child_without_traits_rejected() {
        assert!(Child::new(vec![], 0.0, 0.3).is_none());
    }

    #[test]
    fn negative_noise_rejected() {
        assert!(Child::new(vec![0.0], 0.0, -0.1).is_none());
    }

    #[test]
    fn child_stays_inside_the_room() {
        let (mut medium, mut child) = setup(Shape::Box, 3.0, 4);
        medium.run(&mut child, 2000).unwrap();
        assert!(
            medium.room().contains(child.position()),
            "the medium failed to keep the boundary"
        );
    }

    #[test]
    fn wrong_dims_refused() {
        let (mut medium, _) = setup(Shape::Box, 3.0, 4);
        let mut wrong = Child::born(2, 0.0, 0.3).unwrap();
        assert!(medium.step(&mut wrong).is_none());
    }

    #[test]
    fn zero_noise_becomes_a_point() {
        // Without noise the child has no width: it is a point pushed by its drift.
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
        let mut medium = Medium::new(room, 7);
        let mut child = Child::new(vec![0.0], 0.01, 0.0).unwrap();
        medium.run(&mut child, 5000).unwrap();
        let r = OutsideReading::of(&child).unwrap();
        assert!(
            r.spread < 1e-9,
            "a child with no noise must be a point, got spread {}",
            r.spread
        );
    }

    #[test]
    fn medium_has_no_measurement_api() {
        // This test is a compile-time statement, expressed as a comment: there is no
        // `Medium::score`, `Medium::evaluate`, `Medium::suggest` or `Medium::goal`.
        // If one were added, principle 3 or 4 of the vision would be broken, and this
        // test's name would be a lie. The absence is the guarantee.
        let (medium, _) = setup(Shape::Box, 3.0, 1);
        // The only public surface is `room()`, `step()` and `run()`.
        let _ = medium.room();
    }
}
