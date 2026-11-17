//! A form with parts: geometry, and the economy that can make shape matter.
//!
//! `docs/DESIGN-structures.md` sets out why nothing in this project could be selected for its
//! **shape**: a form was a point on a line, and its income and upkeep both scaled with one
//! unit, so size and shape were economically neutral. This module adds the missing half -
//! a form made of cells with a boundary - and the arithmetic that makes shape matter.
//!
//! It is deliberately **not** wired into `Life`. Every recorded run depends on `Life` and on
//! `hash_golden`; new geometry must be able to arrive without moving a single bit of them.
//!
//! The economy, from the design:
//!
//! ```text
//! income    sigma * p        only the boundary touches the medium
//! upkeep    mu * n           every cell costs
//! transport kappa * n^2 / p  the interior is further from the boundary
//! ```
//!
//! A form survives while `sigma*p >= mu*n + kappa*n^2/p`, i.e. while
//! `x = n/p <= x* = (sqrt(mu^2 + 4*kappa*sigma) - mu) / (2*kappa)`.

use std::collections::BTreeSet;

/// A connected set of cells on the integer lattice.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Form {
    cells: BTreeSet<(i32, i32)>,
}

impl Form {
    fn from_cells(cells: impl IntoIterator<Item = (i32, i32)>) -> Self {
        Self {
            cells: cells.into_iter().collect(),
        }
    }

    /// A solid rectangle of `w` by `h` cells.
    pub fn rectangle(w: u32, h: u32) -> Self {
        let mut cells = Vec::new();
        for x in 0..w as i32 {
            for y in 0..h as i32 {
                cells.push((x, y));
            }
        }
        Self::from_cells(cells)
    }

    /// A square of side `side`.
    pub fn square(side: u32) -> Self {
        Self::rectangle(side, side)
    }

    /// A one-cell-wide strip of `len` cells.
    pub fn strip(len: u32) -> Self {
        Self::rectangle(len, 1)
    }

    /// A hollow ring: the border of a square, with the inside empty.
    ///
    /// `side` must be at least three, otherwise the ring is a solid square.
    pub fn ring(side: u32) -> Self {
        let s = side as i32;
        let mut cells = Vec::new();
        for x in 0..s {
            for y in 0..s {
                if x == 0 || y == 0 || x == s - 1 || y == s - 1 {
                    cells.push((x, y));
                }
            }
        }
        Self::from_cells(cells)
    }

    /// An L made of two arms of length `arm`, sharing the corner cell.
    pub fn l_shape(arm: u32) -> Self {
        let a = arm as i32;
        let mut cells = Vec::new();
        for x in 0..a {
            cells.push((x, 0));
        }
        for y in 1..a {
            cells.push((0, y));
        }
        Self::from_cells(cells)
    }

    pub fn cells(&self) -> usize {
        self.cells.len()
    }

