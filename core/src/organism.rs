//! # A minimal organism
//!
//! Everything before this module was a **carrier of state**: a vector of numbers
//! moved by drift and noise. This module adds the first thing that makes it an
//! **organism**: it must maintain itself, and it can die.
//!
//! ## The three quantities
//!
//! From `docs/DEVELOPMENTAL_ENVIRONMENT.md`:
//!
//! | quantity | meaning |
//! |---|---|
//! | `energy` | the reserve that pays for maintenance |
//! | `damage` | accumulated harm, in `[0, 1]` |
//!
//! There used to be a third quantity, `structure`, documented as "the inner
//! organisation". It was defined as `1 - damage` and never changed by anything
//! else, so it carried no information: death by `structure <= 0` was the same
//! event as death by `damage >= 1`. It was removed (2026-11-14). The inner
//! organisation the goal asks about is not modelled yet; a derived number
//! standing in for it was worse than an honest absence.
//!
//! ## The processes
//!
//! Each step:
//!
//! 1. **Income**: resources are taken from the environment, up to what is available.
//! 2. **Maintenance**: staying alive costs energy.
//! 3. **Repair**: damage is reduced, and repair costs energy.
//! 4. **Damage**: harm accumulates from the environment.
//! 5. **Death**: if energy runs out, or damage reaches 1, the organism dies.
//!
//! ## What this module deliberately does not have
//!
//! No memory, no learning, no action, no interaction. Reproduction is not a
//! property of one organism: it is a population step in `life.rs`, switched by the
//! `World` birth fields (`birth_threshold`, `birth_cost`, `max_population`), and it
//! is off by default. See `docs/FINDING-153.md`.
//!
//! The rest is added one step at a time, so that it is possible to tell what
//! caused a result.
//!
//! ## The design rule
//!
//! An organism that cannot pay for maintenance **dies**. There is no free survival:
//! the earlier model let a point exist forever in a room, and that is exactly what
//! this module stops.

#![forbid(unsafe_code)]

/// A minimal organism: energy and damage.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Organism {
    energy: f64,
    damage: f64,
    alive: bool,
}

/// The parameters of the world. All are per step.
/// Who gets what when several organisms stand on one cell.
///
/// `Sequential` is the original protocol: organisms are stepped in
/// index order and each takes `min(income, what is left)`. The first
/// one on the cell eats first, so adding a `k`-th organism does not
/// touch the first `k-1`.
///
/// `Proportional` splits one `income` among all the organisms on the
/// cell at once: each gets `income / k`. Adding a `k`-th organism
/// dilutes everyone, which is what a softmax attention head does when
/// another key is inserted.
///
/// The two give different integer laws for how many organisms a cell
/// can hold on the SAME resource and the SAME eater. See
/// `checks/exp99_protocol_capacity.py`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShareProtocol {
    /// Index order, `min(income, rest)` each.
    Sequential,
    /// One `income` split evenly among everyone on the cell.
    Proportional,
}

impl Default for ShareProtocol {
    fn default() -> Self {
        Self::Sequential
    }
}

impl ShareProtocol {
    /// The name that goes into a trace and its hash.
    ///
    /// The protocol decides how many organisms a cell holds on the same
    /// resource, so a trace that does not record it cannot be compared to
    /// another trace. `Trace::hash_with_protocol` folds this string in.
    pub fn name(self) -> &'static str {
        match self {
            Self::Sequential => "sequential",
            Self::Proportional => "proportional",
        }
    }
}

/// What an organism does when its two neighbours are equally rich.
///
/// The rule `if left >= right { go left }` looks like a detail and is not: on
/// a uniform field every comparison is a tie, so the organism walks left
/// forever. That is a systematic drift produced by the tie-break, not by the
/// environment, and it was never written into a trace -- two runs that differ
/// only in this rule hash the same.
///
/// `Left` is the historical behaviour and stays the default, so no committed
/// number moves. `Random` draws from the organism's own stream, which makes
/// the drift measurable: on a uniform field the mean displacement should be
/// zero, and `Left` is the control that shows what a drift looks like.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TieBreak {
    /// Ties go left. Systematic drift on a symmetric field.
    Left,
    /// Ties go right. The mirror image, kept so `Left` can be checked
    /// against something that drifts the other way.
    Right,
    /// Ties are drawn from the stream. No drift expected.
    Random,
}

impl Default for TieBreak {
    fn default() -> Self {
        Self::Left
    }
}

impl TieBreak {
    /// The name that goes into a trace and its hash.
    pub fn name(self) -> &'static str {
        match self {
            Self::Left => "left",
            Self::Right => "right",
            Self::Random => "random",
        }
    }

    /// Resolves a tie: `-1` for left, `+1` for right.
    ///
    /// `rng` is only touched by `Random`; the deterministic rules must not
    /// consume from the stream, or turning the tie-break on would shift every
    /// other draw (movement, noise) and change runs that are supposed to be
    /// identical.
    pub fn pick(self, rng: &mut crate::Rng) -> i32 {
        match self {
            Self::Left => -1,
            Self::Right => 1,
            Self::Random => {
                if rng.uniform() < 0.5 {
                    -1
                } else {
                    1
                }
            }
        }
    }
}

