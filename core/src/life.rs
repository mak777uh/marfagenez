//! # The life cycle
//!
//! `organism.rs`, `field.rs` and `memory.rs` are parts. This module puts them
//! together into a **cycle**: a population of organisms in a field, running in time.
//!
//! ## Why this module exists
//!
//! The project has two worlds that do not touch:
//!
//! | old world | new world |
//! |---|---|
//! | `Child`, `Cycle`, `Room` | `Organism`, `Field`, `Memory` |
//! | a point in a room | an organism with energy |
//! | never dies | **can die** |
//!
//! Keeping both is a mistake: it is two models in one repository, and a reader cannot
//! tell which one the results are about. This module is the **one** cycle for the new
//! world. The old world stays as a **control**: it is what the project had before it
//! had organisms, and its laws are still measured.
//!
//! ## What the cycle does
//!
//! Each step, for every living organism:
//!
//! 1. it sees its cell;
//! 2. it remembers;
//! 3. it acts (moves, paying for the move);
//! 4. it takes the resource;
//! 5. it lives (maintenance, damage, repair);
//! 6. it may die.
//!
//! Then the field regrows.
//!
//! ## What it does not do
//!
//! No reproduction, no inheritance, no interaction between organisms. The plan adds
//! those one at a time.

#![forbid(unsafe_code)]

use crate::field::Field;
use crate::memory::Remembering;
use crate::organism::{Organism, World};

/// How an organism decides where to go.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Policy {
    /// Stay where it is.
    Stay,
    /// Move at random.
    Random,
    /// Remember the richest cell seen and return to it, exploring when the memory is
    /// empty.
    ///
    /// **This is a one-shot choice, not a memory.** The memory is updated only when
    /// the organism is NOT standing on the remembered cell, so once it arrives the
    /// memory never changes again. See `docs/FINDING-remember-is-choice.md`.
    Remember,
    /// Keep the best cell seen so far and move toward it, **updating the memory on
    /// every step** — including while standing on it.
    ///
    /// The difference from [`Policy::Remember`] is exactly the update rule: this one
    /// can change its mind. If a richer cell appears, the organism leaves.
    Memory,
    /// Look at the two neighbours and step toward the richer one.
    ///
    /// This is the first policy with **feedback from the world**: every other policy
    /// sees only its own cell, so it can never learn that a better cell exists
    /// nearby. See `docs/FINDING-memory-weak.md`.
    ///
    /// Ties go to `0` (stay), so in a uniform field a sighted organism does not
    /// move — there is nothing to prefer.
    Sighted,
}

/// A reading taken from outside the cycle.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Census {
    pub step: usize,
    pub alive: usize,
    pub total: usize,
    pub mean_energy: f64,
    pub mean_damage: f64,
    pub moves: u64,
}

impl Census {
    /// The fraction still alive.
    pub fn survival(&self) -> f64 {
        if self.total == 0 {
            0.0
        } else {
            self.alive as f64 / self.total as f64
        }
    }
}

/// A population of organisms in a field.
#[derive(Debug)]
pub struct Life {
    world: World,
    field: Field,
    organisms: Vec<Option<Remembering>>,
    policy: Policy,
    rng: crate::Rng,
    step: usize,
    moves: u64,
    memory_life: usize,
    seed: u64,
    /// If true, the field is regrown **before** the organisms act, so that a
    /// cell eaten last step has recovered by the time anybody looks at it.
    ///
    /// This is the difference between two mediums:
    ///
    /// * `feed = false` (default): take, then regrow. A cell that was eaten is
    ///   still low when the next organism looks at it, so the *next* organism
    ///   sees a hole and treats it as a reason to move.
    /// * `feed = true`: regrow, then take. Every organism sees the field at its
    ///   full value, so eating does not create a reason to move. This is the
    ///   model in which `c' = (c - t) + (M - (c - t))*r` describes the cell.
    pub feed: bool,
}

impl Life {
    /// The world the organisms live in, for the recorder to write down.
    ///
    /// The recorder needs it because a run is only reproducible if the header
    /// says what the organisms could see. Two traces with the same policy and
    /// seed but different read budgets are different experiments.
    pub fn world(&self) -> &World {
        &self.world
    }

    /// Builds a cycle. Returns `None` for an empty population or a field with no cells.
    pub fn new(
        world: World,
        field: Field,
        organisms: Vec<Remembering>,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        if organisms.is_empty() || field.cells() == 0 {
            return None;
        }
        Some(Self {
            world,
            field,
            organisms: organisms.into_iter().map(Some).collect(),
            policy,
            rng: crate::Rng::new(seed),
            step: 0,
            moves: 0,
            memory_life,
            seed,
            feed: false,
        })
    }

