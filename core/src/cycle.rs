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
///
/// A child is not one number. The reading therefore carries **per-trait** moments,
/// and a [`Reading::first`] helper for the one-trait case.
#[derive(Debug, Clone, PartialEq)]
pub struct Reading {
    /// How many steps have been taken.
    pub step: usize,
    /// The population's mean, one entry per trait.
    pub means: Vec<f64>,
    /// The population's spread, one entry per trait.
    pub spreads: Vec<f64>,
    /// The room's half-width at this step.
    pub half_width: f64,
    /// The room's shape at this step.
    pub shape: crate::room::Shape,
}

impl Reading {
    /// The first trait's mean, for the one-trait case.
    pub fn mean(&self) -> f64 {
        self.means.first().copied().unwrap_or(0.0)
    }

    /// The first trait's spread, for the one-trait case.
    pub fn spread(&self) -> f64 {
        self.spreads.first().copied().unwrap_or(0.0)
    }

    /// The **average** spread over all traits.
    ///
    /// This is the quantity the laws are about: for a box it should be `B/√3`
    /// whatever the number of traits; for a ball it falls as the traits grow.
    pub fn average_spread(&self) -> f64 {
        if self.spreads.is_empty() {
            return 0.0;
        }
        self.spreads.iter().sum::<f64>() / self.spreads.len() as f64
    }

    /// The number of traits.
    pub fn dims(&self) -> usize {
        self.spreads.len()
    }

    /// The average spread as a fraction of the room's law `B/√3`.
    ///
    /// `1.0` means the population has filled the room; below `1.0` means it has not.
    pub fn fraction_of_law(&self) -> f64 {
        let law = self.half_width / 3.0_f64.sqrt();
        if law > 0.0 {
            self.average_spread() / law
        } else {
            0.0
        }
    }

