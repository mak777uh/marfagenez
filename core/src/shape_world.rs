//! A population of forms under the shape economy: the smallest world in which a *shape* can
//! be selected for.
//!
//! `docs/DESIGN-structures.md` computed the economy; `FINDING-215` implemented the geometry;
//! `FINDING-216` added mutation and found that it ratchets upwards, so size has to be
//! regulated by the economy rather than by the mutation rate. This module is that economy
//! running as selection:
//!
//! ```text
//! each form holds energy
//! each step   energy += margin(form)          margin = sigma*p - mu*n - kappa*n^2/p
//! death       energy < 0
//! birth       energy >= birth_cost  ->  a copy, mutated, pays birth_cost
//! ```
//!
//! Nothing here touches `Life`. Every recorded run of the old model keeps its bits; this is a
//! second world in the same crate, and it is called that.

use crate::form::{Form, ShapeEconomy};
use crate::Rng;

/// One form and its accumulated margin.
#[derive(Debug, Clone, PartialEq)]
pub struct FormState {
    pub form: Form,
    pub energy: f64,
}

/// The prices and rates of the shape world.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ShapeRules {
    pub economy: ShapeEconomy,
    /// Energy needed before a form may spawn a mutated copy.
    pub birth_cost: f64,
    /// Chance that a newborn differs from its parent.
    pub mutation_rate: f64,
    /// Chance that a mutation adds rather than removes a cell.
    pub p_grow: f64,
    /// Largest population allowed.
    pub max_population: usize,
}

impl ShapeRules {
    pub fn new(economy: ShapeEconomy, birth_cost: f64) -> Option<Self> {
        if !(birth_cost.is_finite() && birth_cost > 0.0) {
            return None;
        }
        Some(Self {
            economy,
            birth_cost,
            mutation_rate: 1.0,
            p_grow: 0.5,
            max_population: 32,
        })
    }
}

/// A population of forms, each holding the margin it has earned.
#[derive(Debug, Clone)]
pub struct ShapeWorld {
    pub rules: ShapeRules,
    pub forms: Vec<FormState>,
    pub births: u64,
    pub deaths: u64,
    pub mutations: u64,
}

impl ShapeWorld {
    pub fn new(rules: ShapeRules, forms: Vec<Form>) -> Self {
        let state = forms
            .into_iter()
            .map(|form| FormState { form, energy: 0.0 })
            .collect();
        Self {
            rules,
            forms: state,
            births: 0,
            deaths: 0,
            mutations: 0,
        }
    }

    pub fn alive(&self) -> usize {
        self.forms.len()
    }

    /// Mean cells per boundary edge of the living forms.
    pub fn mean_x(&self) -> f64 {
        if self.forms.is_empty() {
            return 0.0;
        }
        self.forms.iter().map(|f| f.form.x()).sum::<f64>() / self.forms.len() as f64
    }

    /// Mean number of cells.
    pub fn mean_cells(&self) -> f64 {
        if self.forms.is_empty() {
            return 0.0;
        }
        self.forms.iter().map(|f| f.form.cells() as f64).sum::<f64>() / self.forms.len() as f64
    }

    /// One step: every form earns its margin, the insolvent die, the solvent may split.
    ///
    /// Births are collected before any newborn is added, so a form cannot give birth twice
    /// in one step and a newborn does not act in the step it was born in - the same rule the
    /// organism world uses, and for the same reason: otherwise one rich form fills the world
    /// in a single step.
    pub fn step(&mut self, rng: &mut Rng) {
        for f in self.forms.iter_mut() {
            f.energy += self.rules.economy.margin(&f.form);
        }

        let before = self.forms.len();
        self.forms.retain(|f| f.energy >= 0.0);
        self.deaths += (before - self.forms.len()) as u64;

        let mut parents: Vec<usize> = Vec::new();
        for (i, f) in self.forms.iter().enumerate() {
            if f.energy >= self.rules.birth_cost {
                parents.push(i);
            }
        }
        let room = self.rules.max_population.saturating_sub(self.forms.len());
        for i in parents.into_iter().take(room) {
            let child_form = {
                let parent = &self.forms[i];
                if rng.uniform() < self.rules.mutation_rate {
                    self.mutations += 1;
                    parent
                        .form
                        .mutate(rng, self.rules.p_grow)
                        .unwrap_or_else(|| parent.form.clone())
                } else {
                    parent.form.clone()
                }
            };
            if child_form.cells() == 0 {
                continue;
            }
            let child = FormState {
                form: child_form,
                energy: self.rules.birth_cost,
            };
            self.forms[i].energy -= self.rules.birth_cost;
            self.forms.push(child);
            self.births += 1;
        }
    }
}

/// Runs a population and returns the state after `steps`.
pub fn run(rules: ShapeRules, start: Vec<Form>, steps: usize, seed: u64) -> ShapeWorld {
    let mut rng = Rng::new(seed);
    let mut world = ShapeWorld::new(rules, start);
    for _ in 0..steps {
        world.step(&mut rng);
    }
    world
}

#[cfg(test)]
mod tests {
    use super::*;

    fn economy() -> ShapeEconomy {
        ShapeEconomy::new(2.0, 1.0, 0.1).expect("valid economy")
    }

    fn rules() -> ShapeRules {
        ShapeRules::new(economy(), 2.0).expect("valid rules")
    }

    #[test]
    fn a_form_that_cannot_pay_its_way_dies() {
        // a solid 9x9 square has x = 2.25, margin < 0, so its energy falls and it dies
        let mut rng = Rng::new(1);
        let mut world = ShapeWorld::new(rules(), vec![Form::square(9)]);
        assert!(!economy().survives(&Form::square(9)), "the premise of the test");
        for _ in 0..3 {
            world.step(&mut rng);
        }
        assert_eq!(world.alive(), 0, "an insolvent form must die");
        assert_eq!(world.deaths, 1);
    }

    #[test]
    fn a_form_that_pays_lives_and_splits() {
        let mut rng = Rng::new(2);
        let mut world = ShapeWorld::new(rules(), vec![Form::square(3)]);
        for _ in 0..40 {
            world.step(&mut rng);
        }
        assert!(world.alive() >= 1, "a solvent form must persist");
        assert!(world.births >= 1, "and must give birth");
    }

    #[test]
    fn the_population_never_exceeds_the_cap() {
        let mut r = rules();
        r.max_population = 4;
        let mut rng = Rng::new(3);
        let start: Vec<Form> = (0..3).map(|_| Form::strip(6)).collect();
        let mut world = ShapeWorld::new(r, start);
        for _ in 0..200 {
            world.step(&mut rng);
            assert!(world.alive() <= 4, "population {} exceeded the cap", world.alive());
        }
    }

    #[test]
    fn a_newborn_acts_only_on_the_step_after_it_is_born() {
        let mut r = rules();
        r.max_population = 100;
        let mut rng = Rng::new(4);
        let mut world = ShapeWorld::new(r, vec![Form::square(3)]);
        let before = world.alive();
        world.step(&mut rng);
        // a single step can add newborns but they cannot themselves give birth in it
        assert!(world.alive() <= before * 2, "one step doubled the population twice over");
    }

    #[test]
    fn an_impossible_birth_cost_is_refused() {
        assert!(ShapeRules::new(economy(), 0.0).is_none());
        assert!(ShapeRules::new(economy(), -1.0).is_none());
        assert!(ShapeRules::new(economy(), f64::NAN).is_none());
    }
}