/// Whether a `Memory` organism reads its cell before or after it eats.
///
/// This is not a detail of the code, it is a different model of perception, and
/// the two models disagree.
///
/// `LookThenEat` is what the code did before the parameter existed: the organism
/// observes the cell, remembers the level it saw, and then eats from the same
/// cell. The remembered level is therefore the level *before* this step's meal.
/// Two consequences, both measured rather than argued:
///
///   - On the cell it stands on, the memory records a level the organism has
///     already spent. A rich cell is remembered as richer than it now is.
///   - At the start the memory is empty (`best_level = 0.0`), so the first step
///     is always the random-explore branch, whatever the field looks like. The
///     asymmetry is in the starting condition, not in the rule.
///
/// `EatThenLook` reads the cell after the meal. The remembered level is what is
/// actually left, so "the remembered cell has gone poor" is detected a step
/// earlier and the numbers move.
///
/// Which one is right is not a matter of taste: an organism that can only see
/// what is left in front of it, and one that remembers what was there before it
/// ate, are different claims about the world. The default is the historical
/// behaviour so that no committed number moves, and the choice is recorded in
/// the trace and its hash so two arms cannot hide behind one hash.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LookOrder {
    /// Observe the cell, then eat from it. The historical behaviour.
    LookThenEat,
    /// Eat from the cell, then observe what is left.
    EatThenLook,
}

impl Default for LookOrder {
    fn default() -> Self {
        Self::LookThenEat
    }
}

impl LookOrder {
    /// The name that goes into a trace and its hash.
    pub fn name(self) -> &'static str {
        match self {
            Self::LookThenEat => "look-then-eat",
            Self::EatThenLook => "eat-then-look",
        }
    }
}

/// How an organism pays for repairing damage.
///
/// The rule lives here, not in [`World`], because it is a property of the
/// organism, not of the environment: two organisms in the same world may repair
/// differently, and the question "is one strategy better" only exists once this
/// is a choice. [`AllOrNothing`](RepairPolicy::AllOrNothing) is the historical
/// behaviour and the default, so every existing run and every recorded dynamics
/// hash stays where it was.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RepairPolicy {
    /// Never repair. Damage accumulates and the organism dies of it.
    None,
    /// Repair only when the reserve covers the whole damage. Below the
    /// threshold the damage survives the step.
    #[default]
    AllOrNothing,
    /// Repair as much as the reserve can buy, and spend the reserve on it.
    ///
    /// This is the strategy the all-or-nothing rule replaced. It was replaced
    /// because of a defect, and the defect is not the idea but the arithmetic:
    /// `repaired = energy / repair_cost` multiplied back can round above the
    /// reserve, so an organism that asked for a sliver of repair was charged
    /// everything, kept the damage and starved -- the worst of both. Here the
    /// charge is computed from the repaired amount and clamped, so the reserve
    /// never goes negative; the starvation is real and is the point, not a bug.
    Proportional,
}