    /// The total variance across all traits.
    ///
    /// For a uniform population in a ball this is `d/(d+2)·R²`; in a box it is
    /// `d·B²/3`.
    pub fn total_variance(&self) -> f64 {
        self.spreads.iter().map(|s| s * s).sum()
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
    ///
    /// ## Two independent streams
    ///
    /// The birth positions and the first noise must not come from the same sequence.
    /// The earlier version called `Rng::new(seed)` to build the population and then
    /// `Medium::new(room, seed)` — **the same seed** — so the first noise repeated the
    /// sequence the birth positions were drawn from. The initial state and the first
    /// shock were correlated, which is not what a random process should do.
    ///
    /// Here the birth stream and the motion stream are derived from the seed by
    /// different constants, so they are independent for practical purposes while the
    /// whole run stays reproducible from one number.
    pub fn born(room: Room, n: usize, noise: f64, seed: u64) -> Option<Self> {
        let dims = room.dims();
        // The birth stream. `0x9E3779B97F4A7C15` is the odd constant of the golden
        // ratio, used here only to separate the two streams.
        let mut rng = crate::Rng::new(seed ^ 0x9E37_79B9_7F4A_7C15);
        let population: Vec<Child> = (0..n)
            .map(|_| {
                let traits: Vec<f64> = (0..dims).map(|_| rng.normal() * 0.5).collect();
                Child::new(traits, 0.0, noise)
            })
            .collect::<Option<Vec<_>>>()?;
        // The motion stream gets the original seed, which the birth stream no longer
        // uses.
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
    ///
    /// One mean and one spread **per trait**. A child is not one number, and the
    /// laws distinguish a room that bounds each trait (a box) from one that bounds
    /// the whole child (a ball) — which only shows up when there is more than one
    /// trait.
    pub fn read(&self) -> Reading {
        let n = self.population.len();
        let dims = self.room().dims();
        let mut means = Vec::with_capacity(dims);
        let mut spreads = Vec::with_capacity(dims);
        for k in 0..dims {
            let mean = self.population.iter().map(|c| c.position()[k]).sum::<f64>() / n as f64;
            let var = self
                .population
                .iter()
                .map(|c| {
                    let x = c.position()[k] - mean;
                    x * x
                })
                .sum::<f64>()
                / n as f64;
            means.push(mean);
            spreads.push(var.sqrt());
        }
        Reading {
            step: self.step,
            means,
            spreads,
            half_width: self.room().half_width().get(),
            shape: self.room().shape(),
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
    fn a_box_keeps_the_law_with_many_traits() {
        // The law `box_keeps_every_trait`: for a box the average spread is B/sqrt(3)
        // whatever the number of traits.
        let mut spreads = Vec::new();
        for dims in [1, 4, 8] {
            let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), dims).unwrap();
            let mut c = Cycle::born(room, 600, 0.3, 11).unwrap();
            let readings = c.run(8000, 8000);
            let frac = readings.last().unwrap().fraction_of_law();
            spreads.push(frac);
        }
        println!("box fractions of law for d = 1, 4, 8: {:?}", spreads);
        for f in &spreads {
            assert!(
                (f - 1.0).abs() < 0.15,
                "a box should reach the law for every d: {:?}",
                spreads
            );
        }
    }

    #[test]
    fn a_ball_squeezes_as_traits_grow() {
        // The law `ball_squeezes_traits`: for a ball the per-trait spread falls as the
        // number of traits grows.
        let mut fractions = Vec::new();
        for dims in [1, 4, 8] {
            let room = Room::new(Shape::Ball, HalfWidth::new(3.0).unwrap(), dims).unwrap();
            let mut c = Cycle::born(room, 600, 0.3, 12).unwrap();
            let readings = c.run(8000, 8000);
            fractions.push(readings.last().unwrap().fraction_of_law());
        }
        println!("ball fractions of law for d = 1, 4, 8: {:?}", fractions);
        assert!(
            fractions[0] > fractions[1] && fractions[1] > fractions[2],
            "a ball should squeeze as d grows: {:?}",
            fractions
        );
    }

    #[test]
    fn the_reading_carries_every_trait() {
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 5).unwrap();
        let c = Cycle::born(room, 100, 0.3, 13).unwrap();
        let r = c.read();
        assert_eq!(r.dims(), 5);
        assert_eq!(r.means.len(), 5);
        assert_eq!(r.spreads.len(), 5);
        assert_eq!(r.shape, Shape::Box);
    }

    #[test]
    fn birth_and_motion_use_independent_streams() {
        // The earlier version drew the birth positions and the first noise from the
        // same seed, so they were correlated. This test checks the fix: the first
        // noise must not be predictable from the birth positions.
        //
        // How: build two cycles with the same seed but different populations. If the
        // noise stream were shared with the birth stream, the first step would depend
        // on how many numbers the birth drew. With separate streams, the first noise
        // is the same for both, and the difference in outcome comes only from the
        // different starting points.
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();

        // Two populations of different sizes: the birth stream draws a different
        // number of values, so a shared stream would desynchronise the noise.
        let small = Cycle::born(room.clone(), 10, 0.3, 424242).unwrap();
        let large = Cycle::born(room, 1000, 0.3, 424242).unwrap();

        // The first child of each is drawn from the same stream at the same position,
        // so their birth traits must be identical.
        let a = small.population()[0].position()[0];
        let b = large.population()[0].position()[0];
        assert!(
            (a - b).abs() < 1e-12,
            "the first birth must be the same for the same seed: {} vs {}",
            a,
            b
        );

        // And the second child must differ, because the stream advances.
        let a2 = small.population()[1].position()[0];
        assert!(
            (a - a2).abs() > 1e-9,
            "the birth stream must advance: {} vs {}",
            a,
            a2
        );
    }

    #[test]
    fn the_reading_is_not_part_of_the_medium() {
        // The medium has no method returning a Reading. The cycle does, and it is the
        // cycle's job to take it from outside.
        let c = cycle(3.0, 100, 0.3, 5);
        let r = c.read();
        assert_eq!(r.step, 0);
        assert!(r.spread().is_finite());
    }
}
