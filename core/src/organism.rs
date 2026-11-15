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
//! No memory, no learning, no action, no reproduction, no interaction. The plan says
//! to add them one at a time, so that it is possible to tell what caused a result.
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
    /// How many cells an organism may read per step. `0` means it sees only the
    /// cell it stands on, which is the old behaviour; `3` lets it compare its
    /// cell with its neighbours before deciding.
    /// Who gets what when several organisms stand on one cell.
    pub share: ShareProtocol,
    pub read_budget: usize,
    /// What happens when both neighbours are equally rich. See [`TieBreak`].
    pub tiebreak: TieBreak,
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
            share: ShareProtocol::Sequential,
            tiebreak: TieBreak::Left,
        }
    }
}

impl World {
    /// Whether income exceeds the maintenance cost.
    ///
    /// **This is necessary, not sufficient, for survival.** It was the whole
    /// answer once, and it is wrong: an organism also has to pay for repair.
    /// Use [`World::sustains`] for the question "can anything live here at all";
    /// this one only says "the tank fills faster than it leaks".
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

    /// Whether an organism can live here indefinitely, not just for a while.
    ///
    /// The step order in [`Organism::step`] decides this. Income arrives first
    /// (step 1), maintenance is paid (step 2), damage grows (step 3), and repair
    /// is paid (step 4) -- all before the capacity cap (step 5). So the cap does
    /// not decide survival: it trims what is *held* after every payment is made.
    /// A world with `capacity < maintenance_cost` is survivable, because the
    /// income lands before the maintenance is deducted.
    ///
    /// What does decide survival is whether one step's surplus can buy one
    /// step's repair. Damage grows by `damage_rate` every step; repairing it
    /// costs `damage_rate * repair_cost`. If the surplus is smaller, the damage
    /// is never repaired, it reaches `1.0`, and the organism dies of damage --
    /// while `is_viable()` keeps returning `true`.
    ///
    /// Checked against the simulation on 768 parameter combinations
    /// (4 incomes x 4 maintenances x 4 repair costs x 4 damage rates x 3
    /// capacities, 500 steps each, starting full): zero disagreements.
    ///
    /// The boundary itself is a floating-point question, not a mathematical
    /// one. The repair test in step 4 is `price < energy`, so at
    /// `surplus == repair price` the comparison is decided by the rounding
    /// accumulated over the previous steps, and the same parameters can survive
    /// or die depending on the path. This predicate answers the mathematical
    /// question and uses `>=`; the simulation answers the floating-point one.
    /// They agree away from the boundary, and `tests/sustainability.rs` pins
    /// the side where they do.
    ///
    /// `capacity` is deliberately not part of the condition: it sets how many
    /// steps of deficit can be absorbed, not whether there is a deficit.
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

        // 4. Repair: all or nothing.
        //
        // A repair happens only when the reserve covers the whole damage. The
        // earlier rule repaired as much as the reserve could buy, and that was
        // a trap: `repaired` came from `energy / repair_cost`, and multiplying
        // it back could round up to the whole reserve. An organism that asked
        // for a sliver of repair was then charged everything, kept the damage
        // and died of starvation -- the worst of both outcomes. Below the
        // threshold the organism cannot pay, so the damage survives the step.
        if self.damage > 0.0 {
            let price = self.damage * world.repair_cost;
            if price < self.energy {
                self.energy -= price;
                self.damage = 0.0;
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
        };
        let mut o = Organism::healthy(0.0).unwrap();
        o.step(&world, 100.0);
        assert!((o.energy() - 5.0).abs() < 1e-12);
    }
}
