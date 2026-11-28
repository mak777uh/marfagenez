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
//! ## Reproduction and inheritance
//!
//! **Reproduction is implemented and off by default.** Three `World` fields drive
//! it: `birth_threshold` (`INFINITY` = never), `birth_cost` (`0.0`) and
//! `max_population` (`0` = no births). See `docs/FINDING-153.md`.
//!
//! **What is inherited: the policy.** The child takes the parent's policy (not the
//! population's first one), `move_cost` and `memory_life`, with `damage = 0` and an empty
//! memory; it starts with exactly `birth_cost` energy. `policy_mutation` (default `0.0`)
//! is the chance that the policy differs from the parent's; see `docs/FORMS-LINE-CLOSED.md`.
//!
//! **What is not inherited: the organisation.** There is no gene, no heritable variation of
//! structure, and the child starts on the parent's cell as a slot copy. A birth moves energy
//! between slots and does not pass an organisation to the next generation — that is the claim
//! `docs/FINDING-153.md` makes, and it is narrower than "no inheritance at all", which this
//! header used to say while the code copied the parent's policy (review 2026-11-21, §D3).
//!
//! Beyond sharing a cell's income, organisms do not interact.

#![forbid(unsafe_code)]

use crate::field::Field;
use crate::memory::Remembering;
use crate::organism::{LookOrder, Organism, RepairPolicy, ShareProtocol, World};

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

/// Iterator for the three visit-order protocols.
///
/// Historical and Rotate are arithmetic iterators and need no temporary Vec.
/// Random owns a Fisher-Yates permutation because preserving its draw and swap
/// order is part of the seeded trajectory contract.
enum VisitOrder {
    Direct { next: usize, end: usize },
    Rotate { next: usize, len: usize, shift: usize },
    Shuffled(std::vec::IntoIter<usize>),
}

impl Iterator for VisitOrder {
    type Item = usize;

    fn next(&mut self) -> Option<Self::Item> {
        match self {
            Self::Direct { next, end } => {
                if *next >= *end {
                    None
                } else {
                    let value = *next;
                    *next += 1;
                    Some(value)
                }
            }
            Self::Rotate { next, len, shift } => {
                if *next >= *len {
                    None
                } else {
                    let value = (*next + *shift) % *len;
                    *next += 1;
                    Some(value)
                }
            }
            Self::Shuffled(order) => order.next(),
        }
    }
}

/// A population of organisms in a field.
#[derive(Debug)]
pub struct Life {
    world: World,
    field: Field,
    organisms: Vec<Option<Remembering>>,
    policies: Vec<Policy>,
    rng: crate::Rng,
    step: usize,
    moves: u64,
    memory_life: usize,
    seed: u64,
    /// Ownership of cells, if the world has any.
    ///
    /// `None` is the off position and it is a contract, not a placeholder: no
    /// recorded run had ownership, so a `None` here must not change one bit of the
    /// dynamics. Claims are turned on explicitly with [`Life::enable_claims`].
    claims: Option<Claims>,
    /// In what order the organisms of a step are visited.
    ///
    /// `Historical` is the off position and the contract: every recorded run visited the slots in
    /// index order, so the default must not change one bit. The other two exist to measure how much
    /// of an observed advantage is the order rather than the organism (review 2026-11-21, §7).
    order: crate::organism::OrderProtocol,
    /// The chance that a newborn's **policy** differs from its parent's.
    ///
    /// `0.0` is the off position and the contract: every run recorded before this
    /// field existed had no variation, so a zero must not change one bit. With a
    /// positive rate the population carries a repertoire that can change, which is
    /// the one thing the forms line never had - five policies were fixed for the
    /// whole run, so no decision could be selected for. See
    /// `docs/FORMS-LINE-CLOSED.md`, requirement 2.
    ///
    /// It lives on `Life` rather than on `World` on purpose: adding a field to
    /// `World` breaks every struct literal in the tree, and this is a switch on the
    /// cycle, not a property of the medium.
    policy_mutation: f64,
    /// How far a `Sighted` organism looks.
    ///
    /// `0` and `1` mean the same thing and they are the contract: look at the two
    /// neighbours, exactly as every recorded run did. Anything larger makes the
    /// organism scan `[-k, k]` and step toward the best cell it can see.
    ///
    /// The calculation in `docs/DESIGN-perception.md` is what motivated this: with a
    /// one-neighbour rule the flat sea between rich patches is **silent** in 71% of
    /// cells - both neighbours are equal, so the rule cannot tell "toward the island"
    /// from "away from it" and wanders instead of searching. A window of radius half
    /// the spacing has a signal in every sea cell. No policy can search a medium that
    /// offers it no signal, so the medium has to be paired with a perception that can
    /// read it.
    sight_radius: usize,
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

    pub fn feed_enabled(&self) -> bool { self.feed }
    pub fn memory_life(&self) -> usize { self.memory_life }
    pub fn rng_state_words(&self) -> Vec<u64> { self.rng.state_words() }

    /// Per-slot movement price, memory lifetime and random-generator state.
    /// Dead/removed slots return None because the current model drops them.
    pub fn organism_parameters(&self) -> Vec<Option<(f64, usize)>> {
        self.organisms.iter().map(|slot| {
            slot.as_ref().map(|organism| (organism.move_cost, organism.memory_life))
        }).collect()
    }

    pub fn organism_rng_state_words(&self) -> Vec<Option<Vec<u64>>> {
        self.organisms.iter().map(|slot| {
            slot.as_ref().map(|organism| organism.rng.state_words())
        }).collect()
    }

