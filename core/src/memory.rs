//! # Memory
//!
//! The walker in `field.rs` can see its neighbours. This module takes that away: the
//! organism sees **only its own cell**, and must remember where the resource was.
//!
//! ## Why
//!
//! Without memory, an organism that cannot see its neighbours has nothing to act on.
//! With memory, the past changes the present: a cell that was rich is worth
//! returning to.
//!
//! ## The three conditions
//!
//! | condition | what the organism does |
//! |---|---|
//! | **A** | stays |
//! | **B** | moves at random (no memory, no sight) |
//! | **C** | remembers the best cell it has seen and returns to it |
//!
//! ## What is measured
//!
//! The plan's EXP-03: does individual history change the reaction to the same
//! stimulus? Here the stimulus is the field, and the history is the memory.
//!
//! ## What this module does not have
//!
//! No learning in the strong sense: the rule is fixed ("go to the remembered cell").
//! What is added is a **store** that the rule reads. Whether that store helps is the
//! question.

#![forbid(unsafe_code)]

use crate::field::Field;
use crate::organism::{Organism, World};

/// What an organism remembers.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Memory {
    /// The cell that was richest when it was seen.
    pub best_cell: usize,
    /// The level seen there.
    pub best_level: f64,
    /// How many steps ago it was seen.
    pub age: usize,
}

impl Memory {
    /// A fresh memory pointing at the starting cell.
    pub fn new(cell: usize, level: f64) -> Self {
        Self {
            best_cell: cell,
            best_level: level,
            age: 0,
        }
    }

    /// Updates the memory with what is seen now. Returns `true` if the memory changed.
    ///
    /// The rule: a richer cell replaces the memory. An equally rich cell does not,
    /// so the organism does not oscillate between two equally good cells.
    pub fn observe(&mut self, cell: usize, level: f64) -> bool {
        self.age += 1;
        if level > self.best_level {
            self.best_cell = cell;
            self.best_level = level;
            self.age = 0;
            true
        } else {
            false
        }
    }

    /// Forgets the memory if it is older than `max_age`.
    pub fn decay(&mut self, max_age: usize) {
        if self.age > max_age {
            self.best_level = 0.0;
        }
    }
}

/// An organism with memory.
#[derive(Debug, Clone)]
pub struct Remembering {
    /// The direction chosen on the last step, stored so a reading can show the
    /// decision the organism actually made rather than the one it would make now.
    ///
    /// Recomputing `direction()` at reading time gives a value consistent with the
    /// field AFTER the step, which is not the decision the organism took. See
    /// `docs/FINDING-trace-inconsistent.md`.
    pub last_direction: i32,
    /// What the organism actually took from its cell on the last step.
    ///
    /// Like `last_direction`, this is stored rather than recomputed: the cell's
    /// value after the step is not the value the organism took from.
    pub last_taken: f64,
    pub organism: Organism,
    pub cell: usize,
    pub memory: Memory,
    pub move_cost: f64,
    /// How long a memory lasts.
    pub memory_life: usize,
}

impl Remembering {
    pub fn new(organism: Organism, cell: usize, level: f64, move_cost: f64, memory_life: usize) -> Option<Self> {
        if !move_cost.is_finite() || move_cost < 0.0 {
            return None;
        }
        Some(Self {
            last_direction: 0,
            last_taken: 0.0,
            organism,
            cell,
            memory: Memory::new(cell, level),
            move_cost,
            memory_life,
        })
    }

    /// Chooses a direction: toward the remembered cell if it is not here.
    ///
    /// Returns `-1` for left, `1` for right, `0` for stay.
    pub fn direction(&self) -> i32 {
        if self.memory.best_cell == self.cell || self.memory.best_level <= 0.0 {
            return 0;
        }
        if self.memory.best_cell < self.cell {
            -1
        } else {
            1
        }
    }

    /// One step: see the cell, remember, move toward the memory, live.
    pub fn step(&mut self, field: &mut Field, world: &World) -> bool {
        if !self.organism.is_alive() {
            return false;
        }

        // 1. See only the current cell.
        let here = field.level(self.cell);
        self.memory.observe(self.cell, here);
        self.memory.decay(self.memory_life);

        // 2. Move toward the remembered cell.
        let dir = self.direction();
        if dir != 0 && self.organism.spend(self.move_cost) {
            if dir < 0 && self.cell > 0 {
                self.cell -= 1;
            } else if dir > 0 && self.cell + 1 < field.cells() {
                self.cell += 1;
            }
        }

        // 3. Take what is here now.
        let taken = field.take(self.cell, world.income);

        // 4. Live.
        let alive = self.organism.step(world, taken);

        // 5. Regrow.
        field.regrow_all();

        alive
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_starts_at_the_given_cell() {
        let m = Memory::new(3, 0.5);
        assert_eq!(m.best_cell, 3);
        assert!((m.best_level - 0.5).abs() < 1e-12);
        assert_eq!(m.age, 0);
    }

    #[test]
    fn a_richer_cell_replaces_the_memory() {
        let mut m = Memory::new(3, 0.5);
        assert!(m.observe(4, 0.9));
        assert_eq!(m.best_cell, 4);
        assert!((m.best_level - 0.9).abs() < 1e-12);
    }

    #[test]
    fn a_poorer_cell_does_not() {
        let mut m = Memory::new(3, 0.5);
        assert!(!m.observe(4, 0.2));
        assert_eq!(m.best_cell, 3);
    }

    #[test]
    fn an_equal_cell_does_not_replace() {
        // Otherwise the organism would oscillate between two equally good cells.
        let mut m = Memory::new(3, 0.5);
        assert!(!m.observe(4, 0.5));
        assert_eq!(m.best_cell, 3);
    }

    #[test]
    fn memory_decays() {
        let mut m = Memory::new(3, 0.5);
        m.decay(10);
        assert!((m.best_level - 0.5).abs() < 1e-12);
        for _ in 0..12 {
            m.observe(4, 0.1);
        }
        m.decay(10);
        assert!((m.best_level - 0.0).abs() < 1e-12);
    }

    #[test]
    fn direction_points_toward_the_memory() {
        let o = Organism::healthy(5.0).unwrap();
        let mut r = Remembering::new(o, 5, 0.1, 0.1, 100).unwrap();
        r.memory.best_cell = 8;
        r.memory.best_level = 1.0;
        assert_eq!(r.direction(), 1);

        r.memory.best_cell = 2;
        assert_eq!(r.direction(), -1);

        r.memory.best_cell = 5;
        assert_eq!(r.direction(), 0);
    }

    #[test]
    fn no_memory_means_no_direction() {
        let o = Organism::healthy(5.0).unwrap();
        let mut r = Remembering::new(o, 5, 0.1, 0.1, 100).unwrap();
        r.memory.best_level = 0.0;
        assert_eq!(r.direction(), 0);
    }
}
