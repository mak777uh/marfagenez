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
//! | `structure` | the inner organisation, in `[0, 1]` |
//! | `energy` | the reserve that pays for maintenance |
//! | `damage` | accumulated harm, in `[0, 1]` |
//!
//! ## The processes
//!
//! Each step:
//!
//! 1. **Income**: resources are taken from the environment, up to what is available.
//! 2. **Maintenance**: keeping the structure alive costs energy.
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

/// A minimal organism: structure, energy, damage.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Organism {
    structure: f64,
    energy: f64,
    damage: f64,
    alive: bool,
}

/// The parameters of the world. All are per step.
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
    pub read_budget: usize,
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
        }
    }
}

impl World {
    /// Whether the world lets an organism survive at all: income must exceed the
    /// maintenance cost, or nothing can live.
    pub fn is_viable(&self) -> bool {
        self.income > self.maintenance_cost
    }
}

impl Organism {
    /// Builds an organism. Returns `None` for values outside `[0, 1]` or a negative
    /// energy, because those states are meaningless.
    pub fn new(structure: f64, energy: f64, damage: f64) -> Option<Self> {
        if !structure.is_finite() || !energy.is_finite() || !damage.is_finite() {
            return None;
        }
        if !(0.0..=1.0).contains(&structure) || !(0.0..=1.0).contains(&damage) {
            return None;
        }
        if energy < 0.0 {
            return None;
        }
        Some(Self {
            structure,
            energy,
            damage,
            alive: true,
        })
    }

    /// A healthy organism with the given energy.
    pub fn healthy(energy: f64) -> Option<Self> {
        Self::new(1.0, energy, 0.0)
    }

    pub fn structure(&self) -> f64 {
        self.structure
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

        // 4. Repair: if there is energy left, spend it on damage.
        if self.energy > 0.0 && self.damage > 0.0 {
            let affordable = self.energy / world.repair_cost;
            let repaired = affordable.min(self.damage);
            self.damage -= repaired;
            self.energy -= repaired * world.repair_cost;
        }

        // 5. The cap is applied last, so that it limits what is held and not
        //    what is paid.
        self.energy = self.energy.min(world.capacity).max(0.0);

        // 6. Structure erodes with damage: an organism at full damage has no
        // structure left.
        self.structure = (1.0 - self.damage).max(0.0);

        // 6. Death: no energy, or no structure.
        if self.energy <= 0.0 || self.structure <= 0.0 || self.damage >= 1.0 {
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
        assert!(Organism::new(-0.1, 1.0, 0.0).is_none());
        assert!(Organism::new(1.1, 1.0, 0.0).is_none());
        assert!(Organism::new(1.0, -1.0, 0.0).is_none());
        assert!(Organism::new(1.0, 1.0, f64::NAN).is_none());
        assert!(Organism::new(1.0, 1.0, 0.0).is_some());
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
    fn damage_reduces_structure() {
        let world = World {
            income: 0.0,
            maintenance_cost: 0.0,
            repair_cost: 1.0,
            damage_rate: 0.1,
            capacity: 10.0,
            read_budget: 0,
        };
        let mut o = Organism::healthy(0.0).unwrap();
        o.step(&world, 0.0);
        assert!((o.damage() - 0.1).abs() < 1e-12);
        assert!((o.structure() - 0.9).abs() < 1e-12);
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
        };
        let mut o = Organism::healthy(0.0).unwrap();
        o.step(&world, 100.0);
        assert!((o.energy() - 5.0).abs() < 1e-12);
    }
}