    /// Version of the random source driving this cycle.
    pub fn rng_version(&self) -> crate::RngVersion {
        self.rng.version()
    }

    /// Builds a cycle. Returns `None` for an empty population or a field with no cells.
    ///
    /// Also returns `None` when `world` fails [`World::validate`]. Every
    /// constructor funnels through here, so this is the one place where a world
    /// starts driving a simulation. Without the check, `maintenance_cost = NaN`
    /// produces an organism that cannot die: the NaN is erased by `f64::min`,
    /// not propagated, and nothing reports it.
    pub fn new(
        world: World,
        field: Field,
        organisms: Vec<Remembering>,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        Self::new_with_rng_version(
            world, field, organisms, policy, seed, memory_life, crate::RngVersion::LcgV1
        )
    }

    pub fn new_with_rng_version(
        world: World,
        field: Field,
        organisms: Vec<Remembering>,
        policy: Policy,
        seed: u64,
        memory_life: usize,
        rng_version: crate::RngVersion,
    ) -> Option<Self> {
        let n_organisms = organisms.len();
        if organisms.is_empty() || field.cells() == 0 {
            return None;
        }
        if world.validate().is_err() {
            return None;
        }
        Some(Self {
            world,
            field,
            organisms: organisms.into_iter().map(Some).collect(),
            policies: vec![policy; n_organisms],
            rng: crate::Rng::with_version(seed, rng_version),
            step: 0,
            moves: 0,
            memory_life,
            seed,
            feed: false,
            claims: None,
            order: crate::organism::OrderProtocol::Historical,
            policy_mutation: 0.0,
            sight_radius: 0,
        })
    }

    /// Builds a cycle in which **each organism has its own policy**.
    ///
    /// `Life::new` gives every organism the same policy, which makes "two forms in
    /// one world" inexpressible: two `Life`s are not one world, because they do not
    /// share the field and so cannot compete for a cell. This is the constructor the
    /// two-form design in `docs/DESIGN-two-forms.md` needs.
    ///
    /// Returns `None` when the number of policies does not match the population.
    /// Silently padding or truncating the list would let a run that asks for two
    /// forms silently get one policy repeated, which is the class of error this
    /// project has paid for before.
    pub fn new_mixed(
        world: World,
        field: Field,
        organisms: Vec<Remembering>,
        policies: Vec<Policy>,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        Self::new_mixed_with_rng_version(
            world, field, organisms, policies, seed, memory_life, crate::RngVersion::LcgV1
        )
    }

    pub fn new_mixed_with_rng_version(
        world: World,
        field: Field,
        organisms: Vec<Remembering>,
        policies: Vec<Policy>,
        seed: u64,
        memory_life: usize,
        rng_version: crate::RngVersion,
    ) -> Option<Self> {
        if policies.len() != organisms.len() {
            return None;
        }
        let first = policies.first().copied()?;
        let mut life = Self::new_with_rng_version(
            world, field, organisms, first, seed, memory_life, rng_version
        )?;
        life.policies = policies;
        Some(life)
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
        Self::spawn_at_with_rng_version(
            world, field, cells, energy, move_cost, policy, seed, memory_life,
            crate::RngVersion::LcgV1
        )
    }

    pub fn spawn_at_with_rng_version(
        world: World,
        field: Field,
        cells: &[usize],
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
        rng_version: crate::RngVersion,
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
        Self::new_with_rng_version(world, field, pop, policy, seed, memory_life, rng_version)
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
        Self::spawn_even_with_rng_version(
            world, field, n, energy, move_cost, policy, seed, memory_life,
            crate::RngVersion::LcgV1
        )
    }

    pub fn spawn_even_with_rng_version(
        world: World,
        field: Field,
        n: usize,
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
        rng_version: crate::RngVersion,
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
        Self::new_with_rng_version(world, field, pop, policy, seed, memory_life, rng_version)
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
        Self::spawn_with_rng_version(
            world, field, n, energy, move_cost, policy, seed, memory_life,
            crate::RngVersion::LcgV1
        )
    }

    pub fn spawn_with_rng_version(
        world: World,
        field: Field,
        n: usize,
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
        rng_version: crate::RngVersion,
    ) -> Option<Self> {
        if n == 0 {
            return None;
        }
        let cells = field.cells();
        if cells == 0 {
            return None;
        }
        let mut rng = crate::Rng::with_version(seed ^ 0x5DEE_CE66_D1CE_4E5B, rng_version);
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
        Self::new_with_rng_version(world, field, pop, policy, seed, memory_life, rng_version)
    }

    pub fn step(&self) -> usize {
        self.step
    }

    pub fn field(&self) -> &Field {
        &self.field
    }

    pub fn policy(&self) -> Policy {
        self.policies.first().copied().unwrap_or(Policy::Stay)
    }

