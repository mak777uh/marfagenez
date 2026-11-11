//! # The cycle: a medium that runs
//!
//! Everything so far is a library. There is no program. This module is the smallest
//! thing that can be called a **running medium**: a room, a population, and a loop
//! that advances them.
//!
//! ## What the cycle is allowed to do
//!
//! From `docs/LAWS.md`, the medium may only:
//!
//! * move each child by its own drift and noise;
//! * fold each child back into the room.
//!
//! Nothing else. The cycle below does exactly those two things and nothing more.
//!
//! ## What the cycle may report
//!
//! The cycle produces a [`Reading`] once per checkpoint. A reading is taken **from
//! outside**: the medium does not use it, and the child never sees it.
//!
//! This is the shape principle 3 allows: the medium runs blind, and an observer
//! outside watches. The observer is not part of the medium.

#![forbid(unsafe_code)]

use crate::child::{Child, Medium};
use crate::room::Room;

/// A reading taken from outside the medium.
///
/// This is the only thing the cycle emits. The medium never reads it back.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Reading {
    /// How many steps have been taken.
    pub step: usize,
    /// The population's mean on the first trait.
    pub mean: f64,
    /// The population's spread on the first trait.
    pub spread: f64,
    /// The room's half-width at this step.
    pub half_width: f64,
}

impl Reading {
    /// The spread as a fraction of the room's law `B/√3`.
    ///
    /// This is the number the laws are about: `1.0` means the population has filled
    /// the room; below `1.0` means it has not.
    pub fn fraction_of_law(&self) -> f64 {
        let law = self.half_width / 3.0_f64.sqrt();
        if law > 0.0 {
            self.spread / law
        } else {
            0.0
        }
    }
}

/// A running medium: a room, a population, and a loop.
#[derive(Debug)]
pub struct Cycle {
    medium: Medium,
    population: Vec<Child>,
    step: usize,
}

impl Cycle {
    /// Builds a cycle. Returns `None` for an empty population or a child whose number
    /// of traits does not match the room.
    pub fn new(room: Room, population: Vec<Child>, seed: u64) -> Option<Self> {
        if population.is_empty() {
            return None;
        }
        let dims = room.dims();
        if population.iter().any(|c| c.dims() != dims) {
            return None;
        }
        Some(Self {
            medium: Medium::new(room, seed),
            population,
            step: 0,
        })
    }

    /// A population born at the centre of a room, with the given noise.
    pub fn born(room: Room, n: usize, noise: f64, seed: u64) -> Option<Self> {
        let dims = room.dims();
        let mut rng = crate::Rng::new(seed);
        let population: Vec<Child> = (0..n)
            .map(|_| {
                let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
                Child::new(traits, 0.0, noise)
            })
            .collect::<Option<Vec<_>>>()?;
        Self::new(room, population, seed)
    }

    pub fn room(&self) -> &Room {
        self.medium.room()
    }

    pub fn step(&self) -> usize {
        self.step
    }

    pub fn population(&self) -> &[Child] {
        &self.population
    }

    /// Advances the whole population by one step.
    ///
    /// This is the whole of what the medium does: drift-and-noise, then fold.
    pub fn advance(&mut self) -> Option<()> {
        for c in self.population.iter_mut() {
            self.medium.step(c)?;
        }
        self.step += 1;
        Some(())
    }

    /// Runs `steps` steps and returns a reading every `every` steps.
    ///
    /// The readings are taken **from outside**: the medium does not see them.
    pub fn run(&mut self, steps: usize, every: usize) -> Vec<Reading> {
        let every = every.max(1);
        let mut readings = Vec::new();
        for _ in 0..steps {
            if self.advance().is_none() {
                break;
            }
            if self.step % every == 0 {
                readings.push(self.read());
            }
        }
        readings
    }

    /// Takes a reading from outside. The medium does not call this.
    pub fn read(&self) -> Reading {
        let n = self.population.len();
        let mean = self.population.iter().map(|c| c.position()[0]).sum::<f64>() / n as f64;
        let var = self
            .population
            .iter()
            .map(|c| {
                let x = c.position()[0] - mean;
                x * x
            })
            .sum::<f64>()
            / n as f64;
        Reading {
            step: self.step,
            mean,
            spread: var.sqrt(),
            half_width: self.room().half_width().get(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::room::Shape;
    use crate::HalfWidth;

    fn cycle(b: f64, n: usize, noise: f64, seed: u64) -> Cycle {
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        Cycle::born(room, n, noise, seed).unwrap()
    }

    #[test]
    fn an_empty_population_is_refused() {
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
        assert!(Cycle::new(room, vec![], 1).is_none());
    }

    #[test]
    fn a_mismatched_population_is_refused() {
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 2).unwrap();
        let child = Child::born(1, 0.0, 0.3).unwrap();
        assert!(Cycle::new(room, vec![child], 1).is_none());
    }

    #[test]
    fn the_cycle_advances_and_reads() {
        let mut c = cycle(3.0, 500, 0.3, 1);
        let readings = c.run(1000, 100);
        assert_eq!(readings.len(), 10);
        assert_eq!(readings[0].step, 100);
        assert_eq!(readings[9].step, 1000);
    }

    #[test]
    fn the_cycle_reaches_the_law() {
        // The saturation law: a room of half-width 3 with noise 0.3 fills in
        // (3/0.3)^2 = 100 steps, so after 2000 steps the population is at the law.
        let mut c = cycle(3.0, 800, 0.3, 2);
        let readings = c.run(2000, 1000);
        let last = readings.last().unwrap();
        let frac = last.fraction_of_law();
        assert!(
            (frac - 1.0).abs() < 0.1,
            "the cycle should reach the law, got {} of it",
            frac
        );
    }

    #[test]
    fn the_cycle_keeps_every_child_inside() {
        let mut c = cycle(3.0, 300, 0.5, 3);
        c.run(3000, 500);
        for child in c.population() {
            assert!(
                c.room().contains(child.position()),
                "a child left the room: {:?}",
                child.position()
            );
        }
    }

    #[test]
    fn a_wide_room_is_far_from_its_law_early() {
        // The wide-room finding: at 100 steps a room of half-width 30 is far below
        // its law.
        let mut c = cycle(30.0, 500, 0.3, 4);
        let readings = c.run(100, 100);
        let frac = readings.last().unwrap().fraction_of_law();
        assert!(
            frac < 0.5,
            "a wide room should be far below its law at 100 steps, got {}",
            frac
        );
    }

    #[test]
    fn the_reading_is_not_part_of_the_medium() {
        // The medium has no method returning a Reading. The cycle does, and it is the
        // cycle's job to take it from outside.
        let c = cycle(3.0, 100, 0.3, 5);
        let r = c.read();
        assert_eq!(r.step, 0);
        assert!(r.spread.is_finite());
    }
}
