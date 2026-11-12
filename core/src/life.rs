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
}

impl Life {
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
        })
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

    /// Advances every living organism by one step.
    pub fn advance(&mut self) -> Option<()> {
        let cells = self.field.cells();
        for slot in self.organisms.iter_mut() {
            let Some(r) = slot.as_mut() else { continue };
            if !r.organism.is_alive() {
                continue;
            }

            // 1. See the current cell.
            let here = self.field.level(r.cell);

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
            // the memory and the organism can change its mind.
            let update_memory = match self.policy {
                Policy::Memory => true,
                _ => r.memory.best_cell != r.cell,
            };
            if update_memory {
                r.memory.observe(r.cell, here);
            }
            r.memory.decay(self.memory_life);

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
                    let left = if r.cell > 0 {
                        self.field.level(r.cell - 1)
                    } else {
                        f64::NEG_INFINITY
                    };
                    let right = if self.field.inside(r.cell + 1) {
                        self.field.level(r.cell + 1)
                    } else {
                        f64::NEG_INFINITY
                    };
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

            if direction != 0 && r.organism.spend(r.move_cost) {
                let nc = r.cell as i64 + direction as i64;
                if nc >= 0 && (nc as usize) < cells {
                    r.cell = nc as usize;
                    self.moves += 1;
                }
            }

            // 4. Take.
            let taken = self.field.take(r.cell, self.world.income);
            r.last_taken = taken;

            // 5. Live.
            r.organism.step(&self.world, taken);

            // 6. Death is handled inside `step`; nothing to do here.
        }

        // The field regrows once per step.
        self.field.regrow_all();
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
        for slot in self.organisms.iter() {
            match slot.as_ref() {
                Some(r) => out.push(crate::trace::Sample {
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
                }),
                None => out.push(crate::trace::Sample {
                    cell: 0,
                    energy: 0.0,
                    damage: 0.0,
                    alive: false,
                    memory_cell: 0,
                    memory_level: 0.0,
                    direction: 0,
                    taken: 0.0,
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
        };
        let field = Field::alternating(40, 2.0, 0.2, 0.8).unwrap();
        Life::spawn(world, field, 40, 5.0, 0.1, policy, 7, 300).unwrap()
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
        // The gradient itself is erased in 9 steps (see
        // `a_gradient_is_erased_within_ten_steps`), so the climb is measured over
        // the steps where the gradient still exists, not over a long run.
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
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
    fn a_gradient_is_erased_within_ten_steps() {
        // The field regrows toward `max_resource`, which is the HIGHEST cell of the
        // gradient, so a gradient is not a lasting feature of this medium: it is a
        // transient. Measured: after 9 steps every cell is at 2.0 (see the trace in
        // `docs/FINDING-gradient-is-transient.md`).
        //
        // This is why `sighted` cannot climb a gradient here: by the time it has
        // taken ten steps the gradient is gone. The test pins the fact, so nobody
        // reads `gradient` as a permanent landscape again.
        let mut f = Field::gradient(40, 0.2, 2.0, 0.8).unwrap();
        for _ in 0..9 {
            f.regrow_all();
        }
        let spread = (0..40)
            .map(|c| f.level(c))
            .fold(f64::NEG_INFINITY, f64::max)
            - (0..40).map(|c| f.level(c)).fold(f64::INFINITY, f64::min);
        // The spread is 0.2 * (1 - 0.8)^9 = 2.68e-7 times the 1.8 span, i.e.
        // 9.2e-7 in absolute terms. The gradient is gone to six digits.
        assert!(
            spread < 1e-5,
            "the gradient should be erased after 9 steps, spread {spread}"
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