    /// Builds a population of `n` healthy organisms placed round-robin over the
    /// field: organism `i` goes to cell `i % cells`, so with `n = k * cells`
    /// every cell carries exactly `k` of them.
    ///
    /// This exists to test the per-cell law `c* = M - k*t/r`. With `spawn` the
    /// cells get a random multinomial load, so a run meant to be "one organism
    /// per cell" actually has cells with two and three on them, and the law
    /// cannot be checked against it.
    /// Puts organism `i` on `cells[i]`.
    ///
    /// The command line needs this because neither `spawn` (random) nor
    /// `spawn_even` (cell `i % cells`) can ask a question about a chosen cell.
    pub fn spawn_at(
        world: World,
        field: Field,
        cells: &[usize],
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        if cells.is_empty() {
            return None;
        }
        let n_cells = field.cells();
        let mut pop = Vec::with_capacity(cells.len());
        for &cell in cells {
            if cell >= n_cells {
                return None;
            }
            let o = Organism::healthy(energy)?;
            let mut r = Remembering::new(o, cell, 0.0, move_cost, memory_life)?;
            r.memory.best_level = 0.0;
            pop.push(r);
        }
        Self::new(world, field, pop, policy, seed, memory_life)
    }

    pub fn spawn_even(
        world: World,
        field: Field,
        n: usize,
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        if n == 0 {
            return None;
        }
        let cells = field.cells();
        if cells == 0 {
            return None;
        }
        let mut pop = Vec::with_capacity(n);
        for i in 0..n {
            let cell = i % cells;
            let o = Organism::healthy(energy)?;
            let mut r = Remembering::new(o, cell, 0.0, move_cost, memory_life)?;
            r.memory.best_level = 0.0;
            pop.push(r);
        }
        Self::new(world, field, pop, policy, seed, memory_life)
    }

    /// Builds a population of `n` healthy organisms spread over the field.
    pub fn spawn(
        world: World,
        field: Field,
        n: usize,
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        if n == 0 {
            return None;
        }
        let cells = field.cells();
        let mut rng = crate::Rng::new(seed ^ 0x5DEE_CE66_D1CE_4E5B);
        let mut pop = Vec::with_capacity(n);
        for _ in 0..n {
            let cell = (rng.uniform() * cells as f64) as usize;
            let cell = cell.min(cells - 1);
            let o = Organism::healthy(energy)?;
            // Memory starts empty: the organism knows nothing about the field.
            let mut r = Remembering::new(o, cell, 0.0, move_cost, memory_life)?;
            r.memory.best_level = 0.0;
            pop.push(r);
        }
        Self::new(world, field, pop, policy, seed, memory_life)
    }

    pub fn step(&self) -> usize {
        self.step
    }

    pub fn field(&self) -> &Field {
        &self.field
    }

    pub fn policy(&self) -> Policy {
        self.policy
    }

    /// Puts organism `i` on cell `cell`.
    ///
    /// This exists so a test can build a situation the spawners cannot express:
    /// `spawn_even` fills cells in order and `spawn` draws at random, so neither
    /// can place one organism in the middle of a hand-built field. Returns
    /// `false` if there is no such organism or the cell is outside the field.
    ///
    /// It does not touch the memory: what the organism remembers stays what it
    /// remembered, which is the point -- a test that moves an organism wants to
    /// see what it decides from where it now stands.
    pub fn move_to(&mut self, i: usize, cell: usize) -> bool {
        if cell >= self.field.cells() {
            return false;
        }
        match self.organisms.get_mut(i) {
            Some(Some(r)) => {
                r.cell = cell;
                true
            }
            _ => false,
        }
    }

