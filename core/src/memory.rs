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
//!
//! ## What forgetting means
//!
//! A memory older than `memory_life` is dropped to the same state a fresh memory
//! has: nothing is known. While nothing is known the organism **explores** — it
//! takes a random step — instead of treating the cell under its feet as the thing
//! it remembers. The two states used to be conflated, and the result was that a
//! decayed organism stood still until it died; see
//! `docs/REVIEW-emergence-notes.md` §1.2 and `Memory::decay` below.

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

    /// Forgets the memory if it is older than `max_age`. Returns `true` when it
    /// was dropped by this call.
    ///
    /// "Forgotten" is the same state a fresh [`Memory`] has: `best_level = 0.0`.
    /// [`Memory::is_empty`] names it so callers stop spelling it as
    /// `best_level <= 0.0`.
    ///
    /// The old version left `best_cell` pointing at the last target. That was not
    /// the whole defect, but it hid the real one: `Remembering::step` observed the
    /// standing cell **before** choosing a direction, so the first observation
    /// after the drop was richer than `0.0` and re-installed the standing cell as
    /// the best cell. `direction()` then saw `best_cell == cell` and returned
    /// `0` (stay). Every later `decay` was undone the same way in the same
    /// step, so the organism never moved again. Forgetting became paralysis.
    ///
    /// `best_cell` is deliberately not reset here: it is only meaningful while
    /// `is_empty()` is false, and a sentinel would need every reader of the field
    /// (including `life.rs`) to learn it. The empty flag is the authority.
    pub fn decay(&mut self, max_age: usize) -> bool {
        if self.age > max_age {
            self.best_level = 0.0;
            true
        } else {
            false
        }
    }

    /// True when nothing is remembered: the state `decay` leaves behind.
    pub fn is_empty(&self) -> bool {
        self.best_level <= 0.0
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
    /// The cell the organism was on **before** it moved on the last step.
    ///
    /// `cell` is where it is now; this is where it came from. Without it a death
    /// can be described but not traced: EXP-62 found latecomers dying with
    /// 0.0749 energy one step after arriving, and could not say where they had
    /// been. See `docs/FINDING-the-late-deaths-are-latecomers.md`.
    pub last_cell: usize,
    pub organism: Organism,
    pub cell: usize,
    pub memory: Memory,
    pub move_cost: f64,
    /// How long a memory lasts.
    pub memory_life: usize,
    /// Deterministic source for the exploration step taken when the memory is
    /// empty. Seeded from the starting cell in [`Remembering::new`]: the
    /// standalone step has no seed argument, and two organisms that start on the
    /// same cell are the same trajectory anyway. A shared generator would couple
    /// organisms that have nothing to do with each other.
    pub rng: crate::Rng,
}

impl Remembering {
    pub fn new(organism: Organism, cell: usize, level: f64, move_cost: f64, memory_life: usize) -> Option<Self> {
        if !move_cost.is_finite() || move_cost < 0.0 {
            return None;
        }
        Some(Self {
            last_direction: 0,
            last_taken: 0.0,
            last_cell: cell,
            organism,
            cell,
            memory: Memory::new(cell, level),
            move_cost,
            memory_life,
            rng: crate::Rng::new((cell as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15) ^ 0xD1CE),
        })
    }

    /// Chooses a direction: toward the remembered cell if it is not here.
    ///
    /// Returns `-1` for left, `1` for right, `0` for stay.
    pub fn direction(&self) -> i32 {
        if self.memory.is_empty() || self.memory.best_cell == self.cell {
            return 0;
        }
        if self.memory.best_cell < self.cell {
            -1
        } else {
            1
        }
    }