    /// Boundary edges: sides of cells whose neighbour in that direction is empty.
    pub fn perimeter(&self) -> usize {
        let mut p = 0usize;
        for &(x, y) in &self.cells {
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                if !self.cells.contains(&(x + dx, y + dy)) {
                    p += 1;
                }
            }
        }
        p
    }

    /// Cells per unit of boundary. This is the quantity the economy limits.
    pub fn x(&self) -> f64 {
        let p = self.perimeter();
        if p == 0 {
            0.0
        } else {
            self.cells() as f64 / p as f64
        }
    }

    /// Whether a cell belongs to the form.
    pub fn has(&self, x: i32, y: i32) -> bool {
        self.cells.contains(&(x, y))
    }

    /// Whether the form is one connected piece. Required before any mutation: a form
    /// that splits is not a structure that grew, it is two structures that were never.
    pub fn is_connected(&self) -> bool {
        if self.cells.is_empty() {
            return false;
        }
        let mut seen: BTreeSet<(i32, i32)> = BTreeSet::new();
        let mut stack: Vec<(i32, i32)> = vec![*self.cells.iter().next().expect("non-empty")];
        while let Some((x, y)) = stack.pop() {
            if !self.cells.contains(&(x, y)) || seen.contains(&(x, y)) {
                continue;
            }
            seen.insert((x, y));
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                stack.push((x + dx, y + dy));
            }
        }
        seen.len() == self.cells.len()
    }

    /// Whether a cell touches the form from outside.
    pub fn is_adjacent(&self, x: i32, y: i32) -> bool {
        if self.has(x, y) {
            return false;
        }
        [(1, 0), (-1, 0), (0, 1), (0, -1)]
            .iter()
            .any(|(dx, dy)| self.has(x + dx, y + dy))
    }

    /// Adds one cell. Refused unless the cell touches the form and is not already in it,
    /// so growth stays connected by construction.
    pub fn grow(&self, x: i32, y: i32) -> Option<Self> {
        if !self.is_adjacent(x, y) {
            return None;
        }
        let mut out = self.clone();
        out.cells.insert((x, y));
        Some(out)
    }

    /// Removes one cell. Refused unless the cell is in the form, at least one cell stays,
    /// and what stays is still one piece.
    pub fn shrink(&self, x: i32, y: i32) -> Option<Self> {
        if !self.has(x, y) || self.cells.len() < 2 {
            return None;
        }
        let mut out = self.clone();
        out.cells.remove(&(x, y));
        if out.is_connected() {
            Some(out)
        } else {
            None
        }
    }

    /// All cells that could be grown into: empty and adjacent.
    pub fn growth_sites(&self) -> Vec<(i32, i32)> {
        let mut out = BTreeSet::new();
        for &(x, y) in &self.cells {
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                if self.is_adjacent(x + dx, y + dy) {
                    out.insert((x + dx, y + dy));
                }
            }
        }
        out.into_iter().collect()
    }

    /// One mutation: with probability `p_grow` add a random growth site, otherwise try to
    /// remove a random cell. Both operations are refused rather than forced, so a
    /// mutation can leave the form unchanged - which is honest, and is what a real
    /// mutation rate does at the boundary of a legal shape.
    pub fn mutate(&self, rng: &mut crate::Rng, p_grow: f64) -> Option<Self> {
        if rng.uniform() < p_grow {
            let sites = self.growth_sites();
            if sites.is_empty() {
                return None;
            }
            let i = (rng.next_u64() % sites.len() as u64) as usize;
            let (x, y) = sites[i];
            self.grow(x, y)
        } else {
            let cells: Vec<(i32, i32)> = self.cells.iter().copied().collect();
            if cells.is_empty() {
                return None;
            }
            let i = (rng.next_u64() % cells.len() as u64) as usize;
            let (x, y) = cells[i];
            self.shrink(x, y)
        }
    }

    /// Highest and lowest cell coordinates, for placement on a field.
    pub fn extent(&self) -> ((i32, i32), (i32, i32)) {
        let mut lo = (i32::MAX, i32::MAX);
        let mut hi = (i32::MIN, i32::MIN);
        for &(x, y) in &self.cells {
            lo = (lo.0.min(x), lo.1.min(y));
            hi = (hi.0.max(x), hi.1.max(y));
        }
        (lo, hi)
    }
}

/// The prices that decide whether a shape can pay for itself.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ShapeEconomy {
    /// Income per boundary edge.
    pub sigma: f64,
    /// Upkeep per cell.
    pub mu: f64,
    /// Transport cost per cell per unit of mean depth.
    pub kappa: f64,
}

impl ShapeEconomy {
    pub fn new(sigma: f64, mu: f64, kappa: f64) -> Option<Self> {
        if !(sigma.is_finite() && mu.is_finite() && kappa.is_finite()) {
            return None;
        }
        if sigma <= 0.0 || mu < 0.0 || kappa < 0.0 {
            return None;
        }
        Some(Self { sigma, mu, kappa })
    }