impl RepairPolicy {
    /// The name that goes into a trace and its hash.
    pub fn name(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::AllOrNothing => "all-or-nothing",
            Self::Proportional => "proportional",
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct World {
    /// Energy gained per step when a resource is available.
    pub income: f64,
    /// Energy spent per step just to stay alive.
    pub maintenance_cost: f64,
    /// Energy spent per unit of damage repaired.
    pub repair_cost: f64,
    /// Damage added per step by the environment.
    pub damage_rate: f64,
    /// The most energy the organism can hold.
    pub capacity: f64,
    /// Who gets what when several organisms stand on one cell.
    pub share: ShareProtocol,
    /// How many **neighbour** cells an organism may read per step.
    ///
    /// `0` means no neighbour is read: the organism still knows the cell it
    /// stands on, because that is where it eats, but it cannot compare with
    /// either side. `1` buys one look, `3` buys both neighbours (reading a
    /// neighbour costs one read; the own cell costs nothing).
    ///
    /// Reading is free in energy: `Field::observe` does not subtract anything,
    /// so this is a *budget on perception*, not a price for it. A cost was
    /// never modelled, and any claim about memory replacing perception "by
    /// price" is stronger than the code - see `docs/REVIEW-emergence-notes-3.md`.
    pub read_budget: usize,
    /// Energy paid for every **neighbour** read; the own cell is free.
    ///
    /// `read_budget` is how many neighbours may be looked at per step; this is
    /// what each look costs. The cell the organism stands on is never charged:
    /// it already eats there, so knowing it is not perception.
    ///
    /// **The default `0.0` is a contract, not a placeholder.** Every run
    /// recorded before this field existed was produced with free reading, so a
    /// zero must not change one bit of the dynamics: `Organism::spend(0.0)`
    /// subtracts nothing and cannot fail, and the charge is skipped entirely at
    /// zero elsewhere. See `docs/FINDING-156.md` and
    /// `docs/REVIEW-emergence-notes-3.md` §1.3.
    ///
    /// A look the organism cannot afford is **not taken**: it does not borrow
    /// against the future and go into debt to see, it goes short-sighted. That
    /// is the modelling choice `Life::advance_with` makes explicit, and it is
    /// the only one that keeps the reserve a stock: an unpayable price is not a
    /// price, it is a forbidden action.
    ///
    /// `INFINITY` is accepted and means "no read is ever affordable", the same
    /// way `birth_threshold = INFINITY` means "never": it is the off position
    /// of a price that is always larger than any reachable reserve.
    pub read_cost: f64,
    /// How many steps pass between two samples of the world for a `Memory`
    /// organism. `1` means "look every step" and is the default, so a run
    /// recorded before the period existed is unchanged bit for bit.
    ///
    /// On the steps in between, a `Memory` organism reads nothing -- no own
    /// cell, no neighbours -- and pays neither a read nor `read_cost`; it acts
    /// on what it remembers. That is what makes "memory against perception" a
    /// trade-off with a price instead of two names for the same look.
    ///
    /// `Sighted` is deliberately NOT periodic: it has no memory to act on, so
    /// a skipped look would be blindness for a step, not a cheaper policy.
    /// `Remember` is not periodic either: it is a one-shot choice, not a slot.
    ///
    /// `0` is refused by `validate`: a period of zero is "never look", which is
    /// `read_budget = 0`, a different switch with a different meaning.
    pub read_period: usize,
    /// Whether a `Memory` organism may look at the world **out of turn**
    /// when the cell underfoot cannot pay the upkeep.
    ///
    /// The rule was declared in `docs/FINDING-161.md` before it existed:
    /// "look out of turn when the current cell holds less than the upkeep".
    /// The upkeep is `maintenance_cost + damage_rate * repair_cost` -- what
    /// one step costs before any income -- so a cell below it cannot feed the
    /// organism and a memory pointing there would stand until the next
    /// scheduled look, or until death. See `docs/FINDING-162.md`.
    ///
    /// **`false` is the contract, not a placeholder.** Every run recorded
    /// before the rule existed did not look out of turn, so the off position
    /// must not move one bit; the parameter is folded into the dynamics hash
    /// only when `true`, the same rule `read_cost > 0` and `read_period > 1`
    /// follow.
    pub look_on_shortfall: bool,
    /// What happens when both neighbours are equally rich. See [`TieBreak`].
    pub tiebreak: TieBreak,
    /// Whether a `Memory` organism reads its cell before or after eating.
    /// See [`LookOrder`].
    pub look_order: LookOrder,
    /// The energy a parent must hold for a birth to be allowed.
    ///
    /// **The default is `f64::INFINITY`, and it means "never".** It is not a
    /// large number: the cap keeps a reserve finite, so `energy >= INFINITY`
    /// is false for every state the model can reach and the birth branch
    /// cannot fire. A finite default would have been a silent change of the
    /// model, not a new parameter. `validate` therefore rejects `NaN` and
    /// negative values but accepts `INFINITY`: infinite is the "off" position.
    pub birth_threshold: f64,
    /// Energy the parent pays and the child receives.
    ///
    /// The transfer is exact -- the parent loses `birth_cost` and the child is
    /// born with exactly that -- so a birth moves energy and never creates it.
    pub birth_cost: f64,
    /// The most living organisms the population may reach. **`0` means no
    /// births at all**, and that is the default.
    ///
    /// The zero is a switch, not a cap of zero organisms: the model keeps its
    /// one-way feedback (death frees a share, nothing is added) unless a
    /// caller asks for the second arm explicitly. Being `usize`, it cannot be
    /// negative or non-numeric; there is nothing for `validate` to reject.
    pub max_population: usize,
}

impl Default for World {
    fn default() -> Self {
        Self {
            income: 1.0,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.01,
            capacity: 10.0,
            read_budget: 0,
            // Free reading is the contract: a run recorded before the price
            // existed must keep its numbers and its dynamics hash.
            read_cost: 0.0,
            // "Look every step" is the contract: a run recorded before the
            // period existed saw the world on every step.
            read_period: 1,
            // "Never look out of turn" is the contract for the same reason:
            // the rule is a declared policy, not a default.
            look_on_shortfall: false,
            share: ShareProtocol::Sequential,
            tiebreak: TieBreak::Left,
            look_order: LookOrder::LookThenEat,
            // The two defaults are the "off" positions, and they are the
            // contract, not a placeholder: a run recorded before these fields
            // existed must keep its numbers and its dynamics hash.
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0,
        }
    }
}

impl World {
    /// The longest accepted `read_period`. A period beyond this is not a
    /// sampling policy, it is a stopped clock; asking for it is a mistake
    /// worth failing on rather than simulating.
    pub const MAX_READ_PERIOD: usize = 1024;

    /// Whether income exceeds the maintenance cost.
    ///
    /// **This is necessary, not sufficient, for survival.** It was the whole
    /// answer once, and it is wrong: an organism also has to pay for repair.
    /// Use [`World::sustains`] for whether one step's surplus can pay for one
    /// step's repair; neither predicate is the boundary of life, and
    /// `docs/FINDING-148.md` measured what the boundary is.
    /// This one only says "the tank fills faster than it leaks".
    ///
    /// The name is kept because `docs/FINDING-094-settled-level-law.md` cites
    /// it as the settled-level condition, and that citation is about the tank,
    /// not about survival.
    ///
    /// This is a modelling statement, not an input check: an unviable world is
    /// well formed and may be exactly what an experiment wants to show. Use
    /// [`World::validate`] for the "are these numbers at all" question.
    pub fn is_viable(&self) -> bool {
        self.income > self.maintenance_cost
    }

    /// Whether one step's surplus can pay for one step's repair.
    ///
    /// This is the **per-step price** test, not the boundary of life.
    ///
    /// Damage grows by `damage_rate` every step, and repairing one step's
    /// damage costs `damage_rate * repair_cost`. If the step's surplus covers
    /// that price, the repair is affordable on every step, the damage never
    /// accumulates, and the damage cap is never reached. That is the whole of
    /// what this predicate asks.
    ///
    /// The step order in [`Organism::step`] is why `capacity` is deliberately
    /// not part of the condition: income arrives first (step 1), maintenance is
    /// paid (step 2), damage grows (step 3), repair is paid (step 4), and only
    /// then is the reserve capped (step 5). A world with
    /// `capacity < maintenance_cost` is survivable, because the income lands
    /// before the maintenance is deducted.
    ///
    /// **What it is not.** Measured in `docs/FINDING-148.md`:
    ///
    ///   - It is not the cadence condition of `docs/FINDING-145.md`
    ///     (`ceil(1/dr) * surplus >= repair_cost`). That formula charges the
    ///     whole `repair_cost` once per damage clock; 148 refuted it as a
    ///     boundary. It is neither necessary (a per-step payment of
    ///     `damage_rate * repair_cost` can be repeatable while
    ///     `repair_cost > ceil(1/dr) * surplus`) nor sufficient (`repair_cost`
    ///     above the largest reserve `capacity + surplus` can never be paid
    ///     once the payment is deferred).
    ///   - It is not the boundary of life. The criterion that survived 148 is
    ///
    ///     ```text
    ///     alive  <=>  dr*rc <= surplus
    ///              OR (rc <= K*surplus AND rc < capacity + surplus)
    ///     ```
    ///
    ///     where `K` is the model's damage clock -- the number of accumulated
    ///     `damage += dr` steps to the first `damage >= 1.0`, measured as the
    ///     lifetime of the `none` policy. This predicate is the first disjunct
    ///     of that criterion and nothing more.
    ///   - Returning `true` is sufficient for its own branch but not for life:
    ///     the branch's boundary is the equality `dr*rc == surplus`, where the
    ///     strict repair test `price < energy` (step 4) disagrees with the `>=`
    ///     used here. At `dr = 0.03`, `rc = 13.333333333333334`,
    ///     `capacity = 10` an organism starting from 0 holds exactly
    ///     `k*surplus` after `k` steps and is charged exactly that, so
    ///     `price < energy` is false on every step, the damage reaches `1.0`,
    ///     and it dies of damage while this predicate returns `true`.
    ///     `tests/sustainability.rs` pins that point, and pins the one from
    ///     148 (`dr = 0.03`, `rc = 13.466666666666669`, `energy0 = 5`), where
    ///     the cadence condition says "alive" and this predicate already says
    ///     "no".
    ///   - Returning `false` does not mean death: the deferred branch lives by
    ///     paying the whole `repair_cost` once per damage clock out of a
    ///     reserve of at most `capacity + surplus`. That is why the cap is the
    ///     second half of the measured criterion and not a constant -- the
    ///     reserve was tried, and it is not a dead end, it is one of the two
    ///     prices.
    ///
    /// Checked against the simulation on 768 parameter combinations
    /// (4 incomes x 4 maintenances x 4 repair costs x 4 damage rates x 3
    /// capacities, 500 steps each, starting full): zero disagreements. That
    /// grid stays inside the per-step branch or below the clock edge, which is
    /// why it could not see either limit above.
    ///
    /// The boundary itself is a floating-point question, not a mathematical
    /// one. The repair test in step 4 is `price < energy`, so at
    /// `dr*rc == surplus` the comparison is decided by the rounding accumulated
    /// over the previous steps and by `energy0`, and the same parameters can
    /// survive or die depending on the path. This predicate answers the
    /// mathematical question and uses `>=`; the simulation answers the
    /// floating-point one. They agree away from the three equalities
    /// (`dr*rc == surplus`, `rc == K*surplus`, `rc == capacity + surplus`), and
    /// `tests/sustainability.rs` pins the sides where they do.
    pub fn sustains(&self) -> bool {
        let surplus = self.income - self.maintenance_cost;
        let repair_price = self.damage_rate * self.repair_cost;
        surplus >= repair_price
    }

    /// Rejects parameters that make the arithmetic meaningless.
    ///
    /// `World` keeps `pub` fields, so nothing stops a caller from writing
    /// `maintenance_cost = NaN`. The arithmetic does not fail loudly on that:
    /// `energy -= NaN` makes the energy NaN, `NaN.min(capacity)` returns
    /// `capacity` because `f64::min` drops the NaN side, and the death test
    /// `energy <= 0.0` is then false. The result is an organism that survives
    /// on a full tank forever, paying nothing, with no error anywhere.
    ///
    /// The same shape of hole exists for `income = NaN` (`resource.min(NaN)`
    /// returns `resource`, so a cell is drained whole instead of at the income
    /// rate) and for negative costs (free survival by construction).
    ///
    /// Returns the name of the first bad field, so the caller can tell which
    /// one to fix.
    pub fn validate(&self) -> Result<(), String> {
        if !self.income.is_finite() || self.income < 0.0 {
            return Err(format!(
                "income must be finite and non-negative, got {}",
                self.income
            ));
        }
        if !self.maintenance_cost.is_finite() || self.maintenance_cost < 0.0 {
            return Err(format!(
                "maintenance_cost must be finite and non-negative, got {}",
                self.maintenance_cost
            ));
        }
        if !self.repair_cost.is_finite() || self.repair_cost < 0.0 {
            return Err(format!(
                "repair_cost must be finite and non-negative, got {}",
                self.repair_cost
            ));
        }
        if !self.damage_rate.is_finite() || self.damage_rate < 0.0 {
            return Err(format!(
                "damage_rate must be finite and non-negative, got {}",
                self.damage_rate
            ));
        }
        if !self.capacity.is_finite() || self.capacity <= 0.0 {
            return Err(format!(
                "capacity must be finite and positive, got {}",
                self.capacity
            ));
        }
        // `INFINITY` is the default and means "never", so the test here is
        // `NaN` plus a negative value, not `is_finite`. A finite threshold is a
        // real threshold; an infinite one is the switch in its off position.
        if self.birth_threshold.is_nan() || self.birth_threshold < 0.0 {
            return Err(format!(
                "birth_threshold must not be NaN or negative (INFINITY means never), got {}",
                self.birth_threshold
            ));
        }
        // `0.0` is the allowed default and means "free"; only nonsense is
        // rejected. `INFINITY` is let through on purpose, like
        // `birth_threshold`: it is the switch in its off position, a price no
        // reachable reserve can pay.
        if self.read_cost.is_nan() || self.read_cost < 0.0 {
            return Err(format!(
                "read_cost must not be NaN or negative (0.0 means free), got {}",
                self.read_cost
            ));
        }
        // `0` is not "never look": that switch is `read_budget = 0`, and it
        // means something else (the organism still sees its own cell). A
        // period of zero has no step to read on and would divide by zero.
        if self.read_period == 0 {
            return Err(
                "read_period must be at least 1 (0 is not a period; use read_budget = 0 to read nothing)"
                    .to_string(),
            );
        }
        if self.read_period > Self::MAX_READ_PERIOD {
            return Err(format!(
                "read_period must not exceed {} (a longer period is a stopped clock), got {}",
                Self::MAX_READ_PERIOD,
                self.read_period
            ));
        }
        if !self.birth_cost.is_finite() || self.birth_cost < 0.0 {
            return Err(format!(
                "birth_cost must be finite and non-negative, got {}",
                self.birth_cost
            ));
        }
        // `max_population` is a `usize`: it cannot be negative or NaN, so the
        // "reject nonsense" duty is structural and there is nothing to check.
        Ok(())
    }
}

impl Organism {
    /// Builds an organism. Returns `None` for values outside `[0, 1]` or a negative
    /// energy, because those states are meaningless.
    pub fn new(energy: f64, damage: f64) -> Option<Self> {
        if !energy.is_finite() || !damage.is_finite() {
            return None;
        }
        if !(0.0..=1.0).contains(&damage) {
            return None;
        }
        if energy < 0.0 {
            return None;
        }
        Some(Self {
            energy,
            damage,
            alive: true,
        })
    }

    /// A healthy organism with the given energy.
    pub fn healthy(energy: f64) -> Option<Self> {
        Self::new(energy, 0.0)
    }

    pub fn energy(&self) -> f64 {
        self.energy
    }

    pub fn damage(&self) -> f64 {
        self.damage
    }

    pub fn is_alive(&self) -> bool {
        self.alive
    }

    /// Spends energy on an action. Returns `false` if the organism cannot afford it,
    /// in which case nothing is changed.
    ///
    /// This is the hook a move uses: the walker calls it before taking the resource,
    /// so that a move costs energy directly rather than being hidden in the income.
    pub fn spend(&mut self, amount: f64) -> bool {
        if !amount.is_finite() || amount < 0.0 {
            return false;
        }
        if self.energy < amount {
            return false;
        }
        self.energy -= amount;
        true
    }

    /// One step of life.
    ///
    /// `resource` is how much energy is available in the environment this step. It
    /// may be less than `income`, and it may be zero.
    ///
    /// The capacity is applied at the **end** of the step, after every payment.
    /// Applying it right after the income used to erase the move cost: the walker
    /// spends energy before calling this, and a `min` applied before the step's
    /// own payments hands that energy straight back. See
    /// `docs/FINDING-the-cap-is-applied-after-the-spend.md`.
    ///
    /// Returns `true` if the organism is still alive after the step.
    pub fn step(&mut self, world: &World, resource: f64) -> bool {
        self.step_with(world, resource, RepairPolicy::AllOrNothing)
    }

    /// One step of life under an explicit repair strategy.
    ///
    /// [`step`](Self::step) is this with [`RepairPolicy::AllOrNothing`], which
    /// is what every recorded run used. The strategy is a parameter rather than
    /// a field so that a run that does not ask the question cannot change its
    /// answer by accident.
    pub fn step_with(
        &mut self,
        world: &World,
        resource: f64,
        repair: RepairPolicy,
    ) -> bool {
        if !self.alive {
            return false;
        }

        // 1. Income: take what is available, up to the income rate.
        let taken = resource.max(0.0).min(world.income);
        self.energy += taken;

        // 2. Maintenance: staying alive costs energy.
        self.energy -= world.maintenance_cost;

        // 3. Damage accumulates.
        self.damage = (self.damage + world.damage_rate).min(1.0);

        // 4. Repair, by the strategy the caller named.
        //
        // A repair happens only when the reserve covers the whole damage. The
        // earlier rule repaired as much as the reserve could buy, and that was
        // a trap: `repaired` came from `energy / repair_cost`, and multiplying
        // it back could round up to the whole reserve. An organism that asked
        // for a sliver of repair was then charged everything, kept the damage
        // and died of starvation -- the worst of both outcomes. Below the
        // threshold the organism cannot pay, so the damage survives the step.
        match repair {
            RepairPolicy::None => {}
            RepairPolicy::AllOrNothing => {
                if self.damage > 0.0 {
                    let price = self.damage * world.repair_cost;
                    if price < self.energy {
                        self.energy -= price;
                        self.damage = 0.0;
                    }
                }
            }
            RepairPolicy::Proportional => {
                if self.damage > 0.0 {
                    if world.repair_cost <= 0.0 {
                        // Free repair: the division below would be infinite and
                        // the charge zero. It does not need a reserve, which is
                        // why the guard on `energy` is below and not around the
                        // whole arm.
                        self.damage = 0.0;
                    } else if self.energy > 0.0 {
                        let affordable = self.energy / world.repair_cost;
                        let repaired = affordable.min(self.damage);
                        let cost = repaired * world.repair_cost;
                        // The product can land one ulp above the reserve. The
                        // clamp is not cosmetic: the earlier proportional rule
                        // died of exactly this rounding, and an invariant that
                        // holds only up to floating point is not an invariant.
                        self.energy = (self.energy - cost).max(0.0);
                        self.damage = (self.damage - repaired).max(0.0);
                    }
                }
            }
        }

        // 5. The cap is applied last, so that it limits what is held and not
        //    what is paid.
        self.energy = self.energy.min(world.capacity).max(0.0);

        // 6. Death: no energy, or full damage. There is no separate death by
        //    "lost structure" any more: that was `damage >= 1` under another
        //    name.
        if self.energy <= 0.0 || self.damage >= 1.0 {
            self.alive = false;
            self.energy = self.energy.max(0.0);
        }

        self.alive
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_values_are_refused() {
        assert!(Organism::new(1.0, -0.1).is_none());
        assert!(Organism::new(1.0, 1.1).is_none());
        assert!(Organism::new(-1.0, 0.0).is_none());
        assert!(Organism::new(1.0, f64::NAN).is_none());
        assert!(Organism::new(f64::NAN, 0.0).is_none());
        assert!(Organism::new(1.0, 0.0).is_some());
    }

    #[test]
    fn a_healthy_organism_survives_with_resources() {
        let world = World::default();
        let mut o = Organism::healthy(5.0).unwrap();
        for _ in 0..100 {
            assert!(o.step(&world, 1.0), "the organism should survive");
        }
        assert!(o.is_alive());
    }

    #[test]
    fn an_organism_dies_without_resources() {
        // This is the point of the module: no free survival.
        let world = World::default();
        let mut o = Organism::healthy(1.0).unwrap();
        let mut steps = 0;
        while o.step(&world, 0.0) {
            steps += 1;
            if steps > 1000 {
                panic!("the organism should have died without resources");
            }
        }
        assert!(!o.is_alive());
        // With energy 1.0 and maintenance 0.6, it dies after 2 steps.
        assert_eq!(steps, 1, "should die on the second step");
    }

    #[test]
    fn a_non_viable_world_kills_everyone() {
        // If the income is below the maintenance cost, nothing can live.
        let world = World {
            income: 0.5,
            maintenance_cost: 0.6,
            tiebreak: TieBreak::Left,
            ..Default::default()
        };
        assert!(!world.is_viable());
        let mut o = Organism::healthy(100.0).unwrap();
        let mut steps = 0;
        while o.step(&world, 1.0) {
            steps += 1;
            if steps > 10000 {
                panic!("a non-viable world should kill the organism");
            }
        }
        assert!(!o.is_alive());
    }

    #[test]
    fn a_viable_world_lets_it_live() {
        let world = World::default();
        assert!(world.is_viable());
        let mut o = Organism::healthy(1.0).unwrap();
        for _ in 0..1000 {
            o.step(&world, 1.0);
        }
        assert!(o.is_alive());
    }

    #[test]
    fn damage_accumulates() {
        // Repair is switched off by making it unaffordable: with any energy
        // left over, step 4 repairs the damage away before it can be read.
        // Damage only survives a step when the organism cannot pay to undo it.
        //
        // The step also kills at `energy <= 0`, so the organism starts with a
        // reserve. Nothing can spend it: maintenance is free, income is zero
        // and repair is unaffordable, so the reserve survives the step
        // untouched and only the damage moves.
        //
        // The price is above the reserve on purpose: repair is all or
        // nothing, so an unaffordable repair is skipped and the damage stays.
        // A cheap repair is covered by
        // `repair_undoes_damage_when_it_is_affordable` instead.
        let world = World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost: 1e9,
            damage_rate: 0.1,
            capacity: 10.0,
            read_budget: 0,
            share: Default::default(),
            tiebreak: TieBreak::Left,
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        let mut o = Organism::healthy(1.0).unwrap();
        let alive = o.step(&world, 0.0);
        assert!(alive);
        assert!((o.damage() - 0.1).abs() < 1e-12);
        assert!((o.energy() - 1.0).abs() < 1e-12);
        assert!(o.is_alive());
    }

    #[test]
    fn repair_undoes_damage_when_it_is_affordable() {
        // The counterpart of the test above: the same damage rate, but repair
        // is cheap, so the damage never survives the step.
        //
        // The reserve is two units, not one: the charge is `repaired *
        // repair_cost`, and with a one-unit reserve that product rounds up to
        // exactly the reserve, which kills the organism at `energy <= 0` even
        // though it is healthy. Two units leave room for the rounding.
        let world = World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost: 1.0,
            damage_rate: 0.1,
            capacity: 10.0,
            read_budget: 0,
            share: Default::default(),
            tiebreak: TieBreak::Left,
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        let mut o = Organism::healthy(2.0).unwrap();
        assert!(o.step(&world, 0.0));
        assert!(o.damage() < 1e-12, "damage was {}", o.damage());
        assert!((o.energy() - 1.9).abs() < 1e-12);
    }

    #[test]
    fn full_damage_kills() {
        let world = World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost: 1.0,
            damage_rate: 1.0,
            capacity: 10.0,
            read_budget: 0,
            share: Default::default(),
            tiebreak: TieBreak::Left,
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        let mut o = Organism::healthy(0.0).unwrap();
        assert!(!o.step(&world, 0.0));
        assert!(!o.is_alive());
    }

    #[test]
    fn a_dead_organism_stays_dead() {
        let world = World::default();
        let mut o = Organism::healthy(0.0).unwrap();
        o.step(&world, 0.0);
        assert!(!o.is_alive());
        // Further steps do nothing.
        assert!(!o.step(&world, 100.0));
        assert!(!o.is_alive());
    }

    #[test]
    fn spend_reduces_energy_or_refuses() {
        let mut o = Organism::healthy(1.0).unwrap();
        assert!(o.spend(0.3));
        assert!((o.energy() - 0.7).abs() < 1e-12);
        // Cannot afford more than there is.
        assert!(!o.spend(1.0));
        assert!((o.energy() - 0.7).abs() < 1e-12);
        // Invalid amounts are refused.
        assert!(!o.spend(-1.0));
        assert!(!o.spend(f64::NAN));
    }

    #[test]
    fn energy_is_capped() {
        let world = World {
            income: 100.0,
            maintenance_cost: 0.0,
            repair_cost: 1.0,
            damage_rate: 0.0,
            capacity: 5.0,
            read_budget: 0,
            share: Default::default(),
            tiebreak: TieBreak::Left,
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        let mut o = Organism::healthy(0.0).unwrap();
        o.step(&world, 100.0);
        assert!((o.energy() - 5.0).abs() < 1e-12);
    }
}

/// The repair strategies are a choice only if the choice is observable: each
/// test here fixes the world so that only the repair rule differs.
#[cfg(test)]
mod repair_policy_tests {
    use super::*;

    /// A world where nothing else happens: no income, no maintenance, no new
    /// damage, plenty of room. Only the repair rule can move a number.
    fn quiet_world(repair_cost: f64) -> World {
        World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost,
            damage_rate: 0.0,
            capacity: 1e9,
            ..World::default()
        }
    }

    #[test]
    fn none_never_repairs_and_never_charges() {
        let world = quiet_world(1.0);
        let mut o = Organism::new(10.0, 0.5).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::None);
        assert_eq!(o.damage(), 0.5, "damage must survive an organism that does not repair");
        assert_eq!(o.energy(), 10.0, "not repairing must cost nothing");
    }

    #[test]
    fn all_or_nothing_below_the_reserve_leaves_the_damage() {
        let world = quiet_world(100.0);
        let mut o = Organism::new(1.0, 0.5).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::AllOrNothing);
        assert_eq!(o.damage(), 0.5, "price 50 > reserve 1: the damage survives the step");
        assert_eq!(o.energy(), 1.0, "an unaffordable repair is not paid for");
    }

    #[test]
    fn all_or_nothing_above_the_reserve_clears_the_damage() {
        let world = quiet_world(1.0);
        let mut o = Organism::new(10.0, 0.5).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::AllOrNothing);
        assert_eq!(o.damage(), 0.0);
        assert!((o.energy() - 9.5).abs() < 1e-12, "price 0.5 was charged");
    }

