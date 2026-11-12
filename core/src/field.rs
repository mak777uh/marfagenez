//! # Resources and action
//!
//! The organism in `organism.rs` takes whatever resource the world offers. It has no
//! **action**: it cannot influence its income. This module adds the first action.
//!
//! ## The world
//!
//! A one-dimensional line of `cells` cells. Each cell holds a resource level in
//! `[0, max_resource]`. Resources regrow toward the maximum at `regrow` per step.
//!
//! ## The organism
//!
//! An organism sits in a cell and can **move** one cell left or right. Moving costs
//! energy. The resource it gains is the level in the cell it ends up in.
//!
//! ## The question
//!
//! Does having an action help? The plan's EXP-02 compares:
//!
//! | condition | the organism |
//! |---|---|
//! | **A** | cannot move; takes what its cell offers |
//! | **B** | moves toward the richer neighbour |
//! | **C** | moves at random |
//!
//! If B survives where A does not, the action has a causal effect.
//!
//! ## What this module does not have
//!
//! No memory, no learning, no reproduction. The action is a fixed rule. The point is
//! to measure whether the rule helps, not to evolve one.

#![forbid(unsafe_code)]

use crate::organism::{Organism, World};

/// A one-dimensional world of cells, each holding a resource.
#[derive(Debug, Clone)]
pub struct Field {
    cells: Vec<f64>,
    max_resource: f64,
    regrow: f64,
    /// How far the resource pattern shifts per step. `0.0` for a static field.
    ///
    /// This is the one thing a static field cannot show: whether a memory that
    /// keeps updating is worth anything. In a static field every cell's value is
    /// fixed, so a frozen memory and an updating memory see the same world. In a
    /// moving field the best cell changes, and only an updating memory can follow.
    shift: f64,
    /// The step counter, used to compute the shift.
    t: usize,
}

impl Field {
    /// Builds a field. Returns `None` for zero cells or invalid parameters.
    pub fn new(cells: usize, max_resource: f64, regrow: f64) -> Option<Self> {
        if cells == 0 || !max_resource.is_finite() || max_resource <= 0.0 {
            return None;
        }
        if !regrow.is_finite() || !(0.0..=1.0).contains(&regrow) {
            return None;
        }
        Some(Self {
            cells: vec![max_resource; cells],
            max_resource,
            regrow,
            shift: 0.0,
            t: 0,
        })
    }

    /// A field where every second cell is rich and the others are poor.
    pub fn alternating(cells: usize, rich: f64, poor: f64, regrow: f64) -> Option<Self> {
        let mut f = Self::new(cells, rich, regrow)?;
        for i in 0..cells {
            f.cells[i] = if i % 2 == 0 { rich } else { poor };
        }
        Some(f)
    }

    /// A field whose pattern shifts by `shift` cells per step.
    ///
    /// The pattern is a single rich cell that walks along the field and wraps
    /// around. `shift = 0.0` gives a static field; `shift = 1.0` moves it one cell
    /// per step.
    ///
    /// This is the field the memory experiment needs: the best cell moves, so a
    /// memory that keeps updating can follow it and a frozen memory cannot.
    pub fn moving(cells: usize, rich: f64, poor: f64, regrow: f64, shift: f64) -> Option<Self> {
        let mut f = Self::new(cells, rich, regrow)?;
        if !shift.is_finite() || shift < 0.0 {
            return None;
        }
        for i in 0..cells {
            f.cells[i] = poor;
        }
        f.shift = shift;
        f.t = 0;
        f.apply_shift();
        Some(f)
    }

    /// Puts the rich cell where the current time says it should be.
    fn apply_shift(&mut self) {
        let n = self.cells.len();
        if n == 0 {
            return;
        }
        // Reset every cell to the poor level, then light the rich one.
        for c in self.cells.iter_mut() {
            *c = (*c).min(self.max_resource);
        }
        let pos = if self.shift == 0.0 {
            0
        } else {
            ((self.t as f64 * self.shift) as usize) % n
        };
        // The rich cell is the maximum; the rest stay where they are.
        // `max_resource` is the rich value for this field.
        self.cells[pos] = self.max_resource;
    }

    /// A field that rises linearly from `low` at the left edge to `high` at the
    /// right edge.
    ///
    /// This is the field the `remember` experiment needs: a gradient has a single
    /// best cell, so an organism that finds the best and stops will end up at the
    /// right edge. An alternating field has twenty equally best cells, so "the
    /// best" is not a single place.
    pub fn gradient(cells: usize, low: f64, high: f64, regrow: f64) -> Option<Self> {
        let mut f = Self::new(cells, high, regrow)?;
        if cells == 1 {
            f.cells[0] = high;
            return Some(f);
        }
        let span = high - low;
        for i in 0..cells {
            let t = i as f64 / (cells - 1) as f64;
            f.cells[i] = low + span * t;
        }
        Some(f)
    }

    pub fn cells(&self) -> usize {
        self.cells.len()
    }