    /// Advances every living organism by one step.
    pub fn advance(&mut self) -> Option<()> {
        let cells = self.field.cells();
        if self.feed {
            self.field.regrow_all();
        }
        for slot in self.organisms.iter_mut() {
            let Some(r) = slot.as_mut() else { continue };
            if !r.organism.is_alive() {
                continue;
            }

            // 1. See the current cell. Reading is free only while the read
            //    budget lasts; `observe` never removes anything, which is the
            //    whole point of EXP-30. See
            //    `docs/FINDING-reading-is-not-eating.md`.
            //    Reading your own cell is a read too. With no budget the
            //    organism knows nothing, not even where it stands, and
            //    `best_level <= 0.0` already means "nothing seen".
            //    A policy that never looks (`Stay`, `Random`) must not read at
            //    all: otherwise the read budget changes its trace, and a control
            //    that is supposed to be silent would fire. See EXP-30.
            let looks = matches!(
                self.policy,
                Policy::Remember | Policy::Memory | Policy::Sighted
            );
            let mut reads_left = if looks { self.world.read_budget } else { 0 };
            let here = if reads_left > 0 {
                reads_left -= 1;
                self.field.observe(r.cell)
            } else {
                0.0
            };

            // 2. Remember. Only a cell that is RICHER than the memory replaces it.
            // The current cell is observed first, but if it is the best so far the
            // memory points here -- and then the organism would never leave. So the
            // memory is updated only when the organism is NOT already standing on it.
            // The update rule is where `Remember` and `Memory` differ.
            //
            // `Remember` updates only when the organism is NOT on the remembered
            // cell, so once it arrives the memory is frozen — a one-shot choice.
            //
            // `Memory` updates on every step, so a richer cell seen later replaces
            // the memory and the organism can change its mind. It must also be able
            // to DROP a memory: in a moving field the remembered cell goes poor, and
            // a memory that only ever rises pins the organism to a dead cell forever.
            // Measured before the fix: 8 organisms on a 40-cell moving field kept
            // memory cells 3, 4, 12, 1, 37, 22, 10, 6 for 50 steps while the rich
            // cell travelled; the field they stood on was 0.2 everywhere.
            let update_memory = match self.policy {
                Policy::Memory => true,
                _ => r.memory.best_cell != r.cell,
            };
            if update_memory {
                // `Memory` keeps the live level of the cell it stands on, so that
                // `direction()` can notice the remembered cell has gone poor.
                if self.policy == Policy::Memory && r.memory.best_cell == r.cell {
                    r.memory.best_level = here;
                    r.memory.age = 0;
                } else {
                    r.memory.observe(r.cell, here);
                }
            }
            r.memory.decay(self.memory_life);

            // A memory of a cell that is no longer worth going to is dropped.
            // Otherwise `direction()` keeps walking toward a cell that has dried up.
            if self.policy == Policy::Memory
                && r.memory.best_cell != r.cell
                && r.memory.best_level <= here
            {
                r.memory.best_cell = r.cell;
                r.memory.best_level = here;
                r.memory.age = 0;
            }
            // The memory must be able to point AWAY from the current cell, or the
            // organism never moves. A memory that only records "the richest cell I
            // have stood on" is always the current cell the moment the organism
            // arrives, so `direction()` returns 0 forever. `Memory` therefore also
            // remembers the best cell it has SEEN anywhere -- the richer neighbour.
            // Measured before: 8 organisms, 40-cell moving field, 50 steps, memory
            // cells 3, 4, 12, 1, 37, 22, 10, 6 unchanged, direction 0 every step.
            if self.policy == Policy::Memory {
                // Each neighbour read costs one from the budget, exactly as in
                // the `sighted` branch. It used to call `Field::level`, which
                // is a plain array read and does not touch `read_budget`, so
                // `--policy memory --read-budget 0` still saw both neighbours
                // and walked around a uniform field. See
                // `docs/FINDING-memory-sees-for-free.md`.
                let mut left = f64::NEG_INFINITY;
                let mut right = f64::NEG_INFINITY;
                if r.cell > 0 && reads_left > 0 {
                    left = self.field.observe(r.cell - 1);
                    reads_left -= 1;
                }
                if self.field.inside(r.cell + 1) && reads_left > 0 {
                    right = self.field.observe(r.cell + 1);
                    reads_left -= 1;
                }
                let best = here.max(left).max(right);
                let target = if left >= right { r.cell.wrapping_sub(1) } else { r.cell + 1 };
                if best > here && best > r.memory.best_level {
                    r.memory.best_cell = target;
                    r.memory.best_level = best;
                    r.memory.age = 0;
                }
            }
            // Debug: DBG_MEMORY=1 prints the memory decision each step.
            if std::env::var("DBG_MEMORY").is_ok() && self.step < 4 {
                eprintln!(
                    "step {} org cell {} here {:.3} mem {} level {:.3} dir {}",
                    self.step,
                    r.cell,
                    here,
                    r.memory.best_cell,
                    r.memory.best_level,
                    r.direction()
                );
            }



            // 3. Act.
            let direction = match self.policy {
                Policy::Stay => 0,
                Policy::Random => {
                    let u = self.rng.uniform();
                    if u < 1.0 / 3.0 {
                        -1
                    } else if u < 2.0 / 3.0 {
                        0
                    } else {
                        1
                    }
                }
                Policy::Remember => {
                    // If the memory is empty (nothing seen yet), explore: move at
                    // random. A remembering organism that has seen nothing must look
                    // around, or it never finds anything to remember.
                    if r.memory.best_level <= 0.0 {
                        let u = self.rng.uniform();
                        if u < 0.5 { -1 } else { 1 }
                    } else {
                        r.direction()
                    }
                }
                Policy::Memory => {
                    // Same direction rule, but the memory keeps updating, so the
                    // organism can leave a cell that was once the best.
                    if r.memory.best_level <= 0.0 {
                        let u = self.rng.uniform();
                        if u < 0.5 { -1 } else { 1 }
                    } else {
                        r.direction()
                    }
                }
                Policy::Sighted => {
                    // Look at both neighbours and step toward the richer one.
                    // A tie goes to `0`: in a uniform field there is nothing to
                    // prefer, so a sighted organism stays put.
                    //
                    // "No neighbour" is `NEG_INFINITY`, not `0.0`: a level of
                    // `0.0` is a real, empty cell, and reading the outside as
                    // `0.0` made an organism at the edge see its own cell as the
                    // richest and step out of the field.
                    // Reading a neighbour costs one read from the budget. With
                    // `read_budget == 0` nothing is read and the organism cannot
                    // see, which is exactly the old behaviour (`level` was a
                    // read that did not subtract either -- the subtraction was in
                    // `take`, and `take` only ever touched the cell the organism
                    // ended up in).
                    let mut left = f64::NEG_INFINITY;
                    let mut right = f64::NEG_INFINITY;
                    if r.cell > 0 && reads_left > 0 {
                        left = self.field.observe(r.cell - 1);
                        reads_left -= 1;
                    }
                    if self.field.inside(r.cell + 1) && reads_left > 0 {
                        right = self.field.observe(r.cell + 1);
                        reads_left -= 1;
                    }
                    let best = here.max(left).max(right);
                    if best > here {
                        if left >= right { -1 } else { 1 }
                    } else {
                        0
                    }
                }
            };
            // Store the decision so a reading shows what the organism actually
            // did, not what it would do against the field after the step.
            r.last_direction = direction;
            r.last_cell = r.cell;
            let _reads_used = self.world.read_budget.saturating_sub(reads_left);

            if direction != 0 && r.organism.spend(r.move_cost) {
                let nc = r.cell as i64 + direction as i64;
                if nc >= 0 && (nc as usize) < cells {
                    r.cell = nc as usize;
                    self.moves += 1;
                }
            }

            // 4. Eat. Reading is separate: `read_budget > 0` lets the
            //    organism look at cells without emptying them, and what it
            //    reads is what it decides on. With `read_budget == 0` this is
            //    exactly the old `take`, so the trace must not change.
            let taken = self.field.take(r.cell, self.world.income);
            r.last_taken = taken;

            // 5. Live.
            r.organism.step(&self.world, taken);

            // 6. Death is handled inside `step`; nothing to do here.
        }

        // The field regrows once per step. In `feed` mode it already did.
        if !self.feed {
            self.field.regrow_all();
        }
        self.step += 1;
        Some(())
    }