    /// The policy of **each** organism, in population order.
    ///
    /// With `Life::new` every entry is the same policy; with `new_mixed` they can
    /// differ, and this is how a caller checks which form it actually built.
    pub fn policies(&self) -> &[Policy] {
        &self.policies
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
    ///
    /// This is [`advance_with`](Self::advance_with) under
    /// [`RepairPolicy::AllOrNothing`], which is what every recorded run used,
    /// so the numbers and hashes of those runs do not move.
    pub fn advance(&mut self) -> Option<()> {
        self.advance_with(RepairPolicy::AllOrNothing)
    }

    /// Advances every living organism by one step under an explicit repair
    /// strategy.
    ///
    /// The strategy is a parameter rather than a field for the same reason it
    /// is one in [`Organism::step_with`]: a run that does not ask the question
    /// cannot change its answer by accident. Movement, eating, the field and
    /// the step order are untouched -- only step 5 (`repair`) reads `repair`.
    pub fn advance_with(&mut self, repair: RepairPolicy) -> Option<()> {
        let cells = self.field.cells();
        // The population may have grown in the previous step (births reuse dead
        // slots or push); keep one policy per organism so the loop below can
        // read `policies[i]`. A newborn takes the last stored policy, which for
        // the single-policy constructor is that same policy - so every run with
        // one policy for everybody keeps its bits exactly.
        if self.policies.len() < self.organisms.len() {
            let inherited = self.policies.last().copied().unwrap_or(Policy::Stay);
            self.policies.resize(self.organisms.len(), inherited);
        }
        if self.feed {
            self.field.regrow_all();
        }
        // `share_counts` is the number of organisms that have NOT yet eaten
        // on each cell. It starts as the crowd at the beginning of the step,
        // is kept current as organisms move, and drops by one each time an
        // organism eats. The proportional protocol hands out
        // `remaining / not_yet_eaten`, so the parts add up to one `income`.
        //
        // `share_left` is the part of one `income` still unclaimed on each
        // cell. The proportional protocol splits ONE `income` per cell among
        // everyone who eats there, so the budget has to be decremented as it
        // is claimed. Dividing `income` by the live crowd at the moment of
        // eating is not enough: an organism that eats before the crowd grows
        // takes `income / 1`, and the newcomer then takes `income / 2`, for
        // `1.5 * income` from one cell. See `tests/proportional_share.rs`.
        let proportional = self.world.share == ShareProtocol::Proportional;
        // The sequential protocol never consults either scratch array. Avoid
        // allocating O(cells) memory twice on every step in the default path.
        let mut share_counts = if proportional { vec![0usize; cells] } else { Vec::new() };
        let mut share_left = if proportional {
            vec![self.world.income; cells]
        } else {
            Vec::new()
        };
        if proportional {
            for slot in self.organisms.iter() {
                if let Some(r) = slot.as_ref() {
                    if r.organism.is_alive() && r.cell < cells {
                        share_counts[r.cell] += 1;
                    }
                }
            }
        }

        // The canonical policy vector was already padded above. Read one Copy
        // value before borrowing the corresponding organism mutably; cloning
        // the complete vector here created O(population) allocation/copy work
        // on every step for no semantic reason.
        let order = self.visit_order();
        let debug_memory = self.step < 4 && std::env::var("DBG_MEMORY").is_ok();
        for oi in order {
            let pol = self.policies.get(oi).copied().unwrap_or(Policy::Stay);
            let Some(r) = self.organisms.get_mut(oi).and_then(|slot| slot.as_mut()) else { continue };
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
                pol,
                Policy::Remember | Policy::Memory | Policy::Sighted
            );
            let mut reads_left = if looks { self.world.read_budget } else { 0 };
            // A `Memory` organism samples the world only every
            // `read_period`-th step; on the other steps it acts on what it
            // remembers (`direction()`) and pays neither a read nor its price.
            // `1` is "look every step" and is the default, so every run
            // recorded before the period existed is unchanged bit for bit.
            // `Sighted` is NOT gated: it has no memory to fall back on, so a
            // skipped look would be blindness, not economy. See its branch.
            let read_period = self.world.read_period.max(1);
            let due = pol != Policy::Memory || self.step % read_period == 0;
            // The exit rule declared in `docs/FINDING-161.md` **before** it
            // was implemented: "look out of turn when the current cell holds
            // less than the upkeep". The threshold is the upkeep and not a
            // tuned number, because the upkeep is exactly what one step
            // costs before any income:
            // `maintenance_cost + damage_rate * repair_cost`. A cell below
            // it cannot feed the organism; a memory pointing at such a cell
            // would stand there until the next scheduled look, or die.
            //
            // The own cell is read with `Field::level`, which is free: the
            // rule itself buys no look, it only allows one earlier than
            // `read_period` would. Off by default, so every recorded run
            // keeps its bits.
            let upkeep = self.world.maintenance_cost
                + self.world.damage_rate * self.world.repair_cost;
            let needs_look = pol == Policy::Memory
                && self.world.look_on_shortfall
                && self.field.level(r.cell) < upkeep;
            let sample = due || needs_look;
            // What one **neighbour** read costs. The own cell is free: the
            // organism already eats there, so knowing it is not perception.
            //
            // `read_cost == 0.0` is the default and the contract: every run
            // recorded before the price existed was free, so a zero must not
            // change one bit. `Organism::spend(0.0)` subtracts zero and cannot
            // fail, and the branch below tests it exactly as it tests the
            // budget -- no separate `if` that could reorder the reads.
            //
            // A look that cannot be paid for is **not taken**. Going short on
            // energy is a stock, not a promise: the organism does not go into
            // debt to see, it simply stops seeing the neighbour, exactly as if
            // the budget had run out. See `docs/FINDING-156.md`.
            let read_cost = self.world.read_cost;
            // `EatThenLook` defers the read of the standing cell until after
            // the meal (step 4), so that the level remembered is what is left
            // rather than what was there before the organism took its share.
            // It still costs one read from the budget -- the budget is about
            // how much the organism may look at, not about when.
            let look_after_eating = pol == Policy::Memory
                && self.world.look_order == LookOrder::EatThenLook;
            let here = if sample && reads_left > 0 && !look_after_eating {
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
            let update_memory = match pol {
                Policy::Memory => true,
                _ => r.memory.best_cell != r.cell,
            };
            if sample && update_memory {
                // `Memory` keeps the live level of the cell it stands on, so that
                // `direction()` can notice the remembered cell has gone poor.
                if pol == Policy::Memory && r.memory.best_cell == r.cell {
                    r.memory.best_level = here;
                    r.memory.age = 0;
                } else {
                    r.memory.observe(r.cell, here);
                }
            }
            r.memory.decay(self.memory_life);

            // A memory of a cell that is no longer worth going to is dropped.
            // Otherwise `direction()` keeps walking toward a cell that has dried up.
            if pol == Policy::Memory
                && sample
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
            if pol == Policy::Memory && sample {
                // Each neighbour read costs one from the budget, exactly as in
                // the `sighted` branch. It used to call `Field::level`, which
                // is a plain array read and does not touch `read_budget`, so
                // `--policy memory --read-budget 0` still saw both neighbours
                // and walked around a uniform field. See
                // `docs/FINDING-memory-sees-for-free.md`.
                let mut left = f64::NEG_INFINITY;
                let mut right = f64::NEG_INFINITY;
                // The cell that turned out to be the best SEEN, not just the direction
                // toward it. With the two-neighbour rule this is one of the neighbours and
                // the old code derived it from `step_dir`; with a window it can be several
                // cells away, and a memory that only stores a direction cannot walk to it.
                let mut seen_cell: Option<usize> = None;
                let mut seen_level = f64::NEG_INFINITY;
                if self.sight_radius > 1 {
                    // Window + memory: look at [-k, k], remember the best cell found. Without
                    // the memory half the information is used once and lost (`FINDING-230`).
                    for d in 1..=self.sight_radius {
                        if reads_left == 0 {
                            break;
                        }
                        for target in [
                            (r.cell as i64 - d as i64),
                            (r.cell as i64 + d as i64),
                        ] {
                            if target < 0 || target as usize >= cells {
                                continue;
                            }
                            if reads_left == 0 || !r.organism.spend(read_cost) {
                                break;
                            }
                            let level = self.field.observe(target as usize);
                            reads_left -= 1;
                            if level > seen_level && level > here {
                                seen_level = level;
                                seen_cell = Some(target as usize);
                            }
                        }
                    }
                } else {
                    if r.cell > 0 && reads_left > 0 && r.organism.spend(read_cost) {
                        left = self.field.observe(r.cell - 1);
                        reads_left -= 1;
                    }
                    if self.field.inside(r.cell + 1) && reads_left > 0 && r.organism.spend(read_cost) {
                        right = self.field.observe(r.cell + 1);
                        reads_left -= 1;
                    }
                }
                let best = here.max(left).max(right).max(seen_level);
                // A tie between the two neighbours used to go left always.
                // The rule is now a `World` parameter and goes into the trace.
                // See `TieBreak`.
                //
                // Reachability, measured on a uniform field, `--read-budget` 3,
                // 40 steps, seed 20250101 (left vs right arms):
                //   n=1, any start         -> SAME   (one organism always sees
                //                                      symmetric neighbours)
                //   n=2, 20,21 (symmetric) -> SAME
                //   n=2, 10,14 (asymmetric)-> DIFF
                //   n=6, 10,14,18,22,26,30 -> DIFF   (left -> 1,7,15,23,31,39;
                //                                      right -> 9,11,13,15,17,19)
                // So the branch fires whenever the local neighbourhood is
                // asymmetric, and it is the ASYMMETRY OF THE STARTING
                // CONFIGURATION that decides, not the population size. An
                // earlier single-organism measurement (0 calls to `pick`) held
                // only for that symmetric case and does not generalise.
                // The branch is reachable in `Sighted` too, where it mirrors
                // the trajectory (left ends at cell 8, right at cell 2).
                let step_dir = if left > right {
                    -1
                } else if right > left {
                    1
                } else {
                    self.world.tiebreak.pick(&mut self.rng) as i32
                };
                let target = if step_dir < 0 {
                    r.cell.wrapping_sub(1)
                } else {
                    r.cell + 1
                };
                // A neighbour is taken when it is strictly richer than the cell
                // the organism stands on. When it is exactly as rich, the choice
                // is a genuine tie and belongs to `TieBreak` -- otherwise the
                // gate above starves the tie-break: on a uniform field
                // `best == here` always, memory is never set, `direction()`
                // returns 0, and the parameter changes nothing but the hash.
                let take = best > here || (best == here && best > r.memory.best_level);
                if take && best > r.memory.best_level {
                    // With a window the remembered cell is the one actually seen; without
                    // one it is the neighbour the direction points at, exactly as before.
                    r.memory.best_cell = seen_cell.unwrap_or(target);
                    r.memory.best_level = best;
                    r.memory.age = 0;
                }
            }
            // Debug: DBG_MEMORY=1 prints the memory decision each step.
            if debug_memory {
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
            let direction = match pol {
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
                    // `read_period` deliberately does NOT gate this branch: a
                    // sighted organism has no memory, so skipping a look would
                    // not make it read less, it would make it blind for that
                    // step. That is a different policy, not a cheaper one, and
                    // pretending otherwise would put the period's effect in a
                    // branch that cannot carry it.
                    //
                    // Look at both neighbours and step toward the richer one.
                    // A tie goes to `0`: in a uniform field there is nothing to
                    // prefer, so a sighted organism stays put.
                    //
                    // "No neighbour" is `NEG_INFINITY`, not `0.0`: a level of
                    // `0.0` is a real, empty cell, and reading the outside as
                    // `0.0` made an organism at the edge see its own cell as the
                    // richest and step out of the field.
                    // Reading a neighbour costs one read from the budget. With
                    // `read_budget == 0` no neighbour is read, so the organism
                    // knows only the cell it stands on -- it does not go blind,
                    // it goes short-sighted, and "the richest cell I can see is
                    // the one under me" is then true by construction. This used
                    // to be phrased as "nothing is read and the organism cannot
                    // see"; the own cell was never a read.
                    // A window is used only when it is strictly wider than the
                    // two neighbours, so `k = 0` and `k = 1` run the original code
                    // and every recorded run keeps its bits. That is the control the
                    // design asks for, and it is enforced by construction rather
                    // than by testing.
                    if self.sight_radius > 1 {
                        let k = self.sight_radius;
                        let mut best_at: i32 = 0;
                        let mut best_level = here;
                        for d in 1..=k {
                            if reads_left == 0 {
                                break;
                            }
                            let mut scanned = 0;
                            for sign in [-1i32, 1i32] {
                                let target = r.cell as i32 + sign * d as i32;
                                if target < 0 || target as usize >= cells {
                                    continue;
                                }
                                if reads_left == 0 || !r.organism.spend(read_cost) {
                                    break;
                                }
                                let level = self.field.observe(target as usize);
                                reads_left -= 1;
                                scanned += 1;
                                if level > best_level {
                                    best_level = level;
                                    best_at = sign * d as i32;
                                }
                            }
                            if scanned == 0 {
                                break;
                            }
                        }
                        if best_at != 0 {
                            best_at.signum()
                        } else {
                            0
                        }
                    } else {
                    let mut left = f64::NEG_INFINITY;
                    let mut right = f64::NEG_INFINITY;
                    if r.cell > 0 && reads_left > 0 && r.organism.spend(read_cost) {
                        left = self.field.observe(r.cell - 1);
                        reads_left -= 1;
                    }
                    if self.field.inside(r.cell + 1)
                        && reads_left > 0
                        && r.organism.spend(read_cost)
                    {
                        right = self.field.observe(r.cell + 1);
                        reads_left -= 1;
                    }
                    let best = here.max(left).max(right);
                    if best > here {
                        if left > right {
                            -1
                        } else if right > left {
                            1
                        } else {
                            self.world.tiebreak.pick(&mut self.rng) as i32
                        }
                    } else {
                        0
                    }
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
                    if self.world.share == ShareProtocol::Proportional
                        && r.cell < cells
                        && share_counts[r.cell] > 0
                    {
                        share_counts[r.cell] -= 1;
                    }
                    r.cell = nc as usize;
                    if self.world.share == ShareProtocol::Proportional && r.cell < cells {
                        share_counts[r.cell] += 1;
                    }
                    self.moves += 1;
                }
            }

            // 4. Eat. Reading is separate: `read_budget > 0` lets the
            //    organism look at cells without emptying them, and what it
            //    reads is what it decides on. With `read_budget == 0` this is
            //    exactly the old `take`, so the trace must not change.
            let taken = match self.world.share {
                ShareProtocol::Sequential => {
                    self.field.take(r.cell, self.world.income)
                }
                ShareProtocol::Proportional => {
                    // Everyone eating on the cell splits ONE `income` among
                    // the organisms that have not yet eaten here, so
                    // `remaining / k` gives each of them an equal part of what
                    // is still unclaimed. With no movement this is exactly
                    // `income / k`. With movement it keeps the cell's total at
                    // or below `income` -- the structural difference from the
                    // sequential protocol, where the total is `k * income`.
                    //
                    // Both counters must move together: decrementing the
                    // budget alone would shrink every later share, and two
                    // organisms would get 0.5 and 0.25 instead of 0.5 and 0.5.
                    let k = share_counts.get(r.cell).copied().unwrap_or(0).max(1);
                    let remaining = share_left.get(r.cell).copied().unwrap_or(0.0);
                    let share = remaining / k as f64;
                    let got = self.field.take(r.cell, share);
                    if r.cell < cells {
                        share_left[r.cell] = (remaining - got).max(0.0);
                        share_counts[r.cell] = share_counts[r.cell].saturating_sub(1);
                    }
                    got
                }
            };
            // 4a. A stranger eats less on another form's cell until it overwrites
            //     it. This is the revenue side of ownership and the reason a place
            //     is worth holding at all: without it the field fed holder and
            //     stranger alike (`FINDING-199`).
            let taken = match self.claims.as_ref() {
                Some(claims) => match claims.owner_of(r.cell) {
                    Some(owner) if owner != oi => taken * claims.trespass,
                    _ => taken,
                },
                None => taken,
            };
            r.last_taken = taken;

            // 4b. `EatThenLook`: the read of the standing cell happens here, on
            //     what the meal left behind, and the memory is updated with it.
            //     The read is taken from the same budget as the one in step 1,
            //     so the two orders cost the same and cannot be told apart by
            //     the number of reads alone.
            if sample && look_after_eating && reads_left > 0 {
                reads_left -= 1;
                let after = self.field.observe(r.cell);
                if r.memory.best_cell == r.cell {
                    r.memory.best_level = after;
                    r.memory.age = 0;
                } else {
                    r.memory.observe(r.cell, after);
                }
            }

            // 5. Live, under the strategy the caller named.
            r.organism.step_with(&self.world, taken, repair);

            // 6. Death is handled inside `step`; nothing to do here.
        }

        // 7. Births. This is the second arm of the feedback that
        //    `docs/FINDING-152.md` measured only one direction of: a death
        //    frees a share, and nothing used to add one back.
        //
        //    The branch is off twice over by default -- `max_population == 0`
        //    (no births) and `birth_threshold == f64::INFINITY` (unreachable)
        //    -- so a run recorded before these fields existed is bit-for-bit
        //    unchanged. Those defaults are the contract, not a placeholder.
        //
        //    A parent pays `birth_cost` and the child receives exactly
        //    `birth_cost`, so the birth itself moves energy and never creates
        //    it. The child copies the parent's cell, the **parent's** policy
        //    (`self.policies[i]`, optionally mutated by `policy_mutation`),
        //    `move_cost` and `memory_life`; its damage is 0.0 and its memory is
        //    empty. It is a copy of a slot, not a descendant with a gene: the
        //    policy is inherited, the organisation is not. See
        //    `docs/FINDING-153.md`.
        //
        //    The parents are collected BEFORE any child is placed, so a
        //    newborn cannot give birth in the step it was born in: otherwise
        //    one rich organism would fill `max_population` in a single step,
        //    paying `birth_cost` through children that never lived a step.
        if self.world.max_population > 0 {
            let birth_cost = self.world.birth_cost;
            let threshold = self.world.birth_threshold;
            let mut alive = 0usize;
            let mut parents: Vec<usize> = Vec::new();
            for (i, slot) in self.organisms.iter().enumerate() {
                if let Some(r) = slot.as_ref() {
                    if r.organism.is_alive() {
                        alive += 1;
                        // `energy - birth_cost > 0.0` is the "the parent can
                        // pay and stay alive" test; `energy >= threshold` is
                        // the permission. Both are needed: a threshold below
                        // `birth_cost` must not let an organism breed itself
                        // to death.
                        if r.organism.energy() >= threshold
                            && r.organism.energy() - birth_cost > 0.0
                        {
                            parents.push(i);
                        }
                    }
                }
            }
            // Only as many births as the cap still allows. `saturating_sub`
            // because a world whose `max_population` is below the starting
            // population is legal and must not underflow into a huge budget.
            let budget = self.world.max_population.saturating_sub(alive);
            for i in parents.into_iter().take(budget) {
                let (cell, move_cost, memory_life) = match self.organisms.get(i).and_then(|s| s.as_ref()) {
                    Some(r) => (r.cell, r.move_cost, r.memory_life),
                    None => continue,
                };
                // The parent pays. The two tests above already guarantee that
                // `spend` can cover the charge, so a `false` here means the
                // slot changed underneath us and the birth is skipped.
                let paid = match self.organisms.get_mut(i).and_then(|s| s.as_mut()) {
                    Some(r) => r.organism.spend(birth_cost),
                    None => false,
                };
                if !paid {
                    continue;
                }
                let child = match Organism::healthy(birth_cost) {
                    Some(o) => o,
                    // Unreachable: `validate` keeps `birth_cost` finite and
                    // non-negative, and `Organism::healthy` accepts that.
                    None => continue,
                };
                let mut kid = match Remembering::new(child, cell, 0.0, move_cost, memory_life) {
                    Some(k) => k,
                    None => continue,
                };
                // An empty memory: the child knows nothing about the field.
                kid.memory.best_level = 0.0;
                // An EMPTY slot is reused first, then a slot whose organism is
                // dead -- a dead slot is a free slot with a headstone in it,
                // and filling it keeps the Vec from growing a graveyard beside
                // the living. Only when neither exists does the Vec grow.
                let empty = self.organisms.iter().position(|s| s.is_none());
                let dead = empty.or_else(|| {
                    self.organisms.iter().position(|s| {
                        s.as_ref().map_or(false, |r| !r.organism.is_alive())
                    })
                });
                // The child inherits the parent's policy; `policy_mutation` is the
                // chance that it does not. Without this the repertoire was fixed for
                // the whole run and nothing about a decision could be selected for.
                let mut child_policy = self.policies.get(i).copied().unwrap_or_else(|| self.policy());
                if self.policy_mutation > 0.0 && self.rng.uniform() < self.policy_mutation {
                    let u = self.rng.uniform();
                    child_policy = if u < 0.2 {
                        Policy::Stay
                    } else if u < 0.4 {
                        Policy::Random
                    } else if u < 0.6 {
                        Policy::Remember
                    } else if u < 0.8 {
                        Policy::Memory
                    } else {
                        Policy::Sighted
                    };
                }
                let slot = match dead {
                    Some(j) => {
                        self.organisms[j] = Some(kid);
                        j
                    }
                    None => {
                        let j = self.organisms.len();
                        self.organisms.push(Some(kid));
                        j
                    }
                };
                if self.policies.len() <= slot {
                    self.policies.resize(slot + 1, child_policy);
                }
                self.policies[slot] = child_policy;
            }
        }

        // Ownership ticks after everyone has acted, so a step is: what each form
        // did, then what that did to who holds what. Off unless claims exist.
        if let Some(claims) = self.claims.as_mut() {
            // Claim processing changes ownership and energy, not organism
            // presence/cell/death state. Reading each slot just before its own
            // update is equivalent to the old full presence snapshot, without
            // allocating one Option<usize> per organism each step.
            for i in 0..self.organisms.len() {
                let cell = self.organisms[i].as_ref()
                    .filter(|r| r.organism.is_alive())
                    .map(|r| r.cell);
                let Some(cell) = cell else { continue };
                if claims.owner[cell] == Some(i) {
                    claims.health[cell] = 1.0;
                    continue;
                }
                let price = claims.cost;
                let Some(r) = self.organisms[i].as_mut() else { continue };
                if price > 0.0 && !r.organism.spend(price) {
                    continue; // too poor to own: the cell keeps its holder
                }
                claims.take(cell, i);
            }
            claims.decay_all();
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
        match self.policy() {
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

    #[test]
    fn direct_and_rotated_visit_orders_match_the_legacy_sequences() {
        let direct = VisitOrder::Direct { next: 0, end: 5 }.collect::<Vec<_>>();
        assert_eq!(direct, vec![0, 1, 2, 3, 4]);

        let rotated = VisitOrder::Rotate { next: 0, len: 5, shift: 2 }
            .collect::<Vec<_>>();
        assert_eq!(rotated, vec![2, 3, 4, 0, 1]);

        let empty = VisitOrder::Rotate { next: 0, len: 0, shift: 0 }
            .collect::<Vec<_>>();
        assert!(empty.is_empty());
    }

    use super::*;
    use crate::organism::TieBreak;

    fn setup(policy: Policy) -> Life {
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 0,
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
    fn the_sample_reports_what_was_taken_not_what_was_asked_for() {
        // `Sample::taken` used to be recomputed at read time from the field
        // *after* the step, so it could disagree with what the organism got.
        // It now stores the value `field.take` returned. This test pins that:
        // ask for more than the cell holds and the sample must show the cell's
        // value, not the income.
        //
        // What this does NOT prove: that the stored value is used by any
        // policy. No policy reads `taken`; it is a reading only.
        let world = World {
            income: 5.0,          // ask for 5.0
            maintenance_cost: 0.0,
            repair_cost: 0.0,
            damage_rate: 0.0,
            capacity: 100.0,
            read_budget: 0,
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        // A flat field at 0.5: every cell holds far less than the income.
        let field = Field::new(8, 0.5, 1.0).unwrap();
        let mut life = Life::spawn(world, field, 1, 50.0, 0.0, Policy::Stay, 1, 300).unwrap();
        life.run(1, 1);
        let s = &life.samples()[0];
        assert!(
            (s.taken - 0.5).abs() < 1e-12,
            "the cell held 0.5, so the take is 0.5, not the income 5.0; got {}",
            s.taken
        );
        assert!(
            s.taken < 5.0,
            "a take equal to the income would mean the cap did not bite"
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
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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

/// Who holds which cell, and for how long.
///
/// The design in `docs/DESIGN-two-forms.md` asks for a place a form can **lose**.
/// Two things are needed for that and only one existed: a second form (which
/// `Life::new_mixed` provides) and a cell that remembers a holder (this).
///
/// The rule is deliberately the smallest one that makes loss possible:
///
/// * a form holds a cell by standing on it and paying `cost` for it;
/// * another form takes the cell **by overwriting** - presence is the only claim
///   the model has, so there is no separate act of stealing;
/// * a claim decays every step and is restored only by the holder being present, so
///   neglect loses the cell.
///
/// `cost = 0` and `decay = 0` make ownership costless and permanent, which is not a
/// useful world but a useful control.
#[derive(Debug, Clone)]
pub struct Claims {
    owner: Vec<Option<usize>>,
    health: Vec<f64>,
    cost: f64,
    decay: f64,
    /// What share of a cell's income a **stranger** gets while standing on it.
    ///
    /// This is the revenue side of ownership, and without it holding a place was a
    /// pure cost: `FINDING-199` measured a stayer living on one cell while a walker
    /// holding five died sooner, because the field did not know who stood on it.
    ///
    /// `1.0` is the off position and the default for `Claims::new`, so a world with
    /// ownership but no trespass behaves exactly like `FINDING-198`.
    trespass: f64,
    takes: u64,
    losses: u64,
}

impl Claims {
    /// An empty ownership map: nobody holds anything.
    pub fn new(cells: usize, cost: f64, decay: f64) -> Option<Self> {
        if cells == 0 || !cost.is_finite() || cost < 0.0 || !decay.is_finite() || decay < 0.0 {
            return None;
        }
        Some(Self {
            owner: vec![None; cells],
            health: vec![0.0; cells],
            cost,
            decay,
            trespass: 1.0,
            takes: 0,
            losses: 0,
        })
    }

    /// Puts `who` on `cell`, counting it as a take when the cell was held by
    /// somebody else, and as a loss for that somebody.
    fn take(&mut self, cell: usize, who: usize) {
        if let Some(prev) = self.owner[cell] {
            if prev != who {
                self.losses += 1;
            }
        }
        self.owner[cell] = Some(who);
        self.health[cell] = 1.0;
        self.takes += 1;
    }

    fn decay_all(&mut self) {
        if self.decay <= 0.0 {
            return;
        }
        for cell in 0..self.health.len() {
            if self.owner[cell].is_some() {
                self.health[cell] -= self.decay;
                if self.health[cell] <= 0.0 {
                    self.health[cell] = 0.0;
                    self.owner[cell] = None;
                    self.losses += 1;
                }
            }
        }
    }

    pub fn owner_of(&self, cell: usize) -> Option<usize> {
        self.owner.get(cell).copied().flatten()
    }

    pub fn cells(&self) -> usize { self.owner.len() }
    pub fn claim_cost(&self) -> f64 { self.cost }
    pub fn decay_rate(&self) -> f64 { self.decay }
    pub fn owners(&self) -> &[Option<usize>] { &self.owner }
    pub fn health(&self) -> &[f64] { &self.health }

    /// What share of a cell's income a stranger gets. `1.0` means "no trespass rule".
    pub fn trespass(&self) -> f64 {
        self.trespass
    }

    /// Sets the stranger's share; rejects anything outside `[0, 1]`.
    pub fn set_trespass(&mut self, share: f64) -> bool {
        if !share.is_finite() || !(0.0..=1.0).contains(&share) {
            return false;
        }
        self.trespass = share;
        true
    }

    pub fn health_of(&self, cell: usize) -> f64 {
        self.health.get(cell).copied().unwrap_or(0.0)
    }

    /// How many times a cell changed hands, and how many times a holder lost one.
    pub fn counts(&self) -> (u64, u64) {
        (self.takes, self.losses)
    }

    /// Cells held by each form.
    pub fn held_by(&self, who: usize) -> usize {
        self.owner.iter().filter(|o| **o == Some(who)).count()
    }
}

impl Life {
    /// Turns ownership on with a price per take and a decay per step.
    ///
    /// Returns `false` for invalid numbers. Off by default and never turned on by
    /// the single-policy constructor, so every recorded run keeps its bits.
    pub fn enable_claims(&mut self, cost: f64, decay: f64) -> bool {
        match Claims::new(self.field.cells(), cost, decay) {
            Some(c) => {
                self.claims = Some(c);
                true
            }
            None => false,
        }
    }

    pub fn claims(&self) -> Option<&Claims> {
        self.claims.as_ref()
    }

    /// Sets the chance that a newborn's policy differs from its parent's.
    ///
    /// Returns `false` for anything outside `[0, 1]`. Off by default.
    /// The order in which this step will visit the organisms.
    ///
    /// `Historical` returns `0..n`, which is what the loop did before the protocol existed. `Rotate`
    /// shifts by `step % n`; `Random` is one Fisher-Yates shuffle of `0..n` from the run's own rng.
    fn visit_order(&mut self) -> VisitOrder {
        let n = self.organisms.len();
        match self.order {
            crate::organism::OrderProtocol::Historical => VisitOrder::Direct {
                next: 0,
                end: n,
            },
            crate::organism::OrderProtocol::Rotate => VisitOrder::Rotate {
                next: 0,
                len: n,
                shift: if n == 0 { 0 } else { self.step % n },
            },
            crate::organism::OrderProtocol::Random => {
                let mut order: Vec<usize> = (0..n).collect();
                // Preserve the exact Fisher-Yates draws and swap order of the
                // previous implementation; only deterministic protocols bypass a Vec.
                for i in (1..n).rev() {
                    let j = (self.rng.uniform() * (i + 1) as f64) as usize % (i + 1);
                    order.swap(i, j);
                }
                VisitOrder::Shuffled(order.into_iter())
            }
        }
    }

    /// Chooses the visit order. `Historical` is the off position and reproduces recorded runs.
    pub fn set_order_protocol(&mut self, protocol: crate::organism::OrderProtocol) -> bool {
        self.order = protocol;
        true
    }

    /// The current visit order protocol.
    pub fn order_protocol(&self) -> crate::organism::OrderProtocol {
        self.order
    }

    pub fn set_policy_mutation(&mut self, rate: f64) -> bool {
        if !rate.is_finite() || !(0.0..=1.0).contains(&rate) {
            return false;
        }
        self.policy_mutation = rate;
        true
    }

    pub fn policy_mutation(&self) -> f64 {
        self.policy_mutation
    }

    /// Sets how far a `Sighted` organism looks. `0` and `1` are the original two
    /// neighbours; larger values scan `[-k, k]`.
    ///
    /// The radius costs `2k` reads per step out of `read_budget`, so a window wider
    /// than the budget is paid for by going short-sighted: the scan stops when the
    /// budget runs out, which is the same rule as every other price in this code.
    pub fn set_sight_radius(&mut self, radius: usize) -> bool {
        if radius > 64 {
            return false;
        }
        self.sight_radius = radius;
        true
    }

    pub fn sight_radius(&self) -> usize {
        self.sight_radius
    }

    /// How many organisms are alive right now.
    pub fn organisms_alive(&self) -> usize {
        self.organisms
            .iter()
            .filter(|s| matches!(s, Some(r) if r.organism.is_alive()))
            .count()
    }

    /// How the living policies are distributed: stay, random, remember, memory, sighted.
    pub fn policy_census(&self) -> [usize; 5] {
        let mut out = [0usize; 5];
        for (i, slot) in self.organisms.iter().enumerate() {
            if matches!(slot, Some(r) if r.organism.is_alive()) {
                let p = self.policies.get(i).copied().unwrap_or(Policy::Stay);
                let k = match p {
                    Policy::Stay => 0,
                    Policy::Random => 1,
                    Policy::Remember => 2,
                    Policy::Memory => 3,
                    Policy::Sighted => 4,
                };
                out[k] += 1;
            }
        }
        out
    }

    /// The claims, mutably, so a caller can set the trespass share and the price.
    pub fn claims_mut(&mut self) -> Option<&mut Claims> {
        self.claims.as_mut()
    }
}