    #[test]
    fn proportional_clears_damage_when_the_reserve_covers_it() {
        let world = quiet_world(1.0);
        let mut o = Organism::new(10.0, 0.5).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::Proportional);
        assert_eq!(o.damage(), 0.0);
        assert!((o.energy() - 9.5).abs() < 1e-12);
    }

    #[test]
    fn proportional_repairs_a_sliver_and_spends_the_reserve() {
        // The case that makes the strategy a strategy: the reserve buys part of
        // the damage, the organism spends it and keeps the rest of the damage.
        let world = quiet_world(100.0);
        let mut o = Organism::new(1.0, 0.5).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::Proportional);
        assert!(o.damage() < 0.5, "a sliver of the damage is repaired");
        assert_eq!(o.damage(), 0.49);
        assert!(o.energy() < 1e-12, "the reserve pays for it");
    }

    #[test]
    fn proportional_handles_free_repair() {
        let world = quiet_world(0.0);
        let mut o = Organism::new(0.0, 1.0).unwrap();
        o.step_with(&world, 0.0, RepairPolicy::Proportional);
        assert_eq!(o.damage(), 0.0, "free repair must not divide by zero");
    }

    #[test]
    fn proportional_never_overdraws_the_reserve() {
        // The invariant the earlier version of this rule broke: `repaired`
        // came from `energy / repair_cost` and multiplying it back could
        // round above the reserve, so the organism was charged more than it
        // had and went into the red.
        for &repair_cost in &[0.001, 0.1, 0.7, 1.5, 7.3, 1e6] {
            for &energy in &[1e-9, 0.1, 0.5, 1.0, 3.3, 100.0] {
                for &damage in &[1e-9, 0.001, 0.3, 0.5, 0.999, 1.0] {
                    let world = quiet_world(repair_cost);
                    let mut o = Organism::new(energy, damage).unwrap();
                    o.step_with(&world, 0.0, RepairPolicy::Proportional);
                    assert!(
                        o.energy() >= 0.0,
                        "energy went negative: cost {repair_cost} energy {energy} damage {damage} -> {}",
                        o.energy()
                    );
                    assert!(o.damage() >= 0.0, "damage went negative");
                    assert!(o.damage() <= 1.0, "damage above 1.0");
                }
            }
        }
    }

    #[test]
    fn step_is_the_all_or_nothing_strategy() {
        let world = World::default();
        for &energy in &[0.5, 2.0, 7.0] {
            for &damage in &[0.0, 0.25, 0.9] {
                let mut a = Organism::new(energy, damage).unwrap();
                let mut b = Organism::new(energy, damage).unwrap();
                a.step(&world, 1.0);
                b.step_with(&world, 1.0, RepairPolicy::AllOrNothing);
                assert_eq!(a.energy(), b.energy(), "step drifted from all-or-nothing");
                assert_eq!(a.damage(), b.damage());
                assert_eq!(a.is_alive(), b.is_alive());
            }
        }
    }

    #[test]
    fn names_are_distinct() {
        let names = [
            RepairPolicy::None.name(),
            RepairPolicy::AllOrNothing.name(),
            RepairPolicy::Proportional.name(),
        ];
        let mut sorted = names.to_vec();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.len(), names.len(), "two strategies share a name");
        assert_eq!(RepairPolicy::default(), RepairPolicy::AllOrNothing);
    }
}