    /// One step: see the cell, forget, explore or return, live.
    ///
    /// When [`Memory::decay`] has just dropped the memory, the organism
    /// **explores**: it takes one step left or right at random instead of
    /// standing. The decision is made from the post-decay state, because the
    /// observation of the standing cell happens in the same step and would
    /// otherwise re-install that cell as the remembered one in the very step
    /// that forgot it. That is the defect `docs/REVIEW-emergence-notes.md`
    /// §1.2 found: an empty memory meant "the best cell is the one under my
    /// feet", and the organism stood until it died.
    ///
    /// Reason for exploring rather than standing: `best_level <= 0` is "I know
    /// nothing", not "I know this cell". The organism can only ever see its own
    /// cell, so the first thing it sees after forgetting is not a memory of
    /// somewhere worth returning to. Moving is what makes the dropped memory a
    /// fresh search instead of a decision to stay.
    pub fn step(&mut self, field: &mut Field, world: &World) -> bool {
        if !self.organism.is_alive() {
            return false;
        }

        // 1. See only the current cell, then forget.
        let here = field.level(self.cell);
        self.memory.observe(self.cell, here);
        let forgotten = self.memory.decay(self.memory_life);

        // 2. Move toward the remembered cell, or explore when there is none.
        //    `forgotten` matters because `observe` above may have just re-armed
        //    the memory with the standing cell.
        let dir = if forgotten || self.memory.is_empty() {
            if self.rng.uniform() < 0.5 {
                -1
            } else {
                1
            }
        } else {
            self.direction()
        };
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
        assert!(r.memory.is_empty());
        assert_eq!(r.direction(), 0);
    }

    /// The regression from `docs/REVIEW-emergence-notes.md` §1.2: a memory that
    /// has just decayed must not pin the organism to the cell it stands on.
    ///
    /// Before the fix: `decay` zeroed `best_level`, `step` observed the standing
    /// cell first, so `best_cell` became the current cell, `direction()` returned
    /// `0`, and the organism never moved again. The test asks only the question
    /// the defect is about: after the decay fires, is the cell still the same?
    #[test]
    fn a_forgotten_memory_lets_the_organism_leave() {
        let o = Organism::healthy(5.0).unwrap();
        let mut r = Remembering::new(o, 5, 1.0, 0.0, 3).unwrap();
        r.memory.age = 4; // older than `memory_life`
        let mut field = Field::new(20, 1.0, 0.0).unwrap();
        let world = World::default();

        let before = r.cell;
        r.step(&mut field, &world);
        assert!(
            r.memory.is_empty() || r.memory.best_cell == r.cell,
            "the decay step is about exploration, not about the old target"
        );
        assert_ne!(
            r.cell, before,
            "after decay the organism must leave the cell, not stand on it until death"
        );
    }

    /// The same question with no memory at all: `memory_life = 0` makes every
    /// step a forgotten one, so the organism must keep exploring. This is the
    /// stronger form of the regression: the old code never left cell 5.
    #[test]
    fn an_empty_memory_keeps_the_organism_exploring() {
        let o = Organism::healthy(5.0).unwrap();
        let mut r = Remembering::new(o, 5, 1.0, 0.0, 0).unwrap();
        r.memory.best_cell = 9;
        r.memory.age = 1;
        let mut field = Field::new(20, 1.0, 0.0).unwrap();
        let world = World::default();

        // A step that re-observes the cell it just landed on re-arms the memory
        // for one step (`best_level` rises from 0 again) and the next decay sends
        // it on. The claim is not "it moves on every single step", it is "it is
        // never pinned": over ten steps it keeps leaving the cell it stands on.
        let start = r.cell;
        let mut previous = r.cell;
        let mut moves = 0;
        for _ in 0..10 {
            r.step(&mut field, &world);
            if r.cell != previous {
                moves += 1;
            }
            previous = r.cell;
        }
        assert!(
            moves >= 4,
            "with no memory the organism must keep exploring, got {moves} moves in 10 steps"
        );
        assert_ne!(r.cell, start, "exploration must change the position");
    }

    /// Control in the other direction: a long-lived memory is not lost. The
    /// organism still walks toward the remembered cell, and the memory is intact
    /// after the step.
    #[test]
    fn a_long_lived_memory_is_not_lost() {
        let o = Organism::healthy(5.0).unwrap();
        let mut r = Remembering::new(o, 5, 0.1, 0.0, 1000).unwrap();
        r.memory.best_cell = 9;
        r.memory.best_level = 2.0; // richer than any cell of the field below
        let mut field = Field::new(20, 1.0, 0.0).unwrap();
        let world = World::default();

        r.step(&mut field, &world);

        assert_eq!(r.cell, 6, "the organism must walk toward the remembered cell");
        assert_eq!(r.memory.best_cell, 9);
        assert!(
            (r.memory.best_level - 2.0).abs() < 1e-12,
            "a long memory_life must not forget the memory"
        );
    }
}