    /// Runs `steps` steps and returns a census every `every` steps.
    pub fn run(&mut self, steps: usize, every: usize) -> Vec<Census> {
        let every = every.max(1);
        let mut out = Vec::new();
        for _ in 0..steps {
            if self.advance().is_none() {
                break;
            }
            if self.step % every == 0 {
                out.push(self.census());
            }
        }
        out
    }

    /// Takes a census from outside. The cycle does not use it.
    pub fn census(&self) -> Census {
        let total = self.organisms.len();
        let mut alive = 0;
        let mut sum_e = 0.0;
        let mut sum_d = 0.0;
        for slot in self.organisms.iter() {
            if let Some(r) = slot.as_ref() {
                if r.organism.is_alive() {
                    alive += 1;
                    sum_e += r.organism.energy();
                    sum_d += r.organism.damage();
                }
            }
        }
        Census {
            step: self.step,
            alive,
            total,
            mean_energy: if alive > 0 { sum_e / alive as f64 } else { 0.0 },
            mean_damage: if alive > 0 { sum_d / alive as f64 } else { 0.0 },
            moves: self.moves,
        }
    }

    /// The policy's name, for the trace.
    pub fn policy_name(&self) -> &'static str {
        match self.policy {
            Policy::Stay => "stay",
            Policy::Random => "random",
            Policy::Remember => "remember",
            Policy::Memory => "memory",
            Policy::Sighted => "sighted",
        }
    }

    /// The seed the cycle was built with.
    pub fn seed(&self) -> u64 {
        self.seed
    }

    /// A full sample of every organism: where it is, what it has, what it remembers.
    ///
    /// This is the **observation** the census cannot give. The census reduces the
    /// population to a mean; this keeps every organism separate.
    ///
    /// The reading is taken from outside and does not change the cycle.
    pub fn samples(&self) -> Vec<crate::trace::Sample> {
        let mut out = Vec::with_capacity(self.organisms.len());
        for (slot_id, slot) in self.organisms.iter().enumerate() {
            match slot.as_ref() {
                Some(r) => out.push(crate::trace::Sample {
                    slot: slot_id,
                    cell: r.cell,
                    energy: r.organism.energy(),
                    damage: r.organism.damage(),
                    alive: r.organism.is_alive(),
                    memory_cell: r.memory.best_cell,
                    memory_level: r.memory.best_level,
                    // The direction the organism chose on its last step. Reading
                    // `r.direction()` here would recompute it against the field
                    // AFTER the step, which is not the decision that was taken.
                    direction: r.last_direction,
                    taken: r.last_taken,
                    prev_cell: r.last_cell,
                }),
                None => out.push(crate::trace::Sample {
                    slot: slot_id,
                    cell: 0,
                    energy: 0.0,
                    damage: 0.0,
                    alive: false,
                    memory_cell: 0,
                    memory_level: 0.0,
                    direction: 0,
                    taken: 0.0,
                    prev_cell: 0,
                }),
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup(policy: Policy) -> Life {
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 0,
        };
        let field = Field::alternating(40, 2.0, 0.2, 0.8).unwrap();
        Life::spawn(world, field, 40, 5.0, 0.1, policy, 7, 300).unwrap()
    }

    /// Two organisms on one rich cell: does the cell feed both?
    ///
    /// This is the question EXP-76 could not ask, because neither spawner can
    /// place two organisms on the same cell on purpose: `spawn_even` fills cells
    /// in order and `spawn` draws at random. So the situation is built by hand
    /// with `move_to`.
    ///
    /// Arithmetic first. One organism on a rich cell (`M = 2.0`, `r = 0.8`)
    /// settles at `c* = 1.7` and takes `min(c*, income) = min(1.7, 1.2) = 1.2`
    /// against a cost of `0.6 + 0.02 * 1.5 = 0.63`, surplus `+0.57`.
    ///
    /// Two organisms: the first takes `1.2`, leaving `0.4`; the second takes
    /// `min(0.4, 1.2) = 0.4`. Total `1.6` out of the cell, and the cell regrows
    /// to `0.4 + (2.0 - 0.4) * 0.8 = 1.68` at the end of the step, so the next
    /// step starts higher and the pair settles at `c* = 1.6`, where the first
    /// takes `1.2` and the second takes `0.4`. The second's intake is `0.4`,
    /// which is BELOW the cost `0.63`: the second organism starves.
    ///
    /// So the arithmetic says a rich cell feeds exactly one, and the second one
    /// on it dies. The measurement should show alive = 1 after enough steps.
    ///
    /// What this would mean if it holds: `crowding = 1.00` is not a property of
    /// the movement rule (as EXP-76's prediction said) but a property of the
    /// feeding rule -- a cell feeds one organism because the second one's share
    /// falls under the cost of staying alive.
    #[test]
    fn a_rich_cell_feeds_one_organism_not_two() {
        let world = World {
            income: 1.2,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 3,
        };
        // A field of four rich cells: `Field::new` makes every cell equal to
        // `max_resource`, so there is no need for a setter.
        let field = Field::new(4, 2.0, 0.8).unwrap();
        // Two organisms, both starting on cell 2, a rich one.
        let mut life =
            Life::spawn(world, field, 2, 10.0, 0.0, Policy::Stay, 1, 300).unwrap();
        assert!(life.move_to(0, 2), "organism 0 should move to cell 2");
        assert!(life.move_to(1, 2), "organism 1 should move to cell 2");

        // Both start on the same cell: this is the situation being tested.
        assert_eq!(life.census().alive, 2);
        assert_eq!(life.census().total, 2);

        let censuses = life.run(4000, 400);
        let last = censuses.last().expect("some census");
        // The arithmetic says the second intake (0.4) is below the cost (0.63),
        // so exactly one survives.
        assert_eq!(
            last.alive, 1,
            "a rich cell should feed one organism, not two: alive = {} at step {}",
            last.alive, last.step
        );
    }

    // EXP-79: why does a sighted organism on a poor cell stand still when both
    // neighbours are richer?
    //
    // EXP-78 ran `--layout even` with 40 cells and n = 40 -- one organism per
    // cell -- on an alternating field, and every arm froze at occ = 1 1 1 ...
    // with `moving = 0`. With n = 80 the same field froze at occ = 2 1 2 1 ...
    // with 60 alive. The policy says a poor cell's organism must move: its
    // level is 1.35 and both neighbours are 2.15, so `best > here`.
    //
    // These four assertions separate the possible causes. They are the arms of
    // `checks/exp79_why_the_poor_cell_organism_stands_still.py`; the test name
    // is what that script greps for, so keep the `assert!` messages starting
    // with the arm letter.
    #[test]
    fn exp79_the_poor_cell_organism_decides_to_move() {
        // A. A free move must not be refused. `spend` is the gate in
        //    `Life::advance`: `if direction != 0 && r.organism.spend(cost)`.
        //    If `spend(0.0)` returned false, every `move_cost = 0` arm in the
        //    project would be a population that silently cannot move.
        let mut o = Organism::healthy(10.0).expect("healthy organism");
        let before = o.energy();
        let paid = o.spend(0.0);
        assert!(
            paid,
            "A_spend_zero_is_true: spend(0.0) returned false, so a free move is \
             refused and every move_cost = 0 arm measures the refusal, not the \
             policy"
        );
        assert_eq!(o.energy(), before, "A: spend(0.0) must not change energy");

        // B. And it must still refuse a move it cannot pay for.
        let mut poor = Organism::healthy(0.3).expect("healthy organism");
        let refused = poor.spend(0.5);
        assert!(
            !refused,
            "B_spend_more_than_there_is_is_false: spend(0.5) with 0.3 energy \
             returned true"
        );
        assert_eq!(poor.energy(), 0.3, "B: a refused spend must not change energy");

        // C. The decision itself. One organism on cell 1 of a four-cell
        //    alternating field: cell 1 is poor (1.6), cells 0 and 2 are rich
        //    (2.4). `Sighted` reads both neighbours and must step toward one.
        let world = World {
            income: 1.0,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.05,
            capacity: 10.0,
            read_budget: 3,
        };
        let field = Field::alternating(4, 2.4, 1.6, 0.8).expect("alternating field");
        let mut life =
            Life::spawn(world, field, 1, 10.0, 0.0, Policy::Sighted, 1, 100000)
                .expect("one organism");
        assert!(life.move_to(0, 1), "C: organism 0 should move to cell 1");
        assert_eq!(life.samples()[0].cell, 1, "C: starts on the poor cell");

        let samples = life.samples();
        let start = samples[0].cell;
        life.advance().expect("one step");
        let after_step = life.samples();
        let d = after_step[0].direction;
        assert_ne!(
            d, 0,
            "C_poor_cell_organism_moves: on a poor cell (1.35) with two rich \
             neighbours (2.15) the sighted policy chose direction 0. The \
             policy in life.rs is not 'step toward the richer neighbour'."
        );
        assert_ne!(
            after_step[0].cell, start,
            "C: the direction was {} but the cell did not change, so the move \
             was refused after the decision",
            d
        );

        // D. The charge is the parameter and nothing else. The same start with
        //    move_cost 0.05 must end 0.05 lower in energy than the free arm.
        //
        //    The first version of this arm used `capacity = 10` and started at
        //    10.0, so both arms ended at 10.0: `Organism::step` applies
        //    `energy.min(world.capacity)` at the end (organism.rs:184) and the
        //    cap erased the charge before it could be read. The difference was
        //    0 instead of 0.05 and the test failed for the right reason — the
        //    arm could not see what it claimed to measure. Raise the cap and
        //    start below it, so the cap cannot bind on either arm.
        let roomy = World {
            capacity: 100.0,
            ..world
        };
        let mut free_life =
            Life::spawn(roomy, Field::alternating(4, 2.4, 1.6, 0.8).expect("field"),
                        1, 10.0, 0.0, Policy::Sighted, 1, 100000)
                .expect("one organism");
        assert!(free_life.move_to(0, 1), "D: free organism 0 starts on cell 1");
        let mut paid_life =
            Life::spawn(roomy, Field::alternating(4, 2.4, 1.6, 0.8).expect("field"),
                        1, 10.0, 0.05, Policy::Sighted, 1, 100000)
                .expect("one organism");
        assert!(paid_life.move_to(0, 1), "D: paid organism 0 starts on cell 1");
        free_life.advance().expect("one step");
        paid_life.advance().expect("one step");
        let free_energy = free_life.samples()[0].energy;
        let paid_energy = paid_life.samples()[0].energy;
        assert!(
            free_energy < roomy.capacity,
            "D_cap_does_not_bind: the free arm ended at the cap {} — the arm \
             cannot see a charge it is not allowed to keep",
            roomy.capacity
        );
        assert!(
            (free_energy - paid_energy - 0.05).abs() < 1e-12,
            "D_move_cost_is_charged_exactly: free arm ended at {}, paid arm at \
             {}, difference {} instead of 0.05",
            free_energy,
            paid_energy,
            free_energy - paid_energy
        );
    }

    #[test]
    fn spawn_even_puts_organism_i_on_cell_i_mod_cells() {
        // The default layout is `even` (core/src/bin/trace.rs). If `spawn_even`
        // ever stops being `i % cells`, every crowding experiment silently
        // measures the spawner instead of the field — which is exactly what
        // EXP-87 did before the default was fixed (docs/FINDING-087).
        let world = World::default();
        let field = Field::new(4, 2.0, 0.8).expect("field");
        for n in [4usize, 8, 12] {
            let life = Life::spawn_even(world, field.clone(), n, 10.0, 0.0,
                                        Policy::Stay, 1, 100000)
                .expect("population");
            let cells: Vec<usize> = life.samples().iter().map(|s| s.cell).collect();
            let want: Vec<usize> = (0..n).map(|i| i % 4).collect();
            assert_eq!(
                cells, want,
                "A_spawn_even_is_i_mod_cells: n = {} placed {:?}, not {:?}",
                n, cells, want
            );
        }

        // B. And the two layouts must actually differ, or the flag is inert and
        //    a run that says `even` cannot be told from one that does not.
        let even = Life::spawn_even(world, field.clone(), 8, 10.0, 0.0,
                                    Policy::Stay, 7, 100000)
            .expect("even population");
        let random = Life::spawn(world, field, 8, 10.0, 0.0,
                                 Policy::Stay, 7, 100000)
            .expect("random population");
        let even_cells: Vec<usize> = even.samples().iter().map(|s| s.cell).collect();
        let random_cells: Vec<usize> = random.samples().iter().map(|s| s.cell).collect();
        assert_ne!(
            even_cells, random_cells,
            "B_layouts_differ: --layout even and --layout random produced the              same placement {:?}, so the flag cannot be tested",
            even_cells
        );
    }

    #[test]
    fn empty_population_is_refused() {
        let world = World::default();
        let field = Field::new(10, 1.0, 0.1).unwrap();
        assert!(Life::new(world, field, vec![], Policy::Stay, 1, 100).is_none());
        assert!(Life::spawn(world, Field::new(10, 1.0, 0.1).unwrap(), 0, 5.0, 0.1, Policy::Stay, 1, 100).is_none());
    }

    #[test]
    fn the_cycle_advances_and_counts() {
        let mut life = setup(Policy::Stay);
        let censuses = life.run(100, 10);
        assert_eq!(censuses.len(), 10);
        assert_eq!(censuses[0].step, 10);
        assert_eq!(censuses[9].step, 100);
    }

    #[test]
    fn a_staying_policy_never_moves() {
        let mut life = setup(Policy::Stay);
        life.run(100, 100);
        assert_eq!(life.census().moves, 0);
    }

    #[test]
    fn a_random_policy_moves() {
        let mut life = setup(Policy::Random);
        life.run(100, 100);
        assert!(life.census().moves > 0, "random policy should move");
    }

    #[test]
    fn a_remembering_policy_moves() {
        let mut life = setup(Policy::Remember);
        life.run(100, 100);
        assert!(life.census().moves > 0, "remembering policy should move");
    }

    #[test]
    fn organisms_die_without_resources() {
        let world = World {
            income: 0.0,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 0,
        };
        // A field with the smallest legal resource, and income = 0: nothing can be
        // taken, so nothing can be earned. `Field::new` refuses a zero maximum, so
        // the field is not empty -- the *income* is what is zero.
        let field = Field::new(10, 0.01, 0.0).unwrap();
        let mut life = Life::spawn(world, field, 10, 1.0, 0.1, Policy::Stay, 1, 100).unwrap();
        life.run(100, 100);
        assert_eq!(life.census().alive, 0, "all should die without resources");
    }

    #[test]
    fn a_sighted_policy_climbs_the_gradient() {
        // A gradient rises left to right, so a sighted organism steps right on
        // every step, one cell per step. `stay` is the control: it cannot climb.
        //
        // The gradient used to be erased in 9 steps, which is why this test only
        // ran 8. That was a bug in `regrow_all` (see
        // `docs/FINDING-alternating-field-collapses.md`); the gradient now
        // lasts, so the climb can be measured over a long run.
        //
        // `read_budget` is 2, not 0: seeing is a read, and a read budget of 0
        // means the organism cannot see at all. That is the EXP-30 split
        // (`docs/FINDING-reading-is-not-eating.md`), and it is what makes this
        // test a test of sight rather than of a free look.
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 3,
        };
        let field = Field::gradient(40, 0.2, 2.0, 0.8).unwrap();
        let mut sighted = Life::new(
            world,
            field.clone(),
            vec![Remembering::new(Organism::healthy(5.0).unwrap(), 0, 0.0, 0.1, 300).unwrap()],
            Policy::Sighted,
            7,
            300,
        )
        .unwrap();
        sighted.run(8, 8);
        let s = sighted.samples();
        eprintln!(
            "DBG alive={} cell={} energy={:.4} cells={} f0={:.4} f1={:.4}",
            s[0].alive,
            s[0].cell,
            s[0].energy,
            sighted.field().cells(),
            sighted.field().level(0),
            sighted.field().level(1)
        );
        assert!(s[0].alive, "the sighted organism should survive 8 steps");
        assert_eq!(
            s[0].cell, 8,
            "a sighted organism should climb one cell per step, ended at {}",
            s[0].cell
        );

        let mut staying = Life::new(
            world,
            field,
            vec![Remembering::new(Organism::healthy(5.0).unwrap(), 0, 0.0, 0.1, 300).unwrap()],
            Policy::Stay,
            7,
            300,
        )
        .unwrap();
        staying.run(8, 8);
        let t = staying.samples();
        assert_eq!(
            t[0].cell, 0,
            "a staying organism cannot climb, ended at {}",
            t[0].cell
        );
    }

    #[test]
    fn a_gradient_is_not_erased() {
        // This test used to assert the opposite: that the gradient is erased in
        // nine steps. It was true, and it was a bug. `regrow_all` pulled every
        // cell toward one `max_resource` (the highest cell), so the gradient
        // collapsed to a flat field. Now each cell regrows toward its own
        // ceiling, and the gradient is a lasting feature of the medium.
        // See `docs/FINDING-alternating-field-collapses.md`.
        let mut f = Field::gradient(40, 0.2, 2.0, 0.8).unwrap();
        for _ in 0..100 {
            f.regrow_all();
        }
        let spread = (0..40)
            .map(|c| f.level(c))
            .fold(f64::NEG_INFINITY, f64::max)
            - (0..40).map(|c| f.level(c)).fold(f64::INFINITY, f64::min);
        assert!(
            (spread - 1.8).abs() < 1e-12,
            "the gradient should keep its 1.8 span, got {spread}"
        );
    }

    #[test]
    fn a_sighted_policy_stays_put_in_a_uniform_field() {
        // Nothing to prefer: ties go to `0`. This is the control that separates
        // "climbs" from "moves for no reason".
        //
        // The organism must not eat, or the field stops being uniform: the field
        // regrows toward `max_resource`, so after one take the eater's own cell is
        // below its neighbours and the neighbours ARE richer (see
        // `any_take_opens_a_hole_and_the_hole_is_a_gradient`). So the income here
        // is zero and the field is never touched.
        let world = World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost: 1.5,
            damage_rate: 0.0,
            capacity: 10.0,
            // Two neighbours plus its own cell: a sighted organism must be
            // able to see all three to compare them.
            read_budget: 3,
        };
        let field = Field::new(40, 2.0, 0.8).unwrap();
        let mut life = Life::new(
            world,
            field,
            vec![Remembering::new(Organism::healthy(5.0).unwrap(), 20, 0.0, 0.1, 300).unwrap()],
            Policy::Sighted,
            7,
            300,
        )
        .unwrap();
        life.run(100, 100);
        assert_eq!(life.census().moves, 0, "a uniform field gives no reason to move");
        assert_eq!(life.samples()[0].cell, 20);
    }

    #[test]
    fn an_eating_sighted_organism_never_stands_still() {
        // The other half of the same fact: once the organism eats, its own cell is
        // the poorest of the three it can see, so it steps away on every step. It
        // is not "searching"; it is running from the hole it just made.
        //
        // What this does NOT prove: that this is bad. It is only a fact about the
        // medium. Whether the wandering costs more than it gains is measured, not
        // proved here.
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            // Two neighbours plus its own cell: a sighted organism must be
            // able to see all three to compare them.
            read_budget: 3,
        };
        let field = Field::new(40, 2.0, 0.8).unwrap();
        let mut life = Life::new(
            world,
            field,
            vec![Remembering::new(Organism::healthy(5.0).unwrap(), 20, 0.0, 0.1, 300).unwrap()],
            Policy::Sighted,
            7,
            300,
        )
        .unwrap();
        life.run(100, 100);
        let moves = life.census().moves;
        assert!(
            moves >= 99,
            "an eating sighted organism should step away almost every step, moved {moves} times"
        );
    }

    #[test]
    fn a_memory_policy_keeps_updating_its_memory() {
        // In a moving field the rich cell walks one step per cycle, so a memory
        // that observes every step must follow it. This is the difference between
        // `Memory` (updates always) and `Remember` (frozen once arrived).
        //
        // What this does NOT prove: that updating memory helps survival. Both
        // policies are measured in `checks/exp13_memory_vs_remember.py`; the
        // memory is only useful if the organism can act on it.
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            // A memory that cannot read a neighbour has nothing to remember.
            // Budget 3 = underfoot + both neighbours; at budget 0 the policy
            // never records a level and the test would measure the coin, not
            // the memory. See docs/FINDING-blind-memory-never-rests.md.
            read_budget: 3,
        };
        let field = Field::moving(40, 2.0, 0.2, 0.8, 1.0).unwrap();
        let mut memory =
            Life::spawn(world, field.clone(), 8, 5.0, 0.1, Policy::Memory, 3, 300).unwrap();
        memory.run(50, 50);
        let m = memory.samples();
        let distinct: std::collections::BTreeSet<usize> =
            m.iter().filter(|x| x.alive).map(|x| x.memory_cell).collect();
        assert!(
            distinct.len() > 1,
            "an updating memory should hold different cells, got {distinct:?}"
        );
        let _ = distinct;

        let mut remember =
            Life::spawn(world, field, 8, 5.0, 0.1, Policy::Remember, 3, 300).unwrap();
        remember.run(50, 50);
        let r = remember.samples();
        let distinct_frozen: std::collections::BTreeSet<usize> =
            r.iter().filter(|x| x.alive).map(|x| x.memory_cell).collect();
        assert!(
            distinct_frozen.len() <= distinct.len(),
            "a frozen memory should be at least as concentrated as an updating one \
             ({} vs {})",
            distinct_frozen.len(),
            distinct.len()
        );
    }

    #[test]
    fn the_census_is_taken_from_outside() {
        let life = setup(Policy::Stay);
        let c = life.census();
        assert_eq!(c.step, 0);
        assert_eq!(c.total, 40);
        assert_eq!(c.alive, 40);
    }
}