    /// The largest cells-per-boundary a form may have and still pay for itself.
    ///
    /// The positive root of `kappa*x^2 + mu*x - sigma = 0`.
    pub fn x_limit(&self) -> f64 {
        if self.kappa == 0.0 {
            return self.sigma / self.mu.max(f64::MIN_POSITIVE);
        }
        let disc = self.mu * self.mu + 4.0 * self.kappa * self.sigma;
        (disc.sqrt() - self.mu) / (2.0 * self.kappa)
    }

    /// The largest sustainable square: `x = side/4`, so `side = 4*x*`.
    pub fn max_square_side(&self) -> f64 {
        4.0 * self.x_limit()
    }

    pub fn income(&self, form: &Form) -> f64 {
        self.sigma * form.perimeter() as f64
    }

    pub fn upkeep(&self, form: &Form) -> f64 {
        let n = form.cells() as f64;
        let p = form.perimeter().max(1) as f64;
        self.mu * n + self.kappa * n * n / p
    }

    /// Whether the form pays for itself: `income >= upkeep`.
    pub fn survives(&self, form: &Form) -> bool {
        self.income(form) >= self.upkeep(form)
    }

    /// Signed margin, for probes: positive means the form has room.
    pub fn margin(&self, form: &Form) -> f64 {
        self.income(form) - self.upkeep(form)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn economy() -> ShapeEconomy {
        ShapeEconomy::new(2.0, 1.0, 0.1).expect("valid economy")
    }

    #[test]
    fn geometry_is_counted_from_the_cells_not_given() {
        assert_eq!(Form::square(1).cells(), 1);
        assert_eq!(Form::square(1).perimeter(), 4);
        assert_eq!(Form::square(4).cells(), 16);
        assert_eq!(Form::square(4).perimeter(), 16);
        assert_eq!(Form::strip(8).cells(), 8);
        assert_eq!(Form::strip(8).perimeter(), 18);
    }

    #[test]
    fn a_square_of_side_s_has_x_equal_to_s_over_four() {
        for side in [2u32, 4, 6, 9] {
            let f = Form::square(side);
            assert!((f.x() - side as f64 / 4.0).abs() < 1e-12, "side {side} gave {}", f.x());
        }
    }

    #[test]
    fn the_limit_comes_from_the_economy_not_from_a_table() {
        let e = economy();
        assert!((e.x_limit() - 1.70828).abs() < 1e-4, "x* = {}", e.x_limit());
        assert!((e.max_square_side() - 6.8331).abs() < 1e-3);
        // six cells a side is inside the limit, seven is outside
        assert!(e.survives(&Form::square(6)));
        assert!(!e.survives(&Form::square(7)));
        // and the margin crosses zero exactly at the limit, not at a round number
        let six = e.margin(&Form::square(6));
        let seven = e.margin(&Form::square(7));
        assert!(six > 0.0 && seven < 0.0);
    }

    #[test]
    fn a_hollow_form_is_cheaper_per_cell_than_a_solid_one_of_the_same_extent() {
        // This test exists because the first version asserted the opposite, and the
        // arithmetic refused it. With income proportional to the **boundary**, a cavity
        // ADDS boundary without adding cells, so a hollow form is cheaper per cell, not
        // dearer - and it is the compact form that runs into the size limit.
        let e = economy();
        let ring = Form::ring(8);
        let solid = Form::square(8);
        assert!(ring.x() < solid.x(), "ring {} solid {}", ring.x(), solid.x());
        assert!(e.survives(&ring), "x = {} should be inside the limit", ring.x());
        assert!(!e.survives(&solid), "x = {} should be outside the limit", solid.x());
        assert!(e.margin(&ring) > e.margin(&solid));
    }

    #[test]
    fn without_transport_cost_there_is_no_size_limit() {
        let free = ShapeEconomy::new(2.0, 1.0, 0.0).expect("valid economy");
        assert!((free.x_limit() - 2.0).abs() < 1e-12);
        assert!((free.max_square_side() - 8.0).abs() < 1e-12);
        // a form larger than the old limit now pays, which is the prediction the design
        // says to test
        assert!(free.survives(&Form::square(8)));
        assert!(!free.survives(&Form::square(9)));
    }

    #[test]
    fn a_long_strip_approaches_half_a_cell_per_edge() {
        let strip = Form::strip(40);
        assert!((strip.x() - 40.0 / 82.0).abs() < 1e-12);
        assert!(strip.x() > 0.48);
    }

    #[test]
    fn growth_is_refused_unless_the_cell_touches_the_form() {
        let f = Form::square(2);
        assert!(f.grow(2, 0).is_some(), "a cell beside the form should grow");
        assert!(f.grow(5, 5).is_none(), "a distant cell must be refused");
        assert!(f.grow(0, 0).is_none(), "a cell already in the form must be refused");
        let grown = f.grow(2, 0).expect("grown");
        assert_eq!(grown.cells(), 5);
        assert!(grown.is_connected());
    }

    #[test]
    fn a_removal_that_splits_the_form_is_refused() {
        // A dumbbell: two squares joined by one cell. Removing the bridge would leave two
        // pieces, and the mutation must be refused rather than produce a broken form.
        let mut cells = Vec::new();
        for x in 0..2 {
            for y in 0..2 {
                cells.push((x, y));
            }
        }
        cells.push((2, 0));
        for x in 3..5 {
            for y in 0..2 {
                cells.push((x, y));
            }
        }
        let barbell = Form::from_cells(cells);
        assert!(barbell.is_connected());
        assert!(
            barbell.shrink(2, 0).is_none(),
            "removing the bridge must be refused"
        );
        assert!(barbell.shrink(0, 0).is_some(), "removing a leaf must be allowed");
    }

    #[test]
    fn a_form_cannot_be_shrunk_out_of_existence() {
        let one = Form::square(1);
        assert!(one.shrink(0, 0).is_none());
    }

    #[test]
    fn mutation_both_grows_and_shrinks_and_never_breaks_the_form() {
        // The first version of this test asserted that the form's minimum size fell below
        // its start. It failed, and the failure was informative: growth and shrinkage both
        // happen every few steps, but growth wins on average, because a form has many more
        // legal additions than legal removals. So the test counts events, which is the
        // property under study, instead of watching a drift it cannot control.
        let mut rng = crate::Rng::new(7);
        let mut f = Form::square(3);
        let mut grew = 0;
        let mut shrank = 0;
        for _ in 0..60 {
            if let Some(next) = f.mutate(&mut rng, 0.55) {
                assert!(next.is_connected(), "a mutation broke the form into pieces");
                assert!(next.cells() >= 1);
                if next.cells() > f.cells() {
                    grew += 1;
                } else if next.cells() < f.cells() {
                    shrank += 1;
                }
                f = next;
            }
        }
        assert!(grew > 5, "growth should happen often: {grew}");
        assert!(shrank > 3, "shrinkage should happen too: {shrank}");
        assert!(grew > shrank, "growth sites outnumber legal removals: {grew} vs {shrank}");
    }

    #[test]
    fn neutral_mutation_is_not_neutral_it_ratchets_upwards() {
        // A form at a fixed mutation rate grows on average, because the number of cells
        // that can be added exceeds the number that can be removed without splitting it.
        // This is why the size of a form cannot be regulated by mutation alone: the
        // economy has to kill forms, not the mutation rate.
        let mut rng = crate::Rng::new(11);
        let mut f = Form::square(2);
        let start = f.cells();
        for _ in 0..200 {
            if let Some(next) = f.mutate(&mut rng, 0.5) {
                f = next;
            }
        }
        assert!(
            f.cells() > start,
            "expected drift upwards from {start}, got {}",
            f.cells()
        );
    }

    #[test]
    fn an_impossible_economy_is_refused() {
        assert!(ShapeEconomy::new(0.0, 1.0, 0.1).is_none());
        assert!(ShapeEconomy::new(2.0, -1.0, 0.1).is_none());
        assert!(ShapeEconomy::new(f64::NAN, 1.0, 0.1).is_none());
    }
}