    /// The resource in `cell`. A cell outside the field holds nothing, so the
    /// answer is `0.0`, not a panic.
    ///
    /// It used to be `unwrap_or(0.0)`, which is the same number for a field of
    /// resources -- but `0.0` is also a real level, so a sighted organism at the
    /// edge saw "outside" as an empty cell and stepped out of the field. The
    /// caller that needs "no cell there" asks `cell < cells()` instead.
    pub fn level(&self, cell: usize) -> f64 {
        self.cells.get(cell).copied().unwrap_or(0.0)
    }

    /// True if `cell` is inside the field.
    pub fn inside(&self, cell: usize) -> bool {
        cell < self.cells.len()
    }

    /// Takes up to `amount` from a cell and returns what was actually taken.
    pub fn take(&mut self, cell: usize, amount: f64) -> f64 {
        if cell >= self.cells.len() || amount <= 0.0 {
            return 0.0;
        }
        let taken = self.cells[cell].min(amount);
        self.cells[cell] -= taken;
        taken
    }

    /// Regrows every cell toward the maximum.
    pub fn regrow_all(&mut self) {
        for c in self.cells.iter_mut() {
            *c += (self.max_resource - *c) * self.regrow;
        }
        if self.shift > 0.0 {
            self.t += 1;
            self.apply_shift();
        }
    }

    /// The richer of the two neighbours of `cell`, or `None` at the ends.
    pub fn richer_neighbour(&self, cell: usize) -> Option<usize> {
        let left = cell.checked_sub(1);
        let right = if cell + 1 < self.cells.len() {
            Some(cell + 1)
        } else {
            None
        };
        match (left, right) {
            (None, None) => None,
            (Some(l), None) => Some(l),
            (None, Some(r)) => Some(r),
            (Some(l), Some(r)) => {
                // A tie is not a choice: `None` says "neither side is richer".
                // Returning the left cell on a tie makes a walker drift left in a
                // uniform field, which is not what "toward the richer cell" means.
                if self.cells[l] == self.cells[r] {
                    None
                } else if self.cells[l] > self.cells[r] {
                    Some(l)
                } else {
                    Some(r)
                }
            }
        }
    }
}

/// What the organism does when it can act.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    /// Stay in the cell.
    Stay,
    /// Move one cell left.
    Left,
    /// Move one cell right.
    Right,
}

/// An organism that lives in a field and can act.
#[derive(Debug, Clone, Copy)]
pub struct Walker {
    pub organism: Organism,
    pub cell: usize,
    /// Energy spent on a move.
    pub move_cost: f64,
}

impl Walker {
    pub fn new(organism: Organism, cell: usize, move_cost: f64) -> Option<Self> {
        if !move_cost.is_finite() || move_cost < 0.0 {
            return None;
        }
        Some(Self {
            organism,
            cell,
            move_cost,
        })
    }

    /// Chooses an action. The rule is fixed: move toward the richer neighbour if it
    /// is richer than the current cell, otherwise stay.
    pub fn choose(&self, field: &Field) -> Action {
        let here = field.level(self.cell);
        match field.richer_neighbour(self.cell) {
            Some(n) if field.level(n) > here => {
                if n < self.cell {
                    Action::Left
                } else {
                    Action::Right
                }
            }
            _ => Action::Stay,
        }
    }

    /// One step: act, pay for the move, take the resource, then live.
    ///
    /// Returns `true` if the organism is still alive.
    ///
    /// ## The order matters
    ///
    /// 1. The action is applied and **paid for** by `Organism::spend`. If the
    ///    organism cannot afford the move, it stays where it is and pays nothing.
    /// 2. The resource is taken from the cell the organism now occupies.
    /// 3. The organism lives one step with what was taken.
    /// 4. The field regrows.
    ///
    /// The earlier version of this function had a `pay_move` that did nothing: the
    /// move cost was never applied, so moving was free. That is fixed here.
    pub fn step(&mut self, field: &mut Field, world: &World, action: Action) -> bool {
        if !self.organism.is_alive() {
            return false;
        }

        // 1. Apply the action, paying for it if it is a move.
        match action {
            Action::Stay => {}
            Action::Left => {
                if self.cell > 0 && self.organism.spend(self.move_cost) {
                    self.cell -= 1;
                }
            }
            Action::Right => {
                if self.cell + 1 < field.cells() && self.organism.spend(self.move_cost) {
                    self.cell += 1;
                }
            }
        }

        // 2. Take the resource from the cell the organism occupies.
        let taken = field.take(self.cell, world.income);

        // 3. Live one step with what was taken.
        let alive = self.organism.step(world, taken);

        // 4. The field regrows.
        field.regrow_all();

        alive
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn field_rejects_invalid() {
        assert!(Field::new(0, 1.0, 0.1).is_none());
        assert!(Field::new(10, 0.0, 0.1).is_none());
        assert!(Field::new(10, 1.0, 2.0).is_none());
        assert!(Field::new(10, 1.0, 0.1).is_some());
    }

    #[test]
    fn alternating_field_has_rich_and_poor() {
        let f = Field::alternating(10, 1.0, 0.1, 0.1).unwrap();
        assert!((f.level(0) - 1.0).abs() < 1e-12);
        assert!((f.level(1) - 0.1).abs() < 1e-12);
    }

    #[test]
    fn take_reduces_the_cell() {
        let mut f = Field::new(5, 1.0, 0.0).unwrap();
        let taken = f.take(0, 0.3);
        assert!((taken - 0.3).abs() < 1e-12);
        assert!((f.level(0) - 0.7).abs() < 1e-12);
    }

    #[test]
    fn take_is_limited_by_what_is_there() {
        let mut f = Field::new(5, 1.0, 0.0).unwrap();
        f.take(0, 0.9);
        let taken = f.take(0, 1.0);
        assert!((taken - 0.1).abs() < 1e-12);
    }

    #[test]
    fn regrow_moves_toward_max() {
        let mut f = Field::new(5, 1.0, 0.5).unwrap();
        f.take(0, 1.0);
        assert!((f.level(0) - 0.0).abs() < 1e-12);
        f.regrow_all();
        assert!((f.level(0) - 0.5).abs() < 1e-12);
    }

    #[test]
    fn any_take_opens_a_hole_and_the_hole_is_a_gradient() {
        // The field regrows toward `max_resource`, not toward the cell's own value,
        // so a cell that loses anything regrows to `max_resource` and every cell
        // that lost nothing stays at `max_resource`. After one step the field is
        // uniform again and the hole is gone.
        //
        // This is the fact that makes a "uniform" field non-uniform the moment
        // anybody eats: the eater's own cell falls below its neighbours, and a
        // sighted organism sees its neighbours as richer and steps away. The
        // medium produces a gradient out of any take, whether or not one was put
        // there.
        let mut f = Field::new(5, 2.0, 0.8).unwrap();
        f.take(2, 0.8);
        assert!((f.level(2) - 1.2).abs() < 1e-12);
        f.regrow_all();
        // 1.2 + (2.0 - 1.2) * 0.8 = 1.84: one step closes 80% of the gap.
        assert!(
            (f.level(2) - 1.84).abs() < 1e-12,
            "one step closes 80% of the hole, got {}",
            f.level(2)
        );
        // The gap shrinks by (1 - regrow) per step: 0.8 * 0.2^3 = 0.0064.
        f.regrow_all();
        f.regrow_all();
        assert!(
            (f.level(2) - 1.9936).abs() < 1e-12,
            "three steps leave 0.2^3 of the hole, got {}",
            f.level(2)
        );
        // The neighbours never moved: they were already at the maximum.
        assert!((f.level(1) - 2.0).abs() < 1e-12);
        assert!((f.level(3) - 2.0).abs() < 1e-12);
    }

    #[test]
    fn a_tie_between_neighbours_is_not_a_choice() {
        // A uniform field has no richer side. Returning the left cell on a tie
        // would make every walker drift left, which is not "toward the richer".
        let f = Field::new(10, 1.0, 0.0).unwrap();
        assert_eq!(f.richer_neighbour(5), None);
        let o = Organism::healthy(5.0).unwrap();
        let w = Walker::new(o, 5, 0.1).unwrap();
        assert_eq!(w.choose(&f), Action::Stay);
    }

    #[test]
    fn richer_neighbour_finds_the_rich_side() {
        let f = Field::alternating(10, 1.0, 0.1, 0.1).unwrap();
        // Cell 1 is poor; its neighbours are 0 (rich) and 2 (rich) and equally
        // rich, so neither is richer: a tie is not a choice.
        assert_eq!(f.richer_neighbour(1), None);
        // Cell 0 has only the right neighbour.
        assert_eq!(f.richer_neighbour(0), Some(1));
        // Cell 9 has only the left neighbour.
        assert_eq!(f.richer_neighbour(9), Some(8));
    }

    #[test]
    fn walker_moves_toward_the_richer_cell() {
        let f = Field::alternating(10, 1.0, 0.1, 0.1).unwrap();
        let o = Organism::healthy(5.0).unwrap();
        let w = Walker::new(o, 1, 0.1).unwrap();
        // Cell 1 is poor; both neighbours are rich and equally rich. A tie is
        // not a choice, so the walker stays: there is nothing to prefer.
        assert_eq!(w.choose(&f), Action::Stay);
    }

    #[test]
    fn walker_stays_when_already_richest() {
        let f = Field::alternating(10, 1.0, 0.1, 0.1).unwrap();
        let o = Organism::healthy(5.0).unwrap();
        let w = Walker::new(o, 0, 0.1).unwrap();
        // Cell 0 is rich; cell 1 is poor, so there is no reason to move.
        assert_eq!(w.choose(&f), Action::Stay);
    }
}
